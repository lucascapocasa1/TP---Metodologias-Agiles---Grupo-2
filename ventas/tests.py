from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse


class PantallaCobroTests(TestCase):
    def setUp(self):
        self.grupo_cajero = Group.objects.create(name="Cajero")
        self.grupo_admin = Group.objects.create(name="Administrador")

        self.cajero = User.objects.create_user(
            username="cajero_test", password="claveSegura123"
        )
        self.cajero.groups.add(self.grupo_cajero)

        self.admin = User.objects.create_user(
            username="admin_test", password="claveSegura123", is_staff=True
        )
        self.admin.groups.add(self.grupo_admin)

    def test_acceso_requiere_login(self):
        respuesta = self.client.get(reverse("ventas:pantalla_cobro"))
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn("login", respuesta.url)

    def test_cajero_puede_acceder(self):
        self.client.login(username="cajero_test", password="claveSegura123")
        respuesta = self.client.get(reverse("ventas:pantalla_cobro"))
        self.assertEqual(respuesta.status_code, 200)

    def test_administrador_puede_acceder(self):
        self.client.login(username="admin_test", password="claveSegura123")
        respuesta = self.client.get(reverse("ventas:pantalla_cobro"))
        self.assertEqual(respuesta.status_code, 200)

    def test_usa_template_correcto(self):
        self.client.login(username="cajero_test", password="claveSegura123")
        respuesta = self.client.get(reverse("ventas:pantalla_cobro"))
        self.assertTemplateUsed(respuesta, "ventas/pantalla_cobro.html")
