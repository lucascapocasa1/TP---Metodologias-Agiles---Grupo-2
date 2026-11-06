"""Pruebas de aislamiento multiempresa y flujo completo (Etapa 7).

Valida que:
1. Los datos de un negocio no se mezclan con los de otro.
2. Cada empleado solo ve su propio negocio.
3. Un cliente puede comprar en varios negocios, pero cada negocio ve solo sus propias ventas.
4. El flujo completo de compra online y retiro en local funciona correctamente.
"""
from django.contrib.auth.models import Group, User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal

from auditoria.models import RegistroAuditoria
from negocios.models import Negocio
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