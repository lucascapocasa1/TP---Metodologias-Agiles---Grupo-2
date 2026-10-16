from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from auditoria.models import RegistroAuditoria
from ventas.models import Categoria, Producto, Venta

from .models import Cliente
from .services import PUNTOS_POR_PESO, puntos_por_monto


class BaseClientes(TestCase):
    """Usuarios, catálogo y cliente base para los tests de fidelidad (HU-12)."""

    def setUp(self):
        self.grupo_admin = Group.objects.create(name="Administrador")
        self.grupo_cajero = Group.objects.create(name="Cajero")

        self.admin = User.objects.create_user(
            username="admin_fidelidad", password="claveSegura123", is_staff=True
        )
        self.admin.groups.add(self.grupo_admin)

        self.cajero = User.objects.create_user(
            username="cajero_fidelidad", password="claveSegura123"
        )
        self.cajero.groups.add(self.grupo_cajero)

        self.cliente = Cliente.objects.create(
            nombre="Ana", apellido="Pérez", dni="30123456"
        )

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

    def login_admin(self):
        self.client.login(username="admin_fidelidad", password="claveSegura123")

    def login_cajero(self):
        self.client.login(username="cajero_fidelidad", password="claveSegura123")

    def agregar_producto(self):
        return self.client.post(
            reverse("ventas:cobro_agregar"), {"codigo": "7790000000001"}
        )

    def asociar(self, cliente=None, hx=True):
        cliente = cliente or self.cliente
        kwargs = {"HTTP_HX_REQUEST": "true"} if hx else {}
        return self.client.post(
            reverse("clientes:asociar"), {"cliente_id": cliente.pk}, **kwargs
        )

    def confirmar(self, metodo="efectivo", monto="5000"):
        return self.client.post(
            reverse("ventas:cobro_confirmar"),
            {"metodo_pago": metodo, "monto_entregado": monto},
        )

    def cobrar_con_cliente(self):
        """Flujo completo: escanear → asociar → confirmar ($1500)."""
        self.agregar_producto()
        self.asociar()
        return self.confirmar()


class AccesoClientesTests(BaseClientes):
    """Permisos: el CRUD es del Administrador; el cajero solo asocia al cobrar."""

    def test_anonimo_redirige_a_login(self):
        for nombre in (
            "clientes:listar_clientes",
            "clientes:crear_cliente",
            "clientes:buscar",
        ):
            if nombre == "clientes:buscar":
                respuesta = self.client.get(reverse(nombre), {"q": "301"})
            else:
                respuesta = self.client.get(reverse(nombre))
            self.assertEqual(respuesta.status_code, 302, nombre)
            self.assertIn("login", respuesta.url)

    def test_anonimo_no_asocia_clientes(self):
        respuesta = self.client.post(
            reverse("clientes:asociar"), {"cliente_id": self.cliente.pk}
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn("login", respuesta.url)

    def test_cajero_no_accede_al_crud(self):
        self.login_cajero()
        urls = [
            reverse("clientes:listar_clientes"),
            reverse("clientes:crear_cliente"),
            reverse("clientes:editar_cliente", args=[self.cliente.pk]),
            reverse("clientes:eliminar_cliente", args=[self.cliente.pk]),
            reverse("clientes:detalle_cliente", args=[self.cliente.pk]),
        ]
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 403, url)

    def test_admin_accede_al_crud(self):
        self.login_admin()
        urls = [
            reverse("clientes:listar_clientes"),
            reverse("clientes:crear_cliente"),
            reverse("clientes:editar_cliente", args=[self.cliente.pk]),
            reverse("clientes:eliminar_cliente", args=[self.cliente.pk]),
            reverse("clientes:detalle_cliente", args=[self.cliente.pk]),
        ]
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_cajero_puede_buscar_y_asociar_en_el_cobro(self):
        self.login_cajero()
        respuesta = self.client.get(reverse("clientes:buscar"), {"q": "301"})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(self.asociar().status_code, 200)


