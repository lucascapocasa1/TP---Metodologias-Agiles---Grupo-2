from datetime import datetime
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.models import Group, User
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import (
    DecimalField,
    F,
    IntegerField,
    Prefetch,
    Sum,
    Value,
)
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from auditoria.utils import registrar_accion
from usuarios.decorators import rol_requerido
from ventas.models import DetalleVenta, Producto
from negocios.models import Negocio, Documento

from . import reportes
from .exports import exportar_stock_a_excel
from .forms import AsignarRolForm, UsuarioForm


@rol_requerido("Administrador")
def reportes_ventas(request):
    """
    Reporte de ventas con filtro por rango de fechas.

    Por defecto mira los últimos 14 días. El checkbox "solo finalizadas"
    sirve porque `Venta.finalizada` todavía no lo usa el flujo de cobro
    (viene del Sprint 3): sin él, el reporte contaría carritos a medio armar.
    """
    f_desde, f_hasta, desde_dt, hasta_dt = reportes.resolver_rango(
        request.GET.get("desde"), request.GET.get("hasta")
    )
    solo_finalizadas = request.GET.get("finalizadas") == "1"
    # La tarjeta de rentables se puede mirar por total del período o por
    # unidad vendida; el toggle solo cambia el orden y los montos mostrados.
    modo_rentables = "unidad" if request.GET.get("modo") == "unidad" else "total"

    resumen = reportes.resumen_ventas(
        desde_dt, hasta_dt, solo_finalizadas, negocio=request.negocio
    )
    serie = reportes.ventas_por_dia(
        desde_dt, hasta_dt, solo_finalizadas, negocio=request.negocio
    )
    top = reportes.top_productos(
        desde_dt, hasta_dt, solo_finalizadas=solo_finalizadas, negocio=request.negocio
    )
    rentables = reportes.productos_mas_rentables(
        desde_dt,
        hasta_dt,
        solo_finalizadas=solo_finalizadas,
        negocio=request.negocio,
        por_unidad=modo_rentables == "unidad",
    )
    # HU-14: lo fiado va aparte de los ingresos (no es plata que entró).
    fiado = reportes.deuda_otorgada(
        desde_dt, hasta_dt, solo_finalizadas, negocio=request.negocio
    )

    ventas_qs = (
        reportes.ventas_del_rango(
            desde_dt, hasta_dt, solo_finalizadas, negocio=request.negocio
        )
        .annotate(
            unidades=Coalesce(
                Sum("detalles__cantidad"),
                Value(0),
                output_field=IntegerField(),
            ),
            costo=Coalesce(
                Sum(
                    F("detalles__cantidad")
                    * Coalesce(F("detalles__costo_unitario"), F("detalles__producto__costo"))
                ),
                Value(Decimal("0.00")),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            ),
        )
        .annotate(ganancia=F("total") - F("costo"))
        .prefetch_related(
            Prefetch("detalles", queryset=DetalleVenta.objects.select_related("producto"))
        )
        .order_by("-fecha")
    )

    # Paginación de ventas
    paginator = Paginator(ventas_qs, 10)  # 10 ventas por página
    pagina = request.GET.get("page")
    try:
        ventas = paginator.page(pagina)
    except PageNotAnInteger:
        ventas = paginator.page(1)
    except EmptyPage:
        ventas = paginator.page(paginator.num_pages)

    # Las barras son CSS puro, así que el template necesita el techo de cada
    # serie para escalarlas con widthratio.
    max_ingresos = max((fila["ingresos"] for fila in serie), default=0)
    max_ganancia = max((fila["ganancia"] for fila in serie), default=0)

    context = {
        "desde": f_desde,
        "hasta": f_hasta,
        "solo_finalizadas": solo_finalizadas,
        "resumen": resumen,
        "serie": serie,
        "max_ingresos": max_ingresos,
        "max_ganancia": max_ganancia,
        "top": top,
        "rentables": rentables,
        "modo_rentables": modo_rentables,
        "deuda_otorgada": fiado,
        "ventas": ventas,
        "paginator": paginator,
        "is_paginated": ventas.has_other_pages(),
    }
    return render(request, "administracion/reportes_ventas.html", context)


