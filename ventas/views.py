"""
Vistas del POS (Sprint 2).

Pantalla rápida del cajero: escaneo por código de barras o botones de
productos, carrito en la sesión y cobro con cálculo de vuelto en billetes.

Todos los endpoints son HTMX-friendly: las peticiones que vienen de HTMX
(header `HX-Request`) devuelven solo el fragmento del panel de cobro, así
el cajero agrega productos y cobra sin recargar la página.
"""
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from usuarios.decorators import es_administrador, es_cajero

from . import services
from .models import DetalleVenta, Producto, Venta
from .vuelto import DENOMINACIONES, desglosar_vuelto


def _pantalla_habilitada(request):
    """El POS lo usan tanto el Cajero como el Administrador (el dueño
    también puede pararse a cobrar en el mostrador)."""
    return es_administrador(request.user) or es_cajero(request.user)


def _panel_cobro(request, contexto_extra=None):
    """
    Common context para los fragmentos del carrito. Dependiendo de si la
    petición vino por HTMX devuelve el fragmento HTML o la página completa.
    """
    items, total = services.detalle_carrito(request.session)
    contexto = {
        "items": items,
        "total": total,
        "denominaciones": DENOMINACIONES,
    }
    if contexto_extra:
        contexto.update(contexto_extra)

    if request.headers.get("HX-Request"):
        return render(request, "ventas/partials/panel_cobro.html", contexto)
    return redirect("ventas:pantalla_cobro")


def _error_mensaje(texto, tipo="error"):
    return {"mensaje": texto, "mensaje_tipo": tipo}


def contexto_cobro(request, **extra):
    """
    Contexto completo de la pantalla de cobro (lo usan también las vistas
    de clientes que devuelven la pantalla después de una acción HTMX).
    """
    productos = Producto.objects.filter(activo=True).order_by("categoria", "nombre")
    ultima_venta = request.session.get("ultima_venta", None)
    items, total = services.detalle_carrito(request.session)
    contexto = {
        "productos": productos,
        "items": items,
        "total": total,
        "denominaciones": DENOMINACIONES,
        "ultima_venta": ultima_venta,
        "venta_reciente": ultima_venta,
    }
    contexto.update(extra)
    return contexto


@login_required
def pantalla_cobro(request):
    """
    Pantalla rápida del cajero: escáner + botones de productos + carrito
    + panel de cobro con vuelto.
    """
    if not _pantalla_habilitada(request):
        raise PermissionDenied(
            "No tenés permisos para acceder a esta sección del sistema."
        )

    productos = Producto.objects.filter(activo=True).order_by("categoria", "nombre")

    # Si quedó una venta recién cobrada, se muestra el comprobante con el
    # desglose del vuelto hasta que el cajero arranque la siguiente.
    ultima_venta = request.session.pop("ultima_venta", None)

    items, total = services.detalle_carrito(request.session)
    contexto = {
        "productos": productos,
        "items": items,
        "total": total,
        "denominaciones": DENOMINACIONES,
        "ultima_venta": ultima_venta,
        "venta_reciente": ultima_venta,
    }

    return render(request, "ventas/pantalla_cobro.html", contexto)


@require_POST
@login_required
def agregar_al_carrito(request):
    """Agrega 1 producto al carrito buscando por código de barras o por id."""
    if not _pantalla_habilitada(request):
        raise PermissionDenied("No tenés permisos para acceder a esta sección del sistema.")

    codigo = request.POST.get("codigo", "").strip()
    producto_id = request.POST.get("producto")
    cantidad = int(request.POST.get("cantidad", 1) or 1)

    producto = None
    if producto_id:
        try:
            producto = Producto.objects.get(pk=producto_id, activo=True)
        except (Producto.DoesNotExist, ValueError):
            producto = None
    elif codigo:
        try:
            producto = Producto.objects.get(codigo_barras=codigo, activo=True)
        except Producto.DoesNotExist:
            producto = None

    if producto is None:
        return _panel_cobro(
            request,
            _error_mensaje(
                f"No se encontró ningún producto activo con el código '{codigo or producto_id}'."
            ),
        )

    services.agregar_producto(request.session, producto, cantidad)
    return _panel_cobro(request)


