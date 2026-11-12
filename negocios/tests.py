"""Pruebas de aislamiento multiempresa y flujo completo (Etapa 7).

Valida que:
1. Los datos de un negocio no se mezclan con los de otro.
2. Cada empleado solo ve su propio negocio.
3. Un cliente puede comprar en varios negocios, pero cada negocio ve solo sus propias ventas.
4. El flujo completo de compra online y retiro en local funciona correctamente.
"""
import io
from django.contrib.auth.models import Group, User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal

from auditoria.models import RegistroAuditoria
from negocios.models import Documento, Negocio, Proveedor
from usuarios.models import Empleado
from ventas.models import Categoria, Producto, Venta, DetalleVenta
from clientes.models import Cliente
from pedidos.models import Pedido, ItemPedido, ReservaStock


class NegocioTests(TestCase):
    """Pruebas del modelo Negocio y aislamiento de datos."""

    def setUp(self):
        self.negocio_barrio = Negocio.objects.create(
            nombre="Kiosco De Barrio",
            slug="de-barrio",
            whatsapp="5491155554444",
            email="barrio@example.com",
            activo=True,
        )
        self.negocio_martillito = Negocio.objects.create(
            nombre="Ferretería Martillito",
            slug="ferreteria-martillito",
            whatsapp="5491166667777",
            email="martillito@example.com",
            activo=True,
        )
        self.negocio_inactivo = Negocio.objects.create(
            nombre="Negocio Inactivo",
            slug="negocio-inactivo",
            activo=False,
        )

    def test_negocio_activo_solo_visible(self):
        """Solo los negocios activos deben estar disponibles para la tienda pública."""
        activos = Negocio.objects.filter(activo=True)
        self.assertEqual(activos.count(), 2)
        self.assertIn(self.negocio_barrio, activos)
        self.assertIn(self.negocio_martillito, activos)
        self.assertNotIn(self.negocio_inactivo, activos)

    def test_slug_unico(self):
        """El slug debe ser único por negocio."""
        with self.assertRaises(Exception):
            Negocio.objects.create(
                nombre="Otro Barrio",
                slug="de-barrio",  # duplicado
                activo=True,
            )


class EmpleadoTests(TestCase):
    """Pruebas del modelo Empleado y su relación con Negocio."""

    def setUp(self):
        self.grupo_admin = Group.objects.create(name="Administrador")
        self.grupo_cajero = Group.objects.create(name="Cajero")

        self.negocio_barrio = Negocio.objects.create(
            nombre="Kiosco De Barrio",
            slug="de-barrio",
            activo=True,
        )
        self.negocio_martillito = Negocio.objects.create(
            nombre="Ferretería Martillito",
            slug="ferreteria-martillito",
            activo=True,
        )

        self.admin_barrio = User.objects.create_user(
            username="admin_barrio", password="clave123", is_staff=True
        )
        self.admin_barrio.groups.add(self.grupo_admin)
        Empleado.objects.create(
            usuario=self.admin_barrio, negocio=self.negocio_barrio, activo=True
        )

        self.cajero_martillito = User.objects.create_user(
            username="cajero_martillito", password="clave123"
        )
        self.cajero_martillito.groups.add(self.grupo_cajero)
        Empleado.objects.create(
            usuario=self.cajero_martillito,
            negocio=self.negocio_martillito,
            activo=True,
        )

    def test_empleado_vinculado_a_un_solo_negocio(self):
        """Un empleado pertenece a exactamente un negocio."""
        self.assertEqual(self.admin_barrio.empleado.negocio, self.negocio_barrio)
        self.assertEqual(
            self.cajero_martillito.empleado.negocio, self.negocio_martillito
        )
        self.assertNotEqual(
            self.admin_barrio.empleado.negocio,
            self.cajero_martillito.empleado.negocio,
        )

    def test_superadmin_no_tiene_negocio_asignado(self):
        """Un superusuario no necesita Empleado para acceder a todo."""
        superadmin = User.objects.create_user(
            username="superadmin", password="clave123", is_superuser=True
        )
        self.assertTrue(superadmin.is_superuser)


