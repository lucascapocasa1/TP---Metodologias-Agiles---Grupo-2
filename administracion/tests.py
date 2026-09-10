from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.urls import reverse


class DashboardTests(TestCase):
    def setUp(self):
        self.grupo_admin = Group.objects.create(name="Administrador")
        self.grupo_cajero = Group.objects.create(name="Cajero")

        self.admin = User.objects.create_user(
            username="admin_test", password="claveSegura123", is_staff=True
        )
        self.admin.groups.add(self.grupo_admin)

        self.cajero = User.objects.create_user(
            username="cajero_test", password="claveSegura123"
        )
        self.cajero.groups.add(self.grupo_cajero)

        self.superuser = User.objects.create_superuser(
            username="super_test", password="claveSegura123"
        )

    def test_acceso_requiere_login(self):
        respuesta = self.client.get(reverse("administracion:dashboard"))
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn("login", respuesta.url)

    def test_administrador_puede_acceder(self):
        self.client.login(username="admin_test", password="claveSegura123")
        respuesta = self.client.get(reverse("administracion:dashboard"))
        self.assertEqual(respuesta.status_code, 200)

    def test_cajero_recibe_403(self):
        self.client.login(username="cajero_test", password="claveSegura123")
        respuesta = self.client.get(reverse("administracion:dashboard"))
        self.assertEqual(respuesta.status_code, 403)

    def test_superuser_puede_acceder(self):
        self.client.login(username="super_test", password="claveSegura123")
        respuesta = self.client.get(reverse("administracion:dashboard"))
        self.assertEqual(respuesta.status_code, 200)

    def test_usa_template_correcto(self):
        self.client.login(username="admin_test", password="claveSegura123")
        respuesta = self.client.get(reverse("administracion:dashboard"))
        self.assertTemplateUsed(respuesta, "administracion/dashboard.html")

    def test_usuario_sin_grupo_recibe_403(self):
        user_sin_rol = User.objects.create_user(
            username="sin_rol", password="claveSegura123"
        )
        self.client.login(username="sin_rol", password="claveSegura123")
        respuesta = self.client.get(reverse("administracion:dashboard"))
        self.assertEqual(respuesta.status_code, 403)
