from decimal import Decimal

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


class BaseCatalogo(TestCase):
    """Usuarios y datos base para todo el catálogo de productos (Sprint 2)."""

    def setUp(self):
        self.grupo_cajero = Group.objects.create(name="Cajero")
        self.grupo_admin = Group.objects.create(name="Administrador")

        self.cajero = User.objects.create_user(
            username="cajero_cat", password="claveSegura123"
        )
        self.cajero.groups.add(self.grupo_cajero)

        self.admin = User.objects.create_user(
            username="admin_cat", password="claveSegura123"
        )
        self.admin.groups.add(self.grupo_admin)

        self.categoria = Categoria.objects.create(nombre="Bebidas")
        self.producto = Producto.objects.create(
            nombre="Coca 500ml",
            descripcion="Gaseosa cola",
            codigo_barras="7790000000001",
            precio=Decimal("1500.00"),
            costo=Decimal("900.00"),
            stock=10,
            stock_minimo=5,
            categoria=self.categoria,
        )


class CatalogoAccesoTests(BaseCatalogo):
    """HU-02/HU-04: el catálogo es del administrador, el cajero no entra."""

    def test_anonimo_redirige_a_login(self):
        for nombre in ("ventas:lista_productos", "ventas:agregar_producto"):
            respuesta = self.client.get(reverse(nombre))
            self.assertEqual(respuesta.status_code, 302, nombre)
            self.assertIn("login", respuesta.url)

    def test_cajero_recibe_403_en_lista(self):
        self.client.login(username="cajero_cat", password="claveSegura123")
        respuesta = self.client.get(reverse("ventas:lista_productos"))
        self.assertEqual(respuesta.status_code, 403)

    def test_cajero_recibe_403_en_alta(self):
        self.client.login(username="cajero_cat", password="claveSegura123")
        respuesta = self.client.get(reverse("ventas:agregar_producto"))
        self.assertEqual(respuesta.status_code, 403)

    def test_cajero_recibe_403_en_edicion_y_baja(self):
        self.client.login(username="cajero_cat", password="claveSegura123")
        url_edicion = reverse("ventas:editar_producto", args=[self.producto.id])
        url_baja = reverse("ventas:eliminar_producto", args=[self.producto.id])
        self.assertEqual(self.client.get(url_edicion).status_code, 403)
        self.assertEqual(self.client.get(url_baja).status_code, 403)
        self.assertEqual(self.client.post(url_baja).status_code, 403)

    def test_admin_accede_a_todo(self):
        self.client.login(username="admin_cat", password="claveSegura123")
        self.assertEqual(
            self.client.get(reverse("ventas:lista_productos")).status_code, 200
        )
        self.assertEqual(
            self.client.get(reverse("ventas:agregar_producto")).status_code, 200
        )
        url_edicion = reverse("ventas:editar_producto", args=[self.producto.id])
        self.assertEqual(self.client.get(url_edicion).status_code, 200)

    def test_usa_los_templates_nuevos(self):
        self.client.login(username="admin_cat", password="claveSegura123")
        self.assertTemplateUsed(
            self.client.get(reverse("ventas:lista_productos")),
            "ventas/lista_productos.html",
        )
        self.assertTemplateUsed(
            self.client.get(reverse("ventas:agregar_producto")),
            "ventas/agregar_producto.html",
        )


