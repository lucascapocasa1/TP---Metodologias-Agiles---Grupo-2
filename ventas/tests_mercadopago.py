"""
Tests del cobro con QR de Mercado Pago sobre la caja de HU-07/08/09.

La API de Mercado Pago no se llama de verdad: se reemplaza con `mock` para
probar qué hace el sistema cuando Mercado Pago responde bien, mal o tarde.
"""
from unittest import mock

from django.test import override_settings
from django.urls import reverse

from clientes.models import Cliente

from . import services
from .mercadopago import MercadoPagoError
from .models import PagoMercadoPago, Turno, Venta
from .tests import BaseCobro


class BaseQR(BaseCobro):
    def setUp(self):
        super().setUp()
        self.login_cajero()

    def cobrar_qr(self):
        return self.confirmar(metodo="mercado_pago", monto="")

    def pago(self):
        return PagoMercadoPago.objects.select_related("venta").get()


@override_settings(MP_ACCESS_TOKEN="")
class CobroQRSimuladoTests(BaseQR):
    """Sin credenciales: modo de prueba con pago simulado."""

    def test_genera_venta_pendiente_y_reserva_stock(self):
        self.agregar("7790000000001")
        self.agregar("7790000000001")
        respuesta = self.cobrar_qr()
        self.assertRedirects(respuesta, reverse("ventas:pantalla_cobro"))

        pago = self.pago()
        self.assertTrue(pago.simulado)
        self.assertEqual(pago.estado, PagoMercadoPago.PENDIENTE)
        self.assertFalse(pago.venta.finalizada)  # no cuenta en reportes todavía
        self.assertEqual(pago.venta.metodo_pago, "mercado_pago")
        self.assertEqual(pago.venta.total, 3000)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 8)
        self.assertEqual(self.carrito(), [])

    def test_la_caja_muestra_el_qr_pendiente(self):
        self.agregar("7790000000001")
        self.cobrar_qr()
        respuesta = self.client.get(reverse("ventas:pantalla_cobro"))
        self.assertContains(respuesta, 'id="qrOverlay"')
        self.assertContains(respuesta, self.pago().link_pago)

    def test_pago_desde_el_celular_finaliza_la_venta(self):
        self.agregar("7790000000001")
        self.cobrar_qr()
        pago = self.pago()

        # El display del celular muestra el QR del cobro en curso.
        datos = self.client.get(reverse("ventas:display_estado")).json()
        self.assertEqual(datos["estado"], "pendiente")
        self.assertEqual(datos["link"], pago.link_pago)

        # El cliente paga en la página de prueba, sin iniciar sesión.
        self.client_class().post(reverse("ventas:pago_simulado", args=[pago.token]))

        pago.refresh_from_db()
        self.assertEqual(pago.estado, PagoMercadoPago.APROBADO)
        self.assertTrue(pago.venta.finalizada)
        estado = self.client.get(reverse("ventas:pago_estado", args=[pago.pk])).json()
        self.assertEqual(estado["estado"], "aprobado")
        self.assertIn(f"venta={pago.venta_id}", estado["comprobante"])
        self.assertEqual(self.client.get(reverse("ventas:display_estado")).json()["estado"], "aprobado")

    def test_cancelar_devuelve_stock_y_carrito(self):
        self.agregar("7790000000001")
        self.agregar("7790000000001")
        self.cobrar_qr()
        pago = self.pago()

        self.client.post(reverse("ventas:pago_cancelar", args=[pago.pk]))
        pago.refresh_from_db()
        self.producto.refresh_from_db()
        self.assertEqual(pago.estado, PagoMercadoPago.CANCELADO)
        self.assertFalse(pago.venta.finalizada)
        self.assertEqual(self.producto.stock, 10)
        self.assertEqual(self.carrito(), [{"producto_id": self.producto.pk, "cantidad": 2}])

    def test_no_permite_dos_cobros_qr_a_la_vez(self):
        self.agregar("7790000000001")
        self.cobrar_qr()
        self.agregar("7791111111111")
        self.cobrar_qr()
        self.assertEqual(PagoMercadoPago.objects.count(), 1)

    def test_otro_cajero_no_ve_ni_cancela_el_cobro(self):
        self.agregar("7790000000001")
        self.cobrar_qr()
        pago = self.pago()
        self.client.logout()
        self.login_admin()
        respuesta = self.client.post(reverse("ventas:pago_cancelar", args=[pago.pk]))
        self.assertEqual(respuesta.status_code, 404)
        self.assertEqual(self.client.get(reverse("ventas:display_estado")).json()["estado"], "libre")

    def test_suma_puntos_recien_al_aprobar(self):
        cliente = Cliente.objects.create(nombre="Ana", apellido="Pérez", dni="30123456")
        self.client.post(reverse("clientes:asociar"), {"cliente_id": cliente.pk})
        self.agregar("7790000000001")
        self.cobrar_qr()
        pago = self.pago()
        cliente.refresh_from_db()
        self.assertEqual(cliente.puntos, 0)

        self.client_class().post(reverse("ventas:pago_simulado", args=[pago.token]))
        cliente.refresh_from_db()
        self.assertEqual(cliente.puntos, pago.venta.puntos_ganados)
        self.assertGreater(cliente.puntos, 0)

    def test_cierre_de_turno_informa_mercado_pago(self):
        turno = services.abrir_turno(self.cajero)
        self.agregar("7790000000001")
        self.cobrar_qr()
        totales = services.totales_del_turno(turno)
        self.assertEqual(totales["total_mercado_pago"], 0)  # pendiente: no cuenta

        self.client_class().post(reverse("ventas:pago_simulado", args=[self.pago().token]))
        turno = services.cerrar_turno(Turno.objects.get(pk=turno.pk))
        self.assertEqual(turno.total_mercado_pago, 1500)
        self.assertEqual(turno.total_general, 1500)
        self.assertEqual(turno.cantidad_operaciones, 1)

    def test_el_formulario_comun_no_finaliza_mercado_pago_sin_pagar(self):
        self.agregar("7790000000001")
        self.cobrar_qr()
        self.assertFalse(Venta.objects.filter(finalizada=True).exists())

    def test_pago_simulado_no_existe_para_cobros_reales(self):
        self.agregar("7790000000001")
        self.cobrar_qr()
        pago = self.pago()
        PagoMercadoPago.objects.filter(pk=pago.pk).update(simulado=False)
        respuesta = self.client.post(reverse("ventas:pago_simulado", args=[pago.token]))
        self.assertEqual(respuesta.status_code, 404)


