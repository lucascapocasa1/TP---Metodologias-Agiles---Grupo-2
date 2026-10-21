from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.db.models import Sum
from django.test import TestCase
from django.urls import reverse

from auditoria.models import RegistroAuditoria
from pedidos.models import Pedido
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

    def test_la_busqueda_ignora_los_acentos(self):
        """En el mostrador nadie escribe tildes: "perez" tiene que
        encontrar a "Pérez"."""
        self.login_cajero()
        respuesta = self.client.get(reverse("clientes:buscar"), {"q": "pere"})
        self.assertContains(respuesta, "Ana Pérez")

    def test_la_busqueda_ignora_los_acentos_del_apellido(self):
        self.login_cajero()
        respuesta = self.client.get(reverse("clientes:buscar"), {"q": "pere"})
        self.assertContains(respuesta, "Ana Pérez")

    def test_la_busqueda_devuelve_al_cliente_bien_acentuado(self):
        """Con la tilde también tiene que funcionar."""
        self.login_cajero()
        respuesta = self.client.get(reverse("clientes:buscar"), {"q": "Pérez"})
        self.assertContains(respuesta, "Ana Pérez")

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


class BaseCuentaCorriente(BaseClientes):
    """Escenario base del HU-14: cliente con límite, cajero y admin."""

    def setUp(self):
        super().setUp()
        self.cliente.limite_credito = Decimal("5000.00")
        self.cliente.save(update_fields=["limite_credito"])

    def fiar(self, cantidad=1, producto=None, cliente=None):
        """Agrega `cantidad` al carrito, asocia el cliente y cobra fiado."""
        codigo = (producto or self.producto).codigo_barras
        for _ in range(cantidad):
            self.client.post(
                reverse("ventas:cobro_agregar"), {"codigo": codigo}
            )
        self.asociar(cliente=cliente or self.cliente)
        return self.client.post(
            reverse("ventas:cobro_confirmar"),
            {"metodo_pago": "cuenta_corriente"},
        )


class PropiedadesCuentaCorrienteTests(BaseCuentaCorriente):
    """El modelo: límite, disponible y cuándo se puede fiar."""

    def test_tiene_cuenta_corriente_segun_limite(self):
        self.assertTrue(self.cliente.tiene_cuenta_corriente)
        self.cliente.limite_credito = Decimal("0.00")
        self.assertFalse(self.cliente.tiene_cuenta_corriente)

    def test_credito_disponible_descuenta_la_deuda(self):
        self.assertEqual(self.cliente.credito_disponible, Decimal("5000.00"))
        self.cliente.saldo_deuda = Decimal("2000.00")
        self.assertEqual(self.cliente.credito_disponible, Decimal("3000.00"))

    def test_credito_disponible_nunca_es_negativo(self):
        self.cliente.saldo_deuda = Decimal("9999.00")
        self.assertEqual(self.cliente.credito_disponible, Decimal("0.00"))
        self.assertTrue(self.cliente.saldo_al_limite)

    def test_puede_fiar_dentro_del_limite(self):
        self.assertTrue(self.cliente.puede_fiar(Decimal("5000.00")))
        self.assertFalse(self.cliente.puede_fiar(Decimal("5000.01")))

    def test_sin_limite_no_puede_fiar(self):
        self.cliente.limite_credito = Decimal("0.00")
        self.assertFalse(self.cliente.puede_fiar(Decimal("1.00")))


