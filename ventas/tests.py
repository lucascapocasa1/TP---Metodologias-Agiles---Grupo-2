from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from .models import Categoria, Producto


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


class ProductosCRUDTests(TestCase):
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

        self.categoria = Categoria.objects.create(nombre="Bebidas")

    def test_lista_productos_requiere_login(self):
        respuesta = self.client.get(reverse("ventas:lista_productos"))
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn("login", respuesta.url)

    def test_cajero_no_puede_acceder_lista_productos(self):
        self.client.login(username="cajero_test", password="claveSegura123")
        respuesta = self.client.get(reverse("ventas:lista_productos"))
        self.assertEqual(respuesta.status_code, 403)

    def test_administrador_puede_acceder_lista_productos(self):
        self.client.login(username="admin_test", password="claveSegura123")
        respuesta = self.client.get(reverse("ventas:lista_productos"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertTemplateUsed(respuesta, "ventas/lista_productos.html")

    def test_agregar_producto_crea_registro(self):
        self.client.login(username="admin_test", password="claveSegura123")
        respuesta = self.client.post(
            reverse("ventas:agregar_producto"),
            {
                "nombre": "Coca Cola",
                "descripcion": "2.25L",
                "precio": "250.00",
                "stock": "10",
                "categoria": self.categoria.id,
            },
        )
        self.assertRedirects(respuesta, reverse("ventas:lista_productos"))
        self.assertTrue(Producto.objects.filter(nombre="Coca Cola").exists())

    def test_editar_producto_actualiza_datos(self):
        producto = Producto.objects.create(
            nombre="Pepsi",
            precio=200,
            stock=5,
            categoria=self.categoria,
        )
        self.client.login(username="admin_test", password="claveSegura123")
        respuesta = self.client.post(
            reverse("ventas:editar_producto", args=[producto.id]),
            {
                "nombre": "Pepsi 2.25L",
                "descripcion": "",
                "precio": "220.00",
                "stock": "15",
                "categoria": self.categoria.id,
            },
        )
        self.assertRedirects(respuesta, reverse("ventas:lista_productos"))
        producto.refresh_from_db()
        self.assertEqual(producto.nombre, "Pepsi 2.25L")
        self.assertEqual(float(producto.precio), 220.00)
        self.assertEqual(producto.stock, 15)

    def test_eliminar_producto(self):
        producto = Producto.objects.create(
            nombre="Sprite",
            precio=150,
            stock=3,
            categoria=self.categoria,
        )
        self.client.login(username="admin_test", password="claveSegura123")
        respuesta = self.client.post(reverse("ventas:eliminar_producto", args=[producto.id]))
        self.assertRedirects(respuesta, reverse("ventas:lista_productos"))
        self.assertFalse(Producto.objects.filter(nombre="Sprite").exists())

    def test_toggle_producto_cambia_estado(self):
        producto = Producto.objects.create(
            nombre="Fanta",
            precio=150,
            stock=3,
            categoria=self.categoria,
            activo=True,
        )
        self.client.login(username="admin_test", password="claveSegura123")
        respuesta = self.client.get(reverse("ventas:toggle_producto", args=[producto.id]))
        self.assertRedirects(respuesta, reverse("ventas:lista_productos"))
        producto.refresh_from_db()
        self.assertFalse(producto.activo)

