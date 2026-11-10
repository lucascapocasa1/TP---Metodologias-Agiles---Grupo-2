"""Reglas de negocio de documentos (facturas) y proveedores.

Todo lo que decide *cuánto se debe*, *si está vencido* y *cómo se aplica un
pago* vive acá. Las vistas solo orquestan: así la misma regla se usa en el
listado, en el dashboard y en los formularios, y no hay dos definiciones de
"pendiente" que se contradigan.

Criterios:

1. El estado (`pendiente` / `pagada`) es **derivado**: se recalcula desde el
   saldo cada vez que algo lo toca (crear, editar, pagar). `anulada` es la
   única excepción: es una decisión del usuario y se respeta.
2. "Vencida" se mide sobre el **saldo**, no sobre el estado. Una factura de
   $100.000 con $60.000 pagados y vencida ayer sigue vencida por $40.000.
3. Los importes nunca quedan negativos ni por encima del total.
"""
from datetime import timedelta
from decimal import Decimal, InvalidOperation
import uuid

from django.db import transaction
from django.db.models import (
    Case,
    DecimalField,
    ExpressionWrapper,
    F,
    IntegerField,
    Q,
    Sum,
    Value,
    When,
)
from django.utils import timezone

from .models import Documento, PagoDocumento

# Días de anticipación con los que se avisa un vencimiento.
# Un solo valor para el dashboard, el listado y los badges.
DIAS_ALERTA_VENCIMIENTO = 7

# Estados en los que el documento todavía representa una deuda.
ESTADOS_CON_DEUDA = ("pendiente",)

CERO = Decimal("0.00")


# ========== Importes y situación ==========


def saldo(documento):
    """Cuánto falta pagar de un documento (nunca menor a cero)."""
    diferencia = (documento.monto or CERO) - (documento.monto_pagado or CERO)
    return diferencia if diferencia > 0 else CERO


def situacion(documento, hoy=None):
    """Situación de pago de un documento, pensada para la UI.

    Devuelve una de: ``pagada``, ``anulada``, ``vencida``, ``vence_hoy``,
    ``por_vencer`` o ``al_dia``. Se calcula siempre; nunca se guarda.
    """
    if documento.estado == "anulada":
        return "anulada"
    if saldo(documento) <= 0:
        return "pagada"

    hoy = hoy or timezone.localdate()
    dias = (documento.fecha_vencimiento - hoy).days
    if dias < 0:
        return "vencida"
    if dias == 0:
        return "vence_hoy"
    if dias <= DIAS_ALERTA_VENCIMIENTO:
        return "por_vencer"
    return "al_dia"


def dias_para_vencer(documento, hoy=None):
    """Días que faltan (negativo si ya venció)."""
    hoy = hoy or timezone.localdate()
    return (documento.fecha_vencimiento - hoy).days


def etiqueta_vencimiento(documento, hoy=None):
    """Texto corto y claro para la columna de vencimiento.

    'Vencida hace 5 días' dice mucho más que un badge rojo con la fecha.
    """
    dias = dias_para_vencer(documento, hoy)
    if dias == 0:
        return "Vence hoy"
    if dias == 1:
        return "Vence mañana"
    if dias > 1:
        return f"Vence en {dias} días"
    if dias == -1:
        return "Venció ayer"
    return f"Vencida hace {abs(dias)} días"


def etiqueta_situacion(documento, hoy=None):
    """Nombre legible de la situación (para badges y filtros)."""
    return {
        "pagada": "Pagada",
        "anulada": "Anulada",
        "vencida": "Vencida",
        "vence_hoy": "Vence hoy",
        "por_vencer": "Por vencer",
        "al_dia": "Al día",
    }[situacion(documento, hoy)]


# ========== Estado derivado ==========


def estado_calculado(documento):
    """Estado que corresponde según el saldo, respetando la anulación."""
    if documento.estado == "anulada":
        return "anulada"
    return "pagada" if saldo(documento) <= 0 else "pendiente"


