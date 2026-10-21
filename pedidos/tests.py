"""Tests de la integración externa (HU-13): catálogo público + pedidos.

Cubren lo que la cátedra pidió y lo que no queremos romper:
* el catálogo se ve **sin login**;
* nunca se filtra la cantidad exacta de stock (solo Disponible/Agotado);
* el pedido queda registrado con sus ítems y el total congelado;
* el link a WhatsApp se arma con el teléfono configurado y el texto del pedido;
* el panel de pedidos es solo para el Administrador (cajero y anónimo → 403).
"""
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase, override_settings
from django.urls import reverse

from auditoria.models import RegistroAuditoria
from clientes.models import Cliente
from ventas.models import Categoria, Producto, Venta

from . import config, services
from .models import ItemPedido, Pedido


class BasePedidos(TestCase):
    def setUp(self):
        self.grupo_admin = Group.objects.create(name="Administrador")
        self.grupo_cajero = Group.objects.create(name="Cajero")

        self.admin = User.objects.create_user(
            username="admin_pedidos", password="claveSegura123", is_staff=True
        )
        self.admin.groups.add(self.grupo_admin)

        self.cajero = User.objects.create_user(
            username="cajero_pedidos", password="claveSegura123"
        )
        self.cajero.groups.add(self.grupo_cajero)

        self.categoria = Categoria.objects.create(nombre="Bebidas")
        self.producto = Producto.objects.create(
            nombre="Coca 500ml",
            codigo_barras="7790000000101",
            precio=Decimal("1500.00"),
            costo=Decimal("900.00"),
            stock=10,
            stock_minimo=5,
            categoria=self.categoria,
        )
        self.agotado = Producto.objects.create(
            nombre="Alfajor triple",
            codigo_barras="7790000000102",
            precio=Decimal("800.00"),
            costo=Decimal("450.00"),
            stock=0,
            stock_minimo=3,
            categoria=self.categoria,
        )

    def login_admin(self):
        self.client.login(username="admin_pedidos", password="claveSegura123")

    def login_cajero(self):
        self.client.login(username="cajero_pedidos", password="claveSegura123")

    def armar_pedido(self, cantidad=2, producto=None):
        producto = producto or self.producto
        self.client.post(
            reverse("pedidos:pedido_agregar"),
            {"producto_id": producto.pk, "cantidad": cantidad},
        )

    def confirmar(self, nombre="Lucía Gómez", **extra):
        datos = {"nombre_cliente": nombre}
        datos.update(extra)
        return self.client.post(reverse("pedidos:pedido_confirmar"), datos)