class AltaProductoTests(BaseCatalogo):
    """HU-04: alta rápida con código de barras, costo, precio y stock."""

    def _datos(self, **extra):
        datos = {
            "nombre": "Agua Villavicencio 500ml",
            "codigo_barras": "7791111111111",
            "descripcion": "Agua mineral",
            "costo": "700.00",
            "precio": "1200.00",
            "stock": "20",
            "stock_minimo": "4",
            "categoria": str(self.categoria.id),
        }
        datos.update(extra)
        return datos

    def test_alta_crea_producto_con_costo_y_codigo(self):
        self.client.login(username="admin_cat", password="claveSegura123")
        respuesta = self.client.post(
            reverse("ventas:agregar_producto"), self._datos()
        )
        self.assertEqual(respuesta.status_code, 302)
        producto = Producto.objects.get(codigo_barras="7791111111111")
        self.assertEqual(producto.costo, Decimal("700.00"))
        self.assertEqual(producto.precio, Decimal("1200.00"))
        self.assertEqual(producto.stock, 20)
        self.assertEqual(producto.stock_minimo, 4)
        self.assertTrue(producto.activo)

    def test_codigo_de_barras_duplicado_no_se_crea(self):
        """CA de HU-04: si el código ya existe, error y no permite el duplicado."""
        self.client.login(username="admin_cat", password="claveSegura123")
        datos = self._datos(codigo_barras=self.producto.codigo_barras)
        respuesta = self.client.post(reverse("ventas:agregar_producto"), datos)
        self.assertEqual(respuesta.status_code, 200)
        self.assertFormError(
            respuesta.context["form"],
            "codigo_barras",
            "Ese código de barras ya está registrado en otro producto.",
        )
        self.assertEqual(
            Producto.objects.filter(codigo_barras="7790000000001").count(), 1
        )

    def test_precio_de_venta_cero_rechazado(self):
        self.client.login(username="admin_cat", password="claveSegura123")
        respuesta = self.client.post(
            reverse("ventas:agregar_producto"), self._datos(precio="0")
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("precio", respuesta.context["form"].errors)

    def test_categoria_nueva_se_crea_al_guardar(self):
        self.client.login(username="admin_cat", password="claveSegura123")
        datos = self._datos()
        datos["categoria"] = ""
        datos["nueva_categoria"] = "Snacks"
        self.client.post(reverse("ventas:agregar_producto"), datos)
        self.assertTrue(Categoria.objects.filter(nombre="Snacks").exists())


class EdicionYBajaTests(BaseCatalogo):
    """HU-04: modificaciones y bajas de productos."""

    def test_editar_modifica_precio_y_stock(self):
        self.client.login(username="admin_cat", password="claveSegura123")
        url = reverse("ventas:editar_producto", args=[self.producto.id])
        self.client.post(
            url,
            {
                "nombre": self.producto.nombre,
                "codigo_barras": self.producto.codigo_barras,
                "descripcion": "",
                "costo": "950.00",
                "precio": "1700.00",
                "stock": "3",
                "stock_minimo": "5",
                "categoria": str(self.categoria.id),
                "activo": "on",
            },
        )
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.precio, Decimal("1700.00"))
        self.assertEqual(self.producto.costo, Decimal("950.00"))
        self.assertEqual(self.producto.stock, 3)

    def test_editar_no_permite_codigo_duplicado_de_otro_producto(self):
        otro = Producto.objects.create(
            nombre="Pepsi 500ml",
            codigo_barras="7792222222222",
            precio=Decimal("1400.00"),
            costo=Decimal("850.00"),
            categoria=self.categoria,
        )
        self.client.login(username="admin_cat", password="claveSegura123")
        url = reverse("ventas:editar_producto", args=[otro.id])
        respuesta = self.client.post(
            url,
            {
                "nombre": otro.nombre,
                "codigo_barras": self.producto.codigo_barras,  # ya usado
                "descripcion": "",
                "costo": "850.00",
                "precio": "1400.00",
                "stock": "1",
                "stock_minimo": "5",
                "categoria": str(self.categoria.id),
                "activo": "on",
            },
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("codigo_barras", respuesta.context["form"].errors)

    def test_baja_logica_desactiva_el_producto(self):
        self.client.login(username="admin_cat", password="claveSegura123")
        url = reverse("ventas:eliminar_producto", args=[self.producto.id])

        confirmacion = self.client.get(url)
        self.assertEqual(confirmacion.status_code, 200)
        self.assertTemplateUsed(confirmacion, "ventas/eliminar_producto.html")

        respuesta = self.client.post(url)
        self.assertEqual(respuesta.status_code, 302)
        self.producto.refresh_from_db()
        self.assertFalse(self.producto.activo)


class BusquedaStockTests(BaseCatalogo):
    """HU-05 (búsqueda con HTMX) y HU-06 (alerta de stock bajo)."""

    def test_busqueda_por_nombre_filtra(self):
        self.client.login(username="admin_cat", password="claveSegura123")
        respuesta = self.client.get(
            reverse("ventas:lista_productos"), {"buscar": "Coca"}
        )
        nombres = [p.nombre for p in respuesta.context["productos"]]
        self.assertIn("Coca 500ml", nombres)
        self.assertEqual(len(nombres), 1)

    def test_busqueda_por_codigo_de_barras(self):
        self.client.login(username="admin_cat", password="claveSegura123")
        respuesta = self.client.get(
            reverse("ventas:lista_productos"), {"buscar": "7790000"}
        )
        self.assertEqual(len(respuesta.context["productos"]), 1)

    def test_con_htmx_devuelve_solo_el_partial(self):
        self.client.login(username="admin_cat", password="claveSegura123")
        respuesta = self.client.get(
            reverse("ventas:lista_productos"),
            {"buscar": "Coca"},
            HTTP_HX_REQUEST="true",
        )
        self.assertTemplateUsed(respuesta, "ventas/_productos_tabla.html")
        self.assertTemplateNotUsed(respuesta, "ventas/lista_productos.html")

    def test_stock_bajo_se_marca_cuando_llega_al_minimo(self):
        bajo = Producto.objects.create(
            nombre="Alfajor Triple",
            precio=Decimal("900.00"),
            costo=Decimal("500.00"),
            stock=3,
            stock_minimo=5,
            categoria=self.categoria,
        )
        self.assertTrue(bajo.stock_bajo)
        self.assertFalse(self.producto.stock_bajo)

    def test_template_marca_el_stock_bajo(self):
        Producto.objects.create(
            nombre="Alfajor Triple",
            precio=Decimal("900.00"),
            costo=Decimal("500.00"),
            stock=3,
            stock_minimo=5,
            categoria=self.categoria,
        )
        self.client.login(username="admin_cat", password="claveSegura123")
        respuesta = self.client.get(reverse("ventas:lista_productos"))
        self.assertContains(respuesta, "badge-stock-bajo")
