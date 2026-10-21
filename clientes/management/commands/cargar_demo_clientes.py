"""Comando de datos de demostración de clientes y pedidos (HU-12/13/14).

Carga un grupo de clientes con **compras reales** (ventas con detalle, stock
descontado, puntos acumulados y deuda coherente con el límite de crédito) y
los pedidos que llegan por WhatsApp desde el catálogo público.

Los pedidos que ya se retiraron se cobran con el flujo real de entrega
(`pedidos.services.registrar_entrega`): la venta, el stock, los puntos y la
deuda quedan como si el kiosquero los hubiera hecho en el mostrador. Los
pedidos que siguen pendientes **no** son clientes todavía (el cliente todavía
no pasó por el kiosco), así que no aparecen en la lista de clientes.

Uso:
    python manage.py cargar_demo_clientes --limpiar   # recomendado
    python manage.py cargar_demo_clientes               # solo si no hay demo

Corre antes `python manage.py cargar_demo` (hace falta el catálogo de
productos) y `python manage.py setup_inicial` (hacen falta los usuarios).
"""
from datetime import datetime, time
from decimal import ROUND_CEILING, Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db.models import F
from django.utils import timezone

from clientes.demo_data import (
    CLIENTES_DEMO,
    LIMITE_AL_DIA,
    MARGEN_CREDITO,
    PEDIDOS_DEMO,
    REDONDEO_CREDITO,
    dia_del_demo,
)
from clientes.models import Cliente
from pedidos.models import ItemPedido, Pedido
from pedidos.services import ErrorPedido, registrar_entrega
from ventas import services as cobros
from ventas.models import DetalleVenta, Producto, Venta


