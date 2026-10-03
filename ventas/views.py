from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from usuarios.decorators import rol_requerido

from .forms import ProductoForm
from .models import Categoria, Producto


# ========== PANTALLA DE COBRO ==========
@login_required
def pantalla_cobro(request):
    """
    Pantalla de cobro (POS). Hoy es la cáscara protegida por login: el flujo
    real de "escanear código → vuela al carrito", el vuelto rápido con
    billetes y el cierre de caja son del Sprint 3.
    """
    return render(request, "ventas/pantalla_cobro.html")


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