@rol_requerido("Administrador")
def dashboard(request):
    """Panel principal de administración con estadísticas."""
    negocio = request.negocio

    # Si es superadmin y no hay negocio seleccionado, permitir seleccionar uno
    negocio_seleccionado_id = request.GET.get("negocio_id")
    if request.user.is_superuser and negocio is None and negocio_seleccionado_id:
        try:
            negocio = Negocio.objects.get(pk=negocio_seleccionado_id)
        except Negocio.DoesNotExist:
            negocio = None

    usuarios_qs = User.objects.all()
    if negocio is not None:
        usuarios_qs = usuarios_qs.filter(empleado__negocio=negocio)

    total_usuarios = usuarios_qs.count()

    # Stock bajo (HU-06): mismo umbral que el reporte, y la ficha del
    # dashboard es un link a ese reporte para ver de qué productos se trata.
    productos_qs = Producto.objects.filter(activo=True)
    if negocio is not None:
        productos_qs = productos_qs.filter(negocio=negocio)
    productos_stock_bajo = productos_qs.filter(
        stock__lte=reportes.UMBRAL_STOCK_BAJO
    ).count()

    # Productos sin movimiento: sin ventas ni pedidos entregados en los
    # últimos 30 días.
    productos_sin_mov = reportes.productos_sin_movimiento(negocio=negocio, dias=30)

    # Deuda pendiente separada por tipo: facturas de proveedores vs.
    # servicios y gastos (luz, gas, seguridad e higiene, otros).
    deuda_proveedores = Decimal("0.00")
    deuda_servicios = Decimal("0.00")
    if negocio is not None:
        pendientes = Documento.objects.filter(
            negocio=negocio, estado="pendiente"
        )
        deuda_proveedores = pendientes.filter(
            categoria="proveedor"
        ).aggregate(
            total=Coalesce(Sum(F("monto") - F("monto_pagado")), Decimal("0.00"))
        )["total"]
        deuda_servicios = pendientes.exclude(
            categoria="proveedor"
        ).aggregate(
            total=Coalesce(Sum(F("monto") - F("monto_pagado")), Decimal("0.00"))
        )["total"]

    # Lista de negocios para el selector del superadmin
    todos_los_negocios = None
    if request.user.is_superuser:
        todos_los_negocios = Negocio.objects.filter(activo=True).order_by("nombre")

    # Analítica del período: ventas, clientes FIAR, pedidos sin entregar,
    # rotación, medios de pago y próximos vencimientos. El selector admite
    # 7/30/90 días o un rango personalizado (desde/hasta).
    periodo, f_desde, f_hasta, desde_dt, hasta_dt, dias = (
        reportes.resolver_periodo_dashboard(
            request.GET.get("periodo"),
            request.GET.get("desde"),
            request.GET.get("hasta"),
        )
    )
    analitica = reportes.analitica_dashboard(
        desde_dt, hasta_dt, negocio, dias
    )

    context = {
        "total_usuarios": total_usuarios,
        "productos_stock_bajo": productos_stock_bajo,
        "umbral_stock_bajo": reportes.UMBRAL_STOCK_BAJO,
        "productos_sin_movimiento": len(productos_sin_mov),
        "dias_dias": 30,
        "deuda_proveedores": deuda_proveedores,
        "deuda_servicios": deuda_servicios,
        "negocio_actual": negocio,
        "todos_los_negocios": todos_los_negocios,
        "periodo": periodo,
        "periodo_opciones": reportes.PERIODOS_DASHBOARD,
        "desde": f_desde,
        "hasta": f_hasta,
        "dias_periodo": dias,
        **analitica,
    }
    return render(request, "administracion/dashboard.html", context)


