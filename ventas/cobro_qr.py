"""
Cobro con QR de Mercado Pago (se suma a la caja de HU-07/08/09).

Flujo:
    1. El cajero elige "Mercado Pago (QR)" en el carrito y confirma.
    2. Se crea la Venta con el mismo núcleo que el resto de los cobros
       (`services._crear_venta`), pero con `finalizada=False`: el stock queda
       reservado y la venta todavía no cuenta en reportes ni en el turno.
    3. Se pide el link de pago a Mercado Pago y la caja lo muestra como QR.
    4. Cuando Mercado Pago informa el pago aprobado, la venta pasa a
       finalizada y el cliente de la fidelidad suma sus puntos.
    5. Si el cajero cancela, el stock vuelve y los productos regresan al
       carrito para cobrar de otra forma.
"""
from django.db import transaction
from django.db.models import F
from django.urls import reverse

from clientes import services as fidelidad

from . import mercadopago, services
from .models import PagoMercadoPago, Producto, Venta
from .services import ErrorCobro


def pago_pendiente(usuario):
    """El cobro QR que el cajero tiene esperando pago, si hay uno."""
    return (
        PagoMercadoPago.objects.select_related("venta")
        .filter(venta__usuario=usuario, estado=PagoMercadoPago.PENDIENTE)
        .first()
    )


def iniciar_cobro_qr(request, url_pago_simulado):
    """
    Crea la venta pendiente con lo que hay en el carrito y su cobro en
    Mercado Pago. `url_pago_simulado(pago)` arma el link a usar cuando no
    hay credenciales (modo de prueba).
    """
    if pago_pendiente(request.user):
        raise ErrorCobro("Ya hay un cobro con QR esperando pago. Esperalo o cancelalo.")

    items = services.items_del_carrito(request)
    if not items:
        raise ErrorCobro("El carrito está vacío.")

    with transaction.atomic():
        cliente = fidelidad.cliente_para_venta(request)
        venta = services._crear_venta(
            items, services.METODO_QR, cliente, request.user, None, finalizada=False
        )
        pago = PagoMercadoPago(venta=venta, simulado=not mercadopago.esta_configurado())
        if pago.simulado:
            pago.link_pago = url_pago_simulado(pago)
            pago.save()

    if not pago.simulado:
        # La llamada a Mercado Pago va fuera de la transacción para no tener
        # filas bloqueadas mientras se espera la red.
        try:
            pago.preference_id, pago.link_pago = mercadopago.crear_preferencia(
                venta, notification_url=_url_webhook(request)
            )
        except mercadopago.MercadoPagoError as exc:
            _devolver_stock(venta)
            raise ErrorCobro(f"No se pudo generar el QR de Mercado Pago. {exc}")
        pago.save()

    services.vaciar_carrito(request)
    fidelidad.quitar_cliente_de_sesion(request)
    return pago


def _url_webhook(request):
    """
    Dirección pública del webhook. Solo si el sistema está online con https:
    desde la PC (localhost) Mercado Pago no puede llegar, y la caja se entera
    igual consultando cada pocos segundos.
    """
    url = request.build_absolute_uri(reverse("ventas:mercadopago_webhook"))
    return url if url.startswith("https://") else None


@transaction.atomic
def aprobar_pago(pago, payment_id=""):
    """Marca el pago como aprobado y finaliza la venta (no hace nada si ya no estaba pendiente)."""
    pago = PagoMercadoPago.objects.select_for_update().get(pk=pago.pk)
    if pago.estado != PagoMercadoPago.PENDIENTE:
        return pago

    pago.estado = PagoMercadoPago.APROBADO
    pago.payment_id = payment_id
    pago.save(update_fields=["estado", "payment_id", "actualizado"])

    venta = Venta.objects.select_for_update().get(pk=pago.venta_id)
    venta.finalizada = True
    venta.save(update_fields=["finalizada"])
    if venta.cliente_id:
        cliente = fidelidad.cliente_bloqueado(venta.cliente)
        fidelidad.sumar_puntos(cliente, venta.puntos_ganados)
    return pago


def _devolver_stock(venta):
    for detalle in venta.detalles.all():
        Producto.objects.filter(pk=detalle.producto_id).update(
            stock=F("stock") + detalle.cantidad
        )


@transaction.atomic
def cancelar_cobro(pago):
    """
    Cancela un cobro QR pendiente: devuelve el stock y deja el pago como
    cancelado. Devuelve los items para volver a cargarlos en el carrito, o
    None si el cobro ya no estaba pendiente (por ejemplo, se pagó justo antes).
    """
    pago = PagoMercadoPago.objects.select_for_update().get(pk=pago.pk)
    if pago.estado != PagoMercadoPago.PENDIENTE:
        return None
    _devolver_stock(pago.venta)
    pago.estado = PagoMercadoPago.CANCELADO
    pago.save(update_fields=["estado", "actualizado"])
    return [
        {"producto_id": d.producto_id, "cantidad": d.cantidad}
        for d in pago.venta.detalles.all()
    ]


def actualizar_desde_mercadopago(pago):
    """Si el cobro sigue pendiente, pregunta a Mercado Pago si ya se pagó."""
    if pago.estado != PagoMercadoPago.PENDIENTE or pago.simulado:
        return pago
    payment_id = mercadopago.buscar_pago_aprobado(mercadopago.referencia_de(pago.venta))
    if payment_id:
        pago = aprobar_pago(pago, payment_id)
    return pago
