"""
Tests del Sprint 2 — POS (pantalla del cajero, carrito y vuelto).

Cubren el funcionamiento del carrito en sesión, el cobro con efectivo
(validación del monto recibido y vuelto en billetes) y el acceso por rol.
"""
import json
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from ventas.models import DetalleVenta, Producto, Venta
from ventas.vuelto import desglosar, desglosar_vuelto


class VueltoTests(TestCase):
    def test_desglosa_usando_billetes_grandes_primero(self):
        self.assertEqual(desglosar(2350), {2000: 1, 200: 1, 100: 1, 50: 1})

    def test_desglosa_cero_sin_piezas(self):
        self.assertEqual(desglosar(0), {})

    def test_desglosa_con_monedas(self):
        self.assertEqual(desglosar(7), {5: 1, 2: 1})

    def test_desglosa_vuelto_con_centavos(self):
        piezas, centavos = desglosar_vuelto(Decimal("2485.50"))
        self.assertEqual(centavos, 50)
        self.assertEqual(piezas, {2000: 1, 200: 2, 50: 1, 20: 1, 10: 1, 5: 1})


class PoscTestsBase(TestCase):
    def setUp(self):
        self.grupo_cajero = Group.objects.create(name="Cajero")
        self.grupo_admin = Group.objects.create(name="Administrador")

        self.cajero = User.objects.create_user(username="cajero_pos", password="claveSegura123")
        self.cajero.groups.add(self.grupo_cajero)

        self.admin = User.objects.create_user(username="admin_pos", password="claveSegura123")
        self.admin.groups.add(self.grupo_admin)

        self.coca = Producto.objects.create(
            nombre="Coca-Cola 1.5L",
            codigo_barras="7790895000997",
            precio=Decimal("3200.00"),
        )
        self.agua = Producto.objects.create(
            nombre="Agua mineral 500ml",
            codigo_barras="7794000500005",
            precio=Decimal("1200.00"),
        )

    def login_cajero(self):
        return self.client.login(username="cajero_pos", password="claveSegura123")

    def agregar_al_carrito(self, codigo=None, producto_id=None, cantidad=1):
        data = {"cantidad": cantidad}
        if codigo:
            data["codigo"] = codigo
        if producto_id:
            data["producto"] = producto_id
        return self.client.post(
            reverse("ventas:agregar_al_carrito"),
            data,
            HTTP_HX_REQUEST="true",
        )

    def registrar_venta(self, metodo="EFECTIVO", monto_recibido="0"):
        return self.client.post(
            reverse("ventas:registrar_venta"),
            {"metodo_pago": metodo, "monto_recibido": monto_recibido},
            HTTP_HX_REQUEST="true",
        )


class CarritoTests(PoscTestsBase):
    def test_animo_no_puede_agregar_productos(self):
        respuesta = self.agregar_al_carrito(codigo=self.coca.codigo_barras)
        self.assertEqual(respuesta.status_code, 302)  # redirige a login

    def test_cajero_agrega_producto_por_codigo_de_barras(self):
        self.login_cajero()
        producto_id = str(self.coca.pk)
        respuesta = self.agregar_al_carrito(codigo=self.coca.codigo_barras)

        self.assertEqual(respuesta.status_code, 200)
        carrito = self.client.session.get("carrito", {})
        self.assertEqual(carrito, {producto_id: 1})

    def test_cajero_agrega_producto_por_boton_rapido(self):
        self.login_cajero()
        self.agregar_al_carrito(producto_id=self.agua.pk)
        carrito = self.client.session.get("carrito", {})
        self.assertEqual(carrito, {str(self.agua.pk): 1})

    def test_codigo_inexistente_no_agrega_y_avisa(self):
        self.login_cajero()
        respuesta = self.agregar_al_carrito(codigo="9999999999999")
        self.assertEqual(self.client.session.get("carrito", {}), {})
        self.assertContains(respuesta, "No se encontró ningún producto")

    def test_acumula_cantidad_al_agregar_dos_veces(self):
        self.login_cajero()
        self.agregar_al_carrito(codigo=self.coca.codigo_barras)
        self.agregar_al_carrito(codigo=self.coca.codigo_barras)
        carrito = self.client.session.get("carrito", {})
        self.assertEqual(carrito, {str(self.coca.pk): 2})

    def test_actualizar_cantidad_y_quitar(self):
        self.login_cajero()
        self.agregar_al_carrito(codigo=self.coca.codigo_barras)
        self.agregar_al_carrito(codigo=self.agua.codigo_barras)

        # Sumar: 2 cocas
        self.client.post(reverse("ventas:actualizar_cantidad", args=[self.coca.pk]), {"cantidad": 2})
        carrito = self.client.session.get("carrito", {})
        self.assertEqual(carrito, {str(self.coca.pk): 2, str(self.agua.pk): 1})

        # Quitar el agua
        self.client.post(reverse("ventas:quitar_producto", args=[self.agua.pk]))
        carrito = self.client.session.get("carrito", {})
        self.assertEqual(carrito, {str(self.coca.pk): 2})

        # Vaciar
        self.client.post(reverse("ventas:vaciar_carrito"))
        self.assertEqual(self.client.session.get("carrito", {}), {})

    def test_total_del_carrito_se_muestra_en_la_pantalla(self):
        self.login_cajero()
        self.agregar_al_carrito(codigo=self.coca.codigo_barras)  # 3200
        self.agregar_al_carrito(codigo=self.agua.codigo_barras)  # 1200

        respuesta = self.client.get(reverse("ventas:pantalla_cobro"))
        self.assertContains(respuesta, "$ 4400")
        self.assertContains(respuesta, "Carrito")