@rol_requerido("Administrador")
def reportes_stock(request):
    """Reporte de inventario: valorización, faltantes y márgenes del catálogo."""
    solo_activos = request.GET.get("activos") != "0"
    stock = reportes.resumen_stock(
        solo_activos=solo_activos, negocio=request.negocio
    )

    # Paginación para stock bajo
    stock_bajo_qs = Producto.objects.filter(
        negocio=request.negocio, activo=True, stock__lte=reportes.UMBRAL_STOCK_BAJO
    ).order_by("stock", "nombre")
    paginator_stock_bajo = Paginator(stock_bajo_qs, 10)
    pagina_stock_bajo = request.GET.get("page_stock_bajo", 1)
    try:
        stock_bajo_paginado = paginator_stock_bajo.page(pagina_stock_bajo)
    except PageNotAnInteger:
        stock_bajo_paginado = paginator_stock_bajo.page(1)
    except EmptyPage:
        stock_bajo_paginado = paginator_stock_bajo.page(paginator_stock_bajo.num_pages)

    # Paginación para bajo margen
    bajo_margen_qs = reportes.productos_bajo_margen(negocio=request.negocio)
    paginator_bm = Paginator(bajo_margen_qs, 10)
    pagina_bm = request.GET.get("page_bm", 1)
    try:
        bajo_margen_paginado = paginator_bm.page(pagina_bm)
    except PageNotAnInteger:
        bajo_margen_paginado = paginator_bm.page(1)
    except EmptyPage:
        bajo_margen_paginado = paginator_bm.page(paginator_bm.num_pages)

    context = {
        "solo_activos": solo_activos,
        "stock": stock,
        "por_categoria": reportes.stock_por_categoria(negocio=request.negocio),
        "bajo_margen": bajo_margen_paginado,
        "umbral_stock_bajo": reportes.UMBRAL_STOCK_BAJO,
        "stock_bajo": stock_bajo_paginado,
        "is_paginated_stock": stock_bajo_paginado.has_other_pages(),
        "is_paginated_bm": bajo_margen_paginado.has_other_pages(),
    }
    return render(request, "administracion/reportes_stock.html", context)


