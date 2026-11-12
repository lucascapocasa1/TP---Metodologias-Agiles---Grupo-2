"""Tests de la analítica del dashboard: período, FIAR, pedidos, rotación,
medios de pago y próximos vencimientos."""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from administracion import reportes
from clientes.models import Cliente
from negocios.models import Documento, Negocio, Proveedor
from pedidos.models import Pedido
from usuarios.models import Empleado
from ventas.models import Categoria, DetalleVenta, Producto, Venta


class BaseDashboardAnalitica(TestCase):
    def setUp(self):
        self.grupo_admin = Group.objects.create(name="Administrador")
        self.negocio = Negocio.objects.create(
            nombre="Kiosco Analítica",
            slug="kiosco-analitica",
            activo=True,
        )
        self.otro_negocio = Negocio.objects.create(
            nombre="Otro Negocio",
            slug="otro-negocio-analitica",
            activo=True,
        )
        self.admin = User.objects.create_user(
            username="admin_analitica", password="clave123", is_staff=True
        )
        self.admin.groups.add(self.grupo_admin)
        Empleado.objects.create(
            usuario=self.admin, negocio=self.negocio, activo=True
        )
        self.client.login(username="admin_analitica", password="clave123")

        self.categoria = Categoria.objects.create(nombre="Bebidas")
        self.gaseosa = Producto.objects.create(
            nombre="Gaseosa",
            precio=Decimal("100.00"),
            costo=Decimal("60.00"),
            stock=20,
            categoria=self.categoria,
            negocio=self.negocio,
        )
        self.agua = Producto.objects.create(
            nombre="Agua",
            precio=Decimal("50.00"),
            costo=Decimal("30.00"),
            stock=20,
            categoria=self.categoria,
            negocio=self.negocio,
        )
        self.proveedor = Proveedor.objects.create(
            nombre="Distribuidora Sur", negocio=self.negocio, activo=True
        )

    def crear_venta(
        self,
        producto,
        cantidad=1,
        dias_atras=0,
        metodo_pago="efectivo",
        finalizada=True,
        negocio=None,
        cliente=None,
    ):
        venta = Venta.objects.create(
            total=producto.precio * cantidad,
            finalizada=finalizada,
            metodo_pago=metodo_pago,
            negocio=negocio or self.negocio,
            cliente=cliente,
        )
        DetalleVenta.objects.create(
            venta=venta,
            producto=producto,
            cantidad=cantidad,
            precio_unitario=producto.precio,
            costo_unitario=producto.costo,
        )
        Venta.objects.filter(pk=venta.pk).update(
            fecha=timezone.now() - timedelta(days=dias_atras)
        )
        return venta

    def crear_pedido(self, total, estado="pendiente", dias_atras=0, negocio=None):
        pedido = Pedido.objects.create(
            nombre_cliente="Cliente Mostrador",
            total=Decimal(total),
            estado=estado,
            negocio=negocio or self.negocio,
        )
        Pedido.objects.filter(pk=pedido.pk).update(
            fecha=timezone.now() - timedelta(days=dias_atras)
        )
        return pedido

    def crear_documento(
        self, monto, pagado="0.00", estado="pendiente", dias_para_vencer=3
    ):
        hoy = timezone.localdate()
        return Documento.objects.create(
            negocio=self.negocio,
            proveedor=self.proveedor,
            nombre_proveedor=self.proveedor.nombre,
            categoria="proveedor",
            numero_factura=f"D-{dias_para_vencer}-{monto}",
            monto=Decimal(monto),
            monto_pagado=Decimal(pagado),
            fecha_emision=hoy - timedelta(days=10),
            fecha_vencimiento=hoy + timedelta(days=dias_para_vencer),
            estado=estado,
        )


