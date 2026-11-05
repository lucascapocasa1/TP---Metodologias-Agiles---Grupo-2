"""
Tests del Sprint 1.

Verifican el pedido puntual de la profesora/dueña del kiosco:
1) Se puede entrar con usuario y contraseña.
2) Un Cajero NO puede acceder a la parte de administración/precios (403).
3) Un Administrador SÍ puede acceder a todo (cobro + administración).
4) Un usuario anónimo (no logueado) es redirigido al login.
"""
from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse


class RolesYAccesoTests(TestCase):
    def setUp(self):
        self.grupo_admin = Group.objects.create(name="Administrador")
        self.grupo_cajero = Group.objects.create(name="Cajero")

        self.admin = User.objects.create_user(username="admin_test", password="claveSegura123")
        self.admin.groups.add(self.grupo_admin)

        self.cajero = User.objects.create_user(username="cajero_test", password="claveSegura123")
        self.cajero.groups.add(self.grupo_cajero)

    def test_login_exitoso_con_usuario_y_contrasena(self):
        """El sistema permite entrar con usuario y contraseña válidos."""
        respuesta = self.client.post(
            reverse("usuarios:login"),
            {"username": "cajero_test", "password": "claveSegura123"},
        )
        self.assertTrue(respuesta.wsgi_request.user.is_authenticated)

    def test_login_fallido_con_contrasena_incorrecta(self):
        respuesta = self.client.post(
            reverse("usuarios:login"),
            {"username": "cajero_test", "password": "claveIncorrecta"},
        )
        self.assertFalse(respuesta.wsgi_request.user.is_authenticated)

    def test_usuario_anonimo_no_puede_ver_pantalla_de_cobro(self):
        respuesta = self.client.get(reverse("ventas:pantalla_cobro"))
        self.assertEqual(respuesta.status_code, 302)  # redirige a login

    def test_cajero_puede_acceder_a_pantalla_de_cobro(self):
        self.client.login(username="cajero_test", password="claveSegura123")
        respuesta = self.client.get(reverse("ventas:pantalla_cobro"))
        self.assertEqual(respuesta.status_code, 200)

    def test_cajero_NO_puede_acceder_a_administracion(self):
        """Punto central del pedido: el cajero no debe poder tocar la
        parte de administración/precios."""
        self.client.login(username="cajero_test", password="claveSegura123")
        respuesta = self.client.get(reverse("administracion:dashboard"))
        self.assertEqual(respuesta.status_code, 403)

    def test_administrador_puede_acceder_a_administracion(self):
        self.client.login(username="admin_test", password="claveSegura123")
        respuesta = self.client.get(reverse("administracion:dashboard"))
        self.assertEqual(respuesta.status_code, 200)

    def test_administrador_tambien_puede_cobrar(self):
        """El dueño puede pararse a cobrar en el mostrador."""
        self.client.login(username="admin_test", password="claveSegura123")
        respuesta = self.client.get(reverse("ventas:pantalla_cobro"))
        self.assertEqual(respuesta.status_code, 200)

    def test_post_login_redirige_cajero_a_pantalla_de_cobro(self):
        self.client.login(username="cajero_test", password="claveSegura123")
        respuesta = self.client.get(reverse("usuarios:post_login"))
        self.assertRedirects(respuesta, reverse("ventas:pantalla_cobro"))

    def test_post_login_redirige_administrador_a_dashboard(self):
        self.client.login(username="admin_test", password="claveSegura123")
        respuesta = self.client.get(reverse("usuarios:post_login"))
        self.assertRedirects(respuesta, reverse("administracion:dashboard"))
import re
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from django.contrib.auth.models import User


class RecuperacionPasswordTests(TestCase):
    """Recuperar la contraseña por mail (HU de la cátedra, Resend en prod)."""

    def setUp(self):
        self.usuario = User.objects.create_user(
            username="vecino",
            password="claveVieja123",
            email="vecino@example.com",
        )

    def _pedir_enlace(self):
        respuesta = self.client.post(
            reverse("usuarios:password_reset"),
            {"email": "vecino@example.com"},
        )
        self.assertRedirects(respuesta, reverse("usuarios:password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        enlace = re.search(
            r"http://testserver(/usuarios/recuperar-password/[^\s\"<]+)",
            mail.outbox[0].body,
        )
        self.assertIsNotNone(enlace, "el mail no trae el enlace de recuperación")
        return enlace.group(1)

    def test_el_mail_trae_el_enlace_de_confirmacion(self):
        self.assertTrue(
            self._pedir_enlace().startswith("/usuarios/recuperar-password/")
        )

    def test_el_enlace_del_mail_permite_cambiar_la_contrasena(self):
        enlace = self._pedir_enlace()
        # Django redirige al formulario con el token guardado en la sesión.
        respuesta = self.client.get(enlace)
        self.assertEqual(respuesta.status_code, 302)
        formulario = self.client.get(respuesta["Location"])
        self.assertContains(formulario, "Nueva contraseña")
        respuesta = self.client.post(
            respuesta["Location"],
            {"new_password1": "claveNueva456", "new_password2": "claveNueva456"},
        )
        self.assertRedirects(
            respuesta, reverse("usuarios:password_reset_complete")
        )
        self.assertTrue(
            self.client.login(username="vecino", password="claveNueva456")
        )

    def test_un_enlace_invalido_no_rompe_la_pantalla(self):
        respuesta = self.client.get(
            reverse(
                "usuarios:password_reset_confirm",
                kwargs={"uidb64": "abc", "token": "token-invalido"},
            )
        )
        # Con un token inválido la vista responde directo (sin redirección).
        if respuesta.status_code == 302:
            respuesta = self.client.get(respuesta["Location"])
        self.assertContains(respuesta, "Enlace no válido")


class ResendEmailBackendTests(TestCase):
    """El backend de Resend tiene que mandar el HTML estilizado del mail."""

    def test_manda_el_html_adjunto_y_el_texto_plano(self):
        from unittest import mock

        from django.core.mail import EmailMultiAlternatives

        from usuarios.email_backend import ResendEmailBackend

        mensaje = EmailMultiAlternatives(
            subject="Asunto",
            body="texto plano",
            from_email="Norvex <no-reply@norvex.app>",
            to=["vecino@example.com"],
        )
        mensaje.attach_alternative("<p>hola</p>", "text/html")

        with mock.patch("usuarios.email_backend.resend.Emails.send") as enviar:
            enviados = ResendEmailBackend().send_messages([mensaje])

        self.assertEqual(enviados, 1)
        params = enviar.call_args[0][0]
        self.assertEqual(params["html"], "<p>hola</p>")
        self.assertEqual(params["text"], "texto plano")
