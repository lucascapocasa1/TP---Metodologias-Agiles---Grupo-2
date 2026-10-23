from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from auditoria.utils import registrar_accion
from clientes import services as fidelidad
from usuarios.decorators import es_administrador, rol_requerido

from . import cobro_qr, mercadopago, services
from .forms import ProductoForm
from .models import Categoria, Producto, Turno, Venta
from .services import ErrorCobro


def _url_display(request):
    from .views_qr import url_para_celular

    return url_para_celular(request, reverse("ventas:display"))


def contexto_cobro(request, error=None, form_rapido=None):
    """Items, total, métodos de pago y cliente (HU-12/HU-14) para la pantalla."""
    items = services.items_del_carrito(request)
    cliente = fidelidad.cliente_de_sesion(request)
    total = services.total_del_carrito(items)
    return {
        "items": items,
        "total": total,
        "metodos_pago": Venta.METODO_PAGO,
        "cliente": cliente,
        "puntos_venta": fidelidad.puntos_por_monto(total),
        "puntos_regla": fidelidad.PUNTOS_POR_PESO,
        "form_rapido": form_rapido,
        "error": error,
        # HU-14: para decidir si se puede ofrecer "cuenta corriente".
        "puede_fiar": bool(cliente and cliente.puede_fiar(total)),
        # Cobro con QR de Mercado Pago en curso (muestra la ventana del QR).
        "pago_qr": cobro_qr.pago_pendiente(request.user),
        "mp_configurado": mercadopago.esta_configurado(),
        "url_display": _url_display(request),
    }


# ========== PANTALLA DE COBRO (Sprint 3: HU-07/08/09) ==========
@login_required
def pantalla_cobro(request):
    """
    POS del cajero: escanear/tipear código (HU-07), editar el carrito
    (HU-08) y cobrar en efectivo o tarjeta con vuelto (HU-09).
    Con `?venta=<id>` muestra el comprobante de una venta ya confirmada.
    """
    contexto = contexto_cobro(request)

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

    contexto = contexto_cobro(request, error=error)
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
        {
            "consulta": consulta,
            "coincidencias": coincidencias,
            "puede_dar_alta": es_administrador(request.user),
        },
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

    contexto = contexto_cobro(request, error=error)
    if request.headers.get("HX-Request"):
        return render(request, "ventas/_carrito.html", contexto)
    return render(request, "ventas/pantalla_cobro.html", contexto)


@login_required
def cobro_confirmar(request):
    """HU-09: confirma la venta, descuenta stock y muestra el comprobante."""
    if request.method != "POST":
        return redirect("ventas:pantalla_cobro")

    if request.POST.get("metodo_pago") == services.METODO_QR:
        # Mercado Pago: la venta queda pendiente hasta que el cliente paga.
        from .views_qr import iniciar_cobro_qr

        return iniciar_cobro_qr(request)

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
            contexto_cobro(request, error=str(exc)),
        )

    detalle = (
        f"Venta N° {venta.pk} por {services.formatear_monto(venta.total)} "
        f"({venta.get_metodo_pago_display()})"
    )
    if venta.cliente_id:
        detalle += (
            f" · Cliente: {venta.cliente.nombre_completo} "
            f"(+{venta.puntos_ganados} pts)"
        )
    registrar_accion(
        request.user,
        "Venta confirmada",
        detalle,
        request,
    )
    mensaje = (
        f"Venta N° {venta.pk} confirmada. "
        f"Total: {services.formatear_monto(venta.total)}."
    )
    if venta.cliente_id:
        mensaje += (
            f" {venta.cliente.nombre_completo} sumó "
            f"{venta.puntos_ganados} puntos."
        )
    messages.success(request, mensaje)
    return redirect(f"{reverse('ventas:pantalla_cobro')}?venta={venta.pk}")