class PeriodoDashboardTests(BaseDashboardAnalitica):
    def test_periodo_por_defecto_es_30_dias(self):
        respuesta = self.client.get(reverse("administracion:dashboard"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context["periodo"], "30")
        self.assertEqual(respuesta.context["dias_periodo"], 30)
        self.assertEqual(respuesta.context["hasta"], timezone.localdate())

    def test_selector_de_7_dias(self):
        respuesta = self.client.get(
            reverse("administracion:dashboard"), {"periodo": "7"}
        )

        self.assertEqual(respuesta.context["periodo"], "7")
        self.assertEqual(respuesta.context["dias_periodo"], 7)

    def test_rango_personalizado(self):
        respuesta = self.client.get(
            reverse("administracion:dashboard"),
            {"desde": "2026-09-01", "hasta": "2026-09-10"},
        )

        self.assertEqual(respuesta.context["periodo"], "personalizado")
        self.assertEqual(respuesta.context["dias_periodo"], 10)
        self.assertEqual(respuesta.context["desde"], date(2026, 9, 1))
        self.assertEqual(respuesta.context["hasta"], date(2026, 9, 10))

    def test_periodo_invalido_cae_a_30(self):
        respuesta = self.client.get(
            reverse("administracion:dashboard"), {"periodo": "999"}
        )

        self.assertEqual(respuesta.context["periodo"], "30")
        self.assertEqual(respuesta.context["dias_periodo"], 30)

    def test_selector_ignora_las_fechas_ocultas(self):
        # El form manda desde/hasta aunque el selector esté en un preset.
        respuesta = self.client.get(
            reverse("administracion:dashboard"),
            {"periodo": "7", "desde": "2026-09-01", "hasta": "2026-09-20"},
        )

        self.assertEqual(respuesta.context["periodo"], "7")
        self.assertEqual(respuesta.context["dias_periodo"], 7)

    def test_ventas_del_periodo_solo_cuentan_finalizadas_y_del_negocio(self):
        self.crear_venta(self.gaseosa, cantidad=2)  # 200 en el negocio
        self.crear_venta(self.gaseosa, cantidad=1, finalizada=False)
        self.crear_venta(self.gaseosa, cantidad=5, negocio=self.otro_negocio)

        respuesta = self.client.get(
            reverse("administracion:dashboard"), {"periodo": "7"}
        )

        resumen = respuesta.context["resumen_periodo"]
        self.assertEqual(resumen["ingresos"], Decimal("200.00"))
        self.assertEqual(resumen["cantidad_ventas"], 1)

    def test_variacion_compara_con_el_periodo_anterior(self):
        self.crear_venta(self.gaseosa, cantidad=3)  # actual: 300
        self.crear_venta(self.gaseosa, cantidad=2, dias_atras=10)  # anterior: 200

        respuesta = self.client.get(
            reverse("administracion:dashboard"), {"periodo": "7"}
        )

        variacion = respuesta.context["variacion"]
        self.assertEqual(variacion["actual"], Decimal("300.00"))
        self.assertEqual(variacion["anterior"], Decimal("200.00"))
        self.assertEqual(variacion["porcentaje"], Decimal("50.0"))
        self.assertEqual(variacion["direccion"], "sube")


class ClientesFiarDashboardTests(BaseDashboardAnalitica):
    def crear_cliente(self, dni, limite, saldo, nombre="Cliente"):
        return Cliente.objects.create(
            nombre=nombre,
            apellido="Test",
            dni=dni,
            limite_credito=Decimal(limite),
            saldo_deuda=Decimal(saldo),
        )

    def test_solo_cuenta_clientes_del_negocio(self):
        cliente_propio = self.crear_cliente("11111111", "1000", "500", "Propio")
        cliente_ajeno = self.crear_cliente("22222222", "1000", "700", "Ajeno")
        self.crear_venta(
            self.gaseosa, metodo_pago="cuenta_corriente", cliente=cliente_propio
        )
        self.crear_venta(
            self.gaseosa,
            metodo_pago="cuenta_corriente",
            cliente=cliente_ajeno,
            negocio=self.otro_negocio,
        )

        respuesta = self.client.get(reverse("administracion:dashboard"))

        resumen = respuesta.context["clientes_fiar"]
        self.assertEqual(resumen["cantidad"], 1)
        self.assertEqual(resumen["deuda"], Decimal("500.00"))
        self.assertEqual(
            [cliente.nombre for cliente in resumen["top"]], ["Propio"]
        )

    def test_cuenta_clientes_al_limite(self):
        self.crear_cliente("33333333", "1000", "1000", "AlLimite")
        self.crear_venta(
            self.gaseosa,
            metodo_pago="cuenta_corriente",
            cliente=Cliente.objects.get(dni="33333333"),
        )

        respuesta = self.client.get(reverse("administracion:dashboard"))

        resumen = respuesta.context["clientes_fiar"]
        self.assertEqual(resumen["al_limite"], 1)
        self.assertEqual(resumen["con_saldo"], 1)


class PedidosPendientesDashboardTests(BaseDashboardAnalitica):
    def test_cuenta_solo_pendientes_del_negocio(self):
        self.crear_pedido("1000")
        self.crear_pedido("700", dias_atras=3)  # más de 48 h
        self.crear_pedido("500", estado="entregado")
        self.crear_pedido("300", estado="cancelado")
        self.crear_pedido("900", negocio=self.otro_negocio)

        respuesta = self.client.get(reverse("administracion:dashboard"))

        resumen = respuesta.context["pedidos_pendientes"]
        self.assertEqual(resumen["cantidad"], 2)
        self.assertEqual(resumen["monto"], Decimal("1700.00"))
        self.assertEqual(resumen["vencidos"], 1)
        self.assertEqual(len(resumen["top"]), 2)


class RotacionDashboardTests(BaseDashboardAnalitica):
    def test_top_vendidos_y_productos_sin_movimiento(self):
        self.crear_venta(self.gaseosa, cantidad=5)
        self.crear_venta(self.agua, cantidad=1)

        respuesta = self.client.get(
            reverse("administracion:dashboard"), {"periodo": "7"}
        )

        top = respuesta.context["rotacion_top"]
        self.assertEqual(top[0]["producto__nombre"], "Gaseosa")
        self.assertEqual(top[0]["unidades"], 5)
        lentos = [producto.nombre for producto in respuesta.context["rotacion_lentos"]]
        self.assertNotIn("Gaseosa", lentos)
        self.assertNotIn("Agua", lentos)

    def test_producto_sin_ventas_aparece_como_lento(self):
        self.crear_venta(self.gaseosa, cantidad=1)

        respuesta = self.client.get(
            reverse("administracion:dashboard"), {"periodo": "7"}
        )

        lentos = [producto.nombre for producto in respuesta.context["rotacion_lentos"]]
        self.assertEqual(lentos, ["Agua"])


class MediosPagoDashboardTests(BaseDashboardAnalitica):
    def test_excluye_fiado_y_ventas_sin_finalizar(self):
        self.crear_venta(self.gaseosa, cantidad=1, metodo_pago="efectivo")
        self.crear_venta(self.gaseosa, cantidad=2, metodo_pago="tarjeta")
        # Fiado: no es plata que entró.
        self.crear_venta(
            self.gaseosa, cantidad=3, metodo_pago="cuenta_corriente"
        )
        # Carrito a medio armar: no se cuenta.
        self.crear_venta(
            self.gaseosa, cantidad=4, metodo_pago="efectivo", finalizada=False
        )

        respuesta = self.client.get(
            reverse("administracion:dashboard"), {"periodo": "7"}
        )

        metodos = {
            metodo["clave"]: metodo
            for metodo in respuesta.context["metodos_pago"]["metodos"]
        }
        self.assertEqual(metodos["efectivo"]["total"], Decimal("100.00"))
        self.assertEqual(metodos["tarjeta"]["total"], Decimal("200.00"))
        self.assertEqual(
            respuesta.context["metodos_pago"]["total"], Decimal("300.00")
        )
        self.assertNotIn("cuenta_corriente", metodos)
        self.assertEqual(
            respuesta.context["metodos_pago"]["fiado"], Decimal("300.00")
        )

    def test_porcentajes_y_maximo(self):
        self.crear_venta(self.gaseosa, cantidad=3, metodo_pago="efectivo")
        self.crear_venta(self.gaseosa, cantidad=1, metodo_pago="tarjeta")

        respuesta = self.client.get(reverse("administracion:dashboard"))
        metodos = {
            metodo["clave"]: metodo
            for metodo in respuesta.context["metodos_pago"]["metodos"]
        }

        self.assertEqual(metodos["efectivo"]["porcentaje"], Decimal("75.0"))
        self.assertEqual(metodos["tarjeta"]["porcentaje"], Decimal("25.0"))
        self.assertEqual(
            respuesta.context["metodos_pago"]["maximo"], Decimal("300.00")
        )


class VencimientosDashboardTests(BaseDashboardAnalitica):
    def test_solo_pendientes_dentro_de_7_dias_con_saldo(self):
        self.crear_documento("1000.00", pagado="400.00", dias_para_vencer=3)
        self.crear_documento("2000.00", dias_para_vencer=10)  # fuera de 7 días
        self.crear_documento(
            "3000.00", estado="pagada", dias_para_vencer=2
        )  # ya pagada
        self.crear_documento("4000.00", dias_para_vencer=-1)  # vencida

        respuesta = self.client.get(reverse("administracion:dashboard"))

        vencimientos = respuesta.context["vencimientos"]
        self.assertEqual(vencimientos["cantidad"], 1)
        self.assertEqual(vencimientos["total"], Decimal("600.00"))
        self.assertEqual(vencimientos["items"][0].dias_restantes, 3)


class DashboardSinNegocioTests(TestCase):
    def test_superadmin_sin_negocio_no_rompe(self):
        superuser = User.objects.create_superuser(
            username="super_analitica", password="clave123"
        )
        self.client.login(username="super_analitica", password="clave123")

        respuesta = self.client.get(reverse("administracion:dashboard"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            respuesta.context["resumen_periodo"]["ingresos"], Decimal("0.00")
        )
        self.assertEqual(respuesta.context["clientes_fiar"]["cantidad"], 0)
        self.assertEqual(respuesta.context["pedidos_pendientes"]["cantidad"], 0)


class ResolverPeriodoDashboardTests(TestCase):
    def test_periodo_valido(self):
        periodo, _, _, _, _, dias = reportes.resolver_periodo_dashboard("7")
        self.assertEqual(periodo, "7")
        self.assertEqual(dias, 7)

    def test_periodo_elegido_gana_sobre_fechas_ocultas(self):
        # El formulario manda desde/hasta aunque el selector esté en 7 días.
        periodo, _, _, _, _, dias = reportes.resolver_periodo_dashboard(
            "7", "2026-01-01", "2026-01-05"
        )
        self.assertEqual(periodo, "7")
        self.assertEqual(dias, 7)

    def test_rango_personalizado_usa_las_fechas(self):
        periodo, desde, hasta, _, _, dias = reportes.resolver_periodo_dashboard(
            "personalizado", "2026-01-01", "2026-01-05"
        )
        self.assertEqual(periodo, "personalizado")
        self.assertEqual(desde, date(2026, 1, 1))
        self.assertEqual(hasta, date(2026, 1, 5))
        self.assertEqual(dias, 5)

    def test_sin_periodo_pero_con_fechas_es_personalizado(self):
        periodo, desde, hasta, _, _, dias = reportes.resolver_periodo_dashboard(
            None, "2026-02-01", "2026-02-03"
        )
        self.assertEqual(periodo, "personalizado")
        self.assertEqual(dias, 3)


class ProductosSinMovimientoPrecioTests(BaseDashboardAnalitica):
    """El 'Aplicar' de precio nuevo daba 500 (filtro de template dentro de un f-string)."""

    def test_aplicar_precio_nuevo(self):
        url = reverse("administracion:productos_sin_movimiento")
        resp = self.client.post(
            url, {"accion": "descuento", "producto_id": self.agua.pk, "nuevo_precio": "39,50"}, follow=True
        )
        self.assertEqual(resp.status_code, 200)
        self.agua.refresh_from_db()
        self.assertEqual(self.agua.precio, Decimal("39.50"))

    def test_descuento_rapido_y_entradas_invalidas(self):
        url = reverse("administracion:productos_sin_movimiento")
        resp = self.client.get(url, {"accion": "desc", "prod": self.gaseosa.pk, "pct": "10"}, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.gaseosa.refresh_from_db()
        self.assertEqual(self.gaseosa.precio, Decimal("90.00"))
        resp = self.client.post(
            url, {"accion": "descuento", "producto_id": self.agua.pk, "nuevo_precio": "abc"}, follow=True
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.client.get(url, {"dias": "x"}).status_code, 200)
