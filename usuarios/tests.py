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