class FiarEnElCobroTests(BaseCuentaCorriente):
    """HU-14: cobrar a cuenta corriente desde el POS."""

    def test_cajero_fia_dentro_del_limite(self):
        self.login_cajero()
        respuesta = self.fiar(cantidad=2)
        self.assertEqual(respuesta.status_code, 302)

        venta = Venta.objects.latest("pk")
        self.assertEqual(venta.metodo_pago, "cuenta_corriente")
        self.assertEqual(venta.total, Decimal("3000.00"))
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.saldo_deuda, Decimal("3000.00"))

    def test_fiado_queda_auditado_como_venta(self):
        self.login_cajero()
        self.fiar()
        self.assertTrue(
            RegistroAuditoria.objects.filter(accion="Venta confirmada").exists()
        )

    def test_fiado_descuenta_stock(self):
        self.login_cajero()
        self.fiar(cantidad=3)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 7)

    def test_fiado_suma_puntos_de_fidelidad(self):
        self.login_cajero()
        self.fiar()
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.puntos, 15)  # $1500 → 15 puntos

    def test_rechaza_si_se_pasa_del_limite(self):
        self.login_cajero()
        # 4 x $1500 = $6000 > límite de $5000
        respuesta = self.fiar(cantidad=4)
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "límite")
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.saldo_deuda, Decimal("0.00"))
        self.assertFalse(
            Venta.objects.filter(metodo_pago="cuenta_corriente").exists()
        )

    def test_rechazo_no_vacia_el_carrito(self):
        self.login_cajero()
        self.fiar(cantidad=4)
        self.assertEqual(len(self.client.session.get("carrito", [])), 1)

    def test_no_deja_fiar_sin_cliente_asociado(self):
        self.login_cajero()
        self.agregar_producto()
        respuesta = self.confirmar(metodo="cuenta_corriente")
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "asociá un cliente")
        self.assertFalse(
            Venta.objects.filter(metodo_pago="cuenta_corriente").exists()
        )

    def test_no_deja_fiar_sin_cuenta_corriente_habilitada(self):
        sin_cc = Cliente.objects.create(
            nombre="Raúl", apellido="Nuevo", dni="40999888"
        )
        self.login_cajero()
        self.agregar_producto()
        self.asociar(cliente=sin_cc)
        respuesta = self.confirmar(metodo="cuenta_corriente")
        self.assertContains(respuesta, "no tiene cuenta corriente")
        sin_cc.refresh_from_db()
        self.assertEqual(sin_cc.saldo_deuda, Decimal("0.00"))

    def test_una_venta_no_fiada_no_toca_el_saldo(self):
        self.login_cajero()
        self.agregar_producto()
        self.asociar()
        self.confirmar(metodo="efectivo", monto="2000")
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.saldo_deuda, Decimal("0.00"))

    def test_efectivo_sigue_andando_con_limite_cargado(self):
        self.login_cajero()
        self.agregar_producto()
        self.asociar()
        respuesta = self.confirmar(metodo="efectivo", monto="2000")
        self.assertEqual(respuesta.status_code, 302)
        venta = Venta.objects.latest("pk")
        self.assertEqual(venta.metodo_pago, "efectivo")
        self.assertEqual(venta.vuelto, Decimal("500.00"))

    def test_cuenta_corriente_no_ofrece_monto_entregado(self):
        """La opción fiado sólo aparece si el cliente puede fiar."""
        self.login_cajero()
        self.agregar_producto()
        self.asociar()
        respuesta = self.client.post(
            reverse("ventas:cobro_cantidad"),
            {"producto_id": self.producto.pk, "accion": "sumar"},
            HTTP_HX_REQUEST="true",
        )
        self.assertContains(respuesta, "Cuenta corriente (FIAR)")
        self.assertContains(respuesta, "puede fiar hasta")


