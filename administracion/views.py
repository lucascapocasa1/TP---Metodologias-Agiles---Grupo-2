from django.contrib import messages
from django.contrib.auth.models import Group, User
from decimal import Decimal

from django.db.models import (
    DecimalField,
    F,
    IntegerField,
    Prefetch,
    Sum,
    Value,
)
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render

from auditoria.utils import registrar_accion
from usuarios.decorators import rol_requerido
from ventas.models import DetalleVenta

from . import reportes
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

    resumen = reportes.resumen_ventas(desde_dt, hasta_dt, solo_finalizadas)
    serie = reportes.ventas_por_dia(desde_dt, hasta_dt, solo_finalizadas)
    top = reportes.top_productos(desde_dt, hasta_dt, solo_finalizadas=solo_finalizadas)
    rentables = reportes.productos_mas_rentables(
        desde_dt, hasta_dt, solo_finalizadas=solo_finalizadas
    )

    ventas = (
        reportes.ventas_del_rango(desde_dt, hasta_dt, solo_finalizadas)
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
        "ventas": ventas[:100],
        "hay_mas_ventas": ventas.count() > 100,
    }
    return render(request, "administracion/reportes_ventas.html", context)


@rol_requerido("Administrador")
def reportes_stock(request):
    """Reporte de inventario: valorización, faltantes y márgenes del catálogo."""
    solo_activos = request.GET.get("activos") != "0"
    stock = reportes.resumen_stock(solo_activos=solo_activos)

    context = {
        "solo_activos": solo_activos,
        "stock": stock,
        "por_categoria": reportes.stock_por_categoria(),
        "bajo_margen": reportes.productos_bajo_margen(),
        "umbral_stock_bajo": reportes.UMBRAL_STOCK_BAJO,
    }
    return render(request, "administracion/reportes_stock.html", context)


@rol_requerido("Administrador")
def dashboard(request):
    """Panel principal de administración con estadísticas."""
    total_usuarios = User.objects.count()
    usuarios_activos = User.objects.filter(is_active=True).count()
    usuarios_inactivos = User.objects.filter(is_active=False).count()
    admins = User.objects.filter(groups__name="Administrador").distinct().count()
    cajeros = User.objects.filter(groups__name="Cajero").distinct().count()
    sin_rol = User.objects.filter(groups__isnull=True, is_active=True).count()

    context = {
        "total_usuarios": total_usuarios,
        "usuarios_activos": usuarios_activos,
        "usuarios_inactivos": usuarios_inactivos,
        "admins": admins,
        "cajeros": cajeros,
        "sin_rol": sin_rol,
    }
    return render(request, "administracion/dashboard.html", context)


@rol_requerido("Administrador")
def listar_usuarios(request):
    """Lista todos los usuarios con búsqueda y filtros."""
    busqueda = request.GET.get("buscar", "")
    filtro_estado = request.GET.get("estado", "")
    filtro_rol = request.GET.get("rol", "")

    usuarios = User.objects.all().order_by("-date_joined")

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
