"""
Tests del Sprint 1.

Verifican el pedido puntual de la profesora/dueña del kiosco:
1) Se puede entrar con usuario y contraseña.
2) Un Cajero NO puede acceder a la parte de administración/precios (403).
3) Un Administrador SÍ puede acceder a todo (cobro + administración).
4) Un usuario anónimo (no logueado) es redirigido al login.
"""
from django.contrib.auth.models import Group, User
from django.core import mail
from django.test import TestCase, override_settings
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


MEMORIA_EMAIL = "django.core.mail.backends.locmem.EmailBackend"


@override_settings(
    EMAIL_BACKEND=MEMORIA_EMAIL,
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
)
class RecuperarClaveTests(TestCase):
    """Recuperación de acceso por email (usuario y contraseña)."""

    def setUp(self):
        self.grupo_admin = Group.objects.create(name="Administrador")
        self.usuario = User.objects.create_user(
            username="admin_test",
            password="claveSegura123",
            email="admin@kiosco.local",
        )
        self.usuario.groups.add(self.grupo_admin)

    def _link_del_email(self):
        """Saca el link de reseteo del cuerpo del email enviado."""
        cuerpo = mail.outbox[0].body
        for linea in cuerpo.splitlines():
            linea = linea.strip()
            if linea.startswith("http://") or linea.startswith("https://"):
                return linea
        self.fail("El email no contenía ningún link de recuperación")

    def test_formulario_de_recuperacion_se_muestra(self):
        respuesta = self.client.get(reverse("usuarios:recuperar_clave"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertTemplateUsed(respuesta, "usuarios/recuperar_clave.html")

    def test_envia_email_con_el_link(self):
        respuesta = self.client.post(
            reverse("usuarios:recuperar_clave"), {"email": "admin@kiosco.local"}
        )
        self.assertRedirects(respuesta, reverse("usuarios:recuperacion_enviada"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("admin@kiosco.local", mail.outbox[0].to)

    def test_email_desconocido_no_revela_que_no_existe(self):
        """Anti-enumeración: siempre se muestra la misma pantalla de éxito."""
        respuesta = self.client.post(
            reverse("usuarios:recuperar_clave"), {"email": "nadie@kiosco.local"}
        )
        self.assertRedirects(respuesta, reverse("usuarios:recuperacion_enviada"))
        self.assertEqual(len(mail.outbox), 0)

    def test_email_invalido_vuelve_al_formulario(self):
        respuesta = self.client.post(
            reverse("usuarios:recuperar_clave"), {"email": "esto-no-es-un-email"}
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertTemplateUsed(respuesta, "usuarios/recuperar_clave.html")
        self.assertTrue(respuesta.context["form"].errors)
        self.assertEqual(len(mail.outbox), 0)

    def test_flujo_completo_cambia_la_contrasena(self):
        """Pide el link, lo usa y después puede entrar con la clave nueva."""
        self.client.post(
            reverse("usuarios:recuperar_clave"), {"email": "admin@kiosco.local"}
        )
        link = self._link_del_email()
        ruta = link.split("testserver", 1)[1]

        # Django 6.1 redirige el link con token a uno sin token (para no
        # filtrarlo por el Referer), así que hay que seguir la redirección.
        respuesta = self.client.get(ruta, follow=True)
        self.assertEqual(respuesta.status_code, 200)
        self.assertTemplateUsed(respuesta, "usuarios/resetear_clave.html")
        self.assertTrue(respuesta.context["validlink"])
        ruta_limpia = respuesta.redirect_chain[-1][0]

        respuesta = self.client.post(
            ruta_limpia,
            {
                "new_password1": "claveNueva456",
                "new_password2": "claveNueva456",
            },
        )
        self.assertRedirects(respuesta, reverse("usuarios:recuperacion_completada"))

        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password("claveNueva456"))
        self.assertTrue(
            self.client.login(username="admin_test", password="claveNueva456")
        )

    def test_link_invalido_muestra_el_aviso(self):
        respuesta = self.client.get(
            reverse(
                "usuarios:resetear_clave",
                kwargs={
                    "uidb64": "dGVzdC1pbmZhbGlkbwo",
                    "token": "token-falso-123",
                },
            )
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertTemplateUsed(respuesta, "usuarios/resetear_clave.html")
        self.assertFalse(respuesta.context["validlink"])
