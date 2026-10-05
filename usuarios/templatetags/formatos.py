from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def montos(valor):
    """Formatea un importe en pesos, sin decimales de más.

    26600   → "26.600"   (lo más común: precios y totales enteros)
    1234.5  → "1.234,50" (solo aparecen centavos si realmente los hay)

    El símbolo "$" lo pone el template (para poder reusar el filtro donde
    no hace falta).
    """
    if valor in (None, ""):
        return "0"
    try:
        importe = Decimal(str(valor))
    except (InvalidOperation, ValueError, TypeError):
        return str(valor)

    entero = importe.to_integral_value()
    if importe == entero:
        return f"{int(entero):,}".replace(",", ".")

    texto = f"{importe:,.2f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")