class Command(BaseCommand):
    help = (
        "Carga clientes con compras reales y pedidos de WhatsApp (los "
        "entregados se cobran con el flujo real de entrega)"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--limpiar",
            action="store_true",
            help=(
                "Borra la demo anterior (clientes, sus ventas y los pedidos) "
                "y vuelve a cargarla"
            ),
        )

    # ---------- Utilidades ----------

    def _producto(self, nombre):
        producto = Producto.objects.filter(nombre=nombre, activo=True).first()
        if producto is None:
            raise CommandError(
                f"Falta el producto «{nombre}». Corré `manage.py cargar_demo` "
                "primero para cargar el catálogo."
            )
        return producto

    def _cajero(self):
        """El usuario que figura como cajero de las ventas del mostrador."""
        return (
            User.objects.filter(groups__name="Cajero").first()
            or User.objects.filter(groups__name="Administrador").first()
            or User.objects.first()
        )

    def _admin(self):
        """El que entrega los pedidos (el panel es solo del Administrador)."""
        return (
            User.objects.filter(groups__name="Administrador").first()
            or User.objects.first()
        )

    def _restaurar_stock(self, ventas):
        """Devuelve al stock lo que consumieron las ventas que se borran."""
        consumos = {}
        for detalle in DetalleVenta.objects.filter(venta__in=ventas).values(
            "producto_id", "cantidad"
        ):
            pid = detalle["producto_id"]
            consumos[pid] = consumos.get(pid, 0) + detalle["cantidad"]
        for producto_id, cantidad in consumos.items():
            Producto.objects.filter(pk=producto_id).update(
                stock=F("stock") + cantidad
            )
        return consumos

    def _total_de(self, items):
        total = Decimal("0.00")
        for nombre, cantidad in items:
            total += self._producto(nombre).precio * cantidad
        return total

    def _limite_de(self, perfil, fiado):
        """Límite de crédito del cliente según su perfil de demo."""
        if perfil == "limite":
            # Debe exactamente su límite: no le queda nada para fiar.
            return (
                (fiado / REDONDEO_CREDITO).to_integral_value(
                    rounding=ROUND_CEILING
                )
                * REDONDEO_CREDITO
            )
        if perfil == "al_dia_cc":
            return LIMITE_AL_DIA
        if perfil == "al_dia":
            return Decimal("0.00")
        # "debe": el límite siempre alcanza para lo que ya debe, y encima
        # tiene margen para volver a comprar.
        return (
            (fiado / REDONDEO_CREDITO).to_integral_value(rounding=ROUND_CEILING)
            * REDONDEO_CREDITO
            + MARGEN_CREDITO
        )

    # ---------- Limpieza ----------

    def _limpiar(self):
        """Borra la demo anterior: pedidos, ventas de los clientes y clientes."""
        dnis = [d["dni"] for d in CLIENTES_DEMO]
        dnis += [p["cliente"]["dni"] for p in PEDIDOS_DEMO if "cliente" in p]
        nombres = [p["nombre"] for p in PEDIDOS_DEMO]

        pedidos = Pedido.objects.filter(nombre_cliente__in=nombres)
        pedidos_borrados = pedidos.count()
        pedidos.delete()

        ventas = Venta.objects.filter(cliente__dni__in=dnis)
        consumos = self._restaurar_stock(ventas)
        ventas_borradas = ventas.count()
        ventas.delete()

        clientes_borrados = Cliente.objects.filter(dni__in=dnis).delete()[0]

        self.stdout.write(
            f"Demo anterior borrada: {clientes_borrados} clientes, "
            f"{ventas_borradas} ventas, {pedidos_borrados} pedidos."
        )
        if consumos:
            self.stdout.write(
                f"Stock repuesto: {len(consumos)} producto(s) con unidades "
                "devueltas."
            )

    # ---------- Clientes del mostrador ----------

    def _crear_compra(self, cliente, metodo, items, usuario, dias):
        """Una compra en el mostrador, con venta, detalle y stock descontado."""
        objetos = []
        total = Decimal("0.00")
        for nombre, cantidad in items:
            producto = self._producto(nombre)
            objetos.append({"producto": producto, "cantidad": cantidad})
            total += producto.precio * cantidad

        monto_entregado = None
        vuelto = None
        if metodo == "efectivo":
            # Billetes reales del kiosco: se redondea hacia arriba.
            miles = (total / 1000).to_integral_value(rounding=ROUND_CEILING)
            monto_entregado = max(miles * 1000, Decimal("1000"))
            vuelto = monto_entregado - total

        venta = cobros.registrar_venta_desde_items(
            objetos,
            metodo_pago=metodo,
            cliente=cliente,
            usuario=usuario,
            monto_entregado=monto_entregado,
        )

        # `fecha` es auto_now_add: hay que fijarla después de crearla.
        fecha = timezone.make_aware(
            datetime.combine(dia_del_demo(dias), time(18, 30))
        )
        Venta.objects.filter(pk=venta.pk).update(fecha=fecha)
        return venta

    def _cargar_clientes(self, cajero):
        """Crea los clientes del mostrador con sus compras reales."""
        creados = 0
        for datos in CLIENTES_DEMO:
            fiado = sum(
                (
                    self._total_de(items)
                    for _dia, metodo, items in datos["compras"]
                    if metodo == "cuenta_corriente"
                ),
                Decimal("0.00"),
            )

            cliente = Cliente.objects.create(
                nombre=datos["nombre"],
                apellido=datos["apellido"],
                dni=datos["dni"],
                telefono=datos["telefono"],
                limite_credito=self._limite_de(datos["perfil"], fiado),
            )

            for dias, metodo, items in datos["compras"]:
                self._crear_compra(cliente, metodo, items, cajero, dias)

            cliente.refresh_from_db()
            creados += 1
            self.stdout.write(
                f"  · {cliente.nombre_completo}: "
                f"{cliente.ventas.filter(finalizada=True).count()} compras · "
                f"debe ${cliente.saldo_deuda} de ${cliente.limite_credito} · "
                f"{cliente.puntos} pts"
            )
        self.stdout.write(f"Clientes creados: {creados}.")
        return creados

    # ---------- Pedidos de WhatsApp ----------

    def _cargar_pedidos(self, admin):
        """Crea los pedidos del catálogo público y cobra los ya retirados."""
        pendientes = 0
        entregados = 0
        cancelados = 0
        for indice, datos in enumerate(PEDIDOS_DEMO):
            items = [(nombre, cantidad) for nombre, cantidad in datos["items"]]
            total = self._total_de(items)

            pedido = Pedido.objects.create(
                nombre_cliente=datos["nombre"],
                telefono=datos["telefono"],
                comentario=datos["comentario"],
                total=total,
            )
            ItemPedido.objects.bulk_create(
                [
                    ItemPedido(
                        pedido=pedido,
                        producto=self._producto(nombre),
                        nombre_producto=nombre,
                        cantidad=cantidad,
                        precio_unitario=self._producto(nombre).precio,
                    )
                    for nombre, cantidad in items
                ]
            )
            # `fecha` es auto_now_add: los pedidos se reparten en el historial.
            dias = 30 - indice
            Pedido.objects.filter(pk=pedido.pk).update(
                fecha=timezone.make_aware(
                    datetime.combine(dia_del_demo(dias), time(12, 0))
                )
            )

            if datos["estado"] != "entregado":
                if datos["estado"] == "pendiente":
                    pendientes += 1
                else:
                    # Cancelado: el cliente se arrepintió, no se cobra nada.
                    Pedido.objects.filter(pk=pedido.pk).update(
                        estado="cancelado"
                    )
                    cancelados += 1
                continue

            # El cliente retiró y pagó: se cobra con el flujo real.
            datos_cliente = datos["cliente"]
            cliente, _ = Cliente.objects.get_or_create(
                dni=datos_cliente["dni"],
                defaults={
                    "nombre": datos_cliente["nombre"],
                    "apellido": datos_cliente["apellido"],
                    "telefono": datos["telefono"],
                },
            )
            if datos["metodo"] == "cuenta_corriente" and not cliente.tiene_cuenta_corriente:
                # El que llega por WhatsApp y no puede pagar igual es cliente:
                # se le habilita la cuenta corriente con margen.
                cliente.limite_credito = self._limite_de("debe", total)
                cliente.save(update_fields=["limite_credito"])

            monto = None
            if datos["metodo"] == "efectivo":
                miles = (total / 1000).to_integral_value(rounding=ROUND_CEILING)
                monto = max(miles * 1000, Decimal("1000"))

            try:
                registrar_entrega(
                    pedido,
                    cliente,
                    metodo_pago=datos["metodo"],
                    usuario=admin,
                    monto_entregado=monto,
                )
            except ErrorPedido as exc:
                self.stdout.write(
                    self.style.ERROR(
                        f"  ! No se pudo cobrar el pedido #{pedido.pk}: {exc}"
                    )
                )
                continue

            entregados += 1
            self.stdout.write(
                f"  · Pedido #{pedido.pk} de {datos['nombre']}: entregado y "
                f"cobrado (${total})."
            )

        self.stdout.write(
            f"Pedidos creados: {len(PEDIDOS_DEMO)} "
            f"({pendientes} pendientes, {entregados} entregados y cobrados, "
            f"{cancelados} cancelados)."
        )

    # ---------- main ----------

    def handle(self, *args, **options):
        if not Producto.objects.filter(activo=True).exists():
            self.stdout.write(
                self.style.ERROR(
                    "No hay productos: corré `manage.py cargar_demo` primero."
                )
            )
            return

        if options["limpiar"]:
            self._limpiar()
        elif Cliente.objects.filter(
            dni__in=[d["dni"] for d in CLIENTES_DEMO]
        ).exists():
            self.stdout.write(
                self.style.WARNING(
                    "Ya hay clientes de demo cargados: no se generan nuevos "
                    "para no duplicar. Usá --limpiar para recargar."
                )
            )
            return

        self._cargar_clientes(self._cajero())
        self._cargar_pedidos(self._admin())
        self.stdout.write(self.style.SUCCESS("Datos de demo de clientes cargados."))
