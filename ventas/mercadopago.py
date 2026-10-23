"""
Cliente mínimo de la API de Mercado Pago (Checkout Pro + OAuth).

Cobro:
    1. La caja crea una "preferencia" con los productos de la venta.
    2. Mercado Pago devuelve un link de pago; ese link es lo que va en el QR.
    3. El cliente escanea el QR con el celular y paga.
    4. La caja consulta cada pocos segundos si ya hay un pago aprobado con la
       referencia de esa venta (y, si el sistema está online, también llega el
       aviso por webhook).

¿A qué cuenta llega la plata? Se usa, en este orden:
    1. La cuenta que el negocio conectó con el botón "Conectar con Mercado
       Pago" (OAuth, modelo ConexionMercadoPago).
    2. MP_ACCESS_TOKEN del .env (para desarrollo).
    3. Ninguna: modo de prueba con pago simulado, sin plata real.

Se usa urllib de la librería estándar para no sumar dependencias al proyecto.
"""
import json
import secrets
import urllib.error
import urllib.parse
import urllib.request
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

API_URL = "https://api.mercadopago.com"
AUTH_URL = "https://auth.mercadopago.com/authorization"
MINUTOS_VALIDEZ_QR = 30
PREFIJO_REFERENCIA = "norvex-venta-"
# Se renueva el token si le quedan menos de estos días (Mercado Pago lo da por ~6 meses).
DIAS_PARA_RENOVAR = 7


class MercadoPagoError(Exception):
    """Error al hablar con Mercado Pago (red, credenciales, datos inválidos)."""


# --- ¿Con qué cuenta se cobra? ------------------------------------------------

def _conexion():
    from .models import ConexionMercadoPago

    return ConexionMercadoPago.actual()


def esta_configurado():
    """True si hay una cuenta para cobrar de verdad (conectada o en el .env)."""
    return _conexion() is not None or bool(settings.MP_ACCESS_TOKEN)


def usa_sandbox():
    """True si se cobra con una cuenta de prueba (plata ficticia)."""
    conexion = _conexion()
    if conexion is not None:
        return not conexion.produccion
    return settings.MP_ACCESS_TOKEN.startswith("TEST-")


def _token():
    """Access token a usar. Si la cuenta conectada está por vencer, la renueva."""
    conexion = _conexion()
    if conexion is None:
        return settings.MP_ACCESS_TOKEN
    por_vencer = conexion.expira and conexion.expira - timezone.now() < timedelta(days=DIAS_PARA_RENOVAR)
    if por_vencer and conexion.refresh_token:
        try:
            conexion = renovar_conexion(conexion)
        except MercadoPagoError:
            pass  # se intenta con el token actual; si venció, el error lo muestra la caja
    return conexion.access_token


def referencia_de(venta):
    """Referencia que viaja a Mercado Pago para reconocer la venta después."""
    return f"{PREFIJO_REFERENCIA}{venta.pk}"


def _llamar(metodo, ruta, datos=None, token=None):
    cuerpo = json.dumps(datos).encode("utf-8") if datos is not None else None
    encabezados = {"Content-Type": "application/json", "Accept": "application/json"}
    if token is not False:
        encabezados["Authorization"] = f"Bearer {token or _token()}"
    pedido = urllib.request.Request(API_URL + ruta, data=cuerpo, method=metodo, headers=encabezados)
    try:
        with urllib.request.urlopen(pedido, timeout=15) as respuesta:
            return json.loads(respuesta.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detalle = error.read().decode("utf-8", "replace")[:300]
        raise MercadoPagoError(f"Mercado Pago respondió {error.code}: {detalle}") from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise MercadoPagoError(f"No se pudo conectar con Mercado Pago: {error}") from error


# --- Cobro con QR -------------------------------------------------------------

def crear_preferencia(venta, notification_url=None):
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
    notification_url = settings.MP_NOTIFICATION_URL or notification_url
    if notification_url:
        datos["notification_url"] = notification_url

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


# --- Conectar la cuenta del negocio (OAuth) ------------------------------------

def oauth_disponible():
    """True si la plataforma Norvex tiene su aplicación de Mercado Pago cargada."""
    return bool(settings.MP_CLIENT_ID and settings.MP_CLIENT_SECRET)


def nuevo_state():
    """Valor al azar que se guarda en la sesión para validar la vuelta de Mercado Pago."""
    return secrets.token_urlsafe(24)


def url_autorizacion(redirect_uri, state):
    """Página de Mercado Pago donde el dueño del negocio autoriza a Norvex."""
    parametros = urllib.parse.urlencode(
        {
            "client_id": settings.MP_CLIENT_ID,
            "response_type": "code",
            "platform_id": "mp",
            "state": state,
            "redirect_uri": redirect_uri,
        }
    )
    return f"{AUTH_URL}?{parametros}"


def _pedir_token(datos):
    datos = {
        "client_id": settings.MP_CLIENT_ID,
        "client_secret": settings.MP_CLIENT_SECRET,
        **datos,
    }
    respuesta = _llamar("POST", "/oauth/token", datos, token=False)
    if not respuesta.get("access_token"):
        raise MercadoPagoError("Mercado Pago no devolvió las credenciales de la cuenta.")
    return respuesta


def _vencimiento(respuesta):
    segundos = respuesta.get("expires_in")
    return timezone.now() + timedelta(seconds=int(segundos)) if segundos else None


def _nombre_de_cuenta(access_token):
    """Nombre o email de la cuenta conectada, solo para mostrar en el panel."""
    try:
        datos = _llamar("GET", "/users/me", token=access_token)
    except MercadoPagoError:
        return ""
    nombre = " ".join(filter(None, [datos.get("first_name"), datos.get("last_name")]))
    return (nombre or datos.get("nickname") or datos.get("email") or "")[:200]


def conectar_cuenta(code, redirect_uri, usuario):
    """
    Canjea el código que devolvió Mercado Pago por las credenciales del negocio
    y las guarda. Reemplaza cualquier cuenta conectada antes.
    """
    from .models import ConexionMercadoPago

    datos = {"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri}
    if settings.MP_OAUTH_PRUEBA:
        datos["test_token"] = "true"  # credenciales de prueba (sandbox)
    respuesta = _pedir_token(datos)

    ConexionMercadoPago.objects.all().delete()
    return ConexionMercadoPago.objects.create(
        access_token=respuesta["access_token"],
        refresh_token=respuesta.get("refresh_token", ""),
        expira=_vencimiento(respuesta),
        mp_user_id=str(respuesta.get("user_id", "")),
        nombre_cuenta=_nombre_de_cuenta(respuesta["access_token"]),
        produccion=bool(respuesta.get("live_mode")) and not settings.MP_OAUTH_PRUEBA,
        conectada_por=usuario if usuario and usuario.is_authenticated else None,
    )


def renovar_conexion(conexion):
    """Pide credenciales nuevas con el refresh token antes de que venzan."""
    respuesta = _pedir_token({"grant_type": "refresh_token", "refresh_token": conexion.refresh_token})
    conexion.access_token = respuesta["access_token"]
    conexion.refresh_token = respuesta.get("refresh_token", conexion.refresh_token)
    conexion.expira = _vencimiento(respuesta)
    conexion.save(update_fields=["access_token", "refresh_token", "expira", "actualizada"])
    return conexion


def desconectar_cuenta():
    """Borra la cuenta conectada: los cobros con QR vuelven al .env o al modo de prueba."""
    from .models import ConexionMercadoPago

    ConexionMercadoPago.objects.all().delete()
