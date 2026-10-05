from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from auditoria.models import RegistroAuditoria

from .models import Categoria, DetalleVenta, Producto, Venta


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


class BaseCobro(TestCase):
    """Usuarios y catálogo base para el cobro (Sprint 3 - HU-07/08/09)."""

    def setUp(self):
        self.grupo_cajero = Group.objects.create(name="Cajero")
        self.grupo_admin = Group.objects.create(name="Administrador")

        self.cajero = User.objects.create_user(
            username="cajero_cobro", password="claveSegura123"
        )
        self.cajero.groups.add(self.grupo_cajero)

        self.admin = User.objects.create_user(
            username="admin_cobro", password="claveSegura123", is_staff=True
        )
        self.admin.groups.add(self.grupo_admin)

        self.categoria = Categoria.objects.create(nombre="Bebidas")
        self.producto = Producto.objects.create(
            nombre="Coca 500ml",
            codigo_barras="7790000000001",
            precio=Decimal("1500.00"),
            costo=Decimal("900.00"),
            stock=10,
            stock_minimo=5,
            categoria=self.categoria,
        )
        self.otro = Producto.objects.create(
            nombre="Agua Villavicencio 500ml",
            codigo_barras="7791111111111",
            precio=Decimal("1200.00"),
            costo=Decimal("700.00"),
            stock=8,
            stock_minimo=5,
            categoria=self.categoria,
        )

    def login_cajero(self):
        self.client.login(username="cajero_cobro", password="claveSegura123")

    def login_admin(self):
        self.client.login(username="admin_cobro", password="claveSegura123")

    def agregar(self, codigo, hx=False):
        kwargs = {"HTTP_HX_REQUEST": "true"} if hx else {}
        return self.client.post(
            reverse("ventas:cobro_agregar"), {"codigo": codigo}, **kwargs
        )

    def cambiar_cantidad(self, producto, accion, hx=True):
        kwargs = {"HTTP_HX_REQUEST": "true"} if hx else {}
        return self.client.post(
            reverse("ventas:cobro_cantidad"),
            {"producto_id": producto.pk, "accion": accion},
            **kwargs,
        )

    def confirmar(self, metodo="efectivo", monto="0.00"):
        return self.client.post(
            reverse("ventas:cobro_confirmar"),
            {"metodo_pago": metodo, "monto_entregado": monto},
        )

    def carrito(self):
        return self.client.session.get("carrito", [])