def actualizar_estado(documento, guardar=True):
    """Normaliza el estado desde el saldo. Devuelve el estado resultante."""
    nuevo = estado_calculado(documento)
    if documento.estado != nuevo:
        documento.estado = nuevo
        if guardar and documento.pk:
            documento.save(update_fields=["estado"])
    return nuevo


def validar_documento(monto, fecha_emision, fecha_vencimiento, monto_pagado=CERO):
    """Valida los datos de un documento y devuelve el monto como Decimal.

    Lanza ``ValueError`` con un mensaje listo para mostrar al usuario.
    """
    try:
        monto_decimal = Decimal(str(monto)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("Ingresá un monto válido.")

    if monto_decimal <= 0:
        raise ValueError("El monto debe ser mayor a cero.")
    if monto_pagado and monto_decimal < monto_pagado:
        raise ValueError(
            "El monto no puede ser menor a lo ya pagado "
            f"(${monto_pagado})."
        )
    if fecha_emision and fecha_vencimiento and fecha_vencimiento < fecha_emision:
        raise ValueError(
            "La fecha de vencimiento no puede ser anterior a la de emisión."
        )
    return monto_decimal


# ========== Pagos ==========


def registrar_pago(
    documento,
    monto,
    fecha=None,
    metodo="efectivo",
    usuario=None,
    nota="",
    comprobante=None,
    grupo_pago=None,
):
    """Registra un pago (parcial o total) sobre un documento.

    En esta etapa alcanza con actualizar el saldo y el estado; el registro
    histórico del pago se agrega en la etapa de pagos con historial. La
    firma ya contempla todos los datos para no tener que cambiarla después.
    """
    if documento.estado == "anulada":
        raise ValueError("No se puede pagar un documento anulado.")

    pendiente = saldo(documento)
    if pendiente <= 0:
        raise ValueError("Este documento ya está pago.")

    try:
        monto_decimal = Decimal(str(monto)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("Ingresá un monto válido.")

    if monto_decimal <= 0:
        raise ValueError("El monto debe ser mayor a cero.")
    if monto_decimal > pendiente:
        raise ValueError(
            f"El pago no puede superar el saldo pendiente (${pendiente})."
        )

    documento.monto_pagado = (documento.monto_pagado or CERO) + monto_decimal
    actualizar_estado(documento, guardar=False)
    fecha_pago = fecha or timezone.localdate()
    with transaction.atomic():
        documento.save(update_fields=["monto_pagado", "estado"])
        PagoDocumento.objects.create(
            documento=documento,
            negocio=documento.negocio,
            fecha=fecha_pago,
            monto=monto_decimal,
            metodo=metodo,
            usuario=usuario,
            nota=nota,
            comprobante=comprobante,
            grupo_pago=grupo_pago,
        )
    return monto_decimal


# ========== Anulación ==========


def anular_documento(documento, motivo=""):
    """Marca el documento como anulado (deja de contar como deuda)."""
    documento.estado = "anulada"
    campos = ["estado"]
    if hasattr(documento, "motivo_anulacion"):
        documento.motivo_anulacion = (motivo or "").strip()
        campos.append("motivo_anulacion")
    documento.save(update_fields=campos)
    return documento


def reactivar_documento(documento):
    """Saca la anulación y vuelve al estado que marque el saldo."""
    if documento.estado != "anulada":
        return documento
    documento.estado = "pendiente"
    campos = ["estado"]
    if hasattr(documento, "motivo_anulacion"):
        documento.motivo_anulacion = ""
        campos.append("motivo_anulacion")
    documento.estado = estado_calculado(documento)
    documento.save(update_fields=campos)
    return documento


def aplicar_pago_proveedor(proveedor, monto, fecha=None, metodo="transferencia",
                           usuario=None, nota="", grupo_pago=None):
    """
    Aplica un pago a un proveedor usando FIFO por fecha de vencimiento.

    Devuelve un dict con:
      - aplicado: monto total aplicado
      - detalle: lista de (documento, pago_aplicado, saldo_despues, pago_completo)
      - sobrante: monto que no se pudo aplicar (debe ser 0 si se validó antes)

    Cada pago genera su PagoDocumento con el mismo `grupo_pago`, para poder
    mostrar la operación como un solo movimiento y deshacerla completa.
    """
    fecha_pago = fecha or timezone.localdate()
    if grupo_pago is None:
        grupo_pago = uuid.uuid4()

    pendientes = list(
        Documento.objects.select_for_update()
        .filter(
            negocio=proveedor.negocio,
            proveedor=proveedor,
            estado="pendiente",
        )
        .order_by("fecha_vencimiento", "pk")
    )

    detalle = []
    aplicado = CERO
    restante = monto
    with transaction.atomic():
        for factura in pendientes:
            if restante <= 0:
                break
            saldo_factura = factura.monto - factura.monto_pagado
            if saldo_factura <= 0:
                continue
            pago = min(saldo_factura, restante)
            monto_aplicado = registrar_pago(
                factura,
                pago,
                fecha=fecha_pago,
                metodo=metodo,
                usuario=usuario,
                nota=nota or f"Pago FIFO a {proveedor.nombre}",
                comprobante=None,
                grupo_pago=grupo_pago,
            )
            detalle.append(
                {
                    "documento": factura,
                    "pago": monto_aplicado,
                    "saldo_despues": factura.monto - factura.monto_pagado,
                    "pago_completo": factura.monto - factura.monto_pagado <= 0,
                }
            )
            restante -= pago
            aplicado += monto_aplicado

    return {
        "grupo_pago": grupo_pago,
        "aplicado": aplicado,
        "sobrante": restante,
        "detalle": detalle,
    }


def deshacer_pago(grupo_pago):
    """
    Deshace todos los pagos de un grupo (p. ej. una operación FIFO).

    Borra los PagoDocumento del grupo, recalcula monto_pagado y estado de
    cada documento afectado, y devuelve la lista de documentos tocados.
    """
    from django.db.models import Sum

    pagos = list(
        PagoDocumento.objects.filter(grupo_pago=grupo_pago).select_related(
            "documento"
        )
    )
    if not pagos:
        return []

    documentos_tocados = {p.documento_id: p.documento for p in pagos}
    with transaction.atomic():
        for pago in pagos:
            pago.delete()
        for documento in documentos_tocados.values():
            total_pagado = (
                documento.pagos_registrados.aggregate(
                    total=Sum("monto")
                )["total"]
                or CERO
            )
            documento.monto_pagado = total_pagado
            actualizar_estado(documento, guardar=False)
            documento.save(update_fields=["monto_pagado", "estado"])
    return list(documentos_tocados.values())


# ========== Totales para la banda de resumen ==========


def _suma_saldo(queryset):
    """Suma (monto - monto_pagado) sin traer las filas a Python."""
    return queryset.aggregate(
        total=Sum(
            ExpressionWrapper(
                F("monto") - F("monto_pagado"),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        )
    )["total"] or CERO


def totales_documentos(documentos, hoy=None):
    """Totales de la banda superior: deuda, vencido, por vencer y pagado.

    Se calculan sobre el queryset *sin* el filtro de vista, para que los
    números no cambien al cambiar de pestaña.
    """
    hoy = hoy or timezone.localdate()
    limite = hoy + timedelta(days=DIAS_ALERTA_VENCIMIENTO)

    pendientes = documentos.filter(estado="pendiente")
    deuda = _suma_saldo(pendientes)
    vencido = _suma_saldo(pendientes.filter(fecha_vencimiento__lt=hoy))
    por_vencer = _suma_saldo(
        pendientes.filter(
            fecha_vencimiento__gte=hoy, fecha_vencimiento__lte=limite
        )
    )

    return {
        "deuda": deuda,
        "vencido": vencido,
        "por_vencer": por_vencer,
        "cantidad_vencidas": pendientes.filter(
            fecha_vencimiento__lt=hoy
        ).count(),
        "cantidad_por_vencer": pendientes.filter(
            fecha_vencimiento__gte=hoy, fecha_vencimiento__lte=limite
        ).count(),
    }


def contar_por_vista(documentos, hoy=None):
    """Cantidad de documentos en cada pestaña del listado."""
    hoy = hoy or timezone.localdate()
    limite = hoy + timedelta(days=DIAS_ALERTA_VENCIMIENTO)
    pendientes = documentos.filter(estado="pendiente")

    return {
        "por_pagar": pendientes.count(),
        "vencidas": pendientes.filter(fecha_vencimiento__lt=hoy).count(),
        "por_vencer": pendientes.filter(
            fecha_vencimiento__gte=hoy, fecha_vencimiento__lte=limite
        ).count(),
        "pagadas": documentos.filter(estado="pagada").count(),
        "anuladas": documentos.filter(estado="anulada").count(),
        "todas": documentos.count(),
    }


# ========== Proveedores ==========


def clave_proveedor(proveedor_id, nombre_texto):
    """Clave estable para agrupar deuda por proveedor.

    Antes, todas las facturas con el nombre escrito a mano caían en una
    única clave ``"sin"`` y se mezclaban en una sola tarjeta (con el nombre
    de la primera fila que saliera). Ahora cada nombre suelto es su propia
    cuenta (``sin:<nombre>``) y el filtro del listado entiende ese formato.
    """
    if proveedor_id:
        return str(proveedor_id)
    nombre = (nombre_texto or "").strip().lower()
    if not nombre:
        return "sin"
    return f"sin:{nombre}"


def filtrar_por_proveedor(queryset, filtro):
    """Aplica el filtro ``?proveedor=`` del listado.

    Acepta el id de un proveedor, ``sin`` (todos los nombres sueltos) o
    ``sin:<nombre>`` (un nombre suelto en particular, sin distinguir
    mayúsculas).
    """
    filtro = (filtro or "").strip()
    if not filtro:
        return queryset, ""
    if filtro == "sin":
        return queryset.filter(proveedor__isnull=True), "sin"
    if filtro.startswith("sin:"):
        nombre = filtro[4:].strip()
        if not nombre:
            return queryset.filter(proveedor__isnull=True), "sin"
        return (
            queryset.filter(proveedor__isnull=True, nombre_proveedor__iexact=nombre),
            filtro,
        )
    if filtro.isdigit():
        return queryset.filter(proveedor_id=int(filtro)), filtro
    return queryset, ""


def nombre_proveedor_de(documento):
    """Nombre a mostrar para el proveedor de un documento."""
    if documento.proveedor_id:
        return documento.proveedor.nombre
    return (documento.nombre_proveedor or "").strip()


def ordenar_por_urgencia(queryset, hoy=None):
    """Ordena la deuda como se mira en la vida real.

    1. Vencidas, la más vieja primero.
    2. Por vencer, la más próxima primero.
    3. Pendientes con vencimiento lejano.
    4. Pagadas y anuladas al final.
    """
    hoy = hoy or timezone.localdate()
    limite = hoy + timedelta(days=DIAS_ALERTA_VENCIMIENTO)
    return queryset.annotate(
        prioridad=Case(
            When(
                Q(estado="pendiente") & Q(fecha_vencimiento__lt=hoy),
                then=Value(0),
            ),
            When(
                Q(estado="pendiente")
                & Q(fecha_vencimiento__gte=hoy)
                & Q(fecha_vencimiento__lte=limite),
                then=Value(1),
            ),
            When(estado="pendiente", then=Value(2)),
            When(estado="pagada", then=Value(3)),
            default=Value(4),
            output_field=IntegerField(),
        )
    ).order_by("prioridad", "fecha_vencimiento", "-pk")
