"""Lógica de fidelidad de clientes (HU-12): puntos por compras.

El cliente elegido en el cobro vive en la sesión del navegador
(`request.session["cliente_id"]`), igual que el carrito: no se persiste
ningún vínculo hasta que el cajero confirma la venta.
"""
from decimal import Decimal

from django.db.models import F

from .models import Cliente

CLAVE_CLIENTE = "cliente_id"
PUNTOS_POR_PESO = 100  # 1 punto por cada $100 comprados


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


def sumar_puntos(cliente, puntos):
    """Acumula puntos en la transacción de la venta (F() no pisa valores)."""
    Cliente.objects.filter(pk=cliente.pk).update(
        puntos=F("puntos") + puntos
    )
