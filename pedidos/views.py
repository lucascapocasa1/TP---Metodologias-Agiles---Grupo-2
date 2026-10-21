"""Vistas de la integración externa (HU-13) y del panel de pedidos.

Dos zonas bien separadas:

* **Público** (`catalogo`, `pedido_*`): sin login. Un cliente de afuera arma
  su pedido para retirar por el local. Nunca se muestra la cantidad exacta de
  stock: solo "Disponible" / "Agotado".
* **Interno** (`lista_pedidos`, `detalle_pedido`): solo Administrador. El
  kiosquero ve los pedidos recibidos y los marca como entregados/cancelados.
"""
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from auditoria.utils import registrar_accion
from clientes import services as fidelidad
from clientes.models import Cliente
from usuarios.decorators import rol_requerido
from ventas.models import Categoria, Producto, Venta
from ventas.services import formatear_monto

from . import config, services
from .models import Pedido
from .services import ErrorPedido


# ========== CATÁLOGO PÚBLICO (sin login) ==========


def _contexto_catalogo(request, error=None, exito=None):
    productos = (
        Producto.objects.filter(activo=True)
        .select_related("categoria")
        .order_by("categoria__nombre", "nombre")
    )
    categorias = Categoria.objects.filter(productos__activo=True).distinct()
    items = services.items_del_pedido(request)
    return {
        "productos": productos,
        "categorias": categorias,
        "categoria_actual": request.GET.get("categoria", ""),
        "items": items,
        "total": services.total_del_pedido(items),
        "error": error,
        "exito": exito,
        "kiosco_nombre": config.NOMBRE_KIOSCO,
        "whatsapp_configurado": config.whatsapp_configurado(),
    }


def catalogo(request):
    """Vitrina pública: cualquier persona ve precios y disponibilidad."""
    return render(request, "pedidos/catalogo.html", _contexto_catalogo(request))


def _responde_htmx(request, error=None, exito=None):
    contexto = _contexto_catalogo(request, error=error, exito=exito)
    template = (
        "pedidos/_carrito_pedido.html"
        if request.headers.get("HX-Request")
        else "pedidos/catalogo.html"
    )
    return render(request, template, contexto)


def pedido_agregar(request):
    """Suma un producto al pedido que se está armando (HTMX)."""
    if request.method != "POST":
        return redirect("pedidos:catalogo")

    error = None
    try:
        producto = services.buscar_producto_publico(
            request.POST.get("producto_id")
        )
        if producto is None or producto.stock <= 0:
            raise ErrorPedido("Ese producto no está disponible ahora.")
        services.agregar_al_pedido(
            request, producto, request.POST.get("cantidad", 1)
        )
    except ErrorPedido as exc:
        error = str(exc)
    return _responde_htmx(request, error=error)


def pedido_quitar(request):
    """Saca una línea del pedido en curso (HTMX)."""
    if request.method != "POST":
        return redirect("pedidos:catalogo")
    try:
        services.quitar_del_pedido(request, int(request.POST.get("producto_id", "")))
    except (TypeError, ValueError):
        pass
    return _responde_htmx(request)


def pedido_confirmar(request):
    """Cierra el pedido de la sesión y muestra el paso a WhatsApp."""
    if request.method != "POST":
        return redirect("pedidos:catalogo")

    if request.POST.get("accion") == "vaciar":
        services.vaciar_pedido(request)
        messages.info(request, "Vaciamos tu pedido. Podés empezar de nuevo.")
        return redirect("pedidos:catalogo")

    try:
        pedido = services.crear_pedido(
            request,
            request.POST.get("nombre_cliente"),
            request.POST.get("telefono", ""),
            request.POST.get("comentario", ""),
        )
    except ErrorPedido as exc:
        return _responde_htmx(request, error=str(exc))

    return render(
        request,
        "pedidos/pedido_confirmado.html",
        {
            "pedido": pedido,
            "detalles": pedido.detalles.all(),
            "mensaje_whatsapp": services.texto_para_whatsapp(pedido),
            "url_whatsapp": config.url_whatsapp(
                services.texto_para_whatsapp(pedido)
            ),
            "whatsapp_configurado": config.whatsapp_configurado(),
            "kiosco_nombre": config.NOMBRE_KIOSCO,
        },
    )


# ========== PANEL DE PEDIDOS (solo Administrador) ==========


@rol_requerido("Administrador")
def lista_pedidos(request):
    """Los pedidos recibidos desde el catálogo público, con filtro por estado."""
    estado = request.GET.get("estado", "")
    busqueda = request.GET.get("buscar", "").strip()

    pedidos = Pedido.objects.prefetch_related("detalles")
    if estado in dict(Pedido.ESTADOS):
        pedidos = pedidos.filter(estado=estado)
    if busqueda:
        pedidos = pedidos.filter(
            Q(nombre_cliente__icontains=busqueda)
            | Q(telefono__icontains=busqueda)
        )

    pendientes = Pedido.objects.filter(estado="pendiente").count()
    contexto = {
        "pedidos": pedidos,
        "estado_actual": estado,
        "busqueda": busqueda,
        "estados": Pedido.ESTADOS,
        "pendientes": pendientes,
    }
    if request.headers.get("HX-Request"):
        return render(request, "pedidos/_pedidos_tabla.html", contexto)
    return render(request, "pedidos/lista_pedidos.html", contexto)


