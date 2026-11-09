"""Vistas de la app negocios.

Incluye la vista de landing pública que lista los negocios activos
para que los compradores elijan a cuál entrar, y las vistas de gestión
de documentos (facturas) para cada negocio.
"""
from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from auditoria.utils import registrar_accion

from .models import Documento, Negocio, Proveedor


def _negocio_del_usuario(user):
    """Devuelve el negocio del usuario si es empleado, o None."""
    try:
        return user.empleado.negocio
    except Exception:
        return None


def _es_admin_del_negocio(user, negocio):
    """True si el usuario es administrador del negocio dado."""
    try:
        emp = user.empleado
        return emp.negocio_id == negocio.id and emp.activo
    except Exception:
        return False


def _negocio_requerido(vista):
    """Decorador: solo el dueño/admin del negocio puede acceder."""
    from functools import wraps

    @wraps(vista)
    def _envoltorio(request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login

            return redirect_to_login(request.get_full_path())
        negocio_id = kwargs.get("negocio_id") or kwargs.get("documento_id")
        if negocio_id:
            negocio = get_object_or_404(Negocio, pk=negocio_id)
        else:
            negocio = _negocio_del_usuario(request.user)
        if not negocio or not _es_admin_del_negocio(request.user, negocio):
            raise PermissionDenied(
                "Solo el administrador del negocio puede acceder a esta sección."
            )
        request.negocio_actual = negocio
        return vista(request, *args, **kwargs)

    return _envoltorio


def landing(request):
    """
    Página institucional de Noruega.

    Muestra un listado de todos los negocios activos con recuadros
    (nombre, logo, WhatsApp, botón "Entrar a la tienda").
    Cada recuadro lleva a la tienda online del negocio en /t/<slug>/.
    """
    negocios = Negocio.objects.filter(activo=True).order_by("nombre")
    return render(
        request,
        "landing.html",
        {"negocios": negocios},
    )


@login_required
def lista_documentos(request):
    """
    Listado de documentos (facturas) del negocio del usuario.
    Permite filtrar por estado y categoría.
    """
    negocio = _negocio_del_usuario(request.user)
    if negocio is None:
        raise PermissionDenied(
            "No tenés un negocio asociado para ver documentos."
        )

    documentos = Documento.objects.filter(negocio=negocio).order_by(
        "-fecha_vencimiento"
    )

    estado = request.GET.get("estado", "")
    categoria = request.GET.get("categoria", "")

    if estado in dict(Documento.ESTADOS):
        documentos = documentos.filter(estado=estado)
    if categoria in dict(Documento.CATEGORIAS):
        documentos = documentos.filter(categoria=categoria)

    contexto = {
        "negocio": negocio,
        "documentos": documentos,
        "estado_actual": estado,
        "categoria_actual": categoria,
        "categorias": Documento.CATEGORIAS,
        "estados": Documento.ESTADOS,
        "total_pendiente": documentos.filter(estado="pendiente").count(),
        "total_pagada": documentos.filter(estado="pagada").count(),
        "total_deuda": sum(
            d.monto_pendiente for d in documentos if d.estado != "anulada"
        ),
    }
    return render(
        request,
        "negocios/documentos/lista_documentos.html",
        contexto,
    )


@login_required
def crear_documento(request):
    """
    Crear un nuevo documento (factura) para el negocio del usuario.
    """
    negocio = _negocio_del_usuario(request.user)
    if negocio is None:
        raise PermissionDenied(
            "No tenés un negocio asociado para crear documentos."
        )

    proveedores = Proveedor.objects.filter(negocio=negocio, activo=True)

    if request.method == "POST":
        proveedor_id = request.POST.get("proveedor", "").strip()
        nombre_proveedor = request.POST.get("nombre_proveedor", "").strip()
        categoria = request.POST.get("categoria", "otro")
        numero_factura = request.POST.get("numero_factura", "").strip()
        monto = request.POST.get("monto", "0").strip()
        fecha_emision = request.POST.get("fecha_emision", "").strip()
        fecha_vencimiento = request.POST.get("fecha_vencimiento", "").strip()
        observaciones = request.POST.get("observaciones", "").strip()

        try:
            monto_decimal = Decimal(monto)
            if monto_decimal < 0:
                raise ValueError("El monto no puede ser negativo.")
        except (ValueError, TypeError):
            messages.error(request, "Ingresá un monto válido.")
            return render(
                request,
                "negocios/documentos/crear_documento.html",
                {
                    "negocio": negocio,
                    "proveedores": proveedores,
                    "categorias": Documento.CATEGORIAS,
                    "form_data": request.POST,
                },
            )

        proveedor_obj = None
        if proveedor_id:
            try:
                proveedor_obj = Proveedor.objects.get(
                    pk=proveedor_id, negocio=negocio
                )
            except Proveedor.DoesNotExist:
                pass

        documento = Documento.objects.create(
            negocio=negocio,
            proveedor=proveedor_obj,
            nombre_proveedor=nombre_proveedor,
            categoria=categoria,
            numero_factura=numero_factura,
            monto=monto_decimal,
            monto_pagado=Decimal("0.00"),
            fecha_emision=fecha_emision,
            fecha_vencimiento=fecha_vencimiento,
            estado="pendiente",
            observaciones=observaciones,
        )

        registrar_accion(
            request.user,
            "Documento creado",
            f"Documento '{documento.numero_factura or documento.nombre_proveedor}' creado por ${documento.monto}.",
            request,
        )
        messages.success(
            request,
            f"Documento '{documento.numero_factura or documento.nombre_proveedor}' creado correctamente.",
        )
        return redirect("negocios:lista_documentos")

    return render(
        request,
        "negocios/documentos/crear_documento.html",
        {
            "negocio": negocio,
            "proveedores": proveedores,
            "categorias": Documento.CATEGORIAS,
        },
    )


@login_required
def editar_documento(request, documento_id):
    """
    Editar un documento existente del negocio del usuario.
    """
    documento = get_object_or_404(Documento, pk=documento_id)
    if documento.negocio_id != _negocio_del_usuario(request.user).id:
        raise PermissionDenied(
            "No tenés permiso para editar este documento."
        )

    proveedores = Proveedor.objects.filter(
        negocio=documento.negocio, activo=True
    )

    if request.method == "POST":
        proveedor_id = request.POST.get("proveedor", "").strip()
        nombre_proveedor = request.POST.get("nombre_proveedor", "").strip()
        categoria = request.POST.get("categoria", documento.categoria)
        numero_factura = request.POST.get("numero_factura", "").strip()
        monto = request.POST.get("monto", "0").strip()
        fecha_emision = request.POST.get("fecha_emision", "").strip()
        fecha_vencimiento = request.POST.get("fecha_vencimiento", "").strip()
        observaciones = request.POST.get("observaciones", "").strip()

        try:
            monto_decimal = Decimal(monto)
            if monto_decimal < 0:
                raise ValueError("El monto no puede ser negativo.")
        except (ValueError, TypeError):
            messages.error(request, "Ingresá un monto válido.")
            return render(
                request,
                "negocios/documentos/editar_documento.html",
                {
                    "negocio": documento.negocio,
                    "documento": documento,
                    "proveedores": proveedores,
                    "categorias": Documento.CATEGORIAS,
                    "form_data": request.POST,
                },
            )

        proveedor_obj = None
        if proveedor_id:
            try:
                proveedor_obj = Proveedor.objects.get(
                    pk=proveedor_id, negocio=documento.negocio
                )
            except Proveedor.DoesNotExist:
                pass

        documento.proveedor = proveedor_obj
        documento.nombre_proveedor = nombre_proveedor
        documento.categoria = categoria
        documento.numero_factura = numero_factura
        documento.monto = monto_decimal
        documento.fecha_emision = fecha_emision
        documento.fecha_vencimiento = fecha_vencimiento
        documento.observaciones = observaciones
        documento.save()

        registrar_accion(
            request.user,
            "Documento editado",
            f"Documento '{documento.numero_factura or documento.nombre_proveedor}' editado.",
            request,
        )
        messages.success(
            request,
            f"Documento '{documento.numero_factura or documento.nombre_proveedor}' actualizado correctamente.",
        )
        return redirect("negocios:lista_documentos")

    return render(
        request,
        "negocios/documentos/editar_documento.html",
        {
            "negocio": documento.negocio,
            "documento": documento,
            "proveedores": proveedores,
            "categorias": Documento.CATEGORIAS,
        },
    )


@login_required
def subir_pdf(request, documento_id):
    """
    Subir archivo PDF para un documento existente.
    """
    documento = get_object_or_404(Documento, pk=documento_id)
    if documento.negocio_id != _negocio_del_usuario(request.user).id:
        raise PermissionDenied(
            "No tenés permiso para editar este documento."
        )

    if request.method == "POST" and request.FILES.get("archivo_pdf"):
        documento.archivo_pdf = request.FILES["archivo_pdf"]
        documento.save()
        registrar_accion(
            request.user,
            "PDF subido",
            f"PDF subido para documento '{documento.numero_factura or documento.nombre_proveedor}'.",
            request,
        )
        messages.success(
            request,
            "PDF subido correctamente.",
        )
        return redirect("negocios:lista_documentos")

    return render(
        request,
        "negocios/documentos/subir_pdf.html",
        {
            "negocio": documento.negocio,
            "documento": documento,
        },
    )


@login_required
def marcar_pagada(request, documento_id):
    """
    Marcar un documento como pagada (puede ser pago parcial).
    """
    documento = get_object_or_404(Documento, pk=documento_id)
    if documento.negocio_id != _negocio_del_usuario(request.user).id:
        raise PermissionDenied(
            "No tenés permiso para editar este documento."
        )

    if request.method == "POST":
        monto_pagado = request.POST.get("monto_pagado", "0").strip()
        try:
            monto_pagado_decimal = Decimal(monto_pagado)
            if monto_pagado_decimal < 0:
                raise ValueError("El monto no puede ser negativo.")
        except (ValueError, TypeError):
            messages.error(request, "Ingresá un monto válido.")
            return redirect("negocios:lista_documentos")

        nuevo_monto_pagado = documento.monto_pagado + monto_pagado_decimal
        documento.monto_pagado = nuevo_monto_pagado

        if nuevo_monto_pagado >= documento.monto:
            documento.estado = "pagada"
        else:
            documento.estado = "pendiente"

        documento.save()

        registrar_accion(
            request.user,
            "Pago registrado",
            f"Pago de ${monto_pagado_decimal} registrado para documento '{documento.numero_factura or documento.nombre_proveedor}'. Saldo pendiente: ${documento.monto_pendiente}.",
            request,
        )
        messages.success(
            request,
            f"Pago de ${monto_pagado_decimal} registrado. Saldo pendiente: ${documento.monto_pendiente}.",
        )
        return redirect("negocios:lista_documentos")

    return render(
        request,
        "negocios/documentos/marcar_pagada.html",
        {
            "negocio": documento.negocio,
            "documento": documento,
        },
    )
