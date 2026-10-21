"""Lógica de fidelidad de clientes (HU-12): puntos por compras, y cuenta
corriente (HU-14): fiar y cobrar deuda.

El cliente elegido en el cobro vive en la sesión del navegador
(`request.session["cliente_id"]`), igual que el carrito: no se persiste
ningún vínculo hasta que el cajero confirma la venta.
"""
from decimal import Decimal
import unicodedata

from django.db import transaction
from django.db.models import F, Q

from usuarios.templatetags.formatos import montos

from .models import Cliente, PagoCuentaCorriente

CLAVE_CLIENTE = "cliente_id"
PUNTOS_POR_PESO = 100  # 1 punto por cada $100 comprados
MIN_CARACTERES_BUSQUEDA = 2  # con menos no se busca: es ruido, no ayuda
MAX_RESULTADOS_BUSQUEDA = 8
MAX_CLIENTES_REVISADOS = 500  # tope del repaso sin acentos (es un kiosco)


class ErrorCuentaCorriente(Exception):
    """Error de negocio de la cuenta corriente (HU-14)."""


def puntos_por_monto(monto):
    """$30.500 → 305 puntos. Siempre redondea hacia abajo."""
    if monto in (None, ""):
        return 0
    return int(Decimal(str(monto)) // PUNTOS_POR_PESO)


def guardar_cliente_en_sesion(request, cliente):
    request.session[CLAVE_CLIENTE] = cliente.pk
    request.session.modified = True


def quitar_cliente_de_sesion(request):
    request.session.pop(CLAVE_CLIENTE, None)
    request.session.modified = True


def cliente_de_sesion(request):
    """Cliente activo asociado a la venta en curso, o None.

    Si el cliente quedó dado de baja o eliminado, limpia la sesión para
    que el cobro no siga apuntando a un cliente que ya no existe.
    """
    cliente_id = request.session.get(CLAVE_CLIENTE)
    if not cliente_id:
        return None
    cliente = Cliente.objects.filter(pk=cliente_id, activo=True).first()
    if cliente is None:
        quitar_cliente_de_sesion(request)
    return cliente


def cliente_para_venta(request):
    """Como `cliente_de_sesion`, pero con bloqueo de fila.

    Debe llamarse dentro de la transacción de `confirmar_venta` para que
    dos cobros simultáneos no lean/escriban los puntos a la vez.
    """
    cliente_id = request.session.get(CLAVE_CLIENTE)
    if not cliente_id:
        return None
    cliente = (
        Cliente.objects.select_for_update()
        .filter(pk=cliente_id, activo=True)
        .first()
    )
    if cliente is None:
        quitar_cliente_de_sesion(request)
    return cliente


def cliente_bloqueado(cliente):
    """Como `cliente_para_venta`, pero para un cliente que ya se eligió
    (por ejemplo, el de un pedido de WhatsApp que se entrega en el local).

    Devuelve el cliente con la fila bloqueada, para que dos cobros
    simultáneos no accumulen puntos ni deuda a la vez. Si no hay cliente,
    devuelve None.
    """
    if cliente is None:
        return None
    return Cliente.objects.select_for_update().get(pk=cliente.pk)


def _sin_acentos(texto):
    """'Méndez' → 'mendez'.

    En el mostrador nadie escribe los acentos: el cajero tipea "mendez" o
    "costa" y tiene que encontrar al cliente igual. Postgres compara los
    acentos, así que la búsqueda exacta no alcanza y hace falta un segundo
    repaso sin acentos.
    """
    descompuesto = unicodedata.normalize("NFKD", texto or "")
    return "".join(
        caracter for caracter in descompuesto if not unicodedata.combining(caracter)
    ).lower()


def buscar_clientes(consulta):
    """Busca clientes activos por DNI, nombre o apellido.

    La usan el POS (asociar cliente a la venta en curso) y el panel de
    pedidos (cobrar la entrega de un pedido de WhatsApp): es la misma
    búsqueda en los dos lados, así que el kiosquero no ve dos criterios
    distintos para encontrar a un cliente.

    Busca **sin acentos** además de la búsqueda literal: en el mostrador
    nadie escribe tildes, así que "perez" tiene que encontrar a "Pérez".

    Con menos de `MIN_CARACTERES_BUSQUEDA` letras no devuelve nada: con una
    sola letra la lista es larguísima y no ayuda a encontrar a nadie.
    """
    consulta = (consulta or "").strip()
    if len(consulta) < MIN_CARACTERES_BUSQUEDA:
        return []

    coincidencias = list(
        Cliente.objects.filter(activo=True)
        .filter(
            Q(dni__icontains=consulta)
            | Q(nombre__icontains=consulta)
            | Q(apellido__icontains=consulta)
        )
        .order_by("apellido", "nombre")
    )

    consulta_normalizada = _sin_acentos(consulta)
    if not consulta_normalizada:
        return coincidencias[:MAX_RESULTADOS_BUSQUEDA]

    # Segundo repaso: sin acentos y en minúsculas.
    vistos = {cliente.pk for cliente in coincidencias}
    candidatos = (
        Cliente.objects.filter(activo=True)
        .order_by("apellido", "nombre")[:MAX_CLIENTES_REVISADOS]
    )
    for cliente in candidatos:
        if cliente.pk in vistos:
            continue
        if (
            consulta_normalizada in _sin_acentos(cliente.dni)
            or consulta_normalizada in _sin_acentos(cliente.nombre)
            or consulta_normalizada in _sin_acentos(cliente.apellido)
        ):
            coincidencias.append(cliente)
            vistos.add(cliente.pk)

    return coincidencias[:MAX_RESULTADOS_BUSQUEDA]


def sumar_puntos(cliente, puntos):
    """Acumula puntos en la transacción de la venta (F() no pisa valores)."""
    Cliente.objects.filter(pk=cliente.pk).update(
        puntos=F("puntos") + puntos
    )


# ========== CUENTA CORRIENTE (HU-14) ==========


def validar_fiado(cliente, monto):
    """Revisa que se pueda fiar `monto` a `cliente`. Lanza si no.

    Debe llamarse dentro de la transacción de la venta, con el cliente ya
    bloqueado (`select_for_update`), para que dos cobros simultáneos no
    pasen los dos por encima del límite.
    """
    if cliente is None:
        raise ErrorCuentaCorriente(
            "Para cobrar a cuenta corriente primero asociá un cliente."
        )
    if not cliente.tiene_cuenta_corriente:
        raise ErrorCuentaCorriente(
            f"{cliente.nombre_completo} no tiene cuenta corriente habilitada."
        )
    if monto > cliente.credito_disponible:
        raise ErrorCuentaCorriente(
            f"Se pasa del límite de {cliente.nombre_completo}: "
            f"debe ${montos(cliente.saldo_deuda)} y su límite es "
            f"${montos(cliente.limite_credito)} (le quedan "
            f"${montos(cliente.credito_disponible)})."
        )


def sumar_deuda(cliente, monto):
    """Registra una fianza en la transacción de la venta (F() no pisa)."""
    Cliente.objects.filter(pk=cliente.pk).update(
        saldo_deuda=F("saldo_deuda") + monto
    )


def registrar_pago(cliente, monto, usuario=None, observacion=""):
    """Cobra un pago de la deuda del cliente (HU-14).

    Todo o nada: bloquea la fila del cliente, baja el saldo y guarda el
    `PagoCuentaCorriente` en la misma transacción. Rechaza montos <= 0 y
    montos mayores a la deuda (no se fía saldo a favor).
    """
    monto = Decimal(str(monto)).quantize(Decimal("0.01"))
    if monto <= 0:
        raise ErrorCuentaCorriente("El pago tiene que ser mayor a cero.")

    with transaction.atomic():
        bloqueado = Cliente.objects.select_for_update().get(pk=cliente.pk)
        if monto > bloqueado.saldo_deuda:
            raise ErrorCuentaCorriente(
                f"{bloqueado.nombre_completo} debe "
                f"${montos(bloqueado.saldo_deuda)}: no podés cobrar más "
                f"que eso."
            )
        pago = PagoCuentaCorriente.objects.create(
            cliente=bloqueado,
            monto=monto,
            usuario=usuario if (usuario and usuario.is_authenticated) else None,
            observacion=(observacion or "").strip(),
        )
        Cliente.objects.filter(pk=bloqueado.pk).update(
            saldo_deuda=F("saldo_deuda") - monto
        )
    cliente.refresh_from_db(fields=["saldo_deuda"])
    return pago
