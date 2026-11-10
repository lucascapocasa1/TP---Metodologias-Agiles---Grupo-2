"""Tests de la Fase B: pagos con historial (PagoDocumento), FIFO con grupo,
deshacer de operación y estado derivado de documentos."""
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.utils import timezone

from usuarios.models import Empleado

from . import services
from .models import Documento, Negocio, PagoDocumento, Proveedor
from .views import _resumen_por_proveedor


class PagosServicesTests(TestCase):
    """Reglas de pago: parcial, total, anulada, saldo como piso."""

    def setUp(self):
        self.grupo = Group.objects.create(name="Administrador")
        self.negocio = Negocio.objects.create(
            nombre="Kiosco Pagos", slug="kiosco-pagos", activo=True
        )
        self.admin = User.objects.create_user(
            username="admin_pagos", password="clave123", is_staff=True
        )
        self.admin.groups.add(self.grupo)
        Empleado.objects.create(
            usuario=self.admin, negocio=self.negocio, activo=True
        )
        self.proveedor = Proveedor.objects.create(
            nombre="Distribuidora Prueba", negocio=self.negocio, activo=True
        )

    def crear_documento(self, numero, monto, pagado="0.00", estado="pendiente"):
        return Documento.objects.create(
            negocio=self.negocio,
            proveedor=self.proveedor,
            nombre_proveedor=self.proveedor.nombre,
            categoria="proveedor",
            numero_factura=numero,
            monto=Decimal(monto),
            monto_pagado=Decimal(pagado),
            fecha_emision=date(2026, 9, 1),
            fecha_vencimiento=date(2026, 10, 1),
            estado=estado,
        )

    def test_pago_parcial_actualiza_saldo_y_estado(self):
        doc = self.crear_documento("P-001", "10000.00")
        services.registrar_pago(doc, Decimal("4000.00"), usuario=self.admin)
        doc.refresh_from_db()
        self.assertEqual(doc.monto_pagado, Decimal("4000.00"))
        self.assertEqual(doc.estado, "pendiente")
        self.assertEqual(doc.monto_pendiente, Decimal("6000.00"))
        # Queda un pago registrado
        self.assertEqual(doc.pagos_registrados.count(), 1)

    def test_pago_total_marca_pagada(self):
        doc = self.crear_documento("P-001", "10000.00")
        services.registrar_pago(doc, Decimal("10000.00"), usuario=self.admin)
        doc.refresh_from_db()
        self.assertEqual(doc.monto_pagado, Decimal("10000.00"))
        self.assertEqual(doc.estado, "pagada")

    def test_no_se_puede_pagar_documento_anulado(self):
        doc = self.crear_documento("P-001", "10000.00", estado="anulada")
        with self.assertRaises(ValueError):
            services.registrar_pago(doc, Decimal("1000.00"), usuario=self.admin)

    def test_no_se_puede_pagar_mas_que_el_saldo(self):
        doc = self.crear_documento("P-001", "10000.00")
        with self.assertRaises(ValueError):
            services.registrar_pago(doc, Decimal("15000.00"), usuario=self.admin)
        doc.refresh_from_db()
        self.assertEqual(doc.monto_pagado, Decimal("0.00"))

    def test_editar_monto_menor_a_lo_pagado_se_rechaza(self):
        doc = self.crear_documento("P-001", "10000.00", pagado="4000.00")
        with self.assertRaises(ValueError):
            services.validar_documento(
                "3000.00", date(2026, 9, 1), date(2026, 10, 1),
                monto_pagado=doc.monto_pagado,
            )


