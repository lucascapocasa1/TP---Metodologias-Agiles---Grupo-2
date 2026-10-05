from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from auditoria.utils import registrar_accion
from usuarios.decorators import es_administrador, rol_requerido

from . import services
from .forms import ProductoForm
from .models import Categoria, Producto, Venta
from .services import ErrorCobro


def _contexto_cobro(request, error=None):
    """Items, total y métodos de pago para la pantalla (y sus parciales)."""
    items = services.items_del_carrito(request)
    return {
        "items": items,
        "total": services.total_del_carrito(items),
        "metodos_pago": Venta.METODO_PAGO,
        "error": error,
    }


# ========== PANTALLA DE COBRO (Sprint 3: HU-07/08/09) ==========
@login_required
def pantalla_cobro(request):
    """
    POS del cajero: escanear/tipear código (HU-07), editar el carrito
    (HU-08) y cobrar en efectivo o tarjeta con vuelto (HU-09).
    Con `?venta=<id>` muestra el comprobante de una venta ya confirmada.
    """
    contexto = _contexto_cobro(request)

    venta_id = request.GET.get("venta")
    if venta_id:
        venta = get_object_or_404(Venta, pk=venta_id, finalizada=True)
        if venta.usuario_id != request.user.pk and not es_administrador(
            request.user
        ):
            raise PermissionDenied("Solo podés ver tus propias ventas.")
        contexto["venta"] = venta
        contexto["detalles"] = venta.detalles.select_related("producto")

    return render(request, "ventas/pantalla_cobro.html", contexto)


@login_required
def cobro_agregar(request):
    """HU-07: agrega un producto al carrito por código de barras o nombre."""
    if request.method != "POST":
        return redirect("ventas:pantalla_cobro")

    error = None
    try:
        producto = services.buscar_producto(request.POST.get("codigo"))
        services.agregar_al_carrito(request, producto)
    except ErrorCobro as exc:
        error = str(exc)

    contexto = _contexto_cobro(request, error=error)
    if request.headers.get("HX-Request"):
        return render(request, "ventas/_carrito.html", contexto)
    return render(request, "ventas/pantalla_cobro.html", contexto)


@login_required
def cobro_buscar(request):
    """
    Búsqueda en tiempo real del escáner (HTMX): arranca con 3 caracteres y
    devuelve las coincidencias de nombre o código de barras como partial.
    """
    consulta = request.GET.get("codigo", "").strip()
    coincidencias = []

    if len(consulta) >= 3:
        coincidencias = (
            Producto.objects.filter(activo=True)
            .filter(Q(nombre__icontains=consulta) | Q(codigo_barras__icontains=consulta))
            .select_related("categoria")
            .order_by("nombre")[:8]
        )

    return render(
        request,
        "ventas/_cobro_resultados.html",
        {"consulta": consulta, "coincidencias": coincidencias},
    )


@login_required
def cobro_cantidad(request):
    """HU-08: suma, resta o quita un ítem del carrito."""
    if request.method != "POST":
        return redirect("ventas:pantalla_cobro")

    error = None
    try:
        producto_id = int(request.POST.get("producto_id", ""))
        accion = request.POST.get("accion", "")
        if accion not in ("sumar", "restar", "quitar"):
            raise ErrorCobro("Acción no válida sobre el carrito.")
        services.modificar_cantidad(request, producto_id, accion)
    except (ValueError, ErrorCobro) as exc:
        error = str(exc)

    contexto = _contexto_cobro(request, error=error)
    if request.headers.get("HX-Request"):
        return render(request, "ventas/_carrito.html", contexto)
    return render(request, "ventas/pantalla_cobro.html", contexto)