@require_POST
@login_required
def actualizar_cantidad(request, producto_id):
    if not _pantalla_habilitada(request):
        raise PermissionDenied("No tenés permisos para acceder a esta sección del sistema.")

    try:
        cantidad = int(request.POST.get("cantidad", 1))
    except ValueError:
        cantidad = 1

    services.actualizar_cantidad(request.session, producto_id, cantidad)
    return _panel_cobro(request)


@require_POST
@login_required
def quitar_producto(request, producto_id):
    if not _pantalla_habilitada(request):
        raise PermissionDenied("No tenés permisos para acceder a esta sección del sistema.")

    services.quitar_producto(request.session, producto_id)
    return _panel_cobro(request)


@require_POST
@login_required
def vaciar_carrito(request):
    if not _pantalla_habilitada(request):
        raise PermissionDenied("No tenés permisos para acceder a esta sección del sistema.")

    services.vaciar_carrito(request.session)
    return _panel_cobro(request)


@require_POST
@login_required
def registrar_venta(request):
    """
    Cierra el cobro: valida el monto recibido contra el total, persiste la
    Venta + DetalleVenta en una transacción, limpia el carrito y muestra el
    comprobante con el vuelto desglosado en billetes.
    """
    if not _pantalla_habilitada(request):
        raise PermissionDenied("No tenés permisos para acceder a esta sección del sistema.")

    items, total = services.detalle_carrito(request.session)
    if not items:
        return _panel_cobro(request, _error_mensaje("El carrito está vacío. Agregá productos primero."))

    metodo = request.POST.get("metodo_pago", "EFECTIVO").upper()
    if metodo not in dict(Venta.METODO_PAGO_CHOICES):
        metodo = "EFECTIVO"

    try:
        monto_recibido = Decimal(request.POST.get("monto_recibido", "0") or "0")
    except (Decimal.InvalidOperation, ArithmeticError, ValueError):
        monto_recibido = Decimal("0")

    if metodo == "EFECTIVO":
        if monto_recibido < total:
            return _panel_cobro(
                request,
                _error_mensaje(
                    f"El efectivo recibido (${monto_recibido}) no alcanza para el total (${total})."
                ),
            )
        vuelto = monto_recibido - total
    else:
        # Para tarjeta/transferencia el "recibido" es exactamente el total.
        monto_recibido = total
        vuelto = Decimal("0.00")

    with transaction.atomic():
        venta = Venta.objects.create(
            cajero=request.user,
            total=total,
            metodo_pago=metodo,
            monto_recibido=monto_recibido,
            vuelto=vuelto,
        )
        DetalleVenta.objects.bulk_create(
            [
                DetalleVenta(
                    venta=venta,
                    producto=item["producto"],
                    cantidad=item["cantidad"],
                    precio_unitario=item["subtotal"] / item["cantidad"],
                )
                for item in items
            ]
        )

    piezas, centavos = desglosar_vuelto(vuelto)
    request.session["ultima_venta"] = {
        "id": venta.pk,
        "fecha": venta.fecha.strftime("%d/%m/%Y %H:%M"),
        "total": str(total),
        "metodo": venta.get_metodo_pago_display(),
        "monto_recibido": str(monto_recibido),
        "vuelto": str(vuelto),
        "vuelto_piezas": piezas,
        "vuelto_centavos": centavos,
        "detalle": [
            {
                "nombre": it["producto"].nombre,
                "icono": it["producto"].icono,
                "cantidad": it["cantidad"],
                "subtotal": str(it["subtotal"]),
            }
            for it in items
        ],
    }
    services.vaciar_carrito(request.session)

    return _panel_cobro(request, {"venta_reciente": request.session.get("ultima_venta")})
