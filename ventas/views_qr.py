"""
Vistas del cobro con QR de Mercado Pago: estado del pago, cancelación,
pantalla para el celular del cliente, pago simulado y webhook.
"""
import json
import socket
from datetime import timedelta
from urllib.parse import urlsplit

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from auditoria.utils import registrar_accion

from . import cobro_qr, mercadopago, services
from .models import PagoMercadoPago
from .services import ErrorCobro

HOSTS_LOCALES = {"localhost", "127.0.0.1", "::1"}


def _ip_en_la_red():
    """IP de esta PC en la red local (la que tiene que usar el celular)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))  # no manda nada, solo elige la interfaz
        return s.getsockname()[0]
    except OSError:
        return None
    finally:
        s.close()


def url_para_celular(request, ruta):
    """
    URL absoluta que funcione desde un celular. Si la caja se abrió con
    localhost se cambia por la IP de la PC en la red: para el celular,
    "localhost" es el propio celular.
    """
    url = request.build_absolute_uri(ruta)
    partes = urlsplit(url)
    if partes.hostname in HOSTS_LOCALES:
        ip = _ip_en_la_red()
        if ip:
            puerto = f":{partes.port}" if partes.port else ""
            url = f"{partes.scheme}://{ip}{puerto}{ruta}"
    return url


def _pago_del_cajero(request, pago_id):
    return get_object_or_404(
        PagoMercadoPago.objects.select_related("venta"),
        pk=pago_id,
        venta__usuario=request.user,
    )


def iniciar_cobro_qr(request):
    """Lo llama `cobro_confirmar` cuando el método elegido es Mercado Pago."""

    def link_simulado(pago):
        return url_para_celular(request, reverse("ventas:pago_simulado", args=[pago.token]))

    try:
        pago = cobro_qr.iniciar_cobro_qr(request, link_simulado)
    except ErrorCobro as exc:
        messages.error(request, str(exc))
        return redirect("ventas:pantalla_cobro")

    registrar_accion(
        request.user,
        "Cobro con QR iniciado",
        f"Venta N° {pago.venta_id} por {services.formatear_monto(pago.venta.total)}",
        request,
    )
    return redirect("ventas:pantalla_cobro")


@login_required
@require_GET
def pago_estado(request, pago_id):
    """La caja consulta esto cada pocos segundos mientras muestra el QR."""
    pago = _pago_del_cajero(request, pago_id)
    error = ""
    try:
        pago = cobro_qr.actualizar_desde_mercadopago(pago)
    except mercadopago.MercadoPagoError as exc:
        error = str(exc)
    datos = {"estado": pago.estado, "error": error}
    if pago.estado == PagoMercadoPago.APROBADO:
        datos["comprobante"] = f"{reverse('ventas:pantalla_cobro')}?venta={pago.venta_id}"
    return JsonResponse(datos)


@login_required
@require_POST
def pago_cancelar(request, pago_id):
    pago = _pago_del_cajero(request, pago_id)
    items = cobro_qr.cancelar_cobro(pago)
    if items is None:
        messages.info(request, "Ese cobro ya no estaba esperando pago.")
        return redirect("ventas:pantalla_cobro")

    # Los productos vuelven al carrito para cobrar de otra forma.
    services.guardar_carrito(request, items)
    registrar_accion(request.user, "Cobro con QR cancelado", f"Venta N° {pago.venta_id}", request)
    messages.info(request, "Cobro con QR cancelado. Los productos volvieron al carrito.")
    return redirect("ventas:pantalla_cobro")


# --- Pantalla para el celular del cliente ---------------------------------

@login_required
def display(request):
    """Página para dejar abierta en un celular del negocio, mirando al cliente."""
    return render(request, "ventas/display.html")


@login_required
@require_GET
def display_estado(request):
    """Cobro pendiente del cajero, o uno aprobado hace instantes (una sola consulta)."""
    pago = (
        PagoMercadoPago.objects.select_related("venta")
        .filter(venta__usuario=request.user)
        .filter(
            Q(estado=PagoMercadoPago.PENDIENTE)
            | Q(
                estado=PagoMercadoPago.APROBADO,
                actualizado__gte=timezone.now() - timedelta(seconds=10),
            )
        )
        .order_by("-creado")
        .first()
    )
    if pago is None:
        return JsonResponse({"estado": "libre"})
    datos = {
        "estado": pago.estado,
        "pago": pago.pk,
        "total": services.formatear_monto(pago.venta.total),
    }
    if pago.estado == PagoMercadoPago.PENDIENTE:
        datos["link"] = pago.link_pago
    return JsonResponse(datos)


# --- Pago simulado (modo de prueba, sin credenciales) ----------------------

def pago_simulado(request, token):
    """
    Imita la pantalla de pago de Mercado Pago para mostrar el circuito sin
    cuenta ni plata real. Solo existe para cobros creados en modo de prueba.
    """
    pago = get_object_or_404(PagoMercadoPago.objects.select_related("venta"), token=token)
    if not pago.simulado:
        raise Http404
    if request.method == "POST" and pago.estado == PagoMercadoPago.PENDIENTE:
        pago = cobro_qr.aprobar_pago(pago, payment_id="SIMULADO")
    return render(
        request,
        "ventas/pago_simulado.html",
        {"pago": pago, "detalles": pago.venta.detalles.select_related("producto")},
    )


# --- Webhook de Mercado Pago -----------------------------------------------

@csrf_exempt
@require_POST
def mercadopago_webhook(request):
    """
    Mercado Pago avisa acá cuando cambia un pago. No se confía en el aviso:
    con el id se vuelve a pedir el pago a la API y recién ahí se aprueba.
    """
    if not mercadopago.esta_configurado():
        return HttpResponse(status=200)

    tipo = request.GET.get("type") or request.GET.get("topic")
    payment_id = request.GET.get("data.id") or request.GET.get("id")
    try:
        cuerpo = json.loads(request.body or b"{}")
    except ValueError:
        cuerpo = {}
    tipo = tipo or cuerpo.get("type") or cuerpo.get("topic")
    payment_id = payment_id or (cuerpo.get("data") or {}).get("id")

    if tipo != "payment" or not payment_id or not str(payment_id).isdigit():
        return HttpResponse(status=200)

    try:
        datos = mercadopago.obtener_pago(payment_id)
    except mercadopago.MercadoPagoError:
        return HttpResponse(status=502)  # Mercado Pago reintenta más tarde

    referencia = datos.get("external_reference") or ""
    prefijo = mercadopago.PREFIJO_REFERENCIA
    if datos.get("status") == "approved" and referencia.startswith(prefijo):
        venta_id = referencia.removeprefix(prefijo)
        if venta_id.isdigit():
            pago = PagoMercadoPago.objects.filter(venta_id=venta_id).first()
            if pago:
                cobro_qr.aprobar_pago(pago, str(payment_id))
    return HttpResponse(status=200)