class FIFOConGrupoTests(TestCase):
    """El pago FIFO a un proveedor agrupa los pagos bajo un mismo grupo."""

    def setUp(self):
        self.grupo = Group.objects.create(name="Administrador")
        self.negocio = Negocio.objects.create(
            nombre="Kiosco FIFO", slug="kiosco-fifo", activo=True
        )
        self.admin = User.objects.create_user(
            username="admin_fifo", password="clave123", is_staff=True
        )
        self.admin.groups.add(self.grupo)
        Empleado.objects.create(
            usuario=self.admin, negocio=self.negocio, activo=True
        )
        self.proveedor = Proveedor.objects.create(
            nombre="Proveedor FIFO", negocio=self.negocio, activo=True
        )
        self.antigua = Documento.objects.create(
            negocio=self.negocio, proveedor=self.proveedor,
            nombre_proveedor=self.proveedor.nombre, categoria="proveedor",
            numero_factura="A-001", monto=Decimal("100000.00"),
            monto_pagado=Decimal("0.00"), fecha_emision=date(2026, 8, 1),
            fecha_vencimiento=date(2026, 9, 1), estado="pendiente",
        )
        self.nueva = Documento.objects.create(
            negocio=self.negocio, proveedor=self.proveedor,
            nombre_proveedor=self.proveedor.nombre, categoria="proveedor",
            numero_factura="A-002", monto=Decimal("200000.00"),
            monto_pagado=Decimal("0.00"), fecha_emision=date(2026, 9, 1),
            fecha_vencimiento=date(2026, 9, 15), estado="pendiente",
        )

    def test_fifo_aplica_por_vencimiento_y_grupa_pagos(self):
        # Vence primero la antigua (09/01), luego la nueva (09/15).
        resultado = services.aplicar_pago_proveedor(
            self.proveedor, Decimal("150000.00"),
            usuario=self.admin, nota="Pago de prueba",
        )
        self.assertEqual(resultado["aplicado"], Decimal("150000.00"))
        self.assertEqual(resultado["sobrante"], Decimal("0.00"))

        self.antigua.refresh_from_db()
        self.nueva.refresh_from_db()
        self.assertEqual(self.antigua.monto_pagado, Decimal("100000.00"))
        self.assertEqual(self.antigua.estado, "pagada")
        self.assertEqual(self.nueva.monto_pagado, Decimal("50000.00"))
        self.assertEqual(self.nueva.estado, "pendiente")

        # Todos los pagos comparten el mismo grupo_pago
        pagos = PagoDocumento.objects.filter(
            negocio=self.negocio, grupo_pago=resultado["grupo_pago"]
        )
        self.assertEqual(pagos.count(), 2)
        montos = sorted([p.monto for p in pagos])
        self.assertEqual(montos, [Decimal("50000.00"), Decimal("100000.00")])

    def test_deshacer_pago_revierte_operacion(self):
        resultado = services.aplicar_pago_proveedor(
            self.proveedor, Decimal("150000.00"), usuario=self.admin
        )
        grupo = resultado["grupo_pago"]

        tocados = services.deshacer_pago(grupo)
        self.assertEqual(len(tocados), 2)

        self.antigua.refresh_from_db()
        self.nueva.refresh_from_db()
        self.assertEqual(self.antigua.monto_pagado, Decimal("0.00"))
        self.assertEqual(self.antigua.estado, "pendiente")
        self.assertEqual(self.nueva.monto_pagado, Decimal("0.00"))
        self.assertEqual(self.nueva.estado, "pendiente")

        # Los pagos del grupo fueron borrados
        self.assertEqual(
            PagoDocumento.objects.filter(grupo_pago=grupo).count(), 0
        )


class AgrupamientoTextoSueltoTests(TestCase):
    """Cada nombre suelto es su propia cuenta de proveedor."""

    def setUp(self):
        self.grupo = Group.objects.create(name="Administrador")
        self.negocio = Negocio.objects.create(
            nombre="Kiosco Texto", slug="kiosco-texto", activo=True
        )
        self.admin = User.objects.create_user(
            username="admin_texto", password="clave123", is_staff=True
        )
        self.admin.groups.add(self.grupo)
        Empleado.objects.create(
            usuario=self.admin, negocio=self.negocio, activo=True
        )

    def test_nombre_suelto_es_su_propia_cuenta(self):
        Documento.objects.create(
            negocio=self.negocio, proveedor=None,
            nombre_proveedor="Arcor", categoria="proveedor",
            numero_factura="A-001", monto=Decimal("10000.00"),
            monto_pagado=Decimal("0.00"), fecha_emision=date(2026, 9, 1),
            fecha_vencimiento=date(2026, 10, 1), estado="pendiente",
        )
        Documento.objects.create(
            negocio=self.negocio, proveedor=None,
            nombre_proveedor="arcor S.A.", categoria="proveedor",
            numero_factura="A-002", monto=Decimal("20000.00"),
            monto_pagado=Decimal("0.00"), fecha_emision=date(2026, 9, 1),
            fecha_vencimiento=date(2026, 10, 1), estado="pendiente",
        )
        documentos = Documento.objects.filter(negocio=self.negocio)
        resumen = _resumen_por_proveedor(documentos, hoy=date(2026, 11, 1))
        nombres = [item["nombre"] for item in resumen]
        # "Arcor" y "arcor S.A." son cuentas distintas (normalizado a minúsculas)
        self.assertEqual(len(resumen), 2)
        saldos = {item["nombre"]: item["saldo"] for item in resumen}
        self.assertEqual(saldos["Arcor"], Decimal("10000.00"))
        self.assertEqual(saldos["arcor S.A."], Decimal("20000.00"))