class AltaYEdicionTests(BaseClientes):
    """Alta, edición y validaciones del DNI/CUIT."""

    def test_admin_crea_cliente_con_fecha_de_registro(self):
        self.login_admin()
        respuesta = self.client.post(
            reverse("clientes:crear_cliente"),
            {
                "nombre": "Luis",
                "apellido": "Gómez",
                "dni": "28999888",
                "telefono": "11 5555-5555",
                "email": "luis@ejemplo.com",
                "activo": "on",
            },
        )
        self.assertEqual(respuesta.status_code, 302)
        cliente = Cliente.objects.get(dni="28999888")
        self.assertEqual(cliente.nombre_completo, "Luis Gómez")
        self.assertIsNotNone(cliente.fecha_registro)
        self.assertEqual(cliente.puntos, 0)
        self.assertTrue(cliente.activo)

    def test_alta_queda_auditada(self):
        self.login_admin()
        self.client.post(
            reverse("clientes:crear_cliente"),
            {"nombre": "Luis", "apellido": "Gómez", "dni": "28999888"},
        )
        self.assertTrue(
            RegistroAuditoria.objects.filter(accion="Cliente creado").exists()
        )

    def test_dni_duplicado_no_se_crea(self):
        self.login_admin()
        respuesta = self.client.post(
            reverse("clientes:crear_cliente"),
            {"nombre": "Otro", "apellido": "Cliente", "dni": self.cliente.dni},
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "ya está registrado")
        self.assertEqual(Cliente.objects.count(), 1)

    def test_dni_con_puntos_se_normaliza(self):
        """El admin tipea "30.123.456" y se guarda como "30123456"."""
        self.login_admin()
        self.client.post(
            reverse("clientes:crear_cliente"),
            {"nombre": "Otro", "apellido": "Cliente", "dni": "27.111.222"},
        )
        self.assertTrue(Cliente.objects.filter(dni="27111222").exists())

    def test_dni_con_guiones_tambien_se_normaliza(self):
        """El CUIT con guiones ("20-12345678-9") se guarda sin guiones."""
        self.login_admin()
        self.client.post(
            reverse("clientes:crear_cliente"),
            {"nombre": "Empresa", "apellido": "SA", "dni": "30-71112222-9"},
        )
        self.assertTrue(Cliente.objects.filter(dni="30711122229").exists())

    def test_dni_con_letras_rechazado(self):
        self.login_admin()
        respuesta = self.client.post(
            reverse("clientes:crear_cliente"),
            {"nombre": "X", "apellido": "Y", "dni": "abc1234"},
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "entre 7 y 11 dígitos")
        self.assertEqual(Cliente.objects.count(), 1)

    def test_edicion_conserva_puntos_y_dni_unico(self):
        self.cliente.puntos = 50
        self.cliente.save(update_fields=["puntos"])
        self.login_admin()

        respuesta = self.client.post(
            reverse("clientes:editar_cliente", args=[self.cliente.pk]),
            {
                "nombre": "Ana Maria",
                "apellido": "Pérez",
                "dni": self.cliente.dni,
                "telefono": "",
                "email": "",
                "activo": "on",
            },
        )
        self.assertEqual(respuesta.status_code, 302)
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.nombre, "Ana Maria")
        self.assertEqual(self.cliente.puntos, 50)

        # No puede robarle el DNI a otro cliente.
        otro = Cliente.objects.create(
            nombre="Pepe", apellido="Lopez", dni="20555444"
        )
        respuesta = self.client.post(
            reverse("clientes:editar_cliente", args=[otro.pk]),
            {
                "nombre": "Pepe",
                "apellido": "Lopez",
                "dni": self.cliente.dni,
                "telefono": "",
                "email": "",
                "activo": "on",
            },
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "ya está registrado")


class BajaClienteTests(BaseClientes):
    """Baja lógica: conserva ventas y puntos, solo queda inactivo."""

    def test_baja_logica_conserva_ventas_y_puntos(self):
        Venta.objects.create(
            total=Decimal("1500.00"),
            finalizada=True,
            cliente=self.cliente,
            puntos_ganados=15,
        )
        self.cliente.puntos = 15
        self.cliente.save(update_fields=["puntos"])

        self.login_admin()
        url = reverse("clientes:eliminar_cliente", args=[self.cliente.pk])

        # GET: pantalla de confirmación.
        respuesta = self.client.get(url)
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Confirmar Baja")

        # POST: baja lógica.
        self.assertEqual(self.client.post(url).status_code, 302)
        self.cliente.refresh_from_db()
        self.assertFalse(self.cliente.activo)
        self.assertEqual(self.cliente.puntos, 15)
        self.assertTrue(Venta.objects.filter(cliente=self.cliente).exists())
        self.assertTrue(
            RegistroAuditoria.objects.filter(accion="Cliente dado de baja").exists()
        )

    def test_cliente_inactivo_no_se_puede_asociar(self):
        self.cliente.activo = False
        self.cliente.save(update_fields=["activo"])
        self.login_cajero()
        respuesta = self.client.post(
            reverse("clientes:asociar"), {"cliente_id": self.cliente.pk}
        )
        self.assertEqual(respuesta.status_code, 404)