@rol_requerido("Administrador")
def productos_sin_movimiento(request):
    """
    Productos sin ventas ni pedidos entregados en los últimos días
    (default 30). Permite editar el precio directamente o dar de baja.
    """
    negocio = request.negocio
    dias = int(request.GET.get("dias", 30))

    # Descuento rápido desde enlaces: ?accion=desc&prod=<id>&pct=<porcentaje>
    accion_get = request.GET.get("accion", "")
    prod_id_get = request.GET.get("prod", "")
    pct_get = request.GET.get("pct", "")

    if accion_get == "desc" and prod_id_get and pct_get:
        try:
            producto = Producto.objects.get(pk=prod_id_get, negocio=negocio)
            porcentaje = Decimal(pct_get)
            if porcentaje < 0 or porcentaje > 100:
                raise ValueError("Porcentaje fuera de rango.")
            nuevo_precio = producto.precio * (1 - porcentaje / 100)
            producto.precio = nuevo_precio
            producto.save(update_fields=["precio"])
            registrar_accion(
                request.user,
                "Precio modificado (descuento rápido sin movimiento)",
                f"Producto '{producto.nombre}': -{porcentaje}% → ${nuevo_precio}.",
                request,
            )
            messages.success(
                request,
                f"Precio de '{producto.nombre}' reducido un {porcentaje}% a ${nuevo_precio|montos}.",
            )
        except (Producto.DoesNotExist, ValueError, TypeError):
            messages.error(request, "No se pudo aplicar el descuento.")
        return redirect("administracion:productos_sin_movimiento")

    productos = reportes.productos_sin_movimiento(negocio=negocio, dias=dias)

    if request.method == "POST":
        accion = request.POST.get("accion", "")
        producto_id = request.POST.get("producto_id", "")

        try:
            producto = Producto.objects.get(pk=producto_id, negocio=negocio)
        except Producto.DoesNotExist:
            messages.error(request, "El producto ya no existe.")
            return redirect("administracion:productos_sin_movimiento")

        if accion == "baja":
            producto.activo = False
            producto.save(update_fields=["activo"])
            registrar_accion(
                request.user,
                "Producto dado de baja (sin movimiento)",
                f"Producto '{producto.nombre}' dado de baja por falta de movimiento.",
                request,
            )
            messages.success(
                request, f"Producto '{producto.nombre}' dado de baja."
            )
            return redirect("administracion:productos_sin_movimiento")

        elif accion == "descuento":
            try:
                nuevo_precio = Decimal(request.POST.get("nuevo_precio", "0"))
                if nuevo_precio < 0:
                    raise ValueError("El precio no puede ser negativo.")
            except (ValueError, TypeError):
                messages.error(request, "Ingresá un precio válido.")
                return redirect("administracion:productos_sin_movimiento")

            precio_anterior = producto.precio
            producto.precio = nuevo_precio
            producto.save(update_fields=["precio"])

            registrar_accion(
                request.user,
                "Precio modificado (sin movimiento)",
                f"Producto '{producto.nombre}': ${precio_anterior} → ${nuevo_precio}.",
                request,
            )
            messages.success(
                request,
                f"Precio de '{producto.nombre}' actualizado a ${nuevo_precio|montos}.",
            )
            return redirect("administracion:productos_sin_movimiento")

    contexto = {
        "productos": productos,
        "dias": dias,
        "total_sin_movimiento": len(productos),
    }
    return render(request, "administracion/productos_sin_movimiento.html", contexto)


@rol_requerido("Administrador")
def listar_usuarios(request):
    """Lista todos los usuarios con búsqueda y filtros."""
    busqueda = request.GET.get("buscar", "")
    filtro_estado = request.GET.get("estado", "")
    filtro_rol = request.GET.get("rol", "")

    negocio = request.negocio
    usuarios = User.objects.all()
    if negocio is not None:
        usuarios = usuarios.filter(empleado__negocio=negocio)
    usuarios = usuarios.order_by("-date_joined")

    if busqueda:
        usuarios = usuarios.filter(
            username__icontains=busqueda
        ) | usuarios.filter(
            first_name__icontains=busqueda
        ) | usuarios.filter(
            last_name__icontains=busqueda
        ) | usuarios.filter(
            email__icontains=busqueda
        )

    if filtro_estado == "activos":
        usuarios = usuarios.filter(is_active=True)
    elif filtro_estado == "inactivos":
        usuarios = usuarios.filter(is_active=False)

    if filtro_rol:
        usuarios = usuarios.filter(groups__name=filtro_rol)

    context = {
        "usuarios": usuarios.distinct(),
        "busqueda": busqueda,
        "filtro_estado": filtro_estado,
        "filtro_rol": filtro_rol,
    }
    return render(request, "administracion/listar_usuarios.html", context)


@rol_requerido("Administrador")
def crear_usuario(request):
    """Crear un nuevo usuario."""
    if request.method == "POST":
        form = UsuarioForm(request.POST)
        if form.is_valid():
            user = form.save()
            registrar_accion(
                request.user,
                "Usuario creado",
                f"Se creó el usuario '{user.username}'",
                request,
            )
            messages.success(
                request, f"Usuario '{user.username}' creado exitosamente."
            )
            return redirect("administracion:listar_usuarios")
    else:
        form = UsuarioForm()

    return render(request, "administracion/crear_usuario.html", {"form": form})


