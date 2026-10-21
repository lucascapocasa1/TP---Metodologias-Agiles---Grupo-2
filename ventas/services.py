"""
Servicio del carrito de compras del POS.

El carrito vive en la sesión del usuario: es un dict {producto_id: cantidad}.
Guardarlo en la sesión (y no en una tabla de la base de datos) permite que
el cajero arme la venta sin confirmar nada todavía, y que dos cajeros en
dos terminales no se pisen los carritos. La venta recién se persiste cuando
se toca "Cobrar" (ver ventas/models.py -> Venta).
"""
from decimal import Decimal

from .models import Producto


def formatear_monto(valor):
    """Importe en pesos con símbolo: 30500 → "$30.500", 1234.5 → "$1.234,50"."""
    if valor in (None, ""):
        return "$0"
    try:
        importe = Decimal(str(valor))
    except Exception:
        return str(valor)

    entero = importe.to_integral_value()
    if importe == entero:
        return f"${int(entero):,}".replace(",", ".")

    texto = f"{importe:,.2f}"
    return "$" + texto.replace(",", "X").replace(".", ",").replace("X", ".")


def obtener_carrito(sesion):
    """Devuelve el dict {producto_id: cantidad} guardado en la sesión."""
    return sesion.get("carrito", {})


def guardar_carrito(sesion, carrito):
    sesion["carrito"] = carrito
    sesion.modified = True


def agregar_producto(sesion, producto, cantidad=1):
    """Suma `cantidad` unidades de `producto` al carrito de la sesión."""
    if cantidad < 1:
        cantidad = 1
    carrito = obtener_carrito(sesion)
    clave = str(producto.pk)
    carrito[clave] = carrito.get(clave, 0) + cantidad
    guardar_carrito(sesion, carrito)


def actualizar_cantidad(sesion, producto_id, cantidad):
    """Deja `cantidad` unidades del producto (0 o menos lo elimina)."""
    carrito = obtener_carrito(sesion)
    clave = str(producto_id)
    if cantidad < 1:
        carrito.pop(clave, None)
    else:
        carrito[clave] = cantidad
    guardar_carrito(sesion, carrito)


def quitar_producto(sesion, producto_id):
    """Elimina el producto del carrito sin importar su cantidad."""
    carrito = obtener_carrito(sesion)
    carrito.pop(str(producto_id), None)
    guardar_carrito(sesion, carrito)


def vaciar_carrito(sesion):
    sesion.pop("carrito", None)
    sesion.modified = True


def detalle_carrito(sesion):
    """
    Convierte el carrito (dict) en una lista de items listos para la
    plantilla, calculando subtotales y el total general.

    Devuelve (items, total) donde items es una lista de dicts:
        {"producto": Producto, "cantidad": int, "subtotal": Decimal}
    """
    carrito = obtener_carrito(sesion)
    items = []
    total = Decimal("0.00")

    for producto_id, cantidad in carrito.items():
        try:
            producto = Producto.objects.get(pk=producto_id, activo=True)
        except Producto.DoesNotExist:
            # El producto se desactivó o se borró, no se puede vender.
            continue

        cantidad = int(cantidad)
        subtotal = producto.precio * cantidad
        total += subtotal
        items.append(
            {
                "producto": producto,
                "cantidad": cantidad,
                "subtotal": subtotal,
            }
        )

    return items, total
