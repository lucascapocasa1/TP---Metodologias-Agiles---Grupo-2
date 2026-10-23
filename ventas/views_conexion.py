"""
Botón "Conectar con Mercado Pago" (OAuth): el dueño del negocio autoriza a
Norvex desde su cuenta de Mercado Pago y los cobros con QR le llegan directo,
sin copiar credenciales a mano. Solo para el Administrador.
"""
from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from auditoria.utils import registrar_accion
from usuarios.decorators import rol_requerido

from . import mercadopago
from .models import ConexionMercadoPago

CLAVE_STATE = "mp_oauth_state"


def _redirect_uri(request):
    """Dirección a la que vuelve Mercado Pago después de autorizar."""
    return settings.MP_REDIRECT_URI or request.build_absolute_uri(
        reverse("ventas:mercadopago_callback")
    )


def _modo_cobro():
    """Cómo se está cobrando hoy, en palabras para el panel."""
    if ConexionMercadoPago.actual():
        return "conectada"
    if settings.MP_ACCESS_TOKEN:
        return "env"
    return "prueba"


@rol_requerido("Administrador")
def mercadopago_config(request):
    redirect_uri = _redirect_uri(request)
    contexto = {
        "conexion": ConexionMercadoPago.actual(),
        "modo": _modo_cobro(),
        "oauth_disponible": mercadopago.oauth_disponible(),
        "oauth_prueba": settings.MP_OAUTH_PRUEBA,
        "redirect_uri": redirect_uri,
        "redirect_https": redirect_uri.startswith("https://"),
    }
    return render(request, "ventas/mercadopago_config.html", contexto)


@rol_requerido("Administrador")
@require_POST
def mercadopago_conectar(request):
    """Manda al dueño a la página de Mercado Pago para que autorice a Norvex."""
    if not mercadopago.oauth_disponible():
        messages.error(
            request,
            "Falta cargar la aplicación de Norvex en Mercado Pago (MP_CLIENT_ID y "
            "MP_CLIENT_SECRET). La configura una sola vez quien publica el sistema.",
        )
        return redirect("ventas:mercadopago_config")

    state = mercadopago.nuevo_state()
    request.session[CLAVE_STATE] = state
    return redirect(mercadopago.url_autorizacion(_redirect_uri(request), state))


@rol_requerido("Administrador")
def mercadopago_callback(request):
    """Mercado Pago vuelve acá con un código de un solo uso para canjear."""
    state_esperado = request.session.pop(CLAVE_STATE, None)

    if request.GET.get("error"):
        messages.warning(request, "No se conectó la cuenta: la autorización se canceló en Mercado Pago.")
        return redirect("ventas:mercadopago_config")

    code = request.GET.get("code")
    if not code or not state_esperado or request.GET.get("state") != state_esperado:
        # El state protege de que otra página fuerce la conexión de una cuenta ajena.
        messages.error(request, "La respuesta de Mercado Pago no es válida. Probá conectar de nuevo.")
        return redirect("ventas:mercadopago_config")

    try:
        conexion = mercadopago.conectar_cuenta(code, _redirect_uri(request), request.user)
    except mercadopago.MercadoPagoError as exc:
        messages.error(request, f"No se pudo conectar la cuenta de Mercado Pago. {exc}")
        return redirect("ventas:mercadopago_config")

    registrar_accion(
        request.user,
        "Mercado Pago conectado",
        f"Cuenta {conexion.nombre_cuenta or conexion.mp_user_id}"
        f" ({'producción' if conexion.produccion else 'prueba'})",
        request,
    )
    messages.success(request, "¡Listo! Los cobros con QR ahora llegan a tu cuenta de Mercado Pago.")
    return redirect("ventas:mercadopago_config")


@rol_requerido("Administrador")
@require_POST
def mercadopago_desconectar(request):
    conexion = ConexionMercadoPago.actual()
    if conexion is None:
        return redirect("ventas:mercadopago_config")
    mercadopago.desconectar_cuenta()
    registrar_accion(
        request.user,
        "Mercado Pago desconectado",
        f"Cuenta {conexion.nombre_cuenta or conexion.mp_user_id}",
        request,
    )
    messages.info(request, "Cuenta de Mercado Pago desconectada.")
    return redirect("ventas:mercadopago_config")