class CobroConClienteTests(BaseClientes):
    """HU-12 + fidelidad: el cajero asocia el cliente y acumula puntos."""

    def test_busqueda_en_el_cobro_encuentra_por_dni(self):
        self.login_cajero()
        respuesta = self.client.get(reverse("clientes:buscar"), {"q": "301"})
        self.assertContains(respuesta, "Ana Pérez")
        self.assertContains(respuesta, "DNI 30123456")

    def test_busqueda_sin_resultados_avisa(self):
        self.login_cajero()
        respuesta = self.client.get(reverse("clientes:buscar"), {"q": "zzzz"})
        self.assertContains(respuesta, "No hay clientes")

    def test_asociar_guarda_el_cliente_en_sesion(self):
        self.login_cajero()
        respuesta = self.asociar()
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(self.client.session.get("cliente_id"), self.cliente.pk)

    def test_carrito_muestra_al_cliente_asociado(self):
        self.login_cajero()
        self.asociar()
        respuesta = self.client.get(reverse("ventas:pantalla_cobro"))
        self.assertContains(respuesta, "cliente-barra-asociado")
        self.assertContains(respuesta, "Ana Pérez")

    def test_sin_cliente_ofrece_asociar(self):
        self.login_cajero()
        respuesta = self.client.get(reverse("ventas:pantalla_cobro"))
        self.assertContains(respuesta, "Asociar cliente")

    def test_quitar_cliente_limpia_la_sesion(self):
        self.login_cajero()
        self.asociar()
        respuesta = self.client.post(reverse("clientes:quitar"), {}, HTTP_HX_REQUEST="true")
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotIn("cliente_id", self.client.session)

    def test_venta_con_cliente_suma_un_punto_cada_100(self):
        """CA: total $1500 → 15 puntos acumulados en el cliente."""
        self.login_cajero()
        self.cobrar_con_cliente()

        venta = Venta.objects.get()
        self.assertEqual(venta.cliente, self.cliente)
        self.assertEqual(venta.puntos_ganados, 15)

        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.puntos, 15)

    def test_ventas_repetidas_acumulan_puntos(self):
        self.login_cajero()
        self.cobrar_con_cliente()
        self.agregar_producto()
        self.asociar()
        self.confirmar()

        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.puntos, 30)
        self.assertEqual(
            sum(Venta.objects.values_list("puntos_ganados", flat=True)), 30
        )

    def test_venta_sin_cliente_no_suma_puntos(self):
        self.login_cajero()
        self.agregar_producto()
        self.confirmar()

        venta = Venta.objects.get()
        self.assertIsNone(venta.cliente)
        self.assertEqual(venta.puntos_ganados, 0)
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.puntos, 0)

    def test_tras_confirmar_se_limpia_sesion_de_cliente(self):
        self.login_cajero()
        self.cobrar_con_cliente()
        self.assertNotIn("cliente_id", self.client.session)

    def test_comprobante_muestra_cliente_y_puntos(self):
        self.login_cajero()
        self.cobrar_con_cliente()
        venta = Venta.objects.get()
        respuesta = self.client.get(
            reverse("ventas:pantalla_cobro"), {"venta": venta.pk}
        )
        self.assertContains(respuesta, "Ana Pérez (DNI 30123456)")
        self.assertContains(respuesta, "Puntos de fidelidad")
        self.assertContains(respuesta, "+15")

    def test_venta_con_cliente_queda_auditada(self):
        self.login_cajero()
        self.cobrar_con_cliente()
        registro = RegistroAuditoria.objects.filter(
            accion="Venta confirmada"
        ).first()
        self.assertIsNotNone(registro)
        self.assertIn("Ana Pérez", registro.detalle)
        self.assertIn("+15 pts", registro.detalle)

    def test_previsualizacion_de_puntos_en_el_carrito(self):
        self.login_cajero()
        self.agregar_producto()
        self.asociar()
        respuesta = self.client.get(reverse("ventas:pantalla_cobro"))
        self.assertContains(respuesta, "sumás +15")

    def test_cliente_bajado_en_sesion_la_venta_se_hace_sin_cliente(self):
        self.login_cajero()
        self.agregar_producto()
        self.asociar()
        self.cliente.activo = False
        self.cliente.save(update_fields=["activo"])

        self.confirmar()
        venta = Venta.objects.get()
        self.assertIsNone(venta.cliente)
        self.assertEqual(venta.puntos_ganados, 0)
        self.assertNotIn("cliente_id", self.client.session)


