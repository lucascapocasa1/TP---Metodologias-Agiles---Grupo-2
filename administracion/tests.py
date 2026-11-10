from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.urls import reverse

from negocios.models import Documento, Negocio
from usuarios.models import Empleado
from ventas.models import Categoria, Producto


class DashboardTests(TestCase):
    def setUp(self):
        self.grupo_admin = Group.objects.create(name="Administrador")
        self.grupo_cajero = Group.objects.create(name="Cajero")

        self.admin = User.objects.create_user(
            username="admin_test", password="claveSegura123", is_staff=True
        )
        self.admin.groups.add(self.grupo_admin)

        self.cajero = User.objects.create_user(
            username="cajero_test", password="claveSegura123"
        )
        self.cajero.groups.add(self.grupo_cajero)

        self.superuser = User.objects.create_superuser(
            username="super_test", password="claveSegura123"
        )

    def test_acceso_requiere_login(self):
        respuesta = self.client.get(reverse("administracion:dashboard"))
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn("login", respuesta.url)

    def test_administrador_puede_acceder(self):
        self.client.login(username="admin_test", password="claveSegura123")
        respuesta = self.client.get(reverse("administracion:dashboard"))
        self.assertEqual(respuesta.status_code, 200)

    def test_cajero_recibe_403(self):
        self.client.login(username="cajero_test", password="claveSegura123")
        respuesta = self.client.get(reverse("administracion:dashboard"))
        self.assertEqual(respuesta.status_code, 403)

    def test_superuser_puede_acceder(self):
        self.client.login(username="super_test", password="claveSegura123")
        respuesta = self.client.get(reverse("administracion:dashboard"))
        self.assertEqual(respuesta.status_code, 200)

    def test_usa_template_correcto(self):
        self.client.login(username="admin_test", password="claveSegura123")
        respuesta = self.client.get(reverse("administracion:dashboard"))
        self.assertTemplateUsed(respuesta, "administracion/dashboard.html")

    def test_usuario_sin_grupo_recibe_403(self):
        user_sin_rol = User.objects.create_user(
            username="sin_rol", password="claveSegura123"
        )
        self.client.login(username="sin_rol", password="claveSegura123")
        respuesta = self.client.get(reverse("administracion:dashboard"))
        self.assertEqual(respuesta.status_code, 403)

    def test_dashboard_muestra_estadisticas(self):
        self.client.login(username="admin_test", password="claveSegura123")
        respuesta = self.client.get(reverse("administracion:dashboard"))
        self.assertEqual(respuesta.context["total_usuarios"], 3)
        # Los KPIs de usuarios activos / admins / cajeros ya no van: esa
        # info se ve en "Gestionar usuarios".
        self.assertNotIn("usuarios_activos", respuesta.context)
        self.assertNotIn("admins", respuesta.context)
        self.assertNotIn("cajeros", respuesta.context)

    def test_kpi_total_usuarios_linkea_a_gestionar_usuarios(self):
        self.client.login(username="admin_test", password="claveSegura123")
        respuesta = self.client.get(reverse("administracion:dashboard"))

        self.assertContains(
            respuesta,
            f'href="{reverse("administracion:listar_usuarios")}"',
            html=False,
        )

    def test_kpi_clientes_fiar_linkea_al_listado_filtrado(self):
        self.client.login(username="admin_test", password="claveSegura123")
        respuesta = self.client.get(reverse("administracion:dashboard"))

        self.assertContains(respuesta, "?cuenta=corriente")

    def test_kpi_stock_bajo_cuenta_productos_y_linkea_al_reporte(self):
        """El KPI muestra cuántos productos tienen stock bajo y es un link
        al reporte de stock, donde se ven cuáles son (mejora 6)."""
        categoria = Categoria.objects.create(nombre="Bebidas")
        Producto.objects.create(
            nombre="Alfajor", precio=Decimal("100.00"), costo=Decimal("60.00"),
            stock=2, categoria=categoria,
        )
        Producto.objects.create(
            nombre="Gaseosa", precio=Decimal("100.00"), costo=Decimal("60.00"),
            stock=10, categoria=categoria,
        )

        self.client.login(username="admin_test", password="claveSegura123")
        respuesta = self.client.get(reverse("administracion:dashboard"))

        self.assertEqual(respuesta.context["productos_stock_bajo"], 1)
        self.assertEqual(respuesta.context["umbral_stock_bajo"], 5)
        # La ficha es un link al reporte de stock (ancla de la tabla de bajos).
        self.assertContains(
            respuesta,
            f'href="{reverse("administracion:reportes_stock")}#stock-bajo"',
        )

    def test_kpi_stock_bajo_ignora_inactivos(self):
        categoria = Categoria.objects.create(nombre="Bebidas")
        Producto.objects.create(
            nombre="Descontinuado", precio=Decimal("100.00"),
            costo=Decimal("60.00"), stock=1, categoria=categoria, activo=False,
        )
        self.client.login(username="admin_test", password="claveSegura123")
        respuesta = self.client.get(reverse("administracion:dashboard"))
        self.assertEqual(respuesta.context["productos_stock_bajo"], 0)


