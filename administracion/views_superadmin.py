"""Vistas del panel de superadmin (/superadmin/).

Solo usuarios con is_superuser=True pueden acceder. Permite crear
negocios, crear empleados (usuario + negocio + rol) y asignar negocios
a usuarios existentes.
"""
from django.contrib import messages
from django.contrib.auth.models import Group, User
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from auditoria.utils import registrar_accion
from usuarios.decorators import superadmin_requerido

from .forms import AsignarNegocioForm, NegocioForm, UsuarioForm
from negocios.models import Negocio
from usuarios.models import Empleado


@superadmin_requerido
def lista_negocios(request):
    """Listar todos los negocios de la plataforma."""
    negocios = Negocio.objects.all().order_by("nombre")
    return render(
        request,
        "administracion/superadmin/lista_negocios.html",
        {"negocios": negocios},
    )


@superadmin_requerido
def crear_negocio(request):
    """Crear un nuevo negocio."""
    if request.method == "POST":
        form = NegocioForm(request.POST)
        if form.is_valid():
            negocio = form.save()
            registrar_accion(
                request.user,
                "Negocio creado",
                f"Se creó el negocio '{negocio.nombre}' (slug: {negocio.slug})",
                request,
            )
            messages.success(
                request, f"Negocio «{negocio.nombre}» creado correctamente."
            )
            return redirect("administracion:lista_negocios")
    else:
        form = NegocioForm()
    return render(
        request,
        "administracion/superadmin/crear_negocio.html",
        {"form": form},
    )


@superadmin_requerido
def editar_negocio(request, negocio_id):
    """Editar un negocio existente."""
    negocio = get_object_or_404(Negocio, pk=negocio_id)
    if request.method == "POST":
        form = NegocioForm(request.POST, instance=negocio)
        if form.is_valid():
            form.save()
            registrar_accion(
                request.user,
                "Negocio editado",
                f"Se editó el negocio '{negocio.nombre}' (slug: {negocio.slug})",
                request,
            )
            messages.success(
                request, f"Negocio «{negocio.nombre}» actualizado correctamente."
            )
            return redirect("administracion:lista_negocios")
    else:
        form = NegocioForm(instance=negocio)
    return render(
        request,
        "administracion/superadmin/editar_negocio.html",
        {"form": form, "negocio": negocio},
    )


@superadmin_requerido
def crear_empleado(request):
    """Crear un empleado: usuario + negocio + rol."""
    if request.method == "POST":
        form = AsignarNegocioForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            if User.objects.filter(username=username).exists():
                messages.error(
                    request, f"El usuario «{username}» ya existe."
                )
            else:
                user = User.objects.create_user(
                    username=username,
                    password=form.cleaned_data["password"],
                    first_name=form.cleaned_data.get("first_name", ""),
                    last_name=form.cleaned_data.get("last_name", ""),
                )
                negocio = form.cleaned_data["negocio"]
                rol = form.cleaned_data["rol"]
                user.groups.add(rol)
                Empleado.objects.create(usuario=user, negocio=negocio, activo=True)
                registrar_accion(
                    request.user,
                    "Empleado creado",
                    f"Se creó el empleado '{user.username}' para el negocio "
                    f"'{negocio.nombre}' con rol '{rol.name}'.",
                    request,
                )
                messages.success(
                    request,
                    f"Empleado «{username}» creado para «{negocio.nombre}» "
                    f"con rol «{rol.name}».",
                )
                return redirect("administracion:lista_negocios")
    else:
        form = AsignarNegocioForm()
    return render(
        request,
        "administracion/superadmin/crear_empleado.html",
        {"form": form},
    )


@superadmin_requerido
def asignar_negocio_usuario(request, user_id):
    """Asignar (o cambiar) el negocio de un usuario existente."""
    user = get_object_or_404(User, pk=user_id)
    try:
        empleado = user.empleado
    except Empleado.DoesNotExist:
        empleado = None

    if request.method == "POST":
        form = AsignarNegocioForm(request.POST)
        if form.is_valid():
            negocio = form.cleaned_data["negocio"]
            rol = form.cleaned_data["rol"]
            # Actualizar datos del usuario
            user.first_name = form.cleaned_data.get("first_name", "")
            user.last_name = form.cleaned_data.get("last_name", "")
            password = form.cleaned_data.get("password")
            if password:
                user.set_password(password)
            user.save()
            # Actualizar rol
            user.groups.clear()
            user.groups.add(rol)
            # Crear o actualizar Empleado
            if empleado:
                empleado.negocio = negocio
                empleado.activo = True
                empleado.save()
            else:
                Empleado.objects.create(
                    usuario=user, negocio=negocio, activo=True
                )
            registrar_accion(
                request.user,
                "Negocio asignado a usuario",
                f"Se asignó el negocio '{negocio.nombre}' al usuario "
                f"'{user.username}' con rol '{rol.name}'.",
                request,
            )
            messages.success(
                request,
                f"Negocio «{negocio.nombre}» asignado a «{user.username}» "
                f"con rol «{rol.name}».",
            )
            return redirect("administracion:listar_usuarios")
    else:
        initial = {}
        if empleado:
            initial["negocio"] = empleado.negocio.pk
            try:
                initial["rol"] = user.groups.first().pk
            except AttributeError:
                pass
            initial["first_name"] = user.first_name
            initial["last_name"] = user.last_name
        form = AsignarNegocioForm(initial=initial)
    return render(
        request,
        "administracion/superadmin/asignar_negocio_usuario.html",
        {"form": form, "usuario": user, "empleado": empleado},
    )