class CatalogoPublicoTests(BasePedidos):
    def test_catalogo_visible_sin_login(self):
        respuesta = self.client.get(reverse("pedidos:catalogo"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Coca 500ml")

    def test_catalogo_no_expone_el_stock_exacto(self):
        respuesta = self.client.get(reverse("pedidos:catalogo"))
        # El número mágico (stock = 10) no debe aparecer como texto de stock.
        self.assertNotContains(respuesta, "Disponible: 10")
        self.assertNotContains(respuesta, ">10<")
        self.assertContains(respuesta, "Disponible")

    def test_catalogo_marca_agotados(self):
        respuesta = self.client.get(reverse("pedidos:catalogo"))
        self.assertContains(respuesta, "Agotado")

    def test_solo_muestra_productos_activos(self):
        Producto.objects.create(
            nombre="Producto dado de baja",
            precio=Decimal("100.00"),
            stock=5,
            categoria=self.categoria,
            activo=False,
        )
        respuesta = self.client.get(reverse("pedidos:catalogo"))
        self.assertNotContains(respuesta, "Producto dado de baja")

    def test_no_requiere_login_ni_rol(self):
        """Un anónimo entra al catálogo y al flujo de pedido."""
        respuesta = self.client.get(reverse("pedidos:catalogo"))
        self.assertNotIn(respuesta.status_code, (301, 302, 403))


class ArmarPedidoTests(BasePedidos):
    def test_agregar_producto_al_pedido(self):
        self.armar_pedido(cantidad=3)
        carrito = self.client.session.get("pedido", [])
        self.assertEqual(len(carrito), 1)
        self.assertEqual(carrito[0]["cantidad"], 3)
        self.assertEqual(carrito[0]["producto_id"], self.producto.pk)

    def test_agregar_dos_veces_suma_cantidad(self):
        self.armar_pedido(cantidad=1)
        self.armar_pedido(cantidad=2)
        carrito = self.client.session.get("pedido", [])
        self.assertEqual(len(carrito), 1)
        self.assertEqual(carrito[0]["cantidad"], 3)

    def test_no_se_puede_pedir_un_producto_agotado(self):
        respuesta = self.client.post(
            reverse("pedidos:pedido_agregar"),
            {"producto_id": self.agotado.pk, "cantidad": 1},
            HTTP_HX_REQUEST="true",
        )
        self.assertContains(respuesta, "no está disponible")
        self.assertEqual(self.client.session.get("pedido", []), [])

    def test_cantidad_invalida_se_rechaza(self):
        respuesta = self.client.post(
            reverse("pedidos:pedido_agregar"),
            {"producto_id": self.producto.pk, "cantidad": "muchas"},
            HTTP_HX_REQUEST="true",
        )
        self.assertContains(respuesta, "número entero")

    def test_cantidad_cero_o_negativa_se_rechaza(self):
        respuesta = self.client.post(
            reverse("pedidos:pedido_agregar"),
            {"producto_id": self.producto.pk, "cantidad": 0},
            HTTP_HX_REQUEST="true",
        )
        self.assertContains(respuesta, "mínima es 1")

    def test_quitar_producto_del_pedido(self):
        self.armar_pedido()
        self.client.post(
            reverse("pedidos:pedido_quitar"),
            {"producto_id": self.producto.pk},
        )
        self.assertEqual(self.client.session.get("pedido", []), [])

    def test_producto_dado_de_baja_desaparece_del_carrito(self):
        self.armar_pedido()
        self.producto.activo = False
        self.producto.save(update_fields=["activo"])

        class _PeticionFalsa:
            session = self.client.session

        self.assertEqual(services.items_del_pedido(_PeticionFalsa()), [])


class ConfirmarPedidoTests(BasePedidos):
    def test_pedido_queda_registrado_con_items_y_total(self):
        self.armar_pedido(cantidad=2)
        respuesta = self.confirmar(nombre="Lucía Gómez", telefono="1155550000")
        self.assertEqual(respuesta.status_code, 200)
        pedido = Pedido.objects.get()
        self.assertEqual(pedido.nombre_cliente, "Lucía Gómez")
        self.assertEqual(pedido.telefono, "1155550000")
        self.assertEqual(pedido.estado, "pendiente")
        self.assertEqual(pedido.total, Decimal("3000.00"))
        self.assertEqual(pedido.detalles.count(), 1)
        self.assertEqual(pedido.detalles.first().nombre_producto, "Coca 500ml")

    def test_el_precio_queda_congelado_en_el_item(self):
        self.armar_pedido(cantidad=1)
        self.confirmar()
        self.producto.precio = Decimal("9999.00")
        self.producto.save(update_fields=["precio"])
        item = ItemPedido.objects.get()
        self.assertEqual(item.precio_unitario, Decimal("1500.00"))

    def test_confirmar_vacia_el_carrito_de_la_sesion(self):
        self.armar_pedido()
        self.confirmar()
        self.assertEqual(self.client.session.get("pedido", []), [])

    def test_confirmar_sin_items_falla(self):
        respuesta = self.confirmar()
        self.assertContains(respuesta, "no agregaste ningún producto")
        self.assertEqual(Pedido.objects.count(), 0)

    def test_confirmar_sin_nombre_falla(self):
        self.armar_pedido()
        respuesta = self.confirmar(nombre="   ")
        self.assertContains(respuesta, "tu nombre")
        self.assertEqual(Pedido.objects.count(), 0)

    def test_comentario_se_guarda(self):
        self.armar_pedido()
        self.confirmar(comentario="Paso a las 18")
        self.assertEqual(Pedido.objects.get().comentario, "Paso a las 18")

    def test_vaciar_pedido_limpia_la_sesion(self):
        self.armar_pedido()
        self.client.post(
            reverse("pedidos:pedido_confirmar"), {"accion": "vaciar"}
        )
        self.assertEqual(self.client.session.get("pedido", []), [])


class WhatsappTests(BasePedidos):
    def test_texto_incluye_productos_y_total(self):
        self.armar_pedido(cantidad=2)
        self.confirmar()
        texto = services.texto_para_whatsapp(Pedido.objects.get())
        self.assertIn("Coca 500ml x2", texto)
        self.assertIn("$3.000", texto)
        self.assertIn("Lucía Gómez", texto)

    def test_url_whatsapp_usa_el_numero_configurado(self):
        with override_settings():
            config.WHATSAPP_KIOSCO = "5491100001111"
            url = config.url_whatsapp("Hola mundo")
            self.assertTrue(url.startswith("https://wa.me/5491100001111"))
            self.assertIn("Hola%20mundo", url)

    def test_telefono_se_normaliza_a_digitos(self):
        self.assertEqual(config._limpiar_telefono("+54 9 11 5555-4444"), "5491155554444")
        self.assertEqual(config._limpiar_telefono("(011) 4444-3333"), "01144443333")
        self.assertEqual(config._limpiar_telefono(None), "")

    def test_placeholder_no_cuenta_como_configurado(self):
        config.WHATSAPP_KIOSCO = "5491155554444"
        self.assertFalse(config.whatsapp_configurado())


class PanelPedidosTests(BasePedidos):
    def _pedido(self):
        self.armar_pedido()
        self.confirmar()
        return Pedido.objects.get()

    def test_cajero_no_entra_al_panel(self):
        self.login_cajero()
        self.assertEqual(
            self.client.get(reverse("pedidos:lista_pedidos")).status_code, 403
        )

    def test_anonimo_va_al_login(self):
        respuesta = self.client.get(reverse("pedidos:lista_pedidos"))
        self.assertEqual(respuesta.status_code, 302)

    def test_admin_ve_los_pedidos(self):
        self._pedido()
        self.login_admin()
        respuesta = self.client.get(reverse("pedidos:lista_pedidos"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Lucía Gómez")

    def test_admin_filtra_por_estado(self):
        self._pedido()
        self.login_admin()
        respuesta = self.client.get(
            reverse("pedidos:lista_pedidos"), {"estado": "entregado"}
        )
        self.assertNotContains(respuesta, "Lucía Gómez")

    def test_cambiar_estado_a_entregado_exige_cobrar(self):
        """"Entregado" ya no se marca a mano: para entregar hay que cobrar."""
        pedido = self._pedido()
        self.login_admin()
        self.client.post(
            reverse("pedidos:cambiar_estado", args=[pedido.pk, "entregado"])
        )
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, "pendiente")
        self.assertIsNone(pedido.venta_id)

    def test_cambiar_estado_queda_auditado(self):
        pedido = self._pedido()
        self.login_admin()
        self.client.post(
            reverse("pedidos:cambiar_estado", args=[pedido.pk, "cancelado"])
        )
        self.assertTrue(
            RegistroAuditoria.objects.filter(accion__contains="Pedido").exists()
        )

    def test_estado_invalido_no_rompe(self):
        pedido = self._pedido()
        self.login_admin()
        respuesta = self.client.post(
            reverse("pedidos:cambiar_estado", args=[pedido.pk, "inventado"])
        )
        self.assertEqual(respuesta.status_code, 302)
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, "pendiente")

    def test_cambiar_estado_por_get_se_bloquea(self):
        pedido = self._pedido()
        self.login_admin()
        self.assertEqual(
            self.client.get(
                reverse("pedidos:cambiar_estado", args=[pedido.pk, "entregado"])
            ).status_code,
            403,
        )

    def test_detalle_muestra_los_items(self):
        pedido = self._pedido()
        self.login_admin()
        respuesta = self.client.get(
            reverse("pedidos:detalle_pedido", args=[pedido.pk])
        )
        self.assertContains(respuesta, "Coca 500ml")


class EntregaPedidoTests(BasePedidos):
    """Entregar un pedido de WhatsApp = cobrarlo en el mostrador.

    El pedido arma el cliente desde afuera; cuando viene a retirar, el
    kiosquero lo cobra. La venta que se genera usa el mismo núcleo del POS:
    descuenta stock, suma puntos y, si es cuenta corriente, acumula la deuda.
    """

    def setUp(self):
        super().setUp()
        self.cliente = Cliente.objects.create(
            nombre="Pablo",
            apellido="Méndez",
            dni="30111222",
            telefono="1155556666",
            limite_credito=Decimal("10000.00"),
        )
        self.armar_pedido(cantidad=2)
        self.confirmar(nombre="Pablo Méndez")
        self.pedido = Pedido.objects.get()

    def _entregar(self, **extra):
        datos = {"metodo_pago": "efectivo", "monto_entregado": "3000"}
        datos.update(extra)
        return self.client.post(
            reverse("pedidos:entregar", args=[self.pedido.pk]), datos
        )

    # ===== Cobro =====

    def test_entregar_crea_la_venta_y_vincula_el_pedido(self):
        self.login_admin()
        self._entregar(cliente_id=self.cliente.pk)

        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, "entregado")
        self.assertIsNotNone(self.pedido.venta_id)
        self.assertEqual(self.pedido.cliente_id, self.cliente.pk)

        venta = self.pedido.venta
        self.assertTrue(venta.finalizada)
        self.assertEqual(venta.total, Decimal("3000.00"))
        self.assertEqual(venta.metodo_pago, "efectivo")
        self.assertEqual(venta.cliente_id, self.cliente.pk)

    def test_entregar_descuenta_el_stock(self):
        self.login_admin()
        self._entregar(cliente_id=self.cliente.pk)

        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 8)  # 10 - 2

    def test_entregar_suma_los_puntos_de_fidelidad(self):
        self.login_admin()
        self._entregar(cliente_id=self.cliente.pk)

        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.puntos, 30)  # $3.000 → 30 puntos

    def test_entregar_cobra_el_precio_congelado_del_pedido(self):
        """Si el precio del catálogo cambia después del pedido, se cobra el
        precio que el cliente vio cuando lo armó."""
        self.producto.precio = Decimal("2500.00")
        self.producto.save(update_fields=["precio"])

        self.login_admin()
        self._entregar(cliente_id=self.cliente.pk)

        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.venta.total, Decimal("3000.00"))

    def test_entregar_sin_cliente_lo_deja_como_consumidor_final(self):
        self.login_admin()
        self._entregar()

        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, "entregado")
        self.assertIsNone(self.pedido.cliente_id)
        self.assertIsNone(self.pedido.venta.cliente_id)
        self.assertEqual(self.pedido.venta.total, Decimal("3000.00"))

    def test_entregar_con_tarjeta_no_pide_monto(self):
        self.login_admin()
        self._entregar(metodo_pago="tarjeta", monto_entregado="")

        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.venta.metodo_pago, "tarjeta")
        self.assertIsNone(self.pedido.venta.monto_entregado)

    def test_entregar_calcula_el_vuelto(self):
        self.login_admin()
        self._entregar(monto_entregado="5000")

        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.venta.monto_entregado, Decimal("5000.00"))
        self.assertEqual(self.pedido.venta.vuelto, Decimal("2000.00"))

    # ===== Cuenta corriente (HU-14) =====

    def test_entregar_a_cuenta_corriente_suma_la_deuda(self):
        self.login_admin()
        self._entregar(metodo_pago="cuenta_corriente", cliente_id=self.cliente.pk)

        self.cliente.refresh_from_db()
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.venta.metodo_pago, "cuenta_corriente")
        self.assertEqual(self.cliente.saldo_deuda, Decimal("3000.00"))

    def test_entregar_a_cuenta_corriente_sin_limite_no_cobra(self):
        cliente = Cliente.objects.create(
            nombre="Sin", apellido="Fiado", dni="29999888"
        )
        self.login_admin()
        self._entregar(metodo_pago="cuenta_corriente", cliente_id=cliente.pk)

        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, "pendiente")
        self.assertIsNone(self.pedido.venta_id)
        cliente.refresh_from_db()
        self.assertEqual(cliente.saldo_deuda, Decimal("0.00"))

    def test_entregar_a_cuenta_corriente_respeta_el_limite(self):
        self.login_admin()
        self._entregar(metodo_pago="cuenta_corriente", cliente_id=self.cliente.pk)
        # Ya debe $3.000 de un límite de $10.000: le quedan $7.000, así que
        # un pedido de $7.500 (5 unidades) se pasa y no se cobra.
        self.producto.stock = 100
        self.producto.save(update_fields=["stock"])

        pedido2 = self._nuevo_pedido(cantidad=5)  # 5 x $1.500 = $7.500
        self.client.post(
            reverse("pedidos:entregar", args=[pedido2.pk]),
            {
                "metodo_pago": "cuenta_corriente",
                "cliente_id": self.cliente.pk,
            },
        )

        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.saldo_deuda, Decimal("3000.00"))
        pedido2.refresh_from_db()
        self.assertEqual(pedido2.estado, "pendiente")

    # ===== Reglas =====

    def test_no_se_puede_cobrar_dos_veces_el_mismo_pedido(self):
        self.login_admin()
        self._entregar(cliente_id=self.cliente.pk)
        self._entregar(cliente_id=self.cliente.pk)

        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, "entregado")
        # Sigue habiendo una sola venta: el stock se descontó una vez.
        self.assertEqual(Venta.objects.count(), 1)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 8)

    def test_no_se_cobra_un_pedido_cancelado(self):
        self.pedido.estado = "cancelado"
        self.pedido.save(update_fields=["estado"])

        self.login_admin()
        self._entregar(cliente_id=self.cliente.pk)

        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, "cancelado")
        self.assertIsNone(self.pedido.venta_id)

    def test_entregar_por_get_se_bloquea(self):
        self.login_admin()
        self.assertEqual(
            self.client.get(
                reverse("pedidos:entregar", args=[self.pedido.pk])
            ).status_code,
            403,
        )

    def test_cajero_no_puede_entregar(self):
        self.login_cajero()
        self.assertEqual(
            self.client.post(
                reverse("pedidos:entregar", args=[self.pedido.pk]),
                {"metodo_pago": "efectivo", "monto_entregado": "3000"},
            ).status_code,
            403,
        )

    def test_entregar_queda_auditado(self):
        self.login_admin()
        self._entregar(cliente_id=self.cliente.pk)

        self.assertTrue(
            RegistroAuditoria.objects.filter(
                accion__contains="entregado"
            ).exists()
        )

    def test_el_detalle_muestra_el_formulario_de_entrega(self):
        self.login_admin()
        respuesta = self.client.get(
            reverse("pedidos:detalle_pedido", args=[self.pedido.pk])
        )
        self.assertContains(respuesta, "Entregar y cobrar")

    def test_buscar_clientes_del_panel(self):
        self.login_admin()
        respuesta = self.client.get(
            reverse("pedidos:buscar_cliente"), {"q": "Méndez"}
        )
        self.assertContains(respuesta, "Pablo Méndez")

    def test_buscar_clientes_del_panel_ignora_los_acentos(self):
        """En el mostrador nadie escribe tildes."""
        self.login_admin()
        respuesta = self.client.get(
            reverse("pedidos:buscar_cliente"), {"q": "mendez"}
        )
        self.assertContains(respuesta, "Pablo Méndez")

    def test_buscar_clientes_sin_login_va_al_login(self):
        self.assertEqual(
            self.client.get(reverse("pedidos:buscar_cliente")).status_code, 302
        )

    def test_cajero_no_busca_clientes_del_panel(self):
        self.login_cajero()
        self.assertEqual(
            self.client.get(reverse("pedidos:buscar_cliente")).status_code, 403
        )

    def _nuevo_pedido(self, cantidad=2):
        self.armar_pedido(cantidad=cantidad)
        self.confirmar(nombre="Otro pedido")
        return Pedido.objects.exclude(pk=self.pedido.pk).order_by("-pk").first()
