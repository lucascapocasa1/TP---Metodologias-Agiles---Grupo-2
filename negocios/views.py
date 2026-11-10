"""Vistas de la app negocios.

Incluye la vista de landing pública que lista los negocios activos
para que los compradores elijan a cuál entrar, y las vistas de gestión
de documentos (facturas) para cada negocio.
"""
from datetime import timedelta
from decimal import Decimal, InvalidOperation
import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Min, Q, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from auditoria.utils import registrar_accion

from . import services
from .models import Documento, Negocio, Proveedor, PagoDocumento

# Agrupaciones de categorías para los KPIs del dashboard.
GRUPOS_DOCUMENTOS = {
    "proveedores": ["proveedor"],
    "servicios": ["luz", "gas", "seguridad", "otro"],
}

# Pestañas del listado. La vista por defecto muestra solo lo que se debe:
# el admin entra a ver "qué tengo que pagar", no el archivo histórico.
VISTAS_DOCUMENTOS = {
    "por_pagar": "Por pagar",
    "vencidas": "Vencidas",
    "por_vencer": "Esta semana",
    "pagadas": "Pagadas",
    "anuladas": "Anuladas",
    "todas": "Todas",
}

ESTADO_POR_VISTA = {
    "por_pagar": "pendiente",
    "pagadas": "pagada",
    "anuladas": "anulada",
}

