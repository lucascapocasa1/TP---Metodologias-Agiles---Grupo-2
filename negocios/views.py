"""Vistas de la app negocios.

Incluye la vista de landing pública que lista los negocios activos
para que los compradores elijan a cuál entrar, y las vistas de gestión
de documentos (facturas) para cada negocio.
"""
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from auditoria.utils import registrar_accion

from .models import Documento, Negocio, Proveedor

# Agrupaciones de categorías para los KPIs del dashboard.
GRUPOS_DOCUMENTOS = {
    "proveedores": ["proveedor"],
    "servicios": ["luz", "gas", "seguridad", "otro"],
}

# Columnas ordenables del listado de documentos: clave pública -> campo.
ORDEN_DOCUMENTOS = {
    "factura": "numero_factura",
    "categoria": "categoria",
    "proveedor": "proveedor__nombre",
    "monto": "monto",
    "pagado": "monto_pagado",
    "pendiente": "saldo_pendiente",
    "vencimiento": "fecha_vencimiento",
    "estado": "estado",
}

COLUMNAS_DOCUMENTOS = [
    ("factura", "Factura / Nombre"),
    ("categoria", "Categoría"),
    ("proveedor", "Proveedor"),
    ("monto", "Monto"),
    ("pagado", "Pagado"),
    ("pendiente", "Pendiente"),
    ("vencimiento", "Vencimiento"),
    ("estado", "Estado"),
]

DOCUMENTOS_POR_PAGINA = 10


def _documentos_con_saldo(queryset):
    """Anota el saldo pendiente de cada documento para poder ordenar."""
    return queryset.annotate(
        saldo_pendiente=ExpressionWrapper(
            F("monto") - F("monto_pagado"),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        )
    )


def _resumen_por_proveedor(documentos):
    """
    Saldo pendiente agrupado por proveedor.

    Devuelve una lista de dicts ordenada de mayor a menor deuda:
        nombre, clave, proveedor_id, saldo, facturas, vencidas
    """
    filas = (
        documentos.filter(estado="pendiente")
        .values("proveedor_id", "proveedor__nombre", "nombre_proveedor")
        .annotate(
            saldo=Coalesce(
                Sum(F("monto") - F("monto_pagado")), Decimal("0.00")
            ),
            facturas=Count("id"),
            vencidas=Count(
                "id", filter=Q(fecha_vencimiento__lt=timezone.localdate())
            ),
        )
    )

    resumen = {}
    for fila in filas:
        proveedor_id = fila["proveedor_id"]
        clave = str(proveedor_id) if proveedor_id else "sin"
        nombre = (
            fila["proveedor__nombre"]
            or fila["nombre_proveedor"]
            or "Sin proveedor"
        )
        item = resumen.setdefault(
            clave,
            {
                "clave": clave,
                "proveedor_id": proveedor_id,
                "nombre": nombre,
                "saldo": Decimal("0.00"),
                "facturas": 0,
                "vencidas": 0,
            },
        )
        item["saldo"] += fila["saldo"]
        item["facturas"] += fila["facturas"]
        item["vencidas"] += fila["vencidas"]

    return sorted(
        resumen.values(),
        key=lambda item: (-item["saldo"], item["nombre"]),
    )