class AislamientoDatosTests(TestCase):
    """Pruebas de aislamiento: los datos de un negocio no aparecen en otro."""

    def setUp(self):
        self.grupo_admin = Group.objects.create(name="Administrador")
        self.grupo_cajero = Group.objects.create(name="Cajero")

        self.negocio_barrio = Negocio.objects.create(
            nombre="Kiosco De Barrio",
            slug="de-barrio",
            activo=True,
        )
        self.negocio_martillito = Negocio.objects.create(
            nombre="Ferretería Martillito",
            slug="ferreteria-martillito",
            activo=True,
        )

        # Usuario admin de Barrio
        self.admin_barrio = User.objects.create_user(
            username="admin_barrio", password="clave123", is_staff=True
        )
        self.admin_barrio.groups.add(self.grupo_admin)
        Empleado.objects.create(
            usuario=self.admin_barrio, negocio=self.negocio_barrio, activo=True
        )

        # Usuario cajero de Martillito
        self.cajero_martillito = User.objects.create_user(
            username="cajero_martillito", password="clave123"
        )
        self.cajero_martillito.groups.add(self.grupo_cajero)
        Empleado.objects.create(
            usuario=self.cajero_martillito,
            negocio=self.negocio_martillito,
            activo=True,
        )

        # Categorías y productos de cada negocio
        self.cat_barrio = Categoria.objects.create(
            nombre="Bebidas", negocio=self.negocio_barrio
        )
        self.cat_martillito = Categoria.objects.create(
            nombre="Herramientas", negocio=self.negocio_martillito
        )

        self.prod_barrio = Producto.objects.create(
            nombre="Coca 500ml",
            codigo_barras="7790000000101",
            precio=Decimal("1500.00"),
            costo=Decimal("900.00"),
            stock=10,
            categoria=self.cat_barrio,
            negocio=self.negocio_barrio,
            activo=True,
        )
        self.prod_martillito = Producto.objects.create(
            nombre="Martillo",
            codigo_barras="7790000000102",
            precio=Decimal("5000.00"),
            costo=Decimal("3000.00"),
            stock=5,
            categoria=self.cat_martillito,
            negocio=self.negocio_martillito,
            activo=True,
        )

    def test_productos_filtrados_por_negocio(self):
        """Cada negocio ve solo sus propios productos."""
        productos_barrio = Producto.objects.filter(negocio=self.negocio_barrio)
        productos_martillito = Producto.objects.filter(
            negocio=self.negocio_martillito
        )

        self.assertEqual(productos_barrio.count(), 1)
        self.assertEqual(productos_barrio.first(), self.prod_barrio)
        self.assertEqual(productos_martillito.count(), 1)
        self.assertEqual(productos_martillito.first(), self.prod_martillito)

    def test_venta_de_barrio_no_aparece_en_martillito(self):
        """Una venta en De Barrio no debe aparecer en los pedidos/ventas de Martillito."""
        venta_barrio = Venta.objects.create(
            total=Decimal("3000.00"),
            finalizada=True,
            metodo_pago="efectivo",
            usuario=self.admin_barrio,
            negocio=self.negocio_barrio,
        )
        DetalleVenta.objects.create(
            venta=venta_barrio,
            producto=self.prod_barrio,
            cantidad=2,
            precio_unitario=Decimal("1500.00"),
            costo_unitario=Decimal("900.00"),
        )

        # Ventas de Martillito no incluyen la de Barrio
        ventas_martillito = Venta.objects.filter(negocio=self.negocio_martillito)
        self.assertEqual(ventas_martillito.count(), 0)

    def test_cliente_compartido_entre_negocios(self):
        """Un mismo Cliente puede comprar en varios negocios."""
        cliente = Cliente.objects.create(
            nombre="Lucas",
            apellido="Pérez",
            dni="30111222",
            telefono="1155556666",
            limite_credito=Decimal("10000.00"),
        )

        # Venta en Barrio
        venta_barrio = Venta.objects.create(
            total=Decimal("1500.00"),
            finalizada=True,
            metodo_pago="efectivo",
            usuario=self.admin_barrio,
            cliente=cliente,
            negocio=self.negocio_barrio,
        )

        # Venta en Martillito (mismo cliente)
        admin_martillito = User.objects.create_user(
            username="admin_martillito", password="clave123", is_staff=True
        )
        admin_martillito.groups.add(self.grupo_admin)
        Empleado.objects.create(
            usuario=admin_martillito,
            negocio=self.negocio_martillito,
            activo=True,
        )
        venta_martillito = Venta.objects.create(
            total=Decimal("5000.00"),
            finalizada=True,
            metodo_pago="efectivo",
            usuario=admin_martillito,
            cliente=cliente,
            negocio=self.negocio_martillito,
        )

        # Cada negocio ve solo sus propias ventas
        ventas_barrio = Venta.objects.filter(
            cliente=cliente, negocio=self.negocio_barrio
        )
        ventas_martillito = Venta.objects.filter(
            cliente=cliente, negocio=self.negocio_martillito
        )

        self.assertEqual(ventas_barrio.count(), 1)
        self.assertEqual(ventas_barrio.first(), venta_barrio)
        self.assertEqual(ventas_martillito.count(), 1)
        self.assertEqual(ventas_martillito.first(), venta_martillito)

    def test_stock_aislado_por_negocio(self):
        """El stock de un producto en un negocio no afecta al otro."""
        # Ambos productos tienen el mismo nombre pero son de negocios distintos
        prod_barrio_2 = Producto.objects.create(
            nombre="Coca 500ml",
            codigo_barras="7790000000103",
            precio=Decimal("1500.00"),
            costo=Decimal("900.00"),
            stock=10,
            categoria=self.cat_barrio,
            negocio=self.negocio_barrio,
            activo=True,
        )

        # Descontar stock en Barrio no afecta a Martillito
        Producto.objects.filter(pk=self.prod_barrio.pk).update(
            stock=Decimal("5")
        )
        self.prod_martillito.refresh_from_db()
        self.assertEqual(self.prod_martillito.stock, 5)  # inalterado

    def test_reserva_stock_por_negocio(self):
        """Una reserva de stock solo afecta al producto de su propio negocio."""
        from pedidos.models import ReservaStock
        from django.utils import timezone
        from datetime import timedelta

        reserva = ReservaStock.objects.create(
            producto=self.prod_barrio,
            cantidad=3,
            fecha_expiracion=timezone.now() + timedelta(hours=48),
            estado="reservada",
        )

        self.assertEqual(reserva.producto.negocio, self.negocio_barrio)
        self.assertNotEqual(reserva.producto.negocio, self.negocio_martillito)