@login_required
def cobro_confirmar(request):
    """HU-09: confirma la venta, descuenta stock y muestra el comprobante."""
    if request.method != "POST":
        return redirect("ventas:pantalla_cobro")

    try:
        venta = services.confirmar_venta(
            request,
            metodo_pago=request.POST.get("metodo_pago", ""),
            monto_entregado=request.POST.get("monto_entregado"),
        )
    except ErrorCobro as exc:
        return render(
            request,
            "ventas/pantalla_cobro.html",
            _contexto_cobro(request, error=str(exc)),
        )

    registrar_accion(
        request.user,
        "Venta confirmada",
        f"Venta N° {venta.pk} por {services.formatear_monto(venta.total)} "
        f"({venta.get_metodo_pago_display()})",
        request,
    )
    messages.success(
        request,
        f"Venta N° {venta.pk} confirmada. "
        f"Total: {services.formatear_monto(venta.total)}.",
    )
    return redirect(f"{reverse('ventas:pantalla_cobro')}?venta={venta.pk}")


# ========== LISTA DE PRODUCTOS (HU-05: búsqueda en tiempo real con HTMX) ==========
@rol_requerido("Administrador")
def lista_productos(request):
    """
    Catálogo de productos con búsqueda por nombre, descripción o código de
    barras. Con HTMX devuelve solo el partial de la tabla; sin HTMX devuelve
    la página completa.
    """
    busqueda = request.GET.get("buscar", "").strip()
    productos = Producto.objects.select_related("categoria").order_by("nombre")

    if busqueda:
        productos = productos.filter(
            Q(nombre__icontains=busqueda)
            | Q(descripcion__icontains=busqueda)
            | Q(codigo_barras__icontains=busqueda)
        )

    contexto = {"productos": productos, "busqueda": busqueda}

    if request.headers.get("HX-Request"):
        return render(request, "ventas/_productos_tabla.html", contexto)
    return render(request, "ventas/lista_productos.html", contexto)


# ========== ALTA DE PRODUCTOS (HU-04) ==========
@rol_requerido("Administrador")
def agregar_producto(request):
    if request.method == "POST":
        form = _producto_form_desde_post(request)
        if form.is_valid():
            producto = form.save()
            messages.success(
                request, f"Producto «{producto.nombre}» dado de alta correctamente."
            )
            return redirect("ventas:lista_productos")
    else:
        form = ProductoForm()

    return render(
        request,
        "ventas/agregar_producto.html",
        {"form": form, "categorias": Categoria.objects.all()},
    )


# ========== EDICIÓN DE PRODUCTOS (HU-04: modificaciones) ==========
@rol_requerido("Administrador")
def editar_producto(request, producto_id):
    producto = get_object_or_404(Producto, pk=producto_id)

    if request.method == "POST":
        form = _producto_form_desde_post(request, instance=producto, producto=producto)
        if form.is_valid():
            form.save()
            messages.success(
                request, f"Producto «{producto.nombre}» actualizado correctamente."
            )
            return redirect("ventas:lista_productos")
    else:
        form = ProductoForm(instance=producto, producto=producto)

    return render(
        request,
        "ventas/editar_producto.html",
        {"form": form, "producto": producto},
    )


# ========== BAJA DE PRODUCTOS (HU-04: bajas, lógicas para no romper ventas) ==========
@rol_requerido("Administrador")
def eliminar_producto(request, producto_id):
    producto = get_object_or_404(Producto, pk=producto_id)

    if request.method == "POST":
        producto.activo = False
        producto.save(update_fields=["activo"])
        messages.success(
            request, f"Producto «{producto.nombre}» dado de baja (quedó inactivo)."
        )
        return redirect("ventas:lista_productos")

    return render(request, "ventas/eliminar_producto.html", {"producto": producto})


def _producto_form_desde_post(request, instance=None, producto=None):
    """
    Arma el form desde el POST. Si mandaron "categoría nueva", la crea (o la
    reusa si ya existe) y le asigna el id al dato antes de validar.
    En el alta no se muestra el checkbox de "activo": nace activo siempre.
    """
    datos = request.POST.copy()
    nueva_categoria = datos.get("nueva_categoria", "").strip()
    if nueva_categoria:
        categoria, _ = Categoria.objects.get_or_create(nombre=nueva_categoria)
        datos["categoria"] = str(categoria.pk)
    if instance is None and not datos.get("activo"):
        datos["activo"] = "True"
    return ProductoForm(datos, instance=instance, producto=producto)
