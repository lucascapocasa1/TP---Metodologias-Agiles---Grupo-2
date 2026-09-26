
from django.contrib import messages
from django.contrib.auth.models import Group, User
from django.shortcuts import get_object_or_404, redirect, render

from django.shortcuts import render, redirect


from auditoria.utils import registrar_accion
from usuarios.decorators import rol_requerido
from .models import  Bitacora
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required


from .forms import AsignarRolForm, UsuarioForm


@login_required
def dashboard(request):
    # Si el usuario tiene perfil de cajero → va directo a cobro
   if hasattr(request.user, 'perfil_cajero') and request.user.perfil_cajero.activo:
        return redirect('ventas:pantalla_cobro')
    
    # Si no es cajero → ve el panel del dueño 
   else:
       return render(request, 'administracion/dashboard.html')

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