class RegistroPagoTests(BaseCuentaCorriente):
    """HU-14: el Administrador cobra pagos de la deuda."""

    def setUp(self):
        super().setUp()
        self.cliente.saldo_deuda = Decimal("3000.00")
        self.cliente.save(update_fields=["saldo_deuda"])

    def test_registrar_pago_baja_el_saldo(self):
        self.login_admin()
        respuesta = self.client.post(
            reverse("clientes:registrar_pago", args=[self.cliente.pk]),
            {"monto": "1000", "observacion": "primera parte"},
        )
        self.assertEqual(respuesta.status_code, 302)
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.saldo_deuda, Decimal("2000.00"))
        self.assertEqual(self.cliente.pagos.count(), 1)

    def test_pago_queda_auditado(self):
        self.login_admin()
        self.client.post(
            reverse("clientes:registrar_pago", args=[self.cliente.pk]),
            {"monto": "1000"},
        )
        self.assertTrue(
            RegistroAuditoria.objects.filter(
                accion="Pago de cuenta corriente"
            ).exists()
        )

    def test_pago_parcial_deja_saldo(self):
        self.login_admin()
        self.client.post(
            reverse("clientes:registrar_pago", args=[self.cliente.pk]),
            {"monto": "2999.99"},
        )
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.saldo_deuda, Decimal("0.01"))

    def test_pago_total_deja_saldo_en_cero(self):
        self.login_admin()
        self.client.post(
            reverse("clientes:registrar_pago", args=[self.cliente.pk]),
            {"monto": "3000"},
        )
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.saldo_deuda, Decimal("0.00"))

    def test_rechaza_pago_mayor_a_la_deuda(self):
        self.login_admin()
        self.client.post(
            reverse("clientes:registrar_pago", args=[self.cliente.pk]),
            {"monto": "5000"},
        )
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.saldo_deuda, Decimal("3000.00"))
        self.assertEqual(self.cliente.pagos.count(), 0)

    def test_rechaza_pago_cero_o_negativo(self):
        self.login_admin()
        for monto in ("0", "-100"):
            self.client.post(
                reverse("clientes:registrar_pago", args=[self.cliente.pk]),
                {"monto": monto},
            )
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.saldo_deuda, Decimal("3000.00"))

    def test_cajero_no_puede_registrar_pagos(self):
        self.login_cajero()
        respuesta = self.client.post(
            reverse("clientes:registrar_pago", args=[self.cliente.pk]),
            {"monto": "1000"},
        )
        self.assertEqual(respuesta.status_code, 403)
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.saldo_deuda, Decimal("3000.00"))

    def test_get_no_registra_nada(self):
        self.login_admin()
        respuesta = self.client.get(
            reverse("clientes:registrar_pago", args=[self.cliente.pk])
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(self.cliente.pagos.count(), 0)

    def test_pago_guarda_usuario_y_observacion(self):
        self.login_admin()
        self.client.post(
            reverse("clientes:registrar_pago", args=[self.cliente.pk]),
            {"monto": "500", "observacion": "pagó en dos partes"},
        )
        pago = self.cliente.pagos.first()
        self.assertEqual(pago.monto, Decimal("500.00"))
        self.assertEqual(pago.usuario.username, "admin_fidelidad")
        self.assertEqual(pago.observacion, "pagó en dos partes")


class FichaCuentaCorrienteTests(BaseCuentaCorriente):
    """La ficha del cliente muestra el estado de la cuenta corriente."""

    def test_ficha_muestra_saldo_y_limite(self):
        self.cliente.saldo_deuda = Decimal("1200.00")
        self.cliente.save(update_fields=["saldo_deuda"])
        self.login_admin()
        respuesta = self.client.get(
            reverse("clientes:detalle_cliente", args=[self.cliente.pk])
        )
        self.assertContains(respuesta, "Cuenta corriente")
        self.assertContains(respuesta, "1.200")
        self.assertContains(respuesta, "5.000")
        self.assertContains(respuesta, "Registrar pago")

    def test_ficha_sin_deuda_no_muestra_form_de_pago(self):
        self.login_admin()
        respuesta = self.client.get(
            reverse("clientes:detalle_cliente", args=[self.cliente.pk])
        )
        self.assertContains(respuesta, "Sin deuda pendiente")
        self.assertNotContains(respuesta, "Registrar pago")

    def test_ficha_avisa_si_no_tiene_cuenta_corriente(self):
        sin_cc = Cliente.objects.create(
            nombre="Raúl", apellido="Nuevo", dni="40999888"
        )
        self.login_admin()
        respuesta = self.client.get(
            reverse("clientes:detalle_cliente", args=[sin_cc.pk])
        )
        self.assertContains(respuesta, "no tiene cuenta corriente habilitada")

    def test_ficha_lista_los_pagos(self):
        self.cliente.saldo_deuda = Decimal("3000.00")
        self.cliente.save(update_fields=["saldo_deuda"])
        self.login_admin()
        self.client.post(
            reverse("clientes:registrar_pago", args=[self.cliente.pk]),
            {"monto": "1000", "observacion": "parte uno"},
        )
        respuesta = self.client.get(
            reverse("clientes:detalle_cliente", args=[self.cliente.pk])
        )
        self.assertContains(respuesta, "parte uno")

    def test_listado_muestra_deuda(self):
        self.cliente.saldo_deuda = Decimal("2500.00")
        self.cliente.save(update_fields=["saldo_deuda"])
        self.login_admin()
        respuesta = self.client.get(reverse("clientes:listar_clientes"))
        self.assertContains(respuesta, "2.500")


class LimiteEnFormularioTests(BaseCuentaCorriente):
    """El Administrador define el límite desde el alta/edición."""

    def test_crear_cliente_con_limite(self):
        self.login_admin()
        self.client.post(
            reverse("clientes:crear_cliente"),
            {
                "nombre": "Nuevo",
                "apellido": "Fiado",
                "dni": "40555666",
                "limite_credito": "10000",
            },
        )
        nuevo = Cliente.objects.get(dni="40555666")
        self.assertEqual(nuevo.limite_credito, Decimal("10000.00"))

    def test_editar_limite(self):
        self.login_admin()
        self.client.post(
            reverse("clientes:editar_cliente", args=[self.cliente.pk]),
            {
                "nombre": self.cliente.nombre,
                "apellido": self.cliente.apellido,
                "dni": self.cliente.dni,
                "limite_credito": "7500",
                "activo": "on",
            },
        )
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.limite_credito, Decimal("7500.00"))

    def test_rechaza_limite_negativo(self):
        self.login_admin()
        respuesta = self.client.post(
            reverse("clientes:editar_cliente", args=[self.cliente.pk]),
            {
                "nombre": self.cliente.nombre,
                "apellido": self.cliente.apellido,
                "dni": self.cliente.dni,
                "limite_credito": "-100",
                "activo": "on",
            },
        )
        self.assertEqual(respuesta.status_code, 200)
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.limite_credito, Decimal("5000.00"))

    def test_saldo_deuda_no_se_edita_desde_el_form(self):
        """El saldo lo maneja el sistema; el form no lo expone."""
        self.cliente.saldo_deuda = Decimal("800.00")
        self.cliente.save(update_fields=["saldo_deuda"])
        self.login_admin()
        self.client.post(
            reverse("clientes:editar_cliente", args=[self.cliente.pk]),
            {
                "nombre": "Ana",
                "apellido": "Pérez",
                "dni": self.cliente.dni,
                "limite_credito": "5000",
                "activo": "on",
                "saldo_deuda": "0",
            },
        )
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.saldo_deuda, Decimal("800.00"))