class FlujoCompletoTests(TestCase):
    """Prueba de flujo completo: compra online y retiro en local."""

    def setUp(self):
        self.grupo_admin = Group.objects.create(name="Administrador")
        self.grupo_cajero = Group.objects.create(name="Cajero")

        # Superadmin crea un negocio de prueba
        self.negocio_test = Negocio.objects.create(
            nombre="Test Comercio",
            slug="test-comercio",
            whatsapp="5491177778888",
            email="test@example.com",
            activo=True,
        )

        # Dueño del negocio
        self.dueño = User.objects.create_user(
            username="dueno_test", password="clave123", is_staff=True
        )
        self.dueño.groups.add(self.grupo_admin)
        Empleado.objects.create(
            usuario=self.dueño, negocio=self.negocio_test, activo=True
        )

        # Categoría y producto del negocio
        self.categoria = Categoria.objects.create(
            nombre="Bebidas", negocio=self.negocio_test
        )
        self.producto = Producto.objects.create(
            nombre="Coca 500ml",
            codigo_barras="7790000000200",
            precio=Decimal("1500.00"),
            costo=Decimal("900.00"),
            stock=10,
            categoria=self.categoria,
            negocio=self.negocio_test,
            activo=True,
        )

    def test_flujo_compra_online_y_retiro(self):
        """Flujo completo: pedido online → entrega en local → venta."""
        from pedidos.services import crear_pedido, registrar_entrega
        from ventas.services import registrar_venta_desde_items

        # 1. Dueño carga productos (ya creados en setUp)
        self.assertEqual(
            Producto.objects.filter(negocio=self.negocio_test).count(), 1
        )

        # 2. Cliente confirma pedido online (retiro en local)
        # Simulamos carrito en sesión
        from django.test import Client

        client = Client()
        session = client.session
        session["pedido"] = [
            {"producto_id": self.producto.pk, "cantidad": 2}
        ]
        session.save()

        # Simulamos request con negocio resuelto por middleware
        request = type("Request", (), {})()
        request.session = session
        request.negocio = self.negocio_test

        pedido = crear_pedido(
            request,
            nombre_cliente="Lucas Pérez",
            telefono="1155556666",
            comentario="",
            negocio=self.negocio_test,
            tipo_entrega="retiro",
            costo_envio=Decimal("0.00"),
        )

        self.assertEqual(pedido.estado, "pendiente")
        self.assertEqual(pedido.negocio, self.negocio_test)
        self.assertEqual(pedido.tipo_entrega, "retiro")
        self.assertEqual(pedido.costo_envio, Decimal("0.00"))
        self.assertEqual(pedido.total, Decimal("3000.00"))

        # 3. Se crea ReservaStock con 48h de expiración
        reservas = ReservaStock.objects.filter(pedido=pedido)
        self.assertEqual(reservas.count(), 1)
        reserva = reservas.first()
        self.assertEqual(reserva.estado, "reservada")
        self.assertEqual(reserva.cantidad, 2)

        # 4. Dueño ve el pedido en su panel
        self.client.login(username="dueno_test", password="clave123")
        respuesta = self.client.get(reverse("pedidos:lista_pedidos"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Lucas Pérez")

        # 5. Cliente retira y paga en el local
        cliente = Cliente.objects.create(
            nombre="Lucas",
            apellido="Pérez",
            dni="30111222",
            telefono="1155556666",
        )

        venta = registrar_entrega(
            pedido,
            cliente=cliente,
            metodo_pago="efectivo",
            usuario=self.dueño,
            monto_entregado="3000",
        )

        # 6. El pedido queda entregado y vinculado a la venta
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, "entregado")
        self.assertEqual(pedido.venta_id, venta.pk)
        self.assertEqual(pedido.cliente_id, cliente.pk)

        # 7. La venta pertenece al negocio correcto
        self.assertEqual(venta.negocio, self.negocio_test)
        self.assertTrue(venta.finalizada)
        self.assertEqual(venta.total, Decimal("3000.00"))

        # 8. El stock se descontó
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 8)  # 10 - 2

        # 9. La reserva se marcó como convertida
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, "convertida")

        # 10. La venta está vinculada al pedido y es del negocio correcto
        self.assertEqual(venta.pedidos.first(), pedido)