class VentaTests(PoscTestsBase):
    def test_cobrar_efectivo_registra_venta_y_vacía_carrito(self):
        self.login_cajero()
        cantidad = 2
        for _ in range(cantidad):
            self.agregar_al_carrito(codigo=self.coca.codigo_barras)
        total = self.coca.precio * cantidad  # 6400

        respuesta = self.registrar_venta(metodo="EFECTIVO", monto_recibido="10000")

        venta = Venta.objects.get(cajero=self.cajero)
        self.assertEqual(venta.total, total)
        self.assertEqual(venta.monto_recibido, Decimal("10000"))
        self.assertEqual(venta.vuelto, Decimal("3600"))
        self.assertEqual(venta.metodo_pago, "EFECTIVO")
        # 2 líneas de detalle (una por agregado; el carrito acumula 2 en 1 línea)
        self.assertEqual(venta.detalles.count(), 1)
        detalle = venta.detalles.get()
        self.assertEqual(detalle.cantidad, cantidad)
        self.assertEqual(detalle.precio_unitario, self.coca.precio)

        self.assertEqual(self.client.session.get("carrito", {}), {})
        self.assertContains(respuesta, "Vuelto")
        self.assertContains(respuesta, "3600")

    def test_cobrar_con_tarjeta_no_devuelve_vuelto(self):
        self.login_cajero()
        self.agregar_al_carrito(codigo=self.agua.codigo_barras)

        self.registrar_venta(metodo="TARJETA", monto_recibido="0")

        venta = Venta.objects.get(cajero=self.cajero)
        self.assertEqual(venta.metodo_pago, "TARJETA")
        self.assertEqual(venta.monto_recibido, self.agua.precio)
        self.assertEqual(venta.vuelto, Decimal("0.00"))

    def test_no_cobra_si_el_efectivo_no_alcanza(self):
        self.login_cajero()
        self.agregar_al_carrito(codigo=self.coca.codigo_barras)

        respuesta = self.registrar_venta(metodo="EFECTIVO", monto_recibido="2000")

        self.assertEqual(Venta.objects.count(), 0)
        self.assertContains(respuesta, "no alcanza")
        # El carrito se conserva para que el cajero corrija el monto.
        self.assertEqual(self.client.session.get("carrito"), {str(self.coca.pk): 1})

    def test_no_cobra_si_el_carrito_esta_vacio(self):
        self.login_cajero()
        respuesta = self.registrar_venta(metodo="EFECTIVO", monto_recibido="5000")
        self.assertEqual(Venta.objects.count(), 0)
        self.assertContains(respuesta, "vacío")

    def test_ultima_venta_se_muestra_como_comprobante(self):
        self.login_cajero()
        self.agregar_al_carrito(codigo=self.coca.codigo_barras)

        respuesta = self.registrar_venta(metodo="EFECTIVO", monto_recibido="10000")
        self.assertContains(respuesta, "Venta #")
        self.assertContains(respuesta, "quedó registrada")

        # Al entrar a la pantalla se mantiene el aviso de la venta cerrada.
        pantalla = self.client.get(reverse("ventas:pantalla_cobro"))
        self.assertContains(pantalla, "quedó registrada")


class AccesoPocTests(PoscTestsBase):
    def test_cajero_accede_a_la_pantalla_de_cobro(self):
        self.login_cajero()
        respuesta = self.client.get(reverse("ventas:pantalla_cobro"))
        self.assertEqual(respuesta.status_code, 200)

    def test_administrador_accede_a_la_pantalla_de_cobro(self):
        self.client.login(username="admin_pos", password="claveSegura123")
        respuesta = self.client.get(reverse("ventas:pantalla_cobro"))
        self.assertEqual(respuesta.status_code, 200)

    def test_pantalla_lista_productos_activos(self):
        self.login_cajero()
        Producto.objects.create(
            nombre="Producto oculto",
            codigo_barras="7799999999999",
            precio=Decimal("500"),
            activo=False,
        )
        respuesta = self.client.get(reverse("ventas:pantalla_cobro"))
        self.assertContains(respuesta, "Coca-Cola 1.5L")
        self.assertNotContains(respuesta, "Producto oculto")