@rol_requerido("Administrador")
def detalle_pedido(request, pedido_id):
    pedido = get_object_or_404(
        Pedido.objects.prefetch_related("detalles"), pk=pedido_id
    )
    return render(
        request,
        "pedidos/detalle_pedido.html",
        {
            "pedido": pedido,
            "detalles": pedido.detalles.all(),
            "metodos_pago": Venta.METODO_PAGO,
        },
    )


@rol_requerido("Administrador")
def buscar_cliente_pedido(request):
    """Busca clientes para asociar al pedido (HTMX).

    Usa la misma búsqueda del POS (DNI, nombre o apellido): el kiosquero
    no tiene que aprender dos criterios distintos para encontrar a un cliente.
    """
    consulta = request.GET.get("q", "").strip()
    coincidencias = fidelidad.buscar_clientes(consulta)
    return render(
        request,
        "pedidos/_resultados_cliente.html",
        {"consulta": consulta, "coincidencias": coincidencias},
    )


@rol_requerido("Administrador")
def entregar_pedido(request, pedido_id):
    """Entrega el pedido cobrando lo que el cliente pidió (HU-13 → HU-09).

    El cliente pidió por WhatsApp y ahora está en el mostrador: se le cobra
    lo que pidió, con el precio congelado del pedido. La venta que se genera
    descuenta el stock y suma los puntos (o la deuda, si es cuenta corriente)
    con las mismas reglas del POS.
    """
    if request.method != "POST":
        raise PermissionDenied("Esta acción se hace con POST.")

    pedido = get_object_or_404(Pedido, pk=pedido_id)

    cliente = None
    cliente_id = (request.POST.get("cliente_id") or "").strip()
    if cliente_id:
        cliente = Cliente.objects.filter(pk=cliente_id, activo=True).first()
        if cliente is None:
            messages.error(
                request, "El cliente no existe o está dado de baja."
            )
            return redirect("pedidos:detalle_pedido", pedido_id=pedido.pk)

    try:
        venta = services.registrar_entrega(
            pedido,
            cliente,
            metodo_pago=request.POST.get("metodo_pago", ""),
            usuario=request.user,
            monto_entregado=request.POST.get("monto_entregado"),
        )
    except ErrorPedido as exc:
        messages.error(request, str(exc))
        return redirect("pedidos:detalle_pedido", pedido_id=pedido.pk)

    detalle = (
        f"Venta N° {venta.pk} por {formatear_monto(venta.total)} "
        f"({venta.get_metodo_pago_display()})"
    )
    if cliente is not None:
        detalle += (
            f" · Cliente: {cliente.nombre_completo} "
            f"(+{venta.puntos_ganados} pts)"
        )
    registrar_accion(
        request.user,
        f"Pedido #{pedido.pk} entregado",
        detalle=detalle,
        request=request,
    )
    messages.success(
        request,
        f"Pedido #{pedido.pk} entregado. Venta N° {venta.pk} por "
        f"{formatear_monto(venta.total)}.",
    )
    return redirect("pedidos:detalle_pedido", pedido_id=pedido.pk)


@rol_requerido("Administrador")
def cambiar_estado_pedido(request, pedido_id, estado):
    """Cancela el pedido (POST).

    "Entregado" no se marca a mano: para entregar hay que cobrar, y eso lo
    hace `entregar_pedido` (que genera la venta y descuenta el stock).
    """
    if request.method != "POST":
        raise PermissionDenied("Esta acción se hace con POST.")

    pedido = get_object_or_404(Pedido, pk=pedido_id)
    estados_validos = dict(Pedido.ESTADOS)
    if estado not in estados_validos:
        messages.error(request, "Estado de pedido no válido.")
        return redirect("pedidos:detalle_pedido", pedido_id=pedido.pk)

    if estado == "entregado":
        messages.error(
            request,
            "Para entregar un pedido hay que cobrarlo: usá «Entregar y cobrar».",
        )
        return redirect("pedidos:detalle_pedido", pedido_id=pedido.pk)

    anterior = pedido.get_estado_display()
    pedido.estado = estado
    pedido.save(update_fields=["estado"])

    registrar_accion(
        request.user,
        f"Pedido #{pedido.pk}: {estados_validos[estado]}",
        detalle=(
            f"{pedido.nombre_cliente} · {pedido.cantidad_items} ítem(s) · "
            f"estado anterior: {anterior}"
        ),
        request=request,
    )
    messages.success(
        request, f"Pedido #{pedido.pk} marcado como {estados_validos[estado]}."
    )
    return redirect("pedidos:detalle_pedido", pedido_id=pedido.pk)
