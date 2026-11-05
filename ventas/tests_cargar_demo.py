from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from ventas.management.commands import cargar_demo
from ventas.models import Categoria, DetalleVenta, Producto, Venta


class CargarDemoTests(TestCase):
    """`manage.py cargar_demo`: catálogo + historial de ventas de prueba."""

    def setUp(self):
        Group.objects.create(name="Administrador")
        grupo_cajero = Group.objects.create(name="Cajero")
        self.cajero = User.objects.create_user(
            username="cajero_seed", password="claveSegura123"
        )
        self.cajero.groups.add(grupo_cajero)

    def _cargar(self, **kwargs):
        call_command("cargar_demo", **kwargs)

    def test_crea_el_catalogo_completo(self):
        self._cargar()
        self.assertGreaterEqual(Producto.objects.count(), 50)
        self.assertGreaterEqual(Categoria.objects.count(), 7)
        # Todos los productos tienen código de barras único y costo/precio.
        codigos = list(
            Producto.objects.values_list("codigo_barras", flat=True)
        )
        self.assertNotIn(None, codigos)
        self.assertEqual(len(codigos), len(set(codigos)))
        self.assertEqual(
            Producto.objects.filter(costo=0).count(),
            0,
            "el catálogo de demo debe tener costo cargado",
        )

    def test_ventas_desde_el_20_de_septiembre(self):
        self._cargar()
        primera = Venta.objects.order_by("fecha").first()
        self.assertEqual(primera.fecha.date(), date(2026, 9, 20))
        # Nunca venta en el futuro.
        self.assertLessEqual(
            Venta.objects.order_by("-fecha").first().fecha,
            timezone.now(),
        )
        self.assertGreater(Venta.objects.count(), 100)
        self.assertTrue(Venta.objects.filter(finalizada=True).exists())

    def test_los_detalles_congelan_precio_y_costo(self):
        self._cargar()
        detalle = DetalleVenta.objects.select_related("producto").first()
        self.assertEqual(detalle.precio_unitario, detalle.producto.precio)
        self.assertEqual(detalle.costo_unitario, detalle.producto.costo)
        venta = detalle.venta
        total_esperado = sum(
            d.cantidad * d.precio_unitario for d in venta.detalles.all()
        )
        self.assertEqual(venta.total, total_esperado)

    def test_efectivo_tiene_vuelto_y_tarjeta_no(self):
        self._cargar()
        efectivo = (
            Venta.objects.filter(metodo_pago="efectivo")
            .exclude(monto_entregado=None)
            .first()
        )
        self.assertIsNotNone(efectivo)
        self.assertEqual(
            efectivo.vuelto, efectivo.monto_entregado - efectivo.total
        )
        tarjeta = Venta.objects.filter(metodo_pago="tarjeta").first()
        if tarjeta:  # el reparto 65/35 es por semilla fija, pero no lo atamos
            self.assertIsNone(tarjeta.monto_entregado)
            self.assertIsNone(tarjeta.vuelto)

    def test_sin_limpiar_no_duplica_ventas(self):
        self._cargar()
        total = Venta.objects.count()
        self._cargar()  # sin --limpiar: tiene que avisar y no duplicar
        self.assertEqual(Venta.objects.count(), total)

    def test_limpiar_regenera_los_mismos_datos(self):
        """La semilla fija hace que dos corridas den exactamente igual."""
        self._cargar(limpiar=True)
        primera = (
            Venta.objects.count(),
            Venta.objects.order_by("-fecha").first().total,
        )
        self._cargar(limpiar=True)
        segunda = (
            Venta.objects.count(),
            Venta.objects.order_by("-fecha").first().total,
        )
        self.assertEqual(primera, segunda)

    def test_no_pisa_productos_cargados_a_mano(self):
        propio = Producto.objects.create(
            nombre="Producto Mio",
            precio=Decimal("123.00"),
            costo=Decimal("80.00"),
            stock=7,
            categoria=Categoria.objects.create(nombre="Mia"),
        )
        self._cargar()
        propio.refresh_from_db()
        self.assertEqual(propio.precio, Decimal("123.00"))
        self.assertEqual(propio.stock, 7)

    def test_totales_no_multiplos_de_100_no_colgan(self):
        """Regresión: con total de $123 el redondeo por `while ... += 100`
        nunca llegaba a múltiplo de 1000 y el comando se colgaba."""
        Producto.objects.create(
            nombre="Precio Raro",
            precio=Decimal("123.00"),
            costo=Decimal("80.00"),
            stock=50,
            categoria=Categoria.objects.create(nombre="Rara"),
        )
        self._cargar(ventas_por_dia=3)

        efectivos = Venta.objects.filter(
            metodo_pago="efectivo"
        ).exclude(monto_entregado=None)
        self.assertTrue(efectivos.exists())
        for venta in efectivos:
            self.assertGreaterEqual(venta.monto_entregado, venta.total)
            self.assertEqual(
                venta.vuelto, venta.monto_entregado - venta.total
            )

    def test_catalogo_es_determinista(self):
        self.assertEqual(
            len(cargar_demo.CATALOGO),
            len({nombre for nombre, *_ in cargar_demo.CATALOGO}),
            "nombres de productos duplicados en el catálogo",
        )

    def test_limpiar_respeta_las_ventas_con_cliente_y_de_pedidos(self):
        """`--limpiar` borra solo las ventas anónimas que creó este comando.

        Las ventas de clientes y las de pedidos de WhatsApp las administra
        `cargar_demo_clientes`, que repone su stock al limpiarlas. Si este
        comando las borrara, ese stock se perdería en cada recarga de la demo.
        """
        from clientes.models import Cliente
        from pedidos.models import Pedido

        self._cargar(ventas_por_dia=2)
        cliente = Cliente.objects.create(
            nombre="Ana", apellido="Demo", dni="30111222"
        )
        con_cliente = Venta.objects.create(
            total=Decimal("1000.00"),
            finalizada=True,
            metodo_pago="efectivo",
            cliente=cliente,
        )
        pedido = Pedido.objects.create(
            nombre_cliente="Consumidor Final",
            telefono="1100000000",
            comentario="",
            total=Decimal("900.00"),
        )
        de_pedido = Venta.objects.create(
            total=Decimal("900.00"), finalizada=True, metodo_pago="efectivo"
        )
        pedido.venta = de_pedido
        pedido.save(update_fields=["venta"])
        anonima = Venta.objects.create(
            total=Decimal("500.00"), finalizada=True, metodo_pago="efectivo"
        )

        self._cargar(limpiar=True, ventas_por_dia=2)

        self.assertTrue(Venta.objects.filter(pk=con_cliente.pk).exists())
        self.assertTrue(Venta.objects.filter(pk=de_pedido.pk).exists())
        self.assertFalse(Venta.objects.filter(pk=anonima.pk).exists())
