
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from decimal import Decimal
from auditoria.utils import registrar_accion
from usuarios.decorators import es_administrador, rol_requerido
from . import services
from .forms import ProductoForm
from .models import Categoria, Producto, Venta, DetalleVenta
from .services import ErrorCobro
 # === FUNCIÓN AUXILIAR DEL FORMULARIO ===
def _producto_form_desde_post(request, instance=None, producto=None):
     """Arma el formulario desde el POST. Si mandaron categoría nueva, la crea."""
     datos = request.POST.copy()
     
     nueva_categoria = datos.get("nueva_categoria", "").strip()
     if nueva_categoria:
         categoria, _ = Categoria.objects.get_or_create(nombre=nueva_categoria)
         datos["categoria"] = str(categoria.pk)
     
     if instance is None and not datos.get("activo"):
         datos["activo"] = "True"
     
     return ProductoForm(datos, instance=instance, producto=producto)
 # === CONTEXTO DE COBRO ===
def _contexto_cobro(request, error=None):
     """Items, total y métodos de pago para la pantalla."""
     items = services.items_del_carrito(request)
     return {
         "items": items,
         "total": services.total_del_carrito(items),
         "metodos_pago": Venta.METODO_PAGO,
         "error": error,
     }
 # === PANTALLA PRINCIPAL DE COBRO ===
@login_required
def pantalla_cobro(request):
     contexto = _contexto_cobro(request)
     
     venta_id = request.GET.get("venta")
     if venta_id:
         venta = get_object_or_404(Venta, pk=venta_id, finalizada=True)
         if venta.usuario_id != request.user.pk and not es_administrador(request.user):
             raise PermissionDenied("Solo podés ver tus propias ventas.")
     
     return render(request, "ventas/pantalla_cobro.html", contexto)
 # === AGREGAR PRODUCTO AL CARRITO ===
@login_required
def cobro_agregar(request):
     if request.method != "POST":
         return redirect("ventas:pantalla_cobro")
     error = None
     try:
         producto = services.buscar_producto(request.POST)
         services.agregar_al_carrito(request, producto)
     except ErrorCobro as exc:
         error = str(exc)
     contexto = _contexto_cobro(request, error=error)
     if request.headers.get("HX-Request"):
         return render(request, "ventas/_carrito.html", contexto)
     return render(request, "ventas/pantalla_cobro.html", contexto)
 # === BÚSQUEDA EN TIEMPO REAL ===
@login_required
def cobro_buscar(request):
     consulta = request.GET.get("codigo", "").strip()
     coincidencias = []
     if len(consulta) >= 3:
         coincidencias = (
             Producto.objects.filter(activo=True)
             .filter(
                 Q(nombre__icontains=consulta) |
                 Q(codigo_barras__icontains=consulta)
             )
             .select_related("categoria")
             .order_by("nombre")[:8]
         )
     return render(
         request,
         "ventas/_cobro_resultados.html",
         {"consulta": consulta, "coincidencias": coincidencias},
     )
 # === MODIFICAR CANTIDAD ===
@login_required
def cobro_cantidad(request):
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
 # === CONFIRMAR VENTA ===
@login_required
def cobro_confirmar(request):
     if request.method != "POST":
         return redirect("ventas:pantalla_cobro")
     try:
         venta = services.confirmar_venta(
             request,
             metodo_pago=request.POST.get("metodo_pago", ""),
             monto_entregado=request.POST.get("monto_entregado", ""),
         )
         
         registrar_accion(
             request,
             "Venta confirmada",
             f"Venta N° {venta.pk} por {services.formatear_monto(venta.total)} "
             f"({venta.get_metodo_pago_display()})",
         )
         
         messages.success(
             request,
             f"Venta N° {venta.pk} confirmada. "
             f"Total: {services.formatear_monto(venta.total)}.",
         )
         
         return redirect(f"{reverse('ventas:pantalla_cobro')}?venta={venta.pk}")
         
     except ErrorCobro as exc:
         return render(
             request,
             "ventas/pantalla_cobro.html",
             _contexto_cobro(request, error=str(exc)),
         )
 # === LISTA DE PRODUCTOS ===
@rol_requerido("Administrador")
def lista_productos(request):
     busqueda = request.GET.get("buscar", "").strip()
     productos = Producto.objects.select_related("categoria").order_by("nombre")
     
     if busqueda:
         productos = productos.filter(
             Q(nombre__icontains=busqueda) |
             Q(descripcion__icontains=busqueda) |
             Q(codigo_barras__icontains=busqueda)
         )
     
     contexto = {"productos": productos, "busqueda": busqueda}
     
     if request.headers.get("HX-Request"):
         return render(request, "ventas/productos_tabla.html", contexto)
     return render(request, "ventas/lista_productos.html", contexto)
 # === AGREGAR PRODUCTO ===
@rol_requerido("Administrador")
def agregar_producto(request):
     if request.method == "POST":
         form = _producto_form_desde_post(request)
         if form.is_valid():
             producto = form.save()
             registrar_accion(request, f"Creó producto: {producto.nombre}")
             messages.success(request, f"Producto «{producto.nombre}» dado de alta correctamente.")
             return redirect("ventas:lista_productos")
     else:
         form = ProductoForm()
     
     return render(request, "ventas/agregar_producto.html", {
         "form": form,
         "categorias": Categoria.objects.all()
     })
 # === EDITAR PRODUCTO ===
@rol_requerido("Administrador")
def editar_producto(request, producto_id):
     producto = get_object_or_404(Producto, pk=producto_id)
     
     if request.method == "POST":
         form = _producto_form_desde_post(request, instance=producto, producto=producto)
         if form.is_valid():
             form.save()
             messages.success(request, f"Producto «{producto.nombre}» actualizado correctamente.")
             return redirect("ventas:lista_productos")
     else:
         form = ProductoForm(instance=producto, producto=producto)
     
     return render(request, "ventas/editar_producto.html", {
         "form": form,
         "producto": producto
     })
 # === ELIMINAR PRODUCTO (baja lógica) ===
@rol_requerido("Administrador")
def eliminar_producto(request, producto_id):
     producto = get_object_or_404(Producto, pk=producto_id)
     
     if request.method == "POST":
         producto.activo = False
         producto.save(update_fields=["activo"])
         messages.success(request, f"Producto «{producto.nombre}» dado de baja (quedó inactivo).")
         return redirect("ventas:lista_productos")
     
     return render(request, "ventas/eliminar_producto.html", {"producto": producto})