class AltaRapidaTests(BaseClientes):
    """CA del HU-12: la ventanita rápida crea el cliente desde el cobro."""

    def test_alta_rapida_crea_y_asocia(self):
        self.login_cajero()
        respuesta = self.client.post(
            reverse("clientes:alta_rapida"),
            {"nombre": "Carla", "apellido": "Sosa", "dni": "40111222"},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(respuesta.status_code, 200)
        cliente = Cliente.objects.get(dni="40111222")
        self.assertEqual(cliente.nombre_completo, "Carla Sosa")
        self.assertTrue(cliente.activo)
        self.assertEqual(self.client.session.get("cliente_id"), cliente.pk)

    def test_alta_rapida_dni_duplicado_no_crea_y_muestra_error(self):
        self.login_cajero()
        respuesta = self.client.post(
            reverse("clientes:alta_rapida"),
            {"nombre": "Ana", "apellido": "Otra", "dni": "30.123.456"},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "ya está registrado")
        self.assertEqual(Cliente.objects.count(), 1)
        self.assertNotIn("cliente_id", self.client.session)

    def test_alta_rapida_queda_auditada(self):
        self.login_cajero()
        self.client.post(
            reverse("clientes:alta_rapida"),
            {"nombre": "Carla", "apellido": "Sosa", "dni": "40111222"},
            HTTP_HX_REQUEST="true",
        )
        self.assertTrue(
            RegistroAuditoria.objects.filter(accion="Cliente creado").exists()
        )


class ListadoYFichaTests(BaseClientes):
    """Listado con estadísticas y ficha de fidelidad del cliente."""

    def _venta_de(self, total="1500.00", puntos=15):
        return Venta.objects.create(
            total=Decimal(total),
            finalizada=True,
            cliente=self.cliente,
            puntos_ganados=puntos,
            metodo_pago="efectivo",
        )

    def test_listado_muestra_estadisticas_de_fidelidad(self):
        self._venta_de()
        self.login_admin()
        respuesta = self.client.get(reverse("clientes:listar_clientes"))
        cliente = respuesta.context["clientes"][0]
        self.assertEqual(cliente.total_compras, 1)
        self.assertEqual(cliente.total_gastado, Decimal("1500.00"))
        self.assertEqual(cliente.puntos, 0)
        self.assertContains(respuesta, "$1.500")

    def test_listado_con_htmx_devuelve_solo_la_tabla(self):
        self.login_admin()
        respuesta = self.client.get(
            reverse("clientes:listar_clientes"),
            {"buscar": "Ana"},
            HTTP_HX_REQUEST="true",
        )
        self.assertTemplateUsed(respuesta, "clientes/_clientes_tabla.html")
        self.assertTemplateNotUsed(respuesta, "clientes/listar_clientes.html")

    def test_listado_busca_por_dni(self):
        self.login_admin()
        respuesta = self.client.get(
            reverse("clientes:listar_clientes"), {"buscar": "30123"}
        )
        self.assertEqual(len(respuesta.context["clientes"]), 1)

    def test_ficha_muestra_puntos_fecha_e_historial(self):
        venta = self._venta_de()
        self.cliente.puntos = 15
        self.cliente.save(update_fields=["puntos"])

        self.login_admin()
        respuesta = self.client.get(
            reverse("clientes:detalle_cliente", args=[self.cliente.pk])
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context["cliente"].puntos, 15)
        self.assertEqual(respuesta.context["total_compras"], 1)
        self.assertEqual(
            respuesta.context["total_gastado"], Decimal("1500.00")
        )
        self.assertContains(respuesta, "Fecha de registro")
        self.assertContains(respuesta, f"N° {venta.pk}")
        self.assertContains(respuesta, "+15")

    def test_ficha_sin_compras_muestra_estado_vacio(self):
        self.login_admin()
        respuesta = self.client.get(
            reverse("clientes:detalle_cliente", args=[self.cliente.pk])
        )
        self.assertContains(respuesta, "Sin compras registradas")


class ReglaDePuntosTests(TestCase):
    """1 punto cada $100, siempre redondeando hacia abajo."""

    def test_puntos_por_monto(self):
        self.assertEqual(PUNTOS_POR_PESO, 100)
        self.assertEqual(puntos_por_monto(Decimal("1500.00")), 15)
        self.assertEqual(puntos_por_monto(Decimal("100.00")), 1)
        self.assertEqual(puntos_por_monto(Decimal("99.99")), 0)
        self.assertEqual(puntos_por_monto(Decimal("0.00")), 0)
        self.assertEqual(puntos_por_monto(None), 0)