class DocumentosKpiTests(TestCase):
    """El KPI de deuda a proveedores solo debe contar facturas pendientes."""

    def setUp(self):
        self.grupo_admin = Group.objects.create(name="Administrador")
        self.negocio = Negocio.objects.create(
            nombre="Kiosco Documentos",
            slug="kiosco-documentos",
            activo=True,
        )
        self.admin = User.objects.create_user(
            username="admin_docs", password="clave123", is_staff=True
        )
        self.admin.groups.add(self.grupo_admin)
        Empleado.objects.create(
            usuario=self.admin, negocio=self.negocio, activo=True
        )
        self.proveedor = Proveedor.objects.create(
            nombre="EDESUR S.A.", negocio=self.negocio, activo=True
        )
        self.client.login(username="admin_docs", password="clave123")

    def crear_documento(self, numero, monto, pagado, estado, categoria="luz"):
        return Documento.objects.create(
            negocio=self.negocio,
            proveedor=self.proveedor,
            nombre_proveedor=self.proveedor.nombre,
            categoria=categoria,
            numero_factura=numero,
            monto=Decimal(monto),
            monto_pagado=Decimal(pagado),
            fecha_emision=date(2026, 9, 1),
            fecha_vencimiento=date(2026, 9, 30),
            estado=estado,
        )

    def test_deuda_total_solo_suma_facturas_pendientes(self):
        # Pendiente con pago parcial: debe 6000.
        self.crear_documento("P-001", "10000.00", "4000.00", "pendiente")
        # Pagada con pago parcial (dato inconsistente a propósito): NO debe.
        self.crear_documento("P-002", "5000.00", "2000.00", "pagada")
        # Anulada: NO debe.
        self.crear_documento("P-003", "7000.00", "0.00", "anulada")

        respuesta = self.client.get(reverse("negocios:lista_documentos"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context["total_deuda"], Decimal("6000.00"))

    def test_deuda_total_es_cero_sin_facturas_pendientes(self):
        self.crear_documento("P-001", "5000.00", "5000.00", "pagada")
        self.crear_documento("P-002", "7000.00", "0.00", "anulada")

        respuesta = self.client.get(reverse("negocios:lista_documentos"))

        self.assertEqual(respuesta.context["total_deuda"], Decimal("0.00"))

    def test_deuda_total_suma_varias_pendientes(self):
        self.crear_documento("P-001", "68450.00", "0.00", "pendiente")
        self.crear_documento("P-002", "38750.00", "25000.00", "pendiente")
        self.crear_documento("P-003", "18500.00", "18500.00", "pagada")

        respuesta = self.client.get(reverse("negocios:lista_documentos"))

        self.assertEqual(
            respuesta.context["total_deuda"], Decimal("82200.00")
        )

    def test_filtro_grupo_servicios_excluye_proveedores(self):
        self.crear_documento("D-001", "1000.00", "0.00", "pendiente", "luz")
        self.crear_documento(
            "D-002", "2000.00", "0.00", "pendiente", "proveedor"
        )

        respuesta = self.client.get(
            reverse("negocios:lista_documentos"), {"grupo": "servicios"}
        )

        numeros = [d.numero_factura for d in respuesta.context["documentos"]]
        self.assertIn("D-001", numeros)
        self.assertNotIn("D-002", numeros)

    def test_filtro_grupo_proveedores_excluye_servicios(self):
        self.crear_documento("D-001", "1000.00", "0.00", "pendiente", "luz")
        self.crear_documento(
            "D-002", "2000.00", "0.00", "pendiente", "proveedor"
        )

        respuesta = self.client.get(
            reverse("negocios:lista_documentos"), {"grupo": "proveedores"}
        )

        numeros = [d.numero_factura for d in respuesta.context["documentos"]]
        self.assertIn("D-002", numeros)
        self.assertNotIn("D-001", numeros)


class DocumentosListadoTests(TestCase):
    """Paginación, orden, filtro por proveedor y pagos FIFO."""

    def setUp(self):
        self.grupo_admin = Group.objects.create(name="Administrador")
        self.negocio = Negocio.objects.create(
            nombre="Kiosco Listado",
            slug="kiosco-listado",
            activo=True,
        )
        self.otro_negocio = Negocio.objects.create(
            nombre="Otro Negocio",
            slug="otro-negocio",
            activo=True,
        )
        self.admin = User.objects.create_user(
            username="admin_listado", password="clave123", is_staff=True
        )
        self.admin.groups.add(self.grupo_admin)
        Empleado.objects.create(
            usuario=self.admin, negocio=self.negocio, activo=True
        )
        self.proveedor_a = Proveedor.objects.create(
            nombre="Proveedor A", negocio=self.negocio, activo=True
        )
        self.proveedor_b = Proveedor.objects.create(
            nombre="Proveedor B", negocio=self.negocio, activo=True
        )
        self.client.login(username="admin_listado", password="clave123")

    def crear_documento(
        self,
        numero,
        monto,
        pagado="0.00",
        estado="pendiente",
        proveedor=None,
        emision=date(2026, 9, 1),
    ):
        return Documento.objects.create(
            negocio=self.negocio,
            proveedor=proveedor or self.proveedor_a,
            nombre_proveedor=(proveedor or self.proveedor_a).nombre,
            categoria="proveedor",
            numero_factura=numero,
            monto=Decimal(monto),
            monto_pagado=Decimal(pagado),
            fecha_emision=emision,
            fecha_vencimiento=date(2026, 9, 30),
            estado=estado,
        )

    def test_listado_pagina_de_a_10(self):
        for i in range(15):
            self.crear_documento(f"P-{i:03d}", "1000.00")

        respuesta = self.client.get(reverse("negocios:lista_documentos"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context["paginador"].num_pages, 2)
        self.assertEqual(len(respuesta.context["documentos"]), 10)

    def test_orden_por_monto_ascendente_y_descendente(self):
        self.crear_documento("P-300", "300.00")
        self.crear_documento("P-100", "100.00")
        self.crear_documento("P-200", "200.00")

        asc = self.client.get(
            reverse("negocios:lista_documentos"),
            {"orden": "monto", "dir": "asc"},
        )
        self.assertEqual(
            [d.monto for d in asc.context["documentos"]],
            [Decimal("100.00"), Decimal("200.00"), Decimal("300.00")],
        )

        desc = self.client.get(
            reverse("negocios:lista_documentos"),
            {"orden": "monto", "dir": "desc"},
        )
        self.assertEqual(
            [d.monto for d in desc.context["documentos"]],
            [Decimal("300.00"), Decimal("200.00"), Decimal("100.00")],
        )

    def test_filtro_por_proveedor(self):
        self.crear_documento("A-001", "1000.00", proveedor=self.proveedor_a)
        self.crear_documento("B-001", "2000.00", proveedor=self.proveedor_b)

        respuesta = self.client.get(
            reverse("negocios:lista_documentos"),
            {"proveedor": self.proveedor_a.pk},
        )

        numeros = [d.numero_factura for d in respuesta.context["documentos"]]
        self.assertEqual(numeros, ["A-001"])

    def test_resumen_deuda_por_proveedor(self):
        # A: 100.000 + 200.000 con 150.000 pagados -> debe 150.000.
        self.crear_documento("A-001", "100000.00", proveedor=self.proveedor_a)
        self.crear_documento(
            "A-002", "200000.00", pagado="150000.00", proveedor=self.proveedor_a
        )
        self.crear_documento("B-001", "50000.00", proveedor=self.proveedor_b)
        # Una factura pagada no debe sumar deuda.
        self.crear_documento(
            "A-003",
            "80000.00",
            pagado="80000.00",
            estado="pagada",
            proveedor=self.proveedor_a,
        )

        respuesta = self.client.get(reverse("negocios:lista_documentos"))

        resumen = {
            item["nombre"]: item for item in respuesta.context["resumen_proveedores"]
        }
        self.assertEqual(resumen["Proveedor A"]["saldo"], Decimal("150000.00"))
        self.assertEqual(resumen["Proveedor B"]["saldo"], Decimal("50000.00"))
        self.assertEqual(
            respuesta.context["total_deuda"], Decimal("200000.00")
        )

    def test_pago_a_proveedor_aplica_fifo(self):
        antigua = self.crear_documento(
            "A-001",
            "100000.00",
            proveedor=self.proveedor_a,
            emision=date(2026, 8, 1),
        )
        nueva = self.crear_documento(
            "A-002",
            "200000.00",
            proveedor=self.proveedor_a,
            emision=date(2026, 9, 1),
        )

        respuesta = self.client.post(
            reverse("negocios:pagar_proveedor", args=[self.proveedor_a.pk]),
            {"monto": "150000.00"},
        )

        self.assertEqual(respuesta.status_code, 302)
        antigua.refresh_from_db()
        nueva.refresh_from_db()
        self.assertEqual(antigua.monto_pagado, Decimal("100000.00"))
        self.assertEqual(antigua.estado, "pagada")
        self.assertEqual(nueva.monto_pagado, Decimal("50000.00"))
        self.assertEqual(nueva.estado, "pendiente")

    def test_pago_mayor_a_la_deuda_se_rechaza(self):
        documento = self.crear_documento("A-001", "100000.00")

        respuesta = self.client.post(
            reverse("negocios:pagar_proveedor", args=[self.proveedor_a.pk]),
            {"monto": "150000.00"},
        )

        self.assertEqual(respuesta.status_code, 302)
        documento.refresh_from_db()
        self.assertEqual(documento.monto_pagado, Decimal("0.00"))

    def test_pago_cero_se_rechaza(self):
        documento = self.crear_documento("A-001", "100000.00")

        self.client.post(
            reverse("negocios:pagar_proveedor", args=[self.proveedor_a.pk]),
            {"monto": "0"},
        )

        documento.refresh_from_db()
        self.assertEqual(documento.monto_pagado, Decimal("0.00"))

    def test_no_se_puede_pagar_proveedor_de_otro_negocio(self):
        ajeno = Proveedor.objects.create(
            nombre="Ajeno", negocio=self.otro_negocio, activo=True
        )

        respuesta = self.client.get(
            reverse("negocios:pagar_proveedor", args=[ajeno.pk])
        )

        self.assertEqual(respuesta.status_code, 404)

    def test_factura_por_vencer_muestra_la_fecha_en_rojo(self):
        """En vez de la etiqueta "Por vencer" se muestra la fecha exacta."""
        hoy = timezone.localdate()
        documento = self.crear_documento("V-001", "10000.00")
        documento.fecha_vencimiento = hoy + timedelta(days=3)
        documento.save(update_fields=["fecha_vencimiento"])

        respuesta = self.client.get(reverse("negocios:lista_documentos"))

        self.assertContains(respuesta, "badge-estado-por-vencer")
        self.assertContains(
            respuesta, (hoy + timedelta(days=3)).strftime("%d/%m/%Y")
        )
        self.assertNotContains(respuesta, "Por vencer")

    def test_factura_vencida_sigue_marcada_como_vencida(self):
        hoy = timezone.localdate()
        documento = self.crear_documento("V-002", "10000.00")
        documento.fecha_vencimiento = hoy - timedelta(days=2)
        documento.save(update_fields=["fecha_vencimiento"])

        respuesta = self.client.get(reverse("negocios:lista_documentos"))

        self.assertContains(respuesta, "badge-estado-vencida")
        self.assertNotContains(respuesta, "badge-estado-por-vencer")


class DocumentosSeparacionTests(TestCase):
    """Facturas y Proveedores son módulos separados, sin mezclar datos."""

    def setUp(self):
        self.grupo_admin = Group.objects.create(name="Administrador")
        self.negocio = Negocio.objects.create(
            nombre="Kiosco Separado",
            slug="kiosco-separado",
            activo=True,
        )
        self.admin = User.objects.create_user(
            username="admin_separado", password="clave123", is_staff=True
        )
        self.admin.groups.add(self.grupo_admin)
        Empleado.objects.create(
            usuario=self.admin, negocio=self.negocio, activo=True
        )
        self.proveedor = Proveedor.objects.create(
            nombre="Distribuidora Norte", negocio=self.negocio, activo=True
        )
        self.client.login(username="admin_separado", password="clave123")

    def crear_documento(self, numero, categoria, monto="1000.00", pagado="0.00"):
        return Documento.objects.create(
            negocio=self.negocio,
            proveedor=self.proveedor if categoria == "proveedor" else None,
            nombre_proveedor="Distribuidora Norte"
            if categoria == "proveedor"
            else "EDESUR",
            categoria=categoria,
            numero_factura=numero,
            monto=Decimal(monto),
            monto_pagado=Decimal(pagado),
            fecha_emision=date(2026, 9, 1),
            fecha_vencimiento=date(2026, 9, 30),
            estado="pendiente",
        )

    def test_lista_facturas_solo_muestra_servicios(self):
        self.crear_documento("S-001", "luz", monto="3000.00")
        self.crear_documento("P-001", "proveedor", monto="9000.00")

        respuesta = self.client.get(reverse("negocios:lista_facturas"))

        self.assertEqual(respuesta.status_code, 200)
        numeros = [d.numero_factura for d in respuesta.context["documentos"]]
        self.assertEqual(numeros, ["S-001"])
        self.assertEqual(respuesta.context["resumen_proveedores"], [])
        self.assertEqual(list(respuesta.context["proveedores"]), [])
        self.assertEqual(respuesta.context["total_deuda"], Decimal("3000.00"))
        self.assertTrue(respuesta.context["es_facturas"])
        self.assertFalse(respuesta.context["es_proveedores"])

    def test_lista_proveedores_solo_muestra_facturas_de_mercaderia(self):
        self.crear_documento("S-001", "luz", monto="3000.00")
        self.crear_documento("P-001", "proveedor", monto="9000.00")

        respuesta = self.client.get(reverse("negocios:lista_proveedores"))

        self.assertEqual(respuesta.status_code, 200)
        numeros = [d.numero_factura for d in respuesta.context["documentos"]]
        self.assertEqual(numeros, ["P-001"])
        resumen = respuesta.context["resumen_proveedores"]
        self.assertEqual(len(resumen), 1)
        self.assertEqual(resumen[0]["saldo"], Decimal("9000.00"))
        self.assertEqual(respuesta.context["total_deuda"], Decimal("9000.00"))
        self.assertTrue(respuesta.context["es_proveedores"])
        self.assertFalse(respuesta.context["es_facturas"])

    def test_lista_facturas_ignora_filtro_de_proveedor(self):
        self.crear_documento("S-001", "luz")
        self.crear_documento("P-001", "proveedor")

        respuesta = self.client.get(
            reverse("negocios:lista_facturas"),
            {"proveedor": self.proveedor.pk, "categoria": "proveedor"},
        )

        numeros = [d.numero_factura for d in respuesta.context["documentos"]]
        self.assertEqual(numeros, ["S-001"])

    def test_crear_factura_de_proveedor_redirige_al_modulo_proveedores(self):
        respuesta = self.client.post(
            reverse("negocios:crear_documento") + "?grupo=proveedores",
            {
                "proveedor": self.proveedor.pk,
                "categoria": "proveedor",
                "numero_factura": "P-100",
                "monto": "1500.00",
                "fecha_emision": "2026-09-01",
                "fecha_vencimiento": "2026-09-30",
            },
        )

        self.assertRedirects(
            respuesta, reverse("negocios:lista_proveedores")
        )

    def test_crear_servicio_redirige_al_modulo_facturas(self):
        respuesta = self.client.post(
            reverse("negocios:crear_documento") + "?grupo=servicios",
            {
                "categoria": "luz",
                "nombre_proveedor": "EDESUR",
                "numero_factura": "S-100",
                "monto": "2500.00",
                "fecha_emision": "2026-09-01",
                "fecha_vencimiento": "2026-09-30",
            },
        )

        self.assertRedirects(respuesta, reverse("negocios:lista_facturas"))

    def test_crear_desde_proveedores_no_permite_categoria_servicio(self):
        respuesta = self.client.post(
            reverse("negocios:crear_documento") + "?grupo=proveedores",
            {
                "proveedor": self.proveedor.pk,
                "categoria": "luz",
                "numero_factura": "P-200",
                "monto": "1000.00",
                "fecha_emision": "2026-09-01",
                "fecha_vencimiento": "2026-09-30",
            },
        )

        self.assertRedirects(
            respuesta, reverse("negocios:lista_proveedores")
        )
        documento = Documento.objects.get(numero_factura="P-200")
        self.assertEqual(documento.categoria, "proveedor")

    def test_formulario_de_proveedores_solo_ofrece_categoria_proveedor(self):
        respuesta = self.client.get(
            reverse("negocios:crear_documento"), {"grupo": "proveedores"}
        )

        categorias = [valor for valor, _ in respuesta.context["categorias"]]
        self.assertEqual(categorias, ["proveedor"])

    def test_formulario_de_facturas_no_ofrece_categoria_proveedor(self):
        respuesta = self.client.get(
            reverse("negocios:crear_documento"), {"grupo": "servicios"}
        )

        categorias = [valor for valor, _ in respuesta.context["categorias"]]
        self.assertNotIn("proveedor", categorias)
        self.assertIn("luz", categorias)

    def test_pago_a_proveedor_redirige_al_modulo_proveedores(self):
        self.crear_documento("P-300", "proveedor", monto="1000.00")

        respuesta = self.client.post(
            reverse("negocios:pagar_proveedor", args=[self.proveedor.pk]),
            {"monto": "1000.00"},
        )

        self.assertRedirects(
            respuesta,
            f"{reverse('negocios:lista_proveedores')}"
            f"?proveedor={self.proveedor.pk}",
        )


class BackfillNegociosTests(TestCase):
    """backfill_negocios: repara ventas y pedidos que quedaron sin negocio."""

    def setUp(self):
        self.negocio_barrio = Negocio.objects.create(
            nombre="Kiosco De Barrio", slug="de-barrio", activo=True
        )
        self.negocio_ferre = Negocio.objects.create(
            nombre="Ferretería Martillito",
            slug="ferreteria-martillito",
            activo=True,
        )

        self.cajero = User.objects.create_user(
            username="cajero_backfill", password="clave123"
        )
        Empleado.objects.create(
            usuario=self.cajero, negocio=self.negocio_barrio, activo=True
        )

        self.categoria = Categoria.objects.create(
            nombre="Bebidas", negocio=self.negocio_barrio
        )
        self.producto_barrio = Producto.objects.create(
            nombre="Coca 500ml",
            codigo_barras="7790000000500",
            precio=Decimal("1500.00"),
            stock=10,
            categoria=self.categoria,
            negocio=self.negocio_barrio,
        )
        self.producto_ferre = Producto.objects.create(
            nombre="Martillo",
            codigo_barras="7790000000501",
            precio=Decimal("9000.00"),
            stock=5,
            categoria=self.categoria,
            negocio=self.negocio_ferre,
        )

    def backfill(self):
        from django.core.management import call_command

        salida = io.StringIO()
        call_command("backfill_negocios", stdout=salida)
        return salida.getvalue()

    def venta(self, usuario=None, negocio=None):
        return Venta.objects.create(
            total=Decimal("1500.00"),
            finalizada=True,
            metodo_pago="efectivo",
            usuario=usuario,
            negocio=negocio,
        )

    def pedido_con(self, productos):
        pedido = Pedido.objects.create(nombre_cliente="Lucía Gómez")
        for producto in productos:
            ItemPedido.objects.create(
                pedido=pedido,
                producto=producto,
                nombre_producto=producto.nombre,
                cantidad=1,
                precio_unitario=producto.precio,
            )
        return pedido

    def test_asigna_el_negocio_del_empleado_a_las_ventas(self):
        venta_bug = self.venta(usuario=self.cajero)
        venta_ya_asignada = self.venta(
            usuario=self.cajero, negocio=self.negocio_ferre
        )
        sin_usuario = self.venta()

        salida = self.backfill()

        venta_bug.refresh_from_db()
        self.assertEqual(venta_bug.negocio, self.negocio_barrio)
        # No toca las que ya tienen negocio ni resuelve las sin usuario.
        venta_ya_asignada.refresh_from_db()
        self.assertEqual(venta_ya_asignada.negocio, self.negocio_ferre)
        sin_usuario.refresh_from_db()
        self.assertIsNone(sin_usuario.negocio)
        self.assertIn("Backfill de negocios: 1 ventas y 0 pedidos", salida)

    def test_asigna_el_negocio_de_los_items_a_los_pedidos(self):
        pedido_mismo = self.pedido_con([self.producto_barrio])
        pedido_mixto = self.pedido_con(
            [self.producto_barrio, self.producto_ferre]
        )
        sin_items = self.pedido_con([])

        salida = self.backfill()

        pedido_mismo.refresh_from_db()
        self.assertEqual(pedido_mismo.negocio, self.negocio_barrio)
        pedido_mixto.refresh_from_db()
        self.assertIsNone(pedido_mixto.negocio)
        sin_items.refresh_from_db()
        self.assertIsNone(sin_items.negocio)
        self.assertIn("0 ventas y 1 pedidos", salida)

    def test_pedido_con_producto_eliminado_no_se_toca(self):
        pedido = self.pedido_con([self.producto_barrio])
        ItemPedido.objects.filter(pedido=pedido).update(producto=None)

        self.backfill()

        pedido.refresh_from_db()
        self.assertIsNone(pedido.negocio)

    def test_es_idempotente(self):
        self.venta(usuario=self.cajero)
        self.pedido_con([self.producto_barrio])

        self.backfill()
        salida = self.backfill()

        self.assertIn("0 ventas y 0 pedidos asignados", salida)
        self.assertEqual(
            Venta.objects.filter(negocio=self.negocio_barrio).count(), 1
        )
        self.assertEqual(
            Pedido.objects.filter(negocio=self.negocio_barrio).count(), 1
        )

class AdjuntosEnBaseTests(TestCase):
    """Los adjuntos se guardan en la base y se ven solo desde su negocio."""

    def setUp(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        self.pdf = b"%PDF-1.4 factura de prueba"
        grupo, _ = Group.objects.get_or_create(name="Administrador")
        self.negocio = Negocio.objects.create(nombre="A", slug="a")
        otro = Negocio.objects.create(nombre="B", slug="b")
        self.user = User.objects.create_user("adm_a", password="x")
        self.user.groups.add(grupo)
        Empleado.objects.create(usuario=self.user, negocio=self.negocio, activo=True)
        self.ajeno = User.objects.create_user("adm_b", password="x")
        Empleado.objects.create(usuario=self.ajeno, negocio=otro, activo=True)
        self.doc = Documento.objects.create(
            negocio=self.negocio, nombre_proveedor="P", categoria="proveedor",
            numero_factura="F-1", monto=Decimal("100"), monto_pagado=Decimal("0"),
            fecha_emision=date(2026, 9, 1), fecha_vencimiento=date(2026, 9, 30),
            estado="pendiente",
        )
        self.client.force_login(self.user)
        self.client.post(
            reverse("negocios:subir_adjunto", args=[self.doc.pk]),
            {"archivo": SimpleUploadedFile("factura.pdf", self.pdf, content_type="application/pdf")},
        )
        self.doc.refresh_from_db()

    def test_se_ve_el_adjunto(self):
        r = self.client.get(self.doc.archivo.url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, self.pdf)
        self.assertEqual(r["Content-Type"], "application/pdf")

    def test_otro_negocio_no_lo_ve(self):
        self.client.force_login(self.ajeno)
        self.assertEqual(self.client.get(self.doc.archivo.url).status_code, 404)
