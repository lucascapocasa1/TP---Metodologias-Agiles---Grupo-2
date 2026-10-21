"""
Lógica del vuelto: denominaciones de billetes/monedas de $AR y el
desglose que el cajero debe devolver al cliente.

El kiosco usa un criterio "greedy": para devolver un monto se priorizan
siempre las denominaciones más grandes, que es justo lo que hace una
persona al cambiar un billete (y lo que deja la menor cantidad de piezas).
"""

# Billetes y monedas de uso común en Argentina. Ordenados de mayor a menor
# porque el algoritmo de desglose los recorre así.
DENOMINACIONES_BILLETES = [10000, 5000, 2000, 1000, 500, 200, 100, 50, 20, 10]
DENOMINACIONES_MONEDAS = [5, 2, 1]
DENOMINACIONES = DENOMINACIONES_BILLETES + DENOMINACIONES_MONEDAS


def es_billete(denominacion):
    """True si la denominación circula como billete (>= 10)."""
    return denominacion >= 10


def desglosar(monto):
    """
    Devuelve {denominacion: cantidad} para dar `monto` con la menor
    cantidad de billetes/monedas posible.

    `monto` debe ser un número entero (pesos). Los centavos del vuelto se
    manejan aparte (ver `desglosar_vuelto`).
    """
    resultado = {}
    resto = int(monto)
    if resto <= 0:
        return resultado

    for denominacion in DENOMINACIONES:
        cantidad, resto = divmod(resto, denominacion)
        if cantidad:
            resultado[denominacion] = cantidad

    return resultado


def desglosar_vuelto(vuelto):
    """
    Desglosa el vuelto de una venta. Devuelve (piezas enteras, centavos).

    Ej: desglosar_vuelto(2485.50) -> ({2000: 1, 200: 2, 50: 1, 20: 1,
    10: 1, 5: 1}, '50')
    """
    centavos = 0
    if vuelto != int(vuelto):
        # Tomamos la parte decimal (puede haber centavos por redondeo).
        centavos = round((vuelto - int(vuelto)) * 100)

    return desglosar(int(vuelto)), centavos