class DemoClientesTests(TestCase):
    """La demo de clientes tiene que ser coherente de punta a punta.

    Es la que se usa para mostrar el sistema: si un cliente "existe" pero no
    tiene compras, o si un pedido entregado no tiene venta, la demo miente.
    """

    def setUp(self):
        super().setUp()
        self._catalogo()

    def _catalogo(self):
        """Los productos que usa la demo, con los precios del catálogo."""
        from ventas.management.commands.cargar_demo import CATALOGO

        categorias = {}
        for nombre, categoria, precio, costo, stock, _minimo in CATALOGO:
            if categoria not in categorias:
                categorias[categoria], _ = Categoria.objects.get_or_create(
                    nombre=categoria
                )
            Producto.objects.create(
                nombre=nombre,
                categoria=categorias[categoria],
                precio=Decimal(precio),
                costo=Decimal(costo),
                stock=stock,
            )

    def _cargar(self):
        from django.core.management import call_command

        call_command("cargar_demo_clientes", verbosity=0)

    def test_todo_cliente_cargado_tiene_compras(self):
        self._cargar()
        self.assertTrue(Cliente.objects.exists())
        for cliente in Cliente.objects.all():
            self.assertTrue(
                cliente.ventas.filter(finalizada=True).exists(),
                f"{cliente.nombre_completo} quedó cargado sin compras.",
            )

    def test_la_deuda_es_lo_fiado_menos_lo_pagado(self):
        self._cargar()
        for cliente in Cliente.objects.all():
            fiado = (
                cliente.ventas.filter(
                    finalizada=True, metodo_pago="cuenta_corriente"
                ).aggregate(s=Sum("total"))["s"]
                or Decimal("0.00")
            )
            pagado = cliente.pagos.aggregate(s=Sum("monto"))["s"] or Decimal(
                "0.00"
            )
            self.assertEqual(cliente.saldo_deuda, fiado - pagado)
            self.assertLessEqual(cliente.saldo_deuda, cliente.limite_credito)

    def test_los_puntos_suman_las_ventas(self):
        self._cargar()
        for cliente in Cliente.objects.all():
            ganados = (
                cliente.ventas.filter(finalizada=True).aggregate(
                    s=Sum("puntos_ganados")
                )["s"]
                or 0
            )
            self.assertEqual(cliente.puntos, ganados)

    def test_los_pedidos_pendientes_no_son_clientes(self):
        self._cargar()
        pendientes = Pedido.objects.filter(estado="pendiente")
        self.assertTrue(pendientes.exists())
        for pedido in pendientes:
            self.assertIsNone(pedido.cliente_id)
            self.assertIsNone(pedido.venta_id)

    def test_los_pedidos_entregados_cobran_de_verdad(self):
        self._cargar()
        entregados = Pedido.objects.filter(estado="entregado")
        self.assertTrue(entregados.exists())
        for pedido in entregados:
            self.assertIsNotNone(pedido.venta_id)
            self.assertIsNotNone(pedido.cliente_id)
            venta = pedido.venta
            self.assertTrue(venta.finalizada)
            self.assertEqual(venta.total, pedido.total)
            self.assertEqual(venta.cliente_id, pedido.cliente_id)
            # El pedido entregado tiene que tener una compra en la ficha.
            self.assertTrue(
                pedido.cliente.ventas.filter(finalizada=True).exists()
            )

    def test_no_deja_productos_en_stock_negativo(self):
        self._cargar()
        for producto in Producto.objects.all():
            self.assertGreaterEqual(producto.stock, 0, producto.nombre)

    def test_limpiar_devuelve_el_stock_y_borra_la_demo(self):
        """Borrar la demo tiene que dejar el stock como estaba."""
        from clientes.management.commands.cargar_demo_clientes import Command

        stock_inicial = {
            producto.nombre: producto.stock
            for producto in Producto.objects.all()
        }
        self._cargar()

        Command()._limpiar()

        for producto in Producto.objects.all():
            self.assertEqual(
                producto.stock,
                stock_inicial[producto.nombre],
                f"«{producto.nombre}» no volvió a su stock original.",
            )
        self.assertFalse(Cliente.objects.exists())
        self.assertFalse(Pedido.objects.exists())
        self.assertFalse(Venta.objects.exists())

    def test_limpiar_vuelve_a_cargar_la_misma_demo(self):
        """`--limpiar` es idempotente: no duplica clientes ni ventas."""
        from django.core.management import call_command

        self._cargar()
        clientes = Cliente.objects.count()
        ventas = Venta.objects.count()
        pedidos = Pedido.objects.count()
        stock = {
            producto.nombre: producto.stock
            for producto in Producto.objects.all()
        }

        call_command("cargar_demo_clientes", "--limpiar", verbosity=0)

        self.assertEqual(Cliente.objects.count(), clientes)
        self.assertEqual(Venta.objects.count(), ventas)
        self.assertEqual(Pedido.objects.count(), pedidos)
        for producto in Producto.objects.all():
            self.assertEqual(producto.stock, stock[producto.nombre])