class CarritoTests(BaseCobro):
    """HU-07 (carga por código) y HU-08 (editar el carrito)."""

    def test_anonimo_redirige_a_login(self):
        for nombre in (
            "ventas:pantalla_cobro",
            "ventas:cobro_agregar",
            "ventas:cobro_cantidad",
            "ventas:cobro_confirmar",
        ):
            if nombre == "ventas:cobro_agregar":
                respuesta = self.client.post(reverse(nombre), {"codigo": "x"})
            elif nombre == "ventas:cobro_cantidad":
                respuesta = self.client.post(reverse(nombre), {})
            elif nombre == "ventas:cobro_confirmar":
                respuesta = self.client.post(reverse(nombre), {})
            else:
                respuesta = self.client.get(reverse(nombre))
            self.assertEqual(respuesta.status_code, 302, nombre)
            self.assertIn("login", respuesta.url)

    def test_agregar_por_codigo_de_barras(self):
        self.login_cajero()
        self.agregar("7790000000001")
        carrito = self.carrito()
        self.assertEqual(len(carrito), 1)
        self.assertEqual(carrito[0]["producto_id"], self.producto.pk)
        self.assertEqual(carrito[0]["cantidad"], 1)

    def test_agregar_por_nombre_unico(self):
        self.login_cajero()
        self.agregar("Villavicencio")
        self.assertEqual(self.carrito()[0]["producto_id"], self.otro.pk)

    def test_codigo_repetido_suma_cantidad_y_no_duplica_fila(self):
        """CA de HU-07: escanear dos veces el mismo producto suma la cantidad."""
        self.login_cajero()
        self.agregar("7790000000001")
        self.agregar("7790000000001")
        carrito = self.carrito()
        self.assertEqual(len(carrito), 1)
        self.assertEqual(carrito[0]["cantidad"], 2)

    def test_codigo_inexistente_muestra_error(self):
        self.login_cajero()
        respuesta = self.agregar("999", hx=True)
        self.assertContains(respuesta, "No encontré productos")
        self.assertEqual(self.carrito(), [])

    def test_nombre_ambiguo_pide_codigo_de_barras(self):
        self.login_cajero()
        respuesta = self.agregar("500ml", hx=True)
        self.assertContains(respuesta, "Varios productos coinciden")
        self.assertEqual(self.carrito(), [])

    def test_producto_dado_de_baja_no_se_agrega(self):
        self.producto.activo = False
        self.producto.save(update_fields=["activo"])
        self.login_cajero()
        respuesta = self.agregar("7790000000001", hx=True)
        self.assertContains(respuesta, "No encontré productos")
        self.assertEqual(self.carrito(), [])

    def test_con_htmx_devuelve_parcial(self):
        self.login_cajero()
        respuesta = self.agregar("7790000000001", hx=True)
        self.assertTemplateUsed(respuesta, "ventas/_carrito.html")
        self.assertTemplateNotUsed(respuesta, "ventas/pantalla_cobro.html")

    def test_sumar_y_restar_cantidad(self):
        """CA de HU-08: puedo cambiar cantidades antes de cobrar."""
        self.login_cajero()
        self.agregar("7790000000001")
        self.cambiar_cantidad(self.producto, "sumar")
        self.assertEqual(self.carrito()[0]["cantidad"], 2)
        self.cambiar_cantidad(self.producto, "restar")
        self.assertEqual(self.carrito()[0]["cantidad"], 1)

    def test_restar_hasta_cero_quita_el_item(self):
        self.login_cajero()
        self.agregar("7790000000001")
        self.cambiar_cantidad(self.producto, "restar")
        self.assertEqual(self.carrito(), [])

    def test_quitar_item_del_carrito(self):
        self.login_cajero()
        self.agregar("7790000000001")
        self.agregar("7791111111111")
        self.cambiar_cantidad(self.producto, "quitar")
        carrito = self.carrito()
        self.assertEqual(len(carrito), 1)
        self.assertEqual(carrito[0]["producto_id"], self.otro.pk)

    def test_pantalla_muestra_el_carrito(self):
        self.login_cajero()
        self.agregar("7790000000001")
        respuesta = self.client.get(reverse("ventas:pantalla_cobro"))
        self.assertContains(respuesta, "Coca 500ml")
        self.assertContains(respuesta, "$1.500")  # sin decimales, miles con punto

    def test_pantalla_sin_carrito_muestra_vacio(self):
        self.login_cajero()
        respuesta = self.client.get(reverse("ventas:pantalla_cobro"))
        self.assertContains(respuesta, "El carrito está vacío")