class ListarUsuariosTests(TestCase):
    def setUp(self):
        self.grupo_admin = Group.objects.create(name="Administrador")
        self.admin = User.objects.create_user(
            username="admin_test", password="claveSegura123"
        )
        self.admin.groups.add(self.grupo_admin)
        self.cajero = User.objects.create_user(
            username="cajero_test", password="claveSegura123", first_name="Juan"
        )

    def test_acceso_requiere_login(self):
        respuesta = self.client.get(reverse("administracion:listar_usuarios"))
        self.assertEqual(respuesta.status_code, 302)

    def test_admin_puede_listar(self):
        self.client.login(username="admin_test", password="claveSegura123")
        respuesta = self.client.get(reverse("administracion:listar_usuarios"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(respuesta.context["usuarios"]), 2)

    def test_busqueda_por_username(self):
        self.client.login(username="admin_test", password="claveSegura123")
        respuesta = self.client.get(
            reverse("administracion:listar_usuarios"), {"buscar": "cajero"}
        )
        self.assertEqual(len(respuesta.context["usuarios"]), 1)

    def test_busqueda_por_nombre(self):
        self.client.login(username="admin_test", password="claveSegura123")
        respuesta = self.client.get(
            reverse("administracion:listar_usuarios"), {"buscar": "Juan"}
        )
        self.assertEqual(len(respuesta.context["usuarios"]), 1)

    def test_filtro_por_rol(self):
        self.client.login(username="admin_test", password="claveSegura123")
        respuesta = self.client.get(
            reverse("administracion:listar_usuarios"), {"rol": "Administrador"}
        )
        self.assertEqual(len(respuesta.context["usuarios"]), 1)


class CrearUsuarioTests(TestCase):
    def setUp(self):
        self.grupo_admin = Group.objects.create(name="Administrador")
        self.admin = User.objects.create_user(
            username="admin_test", password="claveSegura123"
        )
        self.admin.groups.add(self.grupo_admin)

    def test_acceso_requiere_login(self):
        respuesta = self.client.get(reverse("administracion:crear_usuario"))
        self.assertEqual(respuesta.status_code, 302)

    def test_admin_puede_ver_formulario(self):
        self.client.login(username="admin_test", password="claveSegura123")
        respuesta = self.client.get(reverse("administracion:crear_usuario"))
        self.assertEqual(respuesta.status_code, 200)

    def test_admin_puede_crear_usuario(self):
        self.client.login(username="admin_test", password="claveSegura123")
        respuesta = self.client.post(
            reverse("administracion:crear_usuario"),
            {
                "username": "nuevo_usuario",
                "first_name": "Nuevo",
                "last_name": "Usuario",
                "email": "nuevo@test.com",
                "password": "clave123456",
                "password2": "clave123456",
                "is_active": True,
            },
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(User.objects.filter(username="nuevo_usuario").exists())


class EditarUsuarioTests(TestCase):
    def setUp(self):
        self.grupo_admin = Group.objects.create(name="Administrador")
        self.admin = User.objects.create_user(
            username="admin_test", password="claveSegura123"
        )
        self.admin.groups.add(self.grupo_admin)
        self.usuario = User.objects.create_user(
            username="usuario_test", password="clave123", first_name="Original"
        )

    def test_editar_usuario(self):
        self.client.login(username="admin_test", password="claveSegura123")
        respuesta = self.client.post(
            reverse("administracion:editar_usuario", args=[self.usuario.id]),
            {
                "username": "usuario_test",
                "first_name": "Modificado",
                "last_name": "",
                "email": "",
                "is_active": True,
            },
        )
        self.assertEqual(respuesta.status_code, 302)
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.first_name, "Modificado")


class AsignarRolesTests(TestCase):
    def setUp(self):
        self.grupo_admin = Group.objects.create(name="Administrador")
        self.grupo_cajero = Group.objects.create(name="Cajero")
        self.admin = User.objects.create_user(
            username="admin_test", password="claveSegura123"
        )
        self.admin.groups.add(self.grupo_admin)
        self.usuario = User.objects.create_user(
            username="usuario_test", password="clave123"
        )

    def test_asignar_rol(self):
        self.client.login(username="admin_test", password="claveSegura123")
        respuesta = self.client.post(
            reverse("administracion:asignar_roles", args=[self.usuario.id]),
            {"grupos": [self.grupo_cajero.id]},
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(self.usuario.groups.filter(name="Cajero").exists())

    def test_quitar_rol(self):
        self.usuario.groups.add(self.grupo_cajero)
        self.client.login(username="admin_test", password="claveSegura123")
        respuesta = self.client.post(
            reverse("administracion:asignar_roles", args=[self.usuario.id]),
            {"grupos": []},
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertFalse(self.usuario.groups.filter(name="Cajero").exists())


class ToggleUsuarioTests(TestCase):
    def setUp(self):
        self.grupo_admin = Group.objects.create(name="Administrador")
        self.admin = User.objects.create_user(
            username="admin_test", password="claveSegura123"
        )
        self.admin.groups.add(self.grupo_admin)
        self.usuario = User.objects.create_user(
            username="usuario_test", password="clave123", is_active=True
        )

    def test_desactivar_usuario(self):
        self.client.login(username="admin_test", password="claveSegura123")
        respuesta = self.client.get(
            reverse("administracion:toggle_usuario", args=[self.usuario.id])
        )
        self.assertEqual(respuesta.status_code, 302)
        self.usuario.refresh_from_db()
        self.assertFalse(self.usuario.is_active)

    def test_no_puede_desactivar_superusuario(self):
        superuser = User.objects.create_superuser(
            username="super_test", password="clave123"
        )
        self.client.login(username="admin_test", password="claveSegura123")
        respuesta = self.client.get(
            reverse("administracion:toggle_usuario", args=[superuser.id])
        )
        self.assertEqual(respuesta.status_code, 302)
        superuser.refresh_from_db()
        self.assertTrue(superuser.is_active)


class EliminarUsuarioTests(TestCase):
    def setUp(self):
        self.grupo_admin = Group.objects.create(name="Administrador")
        self.admin = User.objects.create_user(
            username="admin_test", password="claveSegura123"
        )
        self.admin.groups.add(self.grupo_admin)
        self.usuario = User.objects.create_user(
            username="usuario_test", password="clave123"
        )

    def test_no_puede_eliminar_superusuario(self):
        superuser = User.objects.create_superuser(
            username="super_test", password="clave123"
        )
        self.client.login(username="admin_test", password="claveSegura123")
        respuesta = self.client.post(
            reverse("administracion:eliminar_usuario", args=[superuser.id])
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(User.objects.filter(username="super_test").exists())

    def test_eliminar_usuario(self):
        self.client.login(username="admin_test", password="claveSegura123")
        respuesta = self.client.post(
            reverse("administracion:eliminar_usuario", args=[self.usuario.id])
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertFalse(User.objects.filter(username="usuario_test").exists())


class DashboardDeudaProveedoresTests(TestCase):
    """El KPI del dashboard solo suma facturas pendientes, no pagadas ni anuladas."""

    def setUp(self):
        from datetime import date

        self.grupo_admin = Group.objects.create(name="Administrador")
        self.negocio = Negocio.objects.create(
            nombre="Kiosco KPI",
            slug="kiosco-kpi",
            activo=True,
        )
        self.admin = User.objects.create_user(
            username="admin_kpi", password="claveSegura123", is_staff=True
        )
        self.admin.groups.add(self.grupo_admin)
        Empleado.objects.create(
            usuario=self.admin, negocio=self.negocio, activo=True
        )
        self.fecha_emision = date(2026, 9, 1)
        self.fecha_vencimiento = date(2026, 9, 30)
        self.client.login(username="admin_kpi", password="claveSegura123")

    def crear_documento(self, numero, monto, pagado, estado, categoria="proveedor"):
        return Documento.objects.create(
            negocio=self.negocio,
            nombre_proveedor="Proveedor de prueba",
            categoria=categoria,
            numero_factura=numero,
            monto=Decimal(monto),
            monto_pagado=Decimal(pagado),
            fecha_emision=self.fecha_emision,
            fecha_vencimiento=self.fecha_vencimiento,
            estado=estado,
        )

    def test_kpi_solo_suma_pendientes(self):
        self.crear_documento("K-001", "10000.00", "4000.00", "pendiente")
        # Pagada con saldo parcial: no debe sumar deuda.
        self.crear_documento("K-002", "5000.00", "2000.00", "pagada")
        # Anulada: tampoco.
        self.crear_documento("K-003", "7000.00", "0.00", "anulada")

        respuesta = self.client.get(reverse("administracion:dashboard"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            respuesta.context["deuda_proveedores"], Decimal("6000.00")
        )

    def test_kpi_es_cero_sin_pendientes(self):
        self.crear_documento("K-001", "5000.00", "5000.00", "pagada")
        self.crear_documento("K-002", "7000.00", "0.00", "anulada")

        respuesta = self.client.get(reverse("administracion:dashboard"))

        self.assertEqual(
            respuesta.context["deuda_proveedores"], Decimal("0.00")
        )
        self.assertEqual(
            respuesta.context["deuda_servicios"], Decimal("0.00")
        )

    def test_kpi_separa_deuda_de_proveedores_y_servicios(self):
        # Proveedores: solo facturas de mercadería.
        self.crear_documento(
            "K-001", "10000.00", "4000.00", "pendiente", "proveedor"
        )
        # Servicios: luz, gas, seguridad e higiene y otros.
        self.crear_documento("K-002", "68450.00", "0.00", "pendiente", "luz")
        self.crear_documento(
            "K-003", "38750.00", "25000.00", "pendiente", "gas"
        )
        self.crear_documento(
            "K-004", "18000.00", "18000.00", "pagada", "seguridad"
        )
        self.crear_documento("K-005", "55000.00", "0.00", "pendiente", "otro")

        respuesta = self.client.get(reverse("administracion:dashboard"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            respuesta.context["deuda_proveedores"], Decimal("6000.00")
        )
        self.assertEqual(
            respuesta.context["deuda_servicios"], Decimal("137200.00")
        )