@rol_requerido("Administrador")
def editar_usuario(request, user_id):
    """Editar un usuario existente."""
    user = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        form = UsuarioForm(request.POST, instance=user, es_edicion=True)
        if form.is_valid():
            user = form.save()
            registrar_accion(
                request.user,
                "Usuario editado",
                f"Se editó el usuario '{user.username}'",
                request,
            )
            messages.success(
                request, f"Usuario '{user.username}' actualizado exitosamente."
            )
            return redirect("administracion:listar_usuarios")
    else:
        form = UsuarioForm(instance=user, es_edicion=True)

    return render(
        request, "administracion/editar_usuario.html", {"form": form, "usuario": user}
    )


@rol_requerido("Administrador")
def eliminar_usuario(request, user_id):
    """Eliminar un usuario (solo si no es el mismo admin logueado)."""
    user = get_object_or_404(User, id=user_id)

    if user == request.user:
        messages.error(request, "No podés eliminar tu propio usuario.")
        return redirect("administracion:listar_usuarios")

    if user.is_superuser:
        messages.error(request, "No podés eliminar un superusuario.")
        return redirect("administracion:listar_usuarios")

    if request.method == "POST":
        username = user.username
        user.delete()
        registrar_accion(
            request.user,
            "Usuario eliminado",
            f"Se eliminó el usuario '{username}'",
            request,
        )
        messages.success(request, f"Usuario '{username}' eliminado exitosamente.")
        return redirect("administracion:listar_usuarios")

    return render(
        request, "administracion/eliminar_usuario.html", {"usuario": user}
    )


@rol_requerido("Administrador")
def asignar_roles(request, user_id):
    """Asignar o quitar roles (grupos) a un usuario."""
    user = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        form = AsignarRolForm(request.POST, usuario=user)
        if form.is_valid():
            grupos = form.cleaned_data["grupos"]
            user.groups.set(grupos)
            nombres_grupos = ", ".join([g.name for g in grupos]) or "Ninguno"
            registrar_accion(
                request.user,
                "Roles actualizados",
                f"Se actualizaron los roles de '{user.username}': {nombres_grupos}",
                request,
            )
            messages.success(
                request,
                f"Roles de '{user.username}' actualizados: {nombres_grupos}.",
            )
            return redirect("administracion:listar_usuarios")
    else:
        form = AsignarRolForm(usuario=user)

    return render(
        request,
        "administracion/asignar_roles.html",
        {"form": form, "usuario": user},
    )


@rol_requerido("Administrador")
def toggle_usuario(request, user_id):
    """Activar/desactivar un usuario."""
    user = get_object_or_404(User, id=user_id)

    if user == request.user:
        messages.error(request, "No podés desactivar tu propio usuario.")
        return redirect("administracion:listar_usuarios")

    if user.is_superuser:
        messages.error(request, "No podés desactivar un superusuario.")
        return redirect("administracion:listar_usuarios")

    user.is_active = not user.is_active
    user.save()
    estado = "activado" if user.is_active else "desactivado"
    registrar_accion(
        request.user,
        f"Usuario {estado}",
        f"Se {estado} el usuario '{user.username}'",
        request,
    )
    messages.success(request, f"Usuario '{user.username}' {estado} exitosamente.")
    return redirect("administracion:listar_usuarios")


@rol_requerido("Administrador")
def exportar_stock_excel(request):
    """Exporta el stock del negocio del usuario a un archivo Excel."""
    negocio = request.negocio
    if negocio is None:
        messages.error(request, "No se pudo determinar el negocio.")
        return redirect("administracion:reportes_stock")

    wb = exportar_stock_a_excel(negocio)

    nombre_archivo = (
        f"stock_{negocio.slug}_{datetime.now().strftime('%d-%m-%Y')}.xlsx"
    )

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f'attachment; filename="{nombre_archivo}"'
    wb.save(response)

    registrar_accion(
        request.user,
        "Exportó stock a Excel",
        f"Exportó el stock de '{negocio.nombre}' a Excel.",
        request,
    )
    return response