VISTA_POR_ESTADO = {
    "pendiente": "por_pagar",
    "pagada": "pagadas",
    "anulada": "anuladas",
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


def _resumen_por_proveedor(documentos, hoy=None):
    """
    Saldo pendiente agrupado por proveedor.

    Devuelve una lista de dicts ordenada de mayor a menor deuda:
        clave, proveedor_id, nombre, saldo, vencido, facturas,
        vencidas, proximo_vencimiento, es_texto

    `clave` es lo que viaja en ``?proveedor=``: el id para los proveedores
    registrados y ``sin:<nombre>`` para los que se cargaron como texto
    suelto (cada nombre es su propia cuenta, no todos juntos).
    """
    hoy = hoy or timezone.localdate()
    saldo_expr = ExpressionWrapper(
        F("monto") - F("monto_pagado"),
        output_field=DecimalField(max_digits=12, decimal_places=2),
    )
    filas = (
        documentos.filter(estado="pendiente")
        .values("proveedor_id", "proveedor__nombre", "nombre_proveedor")
        .annotate(
            saldo=Coalesce(Sum(saldo_expr), Decimal("0.00")),
            vencido=Coalesce(
                Sum(saldo_expr, filter=Q(fecha_vencimiento__lt=hoy)),
                Decimal("0.00"),
            ),
            facturas=Count("id"),
            vencidas=Count(
                "id", filter=Q(fecha_vencimiento__lt=hoy)
            ),
            proximo=Min("fecha_vencimiento"),
        )
    )

    resumen = {}
    for fila in filas:
        nombre = (
            fila["proveedor__nombre"]
            or fila["nombre_proveedor"]
            or "Sin proveedor"
        )
        clave = services.clave_proveedor(
            fila["proveedor_id"], fila["nombre_proveedor"] or nombre
        )
        item = resumen.setdefault(
            clave,
            {
                "clave": clave,
                "proveedor_id": fila["proveedor_id"],
                "nombre": nombre,
                "es_texto": not fila["proveedor_id"],
                "saldo": Decimal("0.00"),
                "vencido": Decimal("0.00"),
                "facturas": 0,
                "vencidas": 0,
                "proximo_vencimiento": None,
            },
        )
        item["saldo"] += fila["saldo"]
        item["vencido"] += fila["vencido"]
        item["facturas"] += fila["facturas"]
        item["vencidas"] += fila["vencidas"]
        proximo = fila["proximo"]
        if proximo and (
            item["proximo_vencimiento"] is None
            or proximo < item["proximo_vencimiento"]
        ):
            item["proximo_vencimiento"] = proximo

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


def _resolver_proveedor(negocio, proveedor_id, proveedor_nuevo):
    """Resuelve el proveedor de un documento a crear.

    - Si se eligió uno de la lista -> devuelve ese Proveedor.
    - Si se escribió un nombre nuevo y no hay ninguno igual en el negocio,
      lo crea (alta inline de proveedor desde el formulario).
    - Si se escribió un nombre que ya existe, devuelve el existente.
    - Si no hay nada, devuelve None.
    """
    if proveedor_id:
        try:
            return Proveedor.objects.get(pk=proveedor_id, negocio=negocio)
        except Proveedor.DoesNotExist:
            return None
    if proveedor_nuevo:
        proveedor, creado = Proveedor.objects.get_or_create(
            nombre=proveedor_nuevo, negocio=negocio,
            defaults={"activo": True},
        )
        return proveedor
    return None


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

    hoy = timezone.localdate()
    limite_alerta = hoy + timedelta(
        days=services.DIAS_ALERTA_VENCIMIENTO
    )

    documentos = _documentos_con_saldo(
        Documento.objects.filter(negocio=negocio)
    )

    estado_param = request.GET.get("estado", "")
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

    # Totales y resumen se calculan sobre todo el alcance del módulo (sin
    # la pestaña ni el filtro de proveedor) para que los números no bailen
    # al navegar.
    totales = services.totales_documentos(documentos, hoy)
    conteos = services.contar_por_vista(documentos, hoy)

    # Pagado este mes: monto real pagado en el mes actual (no cantidad de
    # comprobantes; esa va en el detalle).
    pagos_mes = PagoDocumento.objects.filter(
        negocio=negocio,
        fecha__month=hoy.month,
        fecha__year=hoy.year,
    )
    pagado_mes_monto = pagos_mes.aggregate(total=Sum("monto"))["total"] or Decimal(
        "0.00"
    )
    pagado_mes_cantidad = pagos_mes.count()

    # Deuda por proveedor: solo tiene sentido en Proveedores (y en la
    # vista histórica sin grupo).
    if es_facturas:
        resumen_proveedores = []
    else:
        resumen_proveedores = _resumen_por_proveedor(documentos, hoy)

    # Pestaña activa. Se mantiene compatibilidad con ?estado= de los
    # enlaces viejos.
    vista = request.GET.get("vista", "").strip()
    if vista not in VISTAS_DOCUMENTOS:
        vista = VISTA_POR_ESTADO.get(estado_param, "por_pagar")

    if vista == "por_pagar":
        documentos = documentos.filter(estado="pendiente")
    elif vista == "vencidas":
        documentos = documentos.filter(
            estado="pendiente", fecha_vencimiento__lt=hoy
        )
    elif vista == "por_vencer":
        documentos = documentos.filter(
            estado="pendiente",
            fecha_vencimiento__gte=hoy,
            fecha_vencimiento__lte=limite_alerta,
        )
    elif vista == "pagadas":
        documentos = documentos.filter(estado="pagada")
    elif vista == "anuladas":
        documentos = documentos.filter(estado="anulada")

    proveedor_seleccionado = ""
    if not es_facturas:
        documentos, proveedor_seleccionado = services.filtrar_por_proveedor(
            documentos, proveedor_filtro
        )

    # Ordenamiento: por defecto, por urgencia (vencidas primero).
    campo = ORDEN_DOCUMENTOS.get(orden)
    if campo is None:
        orden = ""
        direccion = ""
        documentos = services.ordenar_por_urgencia(documentos, hoy)
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

    vistas = [
        {
            "clave": clave,
            "etiqueta": etiqueta,
            "cantidad": conteos.get(clave, 0),
            "activa": clave == vista,
        }
        for clave, etiqueta in VISTAS_DOCUMENTOS.items()
    ]

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
        "vistas": vistas,
        "vista_actual": vista,
        "estado_actual": estado_param,
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
        "totales": totales,
        "total_pendiente": conteos["por_pagar"],
        "total_pagada": conteos["pagadas"],
        "pagado_mes_monto": pagado_mes_monto,
        "pagado_mes_cantidad": pagado_mes_cantidad,
        # KPI de deuda: solo lo que realmente se debe, es decir facturas
        # pendientes. Las pagadas ya no adeudan nada (aunque guarden un
        # monto_pagado parcial por pagos incompletos) y las anuladas tampoco.
        "total_deuda": totales["deuda"],
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
        proveedor_nuevo = request.POST.get("proveedor_nuevo", "").strip()
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

        datos_form = {
            "negocio": negocio,
            "proveedores": proveedores,
            "categorias": categorias_form,
            "categoria_inicial": categoria_inicial,
            "volver_url": volver_url,
            "grupo_form": grupo_form,
            "form_data": request.POST,
        }

        try:
            monto_decimal = services.validar_documento(
                monto, fecha_emision, fecha_vencimiento
            )
        except ValueError as error:
            return render(
                request,
                "negocios/documentos/crear_documento.html",
                {**datos_form, "error": str(error)},
            )

        proveedor_obj = _resolver_proveedor(
            negocio, proveedor_id, proveedor_nuevo
        )
        if proveedor_obj is None and not nombre_proveedor:
            # En Proveedores la factura necesita un proveedor identificable.
            if grupo_form == "proveedores":
                return render(
                    request,
                    "negocios/documentos/crear_documento.html",
                    {
                        **datos_form,
                        "error": "Elegí un proveedor o escribí un nombre.",
                    },
                )

        documento = Documento.objects.create(
            negocio=negocio,
            proveedor=proveedor_obj,
            nombre_proveedor=(
                proveedor_obj.nombre if proveedor_obj else nombre_proveedor
            ),
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
        proveedor_nuevo = request.POST.get("proveedor_nuevo", "").strip()
        nombre_proveedor = request.POST.get("nombre_proveedor", "").strip()
        categoria = request.POST.get("categoria", documento.categoria)
        numero_factura = request.POST.get("numero_factura", "").strip()
        monto = request.POST.get("monto", "0").strip()
        fecha_emision = request.POST.get("fecha_emision", "").strip()
        fecha_vencimiento = request.POST.get("fecha_vencimiento", "").strip()
        observaciones = request.POST.get("observaciones", "").strip()

        try:
            monto_decimal = services.validar_documento(
                monto, fecha_emision, fecha_vencimiento,
                monto_pagado=documento.monto_pagado,
            )
        except ValueError as error:
            proveedores = Proveedor.objects.filter(
                negocio=documento.negocio, activo=True
            )
            return render(
                request,
                "negocios/documentos/editar_documento.html",
                {
                    "negocio": documento.negocio,
                    "documento": documento,
                    "proveedores": proveedores,
                    "categorias": Documento.CATEGORIAS,
                    "form_data": request.POST,
                    "error": str(error),
                    "volver_url": _url_lista_documentos(documento.categoria),
                },
            )

        proveedor_obj = _resolver_proveedor(
            documento.negocio, proveedor_id, proveedor_nuevo
        )

        documento.proveedor = proveedor_obj
        documento.nombre_proveedor = (
            proveedor_obj.nombre if proveedor_obj else nombre_proveedor
        )
        documento.categoria = categoria
        documento.numero_factura = numero_factura
        documento.monto = monto_decimal
        documento.fecha_emision = fecha_emision
        documento.fecha_vencimiento = fecha_vencimiento
        documento.observaciones = observaciones
        # El estado se recalcula desde el saldo (respetando si fue anulada).
        services.actualizar_estado(documento)
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
def subir_adjunto(request, documento_id):
    """
    Subir un adjunto (PDF o imagen) para un documento existente.

    Se aceptan PDF, JPG y PNG con un tamaño máximo de 5 MB.
    """
    documento = get_object_or_404(Documento, pk=documento_id)
    if documento.negocio_id != _negocio_del_usuario(request.user).id:
        raise PermissionDenied(
            "No tenés permiso para editar este documento."
        )

    EXTENSIONES_PERMITIDAS = (".pdf", ".jpg", ".jpeg", ".png")
    TAMANIO_MAXIMO = 5 * 1024 * 1024  # 5 MB

    if request.method == "POST" and request.FILES.get("archivo"):
        archivo = request.FILES["archivo"]
        nombre = archivo.name.lower()

        if not nombre.endswith(EXTENSIONES_PERMITIDAS):
            messages.error(
                request,
                "Solo se permiten archivos PDF, JPG y PNG.",
            )
            return render(
                request,
                "negocios/documentos/subir_adjunto.html",
                {
                    "negocio": documento.negocio,
                    "documento": documento,
                    "volver_url": _url_lista_documentos(documento.categoria),
                },
            )

        if archivo.size > TAMANIO_MAXIMO:
            messages.error(
                request,
                "El archivo no puede superar los 5 MB.",
            )
            return render(
                request,
                "negocios/documentos/subir_adjunto.html",
                {
                    "negocio": documento.negocio,
                    "documento": documento,
                    "volver_url": _url_lista_documentos(documento.categoria),
                },
            )

        documento.archivo = archivo
        documento.save()
        tipo = "imagen" if nombre.endswith((".jpg", ".jpeg", ".png")) else "PDF"
        registrar_accion(
            request.user,
            "Adjunto subido",
            f"{tipo} subido para documento '{documento.numero_factura or documento.nombre_proveedor}'.",
            request,
        )
        messages.success(
            request,
            f"{tipo} subido correctamente.",
        )
        return redirect(_url_lista_documentos(documento.categoria))

    return render(
        request,
        "negocios/documentos/subir_adjunto.html",
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
        fecha_pago = request.POST.get("fecha_pago", "").strip()
        metodo_pago = request.POST.get("metodo_pago", "efectivo").strip()
        nota_pago = request.POST.get("nota_pago", "").strip()

        try:
            monto_decimal = Decimal(monto_pagado).quantize(
                Decimal("0.01")
            )
            if monto_decimal <= 0:
                raise ValueError("El monto debe ser mayor a cero.")
        except (InvalidOperation, ValueError, TypeError):
            messages.error(request, "Ingresá un monto válido.")
            return redirect(_url_lista_documentos(documento.categoria))

        try:
            with transaction.atomic():
                services.registrar_pago(
                    documento,
                    monto_decimal,
                    metodo=metodo_pago,
                    usuario=request.user,
                    nota=nota_pago,
                )
        except ValueError as error:
            messages.error(request, str(error))
            return redirect(_url_lista_documentos(documento.categoria))

        documento.refresh_from_db()
        registrar_accion(
            request.user,
            "Pago registrado",
            f"Pago de ${monto_decimal} registrado para documento '{documento.numero_factura or documento.nombre_proveedor}'. Saldo pendiente: ${documento.monto_pendiente}.",
            request,
        )
        messages.success(
            request,
            f"Pago de ${monto_decimal} registrado. Saldo pendiente: ${documento.monto_pendiente}.",
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
    más antigua a la más nueva (FIFO). En esta versión el FIFO se ordena
    por fecha de vencimiento (la más próxima primero), no por fecha de
    emisión. En GET con ``?monto=X`` se muestra una previsualización del
    reparto sin aplicar nada.
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
        .order_by("fecha_vencimiento", "pk")
    )
    saldo_total = sum(
        (factura.monto_pendiente for factura in facturas), Decimal("0.00")
    )

    # Previsualización del reparto FIFO (solo GET con ?monto=).
    preview = None
    monto_preview = request.GET.get("monto", "").strip()
    if monto_preview:
        try:
            monto_decimal = Decimal(monto_preview).quantize(
                Decimal("0.01")
            )
            if monto_decimal <= 0:
                raise ValueError()
        except (InvalidOperation, ValueError, TypeError):
            monto_decimal = None
        if monto_decimal is not None:
            if monto_decimal > saldo_total:
                preview = {
                    "monto": monto_decimal,
                    "error": "El pago no puede superar la deuda total.",
                    "reparto": [],
                }
            else:
                restante = monto_decimal
                reparto = []
                for factura in facturas:
                    if restante <= 0:
                        break
                    saldo_factura = factura.monto - factura.monto_pagado
                    if saldo_factura <= 0:
                        continue
                    pago = min(saldo_factura, restante)
                    reparto.append(
                        {
                            "documento": factura,
                            "pago": pago,
                            "saldo_despues": saldo_factura - pago,
                            "quedara_pagada": saldo_factura - pago <= 0,
                        }
                    )
                    restante -= pago
                preview = {
                    "monto": monto_decimal,
                    "reparto": reparto,
                    "sobrante": restante,
                }

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
        detalle = []
        with transaction.atomic():
            pendientes = (
                Documento.objects.select_for_update()
                .filter(
                    negocio=negocio,
                    proveedor=proveedor,
                    estado="pendiente",
                )
                .order_by("fecha_vencimiento", "pk")
            )
            restante = monto_decimal
            grupo_pago = uuid.uuid4()
            for factura in pendientes:
                if restante <= 0:
                    break
                saldo_factura = factura.monto - factura.monto_pagado
                if saldo_factura <= 0:
                    continue
                pago = min(saldo_factura, restante)
                try:
                    services.registrar_pago(
                        factura,
                        pago,
                        fecha=timezone.localdate(),
                        metodo="transferencia",
                        usuario=request.user,
                        nota=f"Pago FIFO a {proveedor.nombre}",
                        grupo_pago=grupo_pago,
                    )
                except ValueError:
                    continue
                detalle.append((factura.numero_factura or factura.nombre_proveedor, pago))
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
            "preview": preview,
        },
    )


@login_required
def crear_proveedor(request):
    """Alta de un proveedor (solo administradores del negocio)."""
    negocio = _negocio_del_usuario(request.user)
    if negocio is None:
        raise PermissionDenied(
            "No tenés un negocio asociado para crear proveedores."
        )

    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        telefono = request.POST.get("telefono", "").strip()
        email = request.POST.get("email", "").strip()

        if not nombre:
            messages.error(request, "Ingresá el nombre del proveedor.")
            return render(
                request,
                "negocios/documentos/crear_proveedor.html",
                {"negocio": negocio, "volver_url": reverse("negocios:lista_proveedores")},
            )

        try:
            proveedor = Proveedor.objects.create(
                nombre=nombre,
                negocio=negocio,
                telefono=telefono,
                email=email,
                activo=True,
            )
        except Exception:
            messages.error(
                request, "Ya existe un proveedor con ese nombre en este negocio."
            )
            return render(
                request,
                "negocios/documentos/crear_proveedor.html",
                {
                    "negocio": negocio,
                    "volver_url": reverse("negocios:lista_proveedores"),
                    "form_data": request.POST,
                },
            )

        registrar_accion(
            request.user,
            "Proveedor creado",
            f"Proveedor '{proveedor.nombre}' creado.",
            request,
        )
        messages.success(
            request, f"Proveedor '{proveedor.nombre}' creado correctamente."
        )
        return redirect("negocios:lista_proveedores")

    return render(
        request,
        "negocios/documentos/crear_proveedor.html",
        {
            "negocio": negocio,
            "volver_url": reverse("negocios:lista_proveedores"),
        },
    )


@login_required
def editar_proveedor(request, proveedor_id):
    """Edición de un proveedor existente."""
    negocio = _negocio_del_usuario(request.user)
    if negocio is None:
        raise PermissionDenied(
            "No tenés un negocio asociado para editar proveedores."
        )
    proveedor = get_object_or_404(Proveedor, pk=proveedor_id, negocio=negocio)

    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        telefono = request.POST.get("telefono", "").strip()
        email = request.POST.get("email", "").strip()
        activo = request.POST.get("activo") == "on"

        if not nombre:
            messages.error(request, "Ingresá el nombre del proveedor.")
            return render(
                request,
                "negocios/documentos/editar_proveedor.html",
                {
                    "negocio": negocio,
                    "proveedor": proveedor,
                    "volver_url": reverse("negocios:detalle_proveedor", args=[proveedor.pk]),
                },
            )

        proveedor.nombre = nombre
        proveedor.telefono = telefono
        proveedor.email = email
        proveedor.activo = activo
        proveedor.save()

        registrar_accion(
            request.user,
            "Proveedor editado",
            f"Proveedor '{proveedor.nombre}' editado.",
            request,
        )
        messages.success(
            request, f"Proveedor '{proveedor.nombre}' actualizado correctamente."
        )
        return redirect("negocios:detalle_proveedor", proveedor_id=proveedor.pk)

    return render(
        request,
        "negocios/documentos/editar_proveedor.html",
        {
            "negocio": negocio,
            "proveedor": proveedor,
            "volver_url": reverse("negocios:detalle_proveedor", args=[proveedor.pk]),
        },
    )


@login_required
def detalle_proveedor(request, proveedor_id):
    """Ficha de un proveedor: facturas pendientes, pagadas y saldo."""
    negocio = _negocio_del_usuario(request.user)
    if negocio is None:
        raise PermissionDenied(
            "No tenés un negocio asociado para ver el detalle de un proveedor."
        )
    proveedor = get_object_or_404(Proveedor, pk=proveedor_id, negocio=negocio)

    documentos = _documentos_con_saldo(
        Documento.objects.filter(negocio=negocio, proveedor=proveedor)
    ).order_by("-fecha_vencimiento")

    hoy = timezone.localdate()
    pendientes = documentos.filter(estado="pendiente")
    saldo = services._suma_saldo(pendientes)
    vencido = services._suma_saldo(
        pendientes.filter(fecha_vencimiento__lt=hoy)
    )

    # Historial de pagos del proveedor, agrupado por operación (grupo_pago).
    pagos_qs = (
        PagoDocumento.objects.filter(negocio=negocio, documento__proveedor=proveedor)
        .select_related("documento", "usuario")
        .order_by("-fecha", "-fecha_creacion")
    )
    pagos_agrupados = {}
    pagos_individuales = []
    for pago in pagos_qs:
        clave = str(pago.grupo_pago) if pago.grupo_pago else None
        if clave:
            pagos_agrupados.setdefault(clave, []).append(pago)
        else:
            pagos_individuales.append(pago)

    return render(
        request,
        "negocios/documentos/detalle_proveedor.html",
        {
            "negocio": negocio,
            "proveedor": proveedor,
            "documentos": documentos,
            "saldo": saldo,
            "vencido": vencido,
            "pagos_agrupados": pagos_agrupados,
            "pagos_individuales": pagos_individuales,
            "volver_url": reverse("negocios:lista_proveedores"),
        },
    )


@login_required
def anular_documento(request, documento_id):
    """Anular un documento (deja de contar como deuda)."""
    negocio = _negocio_del_usuario(request.user)
    if negocio is None:
        raise PermissionDenied(
            "No tenés un negocio asociado para anular documentos."
        )
    documento = get_object_or_404(Documento, pk=documento_id)
    if documento.negocio_id != negocio.id:
        raise PermissionDenied(
            "No tenés permiso para anular este documento."
        )

    if request.method == "POST":
        motivo = request.POST.get("motivo_anulacion", "").strip()
        services.anular_documento(documento, motivo=motivo)
        registrar_accion(
            request.user,
            "Documento anulado",
            f"Documento '{documento.numero_factura or documento.nombre_proveedor}' anulado. Motivo: {motivo or '-'}",
            request,
        )
        messages.success(
            request, "Documento anulado. Ya no cuenta como deuda."
        )
        return redirect(_url_lista_documentos(documento.categoria))

    return render(
        request,
        "negocios/documentos/anular_documento.html",
        {
            "negocio": negocio,
            "documento": documento,
            "volver_url": _url_lista_documentos(documento.categoria),
        },
    )


@login_required
def reactivar_documento(request, documento_id):
    """Reactivar un documento anulado (vuelve al estado del saldo)."""
    negocio = _negocio_del_usuario(request.user)
    if negocio is None:
        raise PermissionDenied(
            "No tenés un negocio asociado para reactivar documentos."
        )
    documento = get_object_or_404(Documento, pk=documento_id)
    if documento.negocio_id != negocio.id:
        raise PermissionDenied(
            "No tenés permiso para reactivar este documento."
        )

    if request.method == "POST":
        services.reactivar_documento(documento)
        registrar_accion(
            request.user,
            "Documento reactivado",
            f"Documento '{documento.numero_factura or documento.nombre_proveedor}' reactivado.",
            request,
        )
        messages.success(
            request, "Documento reactivado."
        )
        return redirect(_url_lista_documentos(documento.categoria))

    return redirect(_url_lista_documentos(documento.categoria))


@login_required
def convertir_en_proveedor(request, documento_id):
    """
    Convierte una factura con nombre de proveedor escrito a mano en un
    Proveedor real, reasignando todas las facturas de ese nombre.
    """
    negocio = _negocio_del_usuario(request.user)
    if negocio is None:
        raise PermissionDenied(
            "No tenés un negocio asociado para convertir proveedores."
        )
    documento = get_object_or_404(Documento, pk=documento_id)
    if documento.negocio_id != negocio.id:
        raise PermissionDenied(
            "No tenés permiso para modificar este documento."
        )

    nombre_texto = (documento.nombre_proveedor or "").strip()
    if not nombre_texto or documento.proveedor_id:
        messages.error(
            request, "Este documento ya tiene un proveedor asignado."
        )
        return redirect(_url_lista_documentos(documento.categoria))

    if request.method == "POST":
        proveedor, creado = Proveedor.objects.get_or_create(
            nombre=nombre_texto, negocio=negocio,
            defaults={"activo": True},
        )
        Documento.objects.filter(
            negocio=negocio, proveedor__isnull=True,
            nombre_proveedor__iexact=nombre_texto,
        ).update(proveedor=proveedor)

        registrar_accion(
            request.user,
            "Nombre convertido en proveedor",
            f"'{nombre_texto}' convertido en proveedor y sus facturas reasignadas.",
            request,
        )
        messages.success(
            request,
            f"'{nombre_texto}' ahora es un proveedor registrado. "
            f"Todas sus facturas fueron reasignadas.",
        )
        return redirect("negocios:detalle_proveedor", proveedor_id=proveedor.pk)

    cantidad = Documento.objects.filter(
        negocio=negocio, proveedor__isnull=True,
        nombre_proveedor__iexact=nombre_texto,
    ).count()
    return render(
        request,
        "negocios/documentos/convertir_en_proveedor.html",
        {
            "negocio": negocio,
            "documento": documento,
            "nombre_texto": nombre_texto,
            "cantidad": cantidad,
            "volver_url": _url_lista_documentos(documento.categoria),
        },
    )


@login_required
def deshacer_pago_grupo(request, grupo_pago):
    """
    Deshace una operación de pago completa (grupo_pago), p. ej. un pago FIFO
    a un proveedor repartido en varias facturas.

    Solo accesible por POST. Redirige al detalle del proveedor afectado o,
    si no se puede determinar, al listado de proveedores.
    """
    negocio = _negocio_del_usuario(request.user)
    if negocio is None:
        raise PermissionDenied(
            "No tenés un negocio asociado para deshacer pagos."
        )

    if request.method != "POST":
        return redirect("negocios:lista_proveedores")

    grupo_pago = str(grupo_pago)
    pagos = list(
        PagoDocumento.objects.filter(
            grupo_pago=grupo_pago, negocio=negocio
        ).select_related("documento")
    )
    if not pagos:
        messages.error(request, "No se encontró esa operación de pago.")
        return redirect("negocios:lista_proveedores")

    proveedor_id = pagos[0].documento.proveedor_id
    documentos_afectados = services.deshacer_pago(grupo_pago)

    registrar_accion(
        request.user,
        "Pago deshecho",
        f"Operación {grupo_pago} deshecha: {len(pagos)} pago(s) revertido(s).",
        request,
    )
    messages.success(
        request,
        f"Operación de pago deshecha. Se revirtieron {len(pagos)} pago(s).",
    )
    if proveedor_id:
        return redirect("negocios:detalle_proveedor", proveedor_id=proveedor_id)
    return redirect("negocios:lista_proveedores")