def _url_lista_documentos(categoria, proveedor_id=None):
    """URL del listado que corresponde a la categoría de un documento."""
    nombre = (
        "negocios:lista_proveedores"
        if categoria == "proveedor"
        else "negocios:lista_facturas"
    )
    url = reverse(nombre)
    if proveedor_id:
        url = f"{url}?proveedor={proveedor_id}"
    return url


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
def lista_documentos(request, grupo_fijo=None):
    """
    Listado de documentos (facturas) del negocio del usuario.

    Se usa en dos modos bien diferenciados desde el menú lateral:
      - Facturas (`grupo_fijo="servicios"`): luz, gas, seguridad e higiene
        y otros gastos. No muestra deuda ni filtros de proveedores.
      - Proveedores (`grupo_fijo="proveedores"`): facturas de mercadería,
        con el resumen de deuda por proveedor y sus filtros.

    Sin `grupo_fijo` (URL histórica /documentos/) muestra todo junto.
    También permite ordenar cada columna y pagina de a 10 filas.
    """
    negocio = _negocio_del_usuario(request.user)
    if negocio is None:
        raise PermissionDenied(
            "No tenés un negocio asociado para ver documentos."
        )

    documentos = _documentos_con_saldo(
        Documento.objects.filter(negocio=negocio)
    )

    estado = request.GET.get("estado", "")
    categoria = request.GET.get("categoria", "")
    grupo = grupo_fijo or request.GET.get("grupo", "")
    if grupo not in GRUPOS_DOCUMENTOS:
        grupo = ""
    es_proveedores = grupo == "proveedores"
    es_facturas = grupo == "servicios"
    proveedor_filtro = request.GET.get("proveedor", "").strip()
    orden = request.GET.get("orden", "")
    direccion = request.GET.get("dir", "")

    if grupo:
        documentos = documentos.filter(
            categoria__in=GRUPOS_DOCUMENTOS[grupo]
        )
    # En Proveedores la categoría ya está fijada; en Facturas solo se
    # aceptan categorías de servicios para no mezclar datos.
    if categoria in dict(Documento.CATEGORIAS):
        if es_facturas and categoria == "proveedor":
            categoria = ""
        elif not es_proveedores:
            documentos = documentos.filter(categoria=categoria)

    # Deuda por proveedor: solo tiene sentido en el módulo de proveedores.
    if es_facturas:
        resumen_proveedores = []
        total_deuda = documentos.filter(estado="pendiente").aggregate(
            total=Coalesce(
                Sum(F("monto") - F("monto_pagado")), Decimal("0.00")
            )
        )["total"]
    else:
        resumen_proveedores = _resumen_por_proveedor(documentos)
        total_deuda = sum(
            (item["saldo"] for item in resumen_proveedores),
            Decimal("0.00"),
        )

    if estado in dict(Documento.ESTADOS):
        documentos = documentos.filter(estado=estado)

    proveedor_seleccionado = ""
    if not es_facturas:
        if proveedor_filtro == "sin":
            documentos = documentos.filter(proveedor__isnull=True)
            proveedor_seleccionado = "sin"
        elif proveedor_filtro.isdigit():
            documentos = documentos.filter(proveedor_id=proveedor_filtro)
            proveedor_seleccionado = proveedor_filtro

    total_pendiente = documentos.filter(estado="pendiente").count()
    total_pagada = documentos.filter(estado="pagada").count()

    # Ordenamiento: por defecto vencimiento más próximo primero.
    campo = ORDEN_DOCUMENTOS.get(orden)
    if campo is None:
        orden = "vencimiento"
        direccion = "desc"
        campo = "fecha_vencimiento"
    else:
        direccion = "desc" if direccion == "desc" else "asc"
    prefijo = "-" if direccion == "desc" else ""
    documentos = documentos.order_by(f"{prefijo}{campo}", "-pk")

    # Encabezados ordenables: indican la dirección que aplica al hacer clic.
    columnas = []
    for clave, etiqueta in COLUMNAS_DOCUMENTOS:
        activa = orden == clave
        siguiente = "desc" if (activa and direccion == "asc") else "asc"
        columnas.append(
            {
                "clave": clave,
                "etiqueta": etiqueta,
                "activa": activa,
                "direccion": direccion,
                "siguiente": siguiente,
            }
        )

    paginador = Paginator(documentos, DOCUMENTOS_POR_PAGINA)
    pagina = paginador.get_page(request.GET.get("page"))

    if es_proveedores:
        titulo = "Proveedores"
        categorias_filtro = []
        proveedores_qs = Proveedor.objects.filter(negocio=negocio).order_by(
            "nombre"
        )
    elif es_facturas:
        titulo = "Facturas"
        categorias_filtro = [
            (valor, etiqueta)
            for valor, etiqueta in Documento.CATEGORIAS
            if valor != "proveedor"
        ]
        proveedores_qs = Proveedor.objects.none()
    else:
        titulo = "Documentos"
        categorias_filtro = Documento.CATEGORIAS
        proveedores_qs = Proveedor.objects.filter(negocio=negocio).order_by(
            "nombre"
        )

    contexto = {
        "negocio": negocio,
        "documentos": pagina,
        "pagina": pagina,
        "paginador": paginador,
        "titulo_listado": titulo,
        "es_proveedores": es_proveedores,
        "es_facturas": es_facturas,
        "lista_url": reverse(
            "negocios:lista_proveedores"
            if es_proveedores
            else (
                "negocios:lista_facturas"
                if es_facturas
                else "negocios:lista_documentos"
            )
        ),
        "estado_actual": estado,
        "categoria_actual": categoria,
        "grupo_actual": grupo,
        "proveedor_actual": proveedor_seleccionado,
        "proveedores": proveedores_qs,
        "resumen_proveedores": resumen_proveedores,
        "columnas": columnas,
        "orden_actual": orden,
        "direccion_actual": direccion,
        "categorias": categorias_filtro,
        "categorias_form": Documento.CATEGORIAS,
        "estados": Documento.ESTADOS,
        "total_pendiente": total_pendiente,
        "total_pagada": total_pagada,
        # KPI de deuda: solo lo que realmente se debe, es decir facturas
        # pendientes. Las pagadas ya no adeudan nada (aunque guarden un
        # monto_pagado parcial por pagos incompletos) y las anuladas tampoco.
        "total_deuda": total_deuda,
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
    grupo_form = request.GET.get("grupo", "")
    if grupo_form == "proveedores":
        categorias_form = [
            (valor, etiqueta)
            for valor, etiqueta in Documento.CATEGORIAS
            if valor == "proveedor"
        ]
        categoria_inicial = "proveedor"
        volver_url = reverse("negocios:lista_proveedores")
    elif grupo_form == "servicios":
        categorias_form = [
            (valor, etiqueta)
            for valor, etiqueta in Documento.CATEGORIAS
            if valor != "proveedor"
        ]
        categoria_inicial = "luz"
        volver_url = reverse("negocios:lista_facturas")
    else:
        categorias_form = Documento.CATEGORIAS
        categoria_inicial = ""
        volver_url = reverse("negocios:lista_documentos")

    if request.method == "POST":
        proveedor_id = request.POST.get("proveedor", "").strip()
        nombre_proveedor = request.POST.get("nombre_proveedor", "").strip()
        categoria = request.POST.get("categoria", "otro")
        numero_factura = request.POST.get("numero_factura", "").strip()
        monto = request.POST.get("monto", "0").strip()
        fecha_emision = request.POST.get("fecha_emision", "").strip()
        fecha_vencimiento = request.POST.get("fecha_vencimiento", "").strip()
        observaciones = request.POST.get("observaciones", "").strip()

        # No permitir mezclar categorías entre los módulos Facturas y
        # Proveedores aunque se manipule el POST.
        categorias_validas = [valor for valor, _ in categorias_form]
        if categoria not in categorias_validas:
            categoria = categorias_validas[0] if categorias_validas else "otro"

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
                    "categorias": categorias_form,
                    "categoria_inicial": categoria_inicial,
                    "volver_url": volver_url,
                    "grupo_form": grupo_form,
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
        return redirect(_url_lista_documentos(documento.categoria))

    return render(
        request,
        "negocios/documentos/crear_documento.html",
        {
            "negocio": negocio,
            "proveedores": proveedores,
            "categorias": categorias_form,
            "categoria_inicial": categoria_inicial,
            "volver_url": volver_url,
            "grupo_form": grupo_form,
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
        return redirect(_url_lista_documentos(documento.categoria))

    return render(
        request,
        "negocios/documentos/editar_documento.html",
        {
            "negocio": documento.negocio,
            "documento": documento,
            "proveedores": proveedores,
            "categorias": Documento.CATEGORIAS,
            "volver_url": _url_lista_documentos(documento.categoria),
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
        return redirect(_url_lista_documentos(documento.categoria))

    return render(
        request,
        "negocios/documentos/subir_pdf.html",
        {
            "negocio": documento.negocio,
            "documento": documento,
            "volver_url": _url_lista_documentos(documento.categoria),
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
            monto_pagado_decimal = Decimal(monto_pagado).quantize(
                Decimal("0.01")
            )
            if monto_pagado_decimal <= 0:
                raise ValueError("El monto debe ser mayor a cero.")
            if monto_pagado_decimal > documento.monto_pendiente:
                raise ValueError(
                    f"El pago no puede superar el saldo pendiente "
                    f"(${documento.monto_pendiente})."
                )
        except (InvalidOperation, ValueError, TypeError):
            messages.error(request, "Ingresá un monto válido.")
            return redirect(_url_lista_documentos(documento.categoria))

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
        return redirect(_url_lista_documentos(documento.categoria))

    return render(
        request,
        "negocios/documentos/marcar_pagada.html",
        {
            "negocio": documento.negocio,
            "documento": documento,
            "volver_url": _url_lista_documentos(documento.categoria),
        },
    )


@login_required
def pagar_proveedor(request, proveedor_id):
    """
    Registrar un pago global a un proveedor.

    El pago se aplica a las facturas pendientes de ese proveedor de la
    más antigua a la más nueva (FIFO). Así, si se le debían $100.000 y se
    le paga $150.000, la deuda baja exactamente $150.000 sin importar en
    cuántas facturas esté repartida.
    """
    negocio = _negocio_del_usuario(request.user)
    if negocio is None:
        raise PermissionDenied(
            "No tenés un negocio asociado para registrar pagos."
        )

    proveedor = get_object_or_404(
        Proveedor, pk=proveedor_id, negocio=negocio
    )

    facturas = list(
        _documentos_con_saldo(
            Documento.objects.filter(
                negocio=negocio, proveedor=proveedor, estado="pendiente"
            )
        )
        .filter(saldo_pendiente__gt=0)
        .order_by("fecha_emision", "pk")
    )
    saldo_total = sum(
        (factura.monto_pendiente for factura in facturas), Decimal("0.00")
    )

    if request.method == "POST":
        monto = request.POST.get("monto", "0").strip()
        try:
            monto_decimal = Decimal(monto).quantize(Decimal("0.01"))
            if monto_decimal <= 0:
                raise ValueError("El monto debe ser mayor a cero.")
            if monto_decimal > saldo_total:
                raise ValueError(
                    "El pago no puede superar la deuda total."
                )
        except (InvalidOperation, ValueError, TypeError):
            messages.error(
                request,
                f"Ingresá un monto válido (entre $0,01 y ${saldo_total}).",
            )
            return redirect(
                "negocios:pagar_proveedor", proveedor_id=proveedor.pk
            )

        aplicado = Decimal("0.00")
        with transaction.atomic():
            pendientes = (
                Documento.objects.select_for_update()
                .filter(
                    negocio=negocio,
                    proveedor=proveedor,
                    estado="pendiente",
                )
                .order_by("fecha_emision", "pk")
            )
            restante = monto_decimal
            for factura in pendientes:
                if restante <= 0:
                    break
                saldo_factura = factura.monto - factura.monto_pagado
                if saldo_factura <= 0:
                    continue
                pago = min(saldo_factura, restante)
                factura.monto_pagado += pago
                if factura.monto_pagado >= factura.monto:
                    factura.estado = "pagada"
                factura.save(update_fields=["monto_pagado", "estado"])
                restante -= pago
                aplicado += pago

        registrar_accion(
            request.user,
            "Pago a proveedor",
            f"Pago de ${aplicado} registrado a '{proveedor.nombre}'. "
            f"Deuda restante: ${saldo_total - aplicado}.",
            request,
        )
        messages.success(
            request,
            f"Pago de ${aplicado} registrado a {proveedor.nombre}. "
            f"Deuda restante: ${saldo_total - aplicado}.",
        )
        return redirect(
            f"{reverse('negocios:lista_proveedores')}?proveedor={proveedor.pk}"
        )

    return render(
        request,
        "negocios/documentos/pagar_proveedor.html",
        {
            "negocio": negocio,
            "proveedor": proveedor,
            "facturas": facturas,
            "saldo_total": saldo_total,
        },
    )