class BusquedaCobroTests(BaseCobro):
    """Búsqueda en tiempo real del escáner: arranca con 3 caracteres."""

    def buscar(self, consulta):
        return self.client.get(
            reverse("ventas:cobro_buscar"), {"codigo": consulta}
        )

    def test_anonimo_redirige_a_login(self):
        respuesta = self.client.get(
            reverse("ventas:cobro_buscar"), {"codigo": "coc"}
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn("login", respuesta.url)

    def test_con_menos_de_3_letras_no_busca(self):
        self.login_cajero()
        respuesta = self.buscar("co")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.content.decode().strip(), "")
        self.assertNotContains(respuesta, "Sin productos")

    def test_con_3_letras_encuentra_por_nombre(self):
        self.login_cajero()
        respuesta = self.buscar("coc")
        self.assertContains(respuesta, "Coca 500ml")
        self.assertNotContains(respuesta, "Villavicencio")

    def test_encuentra_por_codigo_de_barras_parcial(self):
        self.login_cajero()
        respuesta = self.buscar("7790000")
        self.assertContains(respuesta, "Coca 500ml")

    def test_sin_coincidencias_avisa(self):
        self.login_cajero()
        respuesta = self.buscar("xyz")
        self.assertContains(respuesta, "Sin productos para")

    def test_no_muestra_productos_dados_de_baja(self):
        self.producto.activo = False
        self.producto.save(update_fields=["activo"])
        self.login_cajero()
        respuesta = self.buscar("coc")
        self.assertNotContains(respuesta, "Coca 500ml")

    def test_agrega_desde_la_lista_al_carrito(self):
        """El botón de cada resultado manda el código a cobro_agregar."""
        self.login_cajero()
        self.agregar("7790000000001", hx=True)
        self.assertEqual(self.carrito()[0]["producto_id"], self.producto.pk)


class CobroVentaTests(BaseCobro):
    """HU-09: cobro con efectivo/tarjeta, vuelto y descuento de stock."""

    def test_efectivo_crea_venta_finalizada_con_vuelto(self):
        """CA de HU-09: monto entregado, vuelto exacto y venta registrada."""
        self.login_cajero()
        self.agregar("7790000000001")  # 1 x $1500
        respuesta = self.confirmar("efectivo", "2000")
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn("venta=", respuesta.url)

        venta = Venta.objects.get()
        self.assertTrue(venta.finalizada)
        self.assertEqual(venta.total, Decimal("1500.00"))
        self.assertEqual(venta.metodo_pago, "efectivo")
        self.assertEqual(venta.monto_entregado, Decimal("2000.00"))
        self.assertEqual(venta.vuelto, Decimal("500.00"))
        self.assertEqual(venta.usuario, self.cajero)

    def test_pago_exacto_da_vuelto_cero(self):
        self.login_cajero()
        self.agregar("7790000000001")
        self.confirmar("efectivo", "1500")
        venta = Venta.objects.get()
        self.assertEqual(venta.vuelto, Decimal("0.00"))

    def test_monto_con_formato_es_ar(self):
        """El cajero puede tipear "2.000,00" (coma decimal, locale es-ar)."""
        self.login_cajero()
        self.agregar("7790000000001")
        self.confirmar("efectivo", "2.000,00")
        venta = Venta.objects.get()
        self.assertEqual(venta.monto_entregado, Decimal("2000.00"))
        self.assertEqual(venta.vuelto, Decimal("500.00"))

    def test_monto_con_letras_rechazado(self):
        self.login_cajero()
        self.agregar("7790000000001")
        respuesta = self.confirmar("efectivo", "mil pesos")
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "no es un número válido")
        self.assertEqual(Venta.objects.count(), 0)

    def test_stock_se_descuenta_al_confirmar(self):
        """CA de HU-09: el stock se descuenta automáticamente."""
        self.login_cajero()
        self.agregar("7790000000001")
        self.agregar("7790000000001")
        self.cambiar_cantidad(self.producto, "sumar")  # 3 unidades
        self.confirmar("efectivo", "5000")
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 7)

    def test_precio_y_costo_se_congelan_en_el_detalle(self):
        self.login_cajero()
        self.agregar("7790000000001")
        self.confirmar("efectivo", "1500")
        detalle = DetalleVenta.objects.get()
        self.assertEqual(detalle.precio_unitario, Decimal("1500.00"))
        self.assertEqual(detalle.costo_unitario, Decimal("900.00"))
        self.assertEqual(detalle.subtotal(), Decimal("1500.00"))
        self.assertEqual(detalle.ganancia(), Decimal("600.00"))

    def test_tarjeta_no_pide_monto_ni_vuelto(self):
        self.login_cajero()
        self.agregar("7790000000001")
        self.confirmar("tarjeta", "")
        venta = Venta.objects.get()
        self.assertEqual(venta.metodo_pago, "tarjeta")
        self.assertIsNone(venta.monto_entregado)
        self.assertIsNone(venta.vuelto)

    def test_monto_menor_al_total_no_crea_venta(self):
        self.login_cajero()
        self.agregar("7790000000001")
        respuesta = self.confirmar("efectivo", "1000")
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "es menor al total")
        self.assertEqual(Venta.objects.count(), 0)
        self.assertEqual(self.carrito()[0]["cantidad"], 1)

    def test_carrito_vacio_no_crea_venta(self):
        self.login_cajero()
        respuesta = self.confirmar("efectivo", "5000")
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "El carrito está vacío")
        self.assertEqual(Venta.objects.count(), 0)

    def test_metodo_pago_invalido_rechazado(self):
        self.login_cajero()
        self.agregar("7790000000001")
        respuesta = self.confirmar("cheque", "5000")
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "método de pago válido")
        self.assertEqual(Venta.objects.count(), 0)

    def test_stock_insuficiente_rechaza_la_venta(self):
        self.login_cajero()
        self.agregar("7790000000001")
        self.agregar("7790000000001")
        self.producto.stock = 1
        self.producto.save(update_fields=["stock"])

        respuesta = self.confirmar("efectivo", "5000")
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Stock insuficiente")
        self.assertEqual(Venta.objects.count(), 0)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 1)

    def test_carrito_se_vacia_tras_confirmar(self):
        self.login_cajero()
        self.agregar("7790000000001")
        self.confirmar("efectivo", "1500")
        self.assertEqual(self.carrito(), [])

    def test_venta_queda_auditoriada(self):
        self.login_cajero()
        self.agregar("7790000000001")
        self.confirmar("efectivo", "1500")
        self.assertTrue(
            RegistroAuditoria.objects.filter(accion="Venta confirmada").exists()
        )

    def test_admin_tambien_puede_cobrar(self):
        self.login_admin()
        self.agregar("7790000000001")
        self.confirmar("efectivo", "1500")
        self.assertEqual(Venta.objects.get().usuario, self.admin)


