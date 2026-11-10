"""Vistas públicas de la tienda online por negocio (`/t/<slug>/`).

Sin login. Un cliente de afuera ve el catálogo de un negocio específico,
agrega productos al carrito y confirma un pedido para retiro o envío.

Todas las vistas usan `request.negocio` (resuelto por NegocioMiddleware
desde el slug de la URL) para aislar los datos del negocio.
"""
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from clientes import services as fidelidad
from ventas.models import Categoria, Producto
from ventas.services import formatear_monto

from . import config, services
from .models import Pedido
from .services import ErrorPedido

COSTO_ENVIO_DOMICILIO = 1000  # $1000 fijo por envío a domicilio


def _contexto_catalogo_negocio(request, negocio, error=None, exito=None):
    """Contexto para la vitrina pública de un negocio."""
    productos = Producto.objects.filter(activo=True, negocio=negocio).select_related("categoria")

    # Filtrar por categoría si se especificó
    categoria_id = request.GET.get("categoria", "").strip()
    if categoria_id:
        productos = productos.filter(categoria_id=categoria_id)

    productos = productos.order_by("categoria__nombre", "nombre")

    categorias = (
        Categoria.objects.filter(productos__activo=True, productos__negocio=negocio)
        .distinct()
    )
    items = services.items_del_pedido(request)
    return {
        "productos": productos,
        "categorias": categorias,
        "categoria_actual": categoria_id,
        "items": items,
        "total": services.total_del_pedido(items),
        "error": error,
        "exito": exito,
        "negocio": negocio,
        "kiosco_nombre": negocio.nombre,
        "whatsapp_configurado": bool(negocio.whatsapp),
        "whatsapp_numero": negocio.whatsapp,
        "formatear_monto": formatear_monto,
    }


def catalogo_negocio(request, slug):
    """Vitrina pública de un negocio específico."""
    negocio = get_object_or_404(
        __import__("negocios.models", fromlist=["Negocio"]).Negocio,
        slug=slug,
        activo=True,
    )
    return render(
        request,
        "pedidos/catalogo_publico.html",
        _contexto_catalogo_negocio(request, negocio),
    )


def _responde_htmx(request, negocio, error=None, exito=None):
    contexto = _contexto_catalogo_negocio(request, negocio, error=error, exito=exito)
    template = (
        "pedidos/_carrito_pedido.html"
        if request.headers.get("HX-Request")
        else "pedidos/catalogo_publico.html"
    )
    return render(request, template, contexto)


def pedido_agregar_publico(request, slug):
    """Suma un producto al pedido que se está armando (HTMX)."""
    negocio = get_object_or_404(
        __import__("negocios.models", fromlist=["Negocio"]).Negocio,
        slug=slug,
        activo=True,
    )
    if request.method != "POST":
        return redirect("pedidos:catalogo_negocio", slug=slug)

    error = None
    try:
        producto_id = request.POST.get("producto_id")
        producto = get_object_or_404(
            Producto, pk=producto_id, activo=True, negocio=negocio
        )
        cantidad = int(request.POST.get("cantidad", 1))
        services.agregar_al_pedido(request, producto, cantidad)
    except (ValueError, ErrorPedido) as exc:
        error = str(exc)
    return _responde_htmx(request, negocio, error=error)


def pedido_quitar_publico(request, slug):
    """Saca una línea del pedido en curso (HTMX)."""
    negocio = get_object_or_404(
        __import__("negocios.models", fromlist=["Negocio"]).Negocio,
        slug=slug,
        activo=True,
    )
    if request.method != "POST":
        return redirect("pedidos:catalogo_negocio", slug=slug)
    try:
        services.quitar_del_pedido(request, int(request.POST.get("producto_id", "")))
    except (TypeError, ValueError):
        pass
    return _responde_htmx(request, negocio)


def pedido_carrito_publico(request, slug):
    """Muestra el carrito del pedido (partial o página completa)."""
    negocio = get_object_or_404(
        __import__("negocios.models", fromlist=["Negocio"]).Negocio,
        slug=slug,
        activo=True,
    )
    return _responde_htmx(request, negocio)


def pedido_confirmar_publico(request, slug):
    """Cierra el pedido: nombre, teléfono, tipo de entrega y costo de envío."""
    negocio = get_object_or_404(
        __import__("negocios.models", fromlist=["Negocio"]).Negocio,
        slug=slug,
        activo=True,
    )
    if request.method != "POST":
        return redirect("pedidos:catalogo_negocio", slug=slug)

    if request.POST.get("accion") == "vaciar":
        services.vaciar_pedido(request)
        messages.info(request, "Vaciamos tu pedido. Podés empezar de nuevo.")
        return redirect("pedidos:catalogo_negocio", slug=slug)

    tipo_entrega = request.POST.get("tipo_entrega", "retiro")
    costo_envio = COSTO_ENVIO_DOMICILIO if tipo_entrega == "domicilio" else 0

    try:
        pedido = services.crear_pedido(
            request,
            request.POST.get("nombre_cliente"),
            request.POST.get("telefono", ""),
            request.POST.get("comentario", ""),
            negocio=negocio,
            tipo_entrega=tipo_entrega,
            costo_envio=costo_envio,
        )
    except ErrorPedido as exc:
        return _responde_htmx(request, negocio, error=str(exc))

    return render(
        request,
        "pedidos/pedido_confirmado.html",
        {
            "pedido": pedido,
            "detalles": pedido.detalles.all(),
            "negocio": negocio,
            "mensaje_whatsapp": services.texto_para_whatsapp(pedido),
            "url_whatsapp": config.url_whatsapp(
                services.texto_para_whatsapp(pedido)
            ),
            "whatsapp_configurado": bool(negocio.whatsapp),
            "whatsapp_numero": negocio.whatsapp,
            "kiosco_nombre": negocio.nombre,
            "costo_envio": costo_envio,
            "tipo_entrega": tipo_entrega,
        },
    )
