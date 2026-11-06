"""
Tests del Sprint 1.

Verifican el pedido puntual de la profesora/dueña del kiosco:
1) Se puede entrar con usuario y contraseña.
2) Un Cajero NO puede acceder a la parte de administración/precios (403).
3) Un Administrador SÍ puede acceder a todo (cobro + administración).
4) Un usuario anónimo (no logueado) es redirigido al login.
"""
import time

from django.conf import settings
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


class AccesoInvitadoTests(TestCase):
    """El comprador cualquiera llega al catálogo solo con la URL directa:
    la interfaz de invitado no ofrece ni enlaza el catálogo."""

    def test_login_no_ofrece_catalogo(self):
        respuesta = self.client.get(reverse("usuarios:login"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotContains(respuesta, "Ver catálogo sin registrarse")
        self.assertNotContains(respuesta, reverse("pedidos:catalogo"))

    def test_login_tiene_barra_de_invitado_sin_catalogo(self):
        """El anónimo ve la navbar mínima: solo link a Ingresar."""
        respuesta = self.client.get(reverse("usuarios:login"))
        self.assertContains(respuesta, "Ingresar")
        self.assertNotContains(respuesta, "Catálogo")
        self.assertNotContains(respuesta, reverse("pedidos:catalogo"))


class AccesoAdminDjangoTests(TestCase):
    """El panel /admin/ está oculto y pide doble candado.

    Lo controla usuarios.middleware.ControlAdminDjangoMiddleware:
    1) sin cuenta completa (anónimo, cajero, staff sin rol) la página
       responde 404, como si no existiera;
    2) el Administrador debe confirmar su contraseña en
       usuarios/confirmar-acceso-admin/ (candado con TTL por settings).
    """

    def setUp(self):
        self.grupo_admin = Group.objects.create(name="Administrador")
        self.grupo_cajero = Group.objects.create(name="Cajero")

        self.dueno = User.objects.create_user(
            username="dueno", password="claveSegura123", is_staff=True
        )
        self.dueno.groups.add(self.grupo_admin)

        self.cajero = User.objects.create_user(
            username="cajero_admin", password="claveSegura123"
        )
        self.cajero.groups.add(self.grupo_cajero)

        self.staff_sin_rol = User.objects.create_user(
            username="staff_sin_rol", password="claveSegura123", is_staff=True
        )

    def _loguear_dueno(self):
        self.client.login(username="dueno", password="claveSegura123")

    def _habilitar_candado(self):
        """Simula que el dueño ya confirmó su contraseña en esta sesión."""
        self._loguear_dueno()
        session = self.client.session
        session["admin_acceso_ts"] = time.time()
        session.save()

    # --- Candado 1: para los demás el panel no existe ---

    def test_anonimo_ve_404_en_admin(self):
        respuesta = self.client.get("/admin/")
        self.assertEqual(respuesta.status_code, 404)

    def test_anonimo_ve_404_en_el_login_de_django(self):
        respuesta = self.client.get("/admin/login/")
        self.assertEqual(respuesta.status_code, 404)

    def test_el_404_es_el_del_sistema_y_no_el_login_de_django(self):
        respuesta = self.client.get("/admin/")
        self.assertContains(respuesta, "Página no encontrada", status_code=404)
        self.assertNotContains(respuesta, "Iniciar sesión", status_code=404)

    def test_cajero_ve_404(self):
        self.client.login(username="cajero_admin", password="claveSegura123")
        self.assertEqual(self.client.get("/admin/").status_code, 404)

    def test_staff_sin_rol_ve_404(self):
        self.client.login(username="staff_sin_rol", password="claveSegura123")
        self.assertEqual(self.client.get("/admin/").status_code, 404)

    # --- Candado 2: confirmar contraseña ---

    def test_admin_sin_confirmar_va_al_candado(self):
        self._loguear_dueno()
        respuesta = self.client.get("/admin/")
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(
            reverse("usuarios:confirmar_acceso_admin"), respuesta["Location"]
        )
        self.assertIn("next=%2Fadmin%2F", respuesta["Location"])

    def test_admin_confirmado_entra_al_panel(self):
        self._habilitar_candado()
        self.assertEqual(self.client.get("/admin/").status_code, 200)

    def test_confirmar_con_password_correcta_habilita_el_panel(self):
        self._loguear_dueno()
        url = reverse("usuarios:confirmar_acceso_admin")
        respuesta = self.client.post(
            f"{url}?next=/admin/", {"password": "claveSegura123"}
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(respuesta["Location"], "/admin/")
        self.assertEqual(self.client.get("/admin/").status_code, 200)

    def test_confirmar_con_password_incorrecta_no_habilita(self):
        self._loguear_dueno()
        url = reverse("usuarios:confirmar_acceso_admin")
        respuesta = self.client.post(f"{url}?next=/admin/", {"password": "mala"})
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Contraseña incorrecta.")
        panel = self.client.get("/admin/")
        self.assertEqual(panel.status_code, 302)
        self.assertIn(reverse("usuarios:confirmar_acceso_admin"), panel["Location"])

    def test_next_invalido_no_redirige_fuera_del_admin(self):
        """El parámetro next solo puede apuntar a /admin/..."""
        self._loguear_dueno()
        url = reverse("usuarios:confirmar_acceso_admin")
        respuesta = self.client.post(
            f"{url}?next=https://ejemplo.com", {"password": "claveSegura123"}
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(respuesta["Location"], "/admin/")

    def test_pantalla_de_confirmacion_oculta_para_no_autorizados(self):
        url = reverse("usuarios:confirmar_acceso_admin")
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.login(username="cajero_admin", password="claveSegura123")
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_candado_vencido_vuelve_a_pedir_password(self):
        self._habilitar_candado()
        ttl = settings.ADMIN_CONFIRMACION_TTL_SEGUNDOS
        session = self.client.session
        session["admin_acceso_ts"] = time.time() - ttl - 1
        session.save()
        respuesta = self.client.get("/admin/")
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(
            reverse("usuarios:confirmar_acceso_admin"), respuesta["Location"]
        )

    def test_logout_pierde_el_candado(self):
        self._habilitar_candado()
        self.assertEqual(self.client.get("/admin/").status_code, 200)
        # LogoutView de Django solo acepta POST.
        self.client.post(reverse("usuarios:logout"))
        self.assertEqual(self.client.get("/admin/").status_code, 404)

    def test_re_loguearse_no_conserva_el_candado(self):
        self._habilitar_candado()
        self.client.post(reverse("usuarios:logout"))
        self.client.login(username="dueno", password="claveSegura123")
        respuesta = self.client.get("/admin/")
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(
            reverse("usuarios:confirmar_acceso_admin"), respuesta["Location"]
        )

    def test_login_con_next_de_admin_lleva_al_candado(self):
        respuesta = self.client.post(
            reverse("usuarios:login") + "?next=/admin/",
            {"username": "dueno", "password": "claveSegura123"},
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(respuesta["Location"], "/admin/")
        # Al seguir a /admin/ recién abierto aparece el candado.
        panel = self.client.get("/admin/")
        self.assertEqual(panel.status_code, 302)
        self.assertIn(
            reverse("usuarios:confirmar_acceso_admin"), panel["Location"]
        )

    def test_administrador_confirmado_que_pide_el_login_de_django_va_al_panel(self):
        self._habilitar_candado()
        self.assertRedirects(self.client.get("/admin/login/"), "/admin/")

    def test_el_dashboard_no_muestra_el_link_al_panel_de_django(self):
        """La tarjeta del panel de Django se quitó del dashboard."""
        self._loguear_dueno()
        respuesta = self.client.get(reverse("administracion:dashboard"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotContains(respuesta, 'href="/admin/')