class ComprobanteTests(BaseCobro):
    """El ticket posterior al cobro: visible para su cajero y para el admin."""

    def _venta_de(self, user):
        self.login_cajero()
        self.agregar("7790000000001")
        self.confirmar("efectivo", "2000")
        self.client.logout()
        return Venta.objects.get()

    def test_comprobante_muestra_totales_y_vuelto(self):
        venta = self._venta_de(self.cajero)
        self.login_cajero()
        respuesta = self.client.get(
            reverse("ventas:pantalla_cobro"), {"venta": venta.pk}
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, f"Venta N° {venta.pk} confirmada")
        self.assertContains(respuesta, "$500")  # vuelto (miles con punto)

    def test_comprobante_de_otro_cajero_da_403(self):
        venta = self._venta_de(self.cajero)
        otro = User.objects.create_user(
            username="cajero2", password="claveSegura123"
        )
        otro.groups.add(self.grupo_cajero)
        self.client.login(username="cajero2", password="claveSegura123")
        respuesta = self.client.get(
            reverse("ventas:pantalla_cobro"), {"venta": venta.pk}
        )
        self.assertEqual(respuesta.status_code, 403)

    def test_admin_puede_ver_cualquier_comprobante(self):
        venta = self._venta_de(self.cajero)
        self.login_admin()
        respuesta = self.client.get(
            reverse("ventas:pantalla_cobro"), {"venta": venta.pk}
        )
        self.assertEqual(respuesta.status_code, 200)

    def test_venta_inexistente_da_404(self):
        self.login_cajero()
        respuesta = self.client.get(
            reverse("ventas:pantalla_cobro"), {"venta": 9999}
        )
        self.assertEqual(respuesta.status_code, 404)
