"""
Cliente mínimo de la API de Mercado Pago (Checkout Pro).

Flujo:
    1. La caja crea una "preferencia" con los productos de la venta.
    2. Mercado Pago devuelve un link de pago; ese link es lo que va en el QR.
    3. El cliente escanea el QR con el celular y paga en la app de Mercado Pago.
    4. La caja consulta cada pocos segundos si ya hay un pago aprobado con la
       referencia de esa venta (y, si hay una URL pública, también llega el
       aviso por webhook).

Se usa urllib de la librería estándar para no sumar dependencias al proyecto.
Las credenciales salen del .env (MP_ACCESS_TOKEN). Si no hay token, la caja
funciona en "modo simulado" para poder probar sin cuenta de Mercado Pago.
"""
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

API_URL = "https://api.mercadopago.com"
MINUTOS_VALIDEZ_QR = 30
PREFIJO_REFERENCIA = "norvex-venta-"


class MercadoPagoError(Exception):
    """Error al hablar con Mercado Pago (red, credenciales, datos inválidos)."""


def esta_configurado():
    return bool(settings.MP_ACCESS_TOKEN)


def usa_sandbox():
    """Las credenciales de prueba empiezan con TEST- y usan el link de sandbox."""
    return settings.MP_ACCESS_TOKEN.startswith("TEST-")


def referencia_de(venta):
    """Referencia que viaja a Mercado Pago para reconocer la venta después."""
    return f"{PREFIJO_REFERENCIA}{venta.pk}"


def _llamar(metodo, ruta, datos=None):
    cuerpo = json.dumps(datos).encode("utf-8") if datos is not None else None
    pedido = urllib.request.Request(
        API_URL + ruta,
        data=cuerpo,
        method=metodo,
        headers={
            "Authorization": f"Bearer {settings.MP_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(pedido, timeout=15) as respuesta:
            return json.loads(respuesta.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detalle = error.read().decode("utf-8", "replace")[:300]
        raise MercadoPagoError(f"Mercado Pago respondió {error.code}: {detalle}") from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise MercadoPagoError(f"No se pudo conectar con Mercado Pago: {error}") from error


def crear_preferencia(venta):
    """Crea el cobro en Mercado Pago. Devuelve (preference_id, link_de_pago)."""
    vence = timezone.localtime() + timedelta(minutes=MINUTOS_VALIDEZ_QR)
    items = [
        {
            "id": str(detalle.producto_id),
            "title": detalle.producto.nombre[:250],
            "quantity": detalle.cantidad,
            "unit_price": float(detalle.precio_unitario),
            "currency_id": "ARS",
        }
        for detalle in venta.detalles.select_related("producto")
    ]
    datos = {
        "items": items,
        "external_reference": referencia_de(venta),
        "statement_descriptor": settings.MP_NOMBRE_EN_RESUMEN,
        "expires": True,
        "expiration_date_to": vence.isoformat(timespec="milliseconds"),
    }
    if settings.MP_NOTIFICATION_URL:
        datos["notification_url"] = settings.MP_NOTIFICATION_URL

    respuesta = _llamar("POST", "/checkout/preferences", datos)
    link = respuesta.get("sandbox_init_point") if usa_sandbox() else None
    link = link or respuesta.get("init_point")
    if not link:
        raise MercadoPagoError("Mercado Pago no devolvió un link de pago.")
    return respuesta["id"], link


def buscar_pago_aprobado(referencia):
    """Devuelve el id del pago aprobado para esa referencia, o None si todavía no hay."""
    consulta = urllib.parse.urlencode(
        {"external_reference": referencia, "sort": "date_created", "criteria": "desc"}
    )
    respuesta = _llamar("GET", f"/v1/payments/search?{consulta}")
    for pago in respuesta.get("results", []):
        if pago.get("status") == "approved":
            return str(pago["id"])
    return None


def obtener_pago(payment_id):
    """Datos de un pago puntual (lo usa el webhook para verificar el aviso)."""
    return _llamar("GET", f"/v1/payments/{int(payment_id)}")