@override_settings(MP_ACCESS_TOKEN="TEST-123")
class CobroQRMercadoPagoTests(BaseQR):
    """Con credenciales: la API de Mercado Pago se reemplaza con mock."""

    def iniciar(self):
        self.agregar("7790000000001")
        with mock.patch(
            "ventas.mercadopago.crear_preferencia",
            return_value=("pref-1", "https://sandbox.mercadopago.com.ar/checkout?pref_id=pref-1"),
        ):
            self.cobrar_qr()
        return self.pago()

    def test_usa_el_link_de_mercado_pago(self):
        pago = self.iniciar()
        self.assertFalse(pago.simulado)
        self.assertEqual(pago.preference_id, "pref-1")
        self.assertIn("mercadopago", pago.link_pago)

    def test_la_caja_consulta_a_mercado_pago(self):
        pago = self.iniciar()
        url = reverse("ventas:pago_estado", args=[pago.pk])
        with mock.patch("ventas.mercadopago.buscar_pago_aprobado", return_value=None):
            self.assertEqual(self.client.get(url).json()["estado"], "pendiente")
        with mock.patch("ventas.mercadopago.buscar_pago_aprobado", return_value="987"):
            self.assertEqual(self.client.get(url).json()["estado"], "aprobado")
        pago.refresh_from_db()
        self.assertEqual(pago.payment_id, "987")
        self.assertTrue(pago.venta.finalizada)

    def test_sin_conexion_sigue_esperando(self):
        pago = self.iniciar()
        url = reverse("ventas:pago_estado", args=[pago.pk])
        with mock.patch("ventas.mercadopago.buscar_pago_aprobado", side_effect=MercadoPagoError("caído")):
            datos = self.client.get(url).json()
        self.assertEqual(datos["estado"], "pendiente")
        self.assertTrue(datos["error"])

    def test_si_mercado_pago_falla_no_queda_stock_reservado(self):
        self.agregar("7790000000001")
        with mock.patch("ventas.mercadopago.crear_preferencia", side_effect=MercadoPagoError("caído")):
            self.cobrar_qr()
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 10)
        self.assertFalse(Venta.objects.filter(finalizada=True).exists())

    def test_webhook_verifica_el_pago_con_la_api(self):
        pago = self.iniciar()
        datos_mp = {"status": "approved", "external_reference": f"norvex-venta-{pago.venta_id}"}
        with mock.patch("ventas.mercadopago.obtener_pago", return_value=datos_mp):
            respuesta = self.client_class().post(
                reverse("ventas:mercadopago_webhook") + "?type=payment&data.id=555"
            )
        self.assertEqual(respuesta.status_code, 200)
        pago.refresh_from_db()
        self.assertEqual(pago.estado, PagoMercadoPago.APROBADO)
        self.assertEqual(pago.payment_id, "555")

    def test_webhook_ignora_pagos_no_aprobados(self):
        pago = self.iniciar()
        datos_mp = {"status": "rejected", "external_reference": f"norvex-venta-{pago.venta_id}"}
        with mock.patch("ventas.mercadopago.obtener_pago", return_value=datos_mp):
            self.client_class().post(reverse("ventas:mercadopago_webhook") + "?type=payment&data.id=556")
        pago.refresh_from_db()
        self.assertEqual(pago.estado, PagoMercadoPago.PENDIENTE)