# ========== CIERRE DE TURNO (Sprint 4: HU-10) ==========
@rol_requerido("Cajero", "Administrador")
def cierre_turno(request):
    """
    HU-10: abrir turno, ver los totales en vivo (efectivo, tarjeta y
    cantidad de operaciones) y cerrarlo para contar la caja.
    Con `?turno=<id>` muestra el resumen de ese turno (el recién cerrado
    o cualquiera histórico, con control de responsable).
    """
    if request.method == "POST":
        accion = request.POST.get("accion", "")
        turno = services.turno_abierto(request.user)

        if accion == "abrir" and turno is None:
            services.abrir_turno(request.user)
            messages.success(request, "Turno abierto. ¡Buen trabajo!")
            return redirect("ventas:cierre_turno")

        if accion == "cerrar" and turno is not None:
            try:
                turno = services.cerrar_turno(turno)
            except ErrorCobro as exc:
                messages.error(request, str(exc))
                return redirect("ventas:cierre_turno")

            registrar_accion(
                request.user,
                "Cierre de turno",
                f"Efectivo {services.formatear_monto(turno.total_efectivo)} · "
                f"Tarjeta {services.formatear_monto(turno.total_tarjeta)} · "
                f"Fiado (cuenta corriente) "
                f"{services.formatear_monto(turno.deuda_otorgada)} · "
                f"{turno.cantidad_operaciones} operaciones",
                request,
            )
            messages.success(
                request, "Turno cerrado. Contá la caja antes de retirarte."
            )
            return redirect(f"{reverse('ventas:cierre_turno')}?turno={turno.pk}")

        messages.error(request, "La acción no coincide con el estado del turno.")
        return redirect("ventas:cierre_turno")

    # GET: ?turno=<id> para un turno puntual, si no el turno abierto propio.
    turno = services.turno_abierto(request.user)
    turno_id = request.GET.get("turno")
    if turno_id:
        turno = get_object_or_404(Turno, pk=turno_id)
        if turno.usuario_id != request.user.pk and not es_administrador(
            request.user
        ):
            raise PermissionDenied("Solo podés ver el turno a tu nombre.")

    contexto = {
        "turno": turno,
        "totales": services.totales_del_turno(turno) if turno else None,
        "puede_cerrar": bool(
            turno
            and turno.activo
            and (
                turno.usuario_id == request.user.pk
                or es_administrador(request.user)
            )
        ),
    }
    return render(request, "ventas/cierre_turno.html", contexto)


# Columnas del catálogo que se pueden ordenar desde el encabezado. El nombre
# del parámetro GET es el de la columna; el valor real es el campo del modelo
# (categoría es FK, hay que ordenar por el nombre anidado).
CAMPOS_ORDEN = {
    "producto": "nombre",
    "codigo": "codigo_barras",
    "categoria": "categoria__nombre",
    "precio": "precio",
    "costo": "costo",
    "stock": "stock",
}


# ========== LISTA DE PRODUCTOS (HU-05: búsqueda en tiempo real con HTMX) ==========
@rol_requerido("Administrador")
def lista_productos(request):
    """
    Catálogo de productos con búsqueda por nombre, descripción o código de
    barras (HU-05) y ordenamiento por columna asc/desc. Con HTMX devuelve
    solo el partial de la tabla; sin HTMX devuelve la página completa.
    """
    busqueda = request.GET.get("buscar", "").strip()

    # Orden: solo se aceptan columnas conocidas y direcciones válidas, para
    # no terminar ordenando por cualquier campo del modelo.
    orden = request.GET.get("orden", "producto")
    if orden not in CAMPOS_ORDEN:
        orden = "producto"
    direccion = request.GET.get("direccion", "asc")
    prefijo = "-" if direccion == "desc" else ""

    productos = Producto.objects.select_related("categoria").order_by(
        prefijo + CAMPOS_ORDEN[orden]
    )

    if busqueda:
        productos = productos.filter(
            Q(nombre__icontains=busqueda)
            | Q(descripcion__icontains=busqueda)
            | Q(codigo_barras__icontains=busqueda)
        )

    contexto = {
        "productos": productos,
        "busqueda": busqueda,
        "orden": orden,
        "direccion": direccion,
    }

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
        # Registro con lector: se puede llegar con ?codigo=<lo escaneado>
        # desde el catálogo o el cobro para precargar el campo.
        form = ProductoForm(
            initial={"codigo_barras": request.GET.get("codigo", "").strip()}
        )

    return render(
        request,
        "ventas/agregar_producto.html",
        {"form": form, "categorias": Categoria.objects.all()},
    )


@rol_requerido("Administrador")
def buscar_por_codigo(request):
    """Lectura para el alta: dado un código escaneado, dice si ya existe.

    GET ?codigo=<lectura>&excluir=<id opcional> → JSON. El lector manda el
    código con Enter; el JS del form lo consulta para avisar en el momento
    si el código ya está registrado (y linkear a editar) o está libre.
    `excluir` se usa en la edición para no marcar el propio producto.
    """
    codigo = request.GET.get("codigo", "").strip()
    if not codigo:
        return JsonResponse({"codigo": "", "existe": False})
    excluidos = {}
    excluir = request.GET.get("excluir", "").strip()
    if excluir.isdigit():
        excluidos = {"pk": int(excluir)}
    producto = (
        Producto.objects.filter(codigo_barras=codigo)
        .exclude(**excluidos)
        .select_related("categoria")
        .first()
    )
    if producto is None:
        return JsonResponse({"codigo": codigo, "existe": False})
    return JsonResponse(
        {
            "codigo": codigo,
            "existe": True,
            "producto_id": producto.pk,
            "nombre": producto.nombre,
            "activo": producto.activo,
            "url_editar": reverse(
                "ventas:editar_producto", args=[producto.pk]
            ),
        }
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
