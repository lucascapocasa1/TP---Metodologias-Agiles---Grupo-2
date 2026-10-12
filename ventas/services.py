"""
Lógica de negocio del cobro (Sprint 3 - HU-07/08/09).

El carrito vive en la sesión del navegador (`request.session["carrito"]`),
como una lista de {"producto_id": ..., "cantidad": ...}. No se crea ninguna
Venta hasta que el cajero confirma el cobro: así no quedan ventas "a medias"
ensuciando los reportes (que sí filtran por `finalizada`).
"""
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import F

from .models import DetalleVenta, Producto, Venta

CLAVE_CARRITO = "carrito"
METODOS_PAGO_VALIDOS = {"efectivo", "tarjeta"}


def formatear_monto(monto):
    """1500.00 → "$1500"? No: "$1.500" (miles con punto, sin decimales de más).

    Usa el mismo filtro que muestran los templates (`|montos`) para que los
    mensajes y la auditoría digan exactamente lo mismo que la pantalla.
    """
    from usuarios.templatetags.formatos import montos

    return "$" + montos(monto)


class ErrorCobro(Exception):
    """Error de negocio del cobro. El mensaje es para mostrarle al cajero."""


def leer_carrito(request):
    """Carrito crudo de la sesión (lista de dicts), nunca None."""
    return request.session.get(CLAVE_CARRITO, [])


def guardar_carrito(request, carrito):
    request.session[CLAVE_CARRITO] = carrito
    request.session.modified = True


def vaciar_carrito(request):
    request.session.pop(CLAVE_CARRITO, None)
    request.session.modified = True


def items_del_carrito(request):
    """
    Hidrata el carrito de la sesión con los productos actuales de la BD.
    Devuelve lista de dicts: producto, cantidad, subtotal.
    Los productos dados de baja o eliminados se sacan del carrito.
    """
    carrito = leer_carrito(request)
    if not carrito:
        return []

    productos = {
        p.pk: p
        for p in Producto.objects.filter(
            pk__in=[fila["producto_id"] for fila in carrito], activo=True
        )
    }

    items = []
    carrito_limpio = []
    for fila in carrito:
        producto = productos.get(fila.get("producto_id"))
        if producto is None:
            continue
        cantidad = max(int(fila.get("cantidad", 0)), 0)
        if cantidad <= 0:
            continue
        items.append(
            {
                "producto": producto,
                "cantidad": cantidad,
                "subtotal": producto.precio * cantidad,
            }
        )
        carrito_limpio.append({"producto_id": producto.pk, "cantidad": cantidad})

    if carrito_limpio != carrito:
        guardar_carrito(request, carrito_limpio)
    return items


def total_del_carrito(items):
    total = sum((item["subtotal"] for item in items), Decimal("0.00"))
    return total


def buscar_producto(termino):
    """
    HU-07: identifica el producto por código de barras exacto (lo que lee el
    lector) o, si no, por nombre. Devuelve el Producto o lanza ErrorCobro.
    """
    termino = (termino or "").strip()
    if not termino:
        raise ErrorCobro("Escaneá o tipeá el código del producto.")

    producto = (
        Producto.objects.filter(codigo_barras=termino, activo=True).first()
    )
    if producto:
        return producto

    coincidencias = list(
        Producto.objects.filter(nombre__icontains=termino, activo=True)[:2]
    )
    if len(coincidencias) == 1:
        return coincidencias[0]
    if not coincidencias:
        raise ErrorCobro(f"No encontré productos para «{termino}».")
    raise ErrorCobro(
        f"Varios productos coinciden con «{termino}». Usá el código de barras."
    )


def agregar_al_carrito(request, producto):
    """
    HU-07: si el producto ya está en el carrito se suma la cantidad en vez de
    crear una fila duplicada.
    """
    carrito = leer_carrito(request)
    for fila in carrito:
        if fila["producto_id"] == producto.pk:
            fila["cantidad"] += 1
            guardar_carrito(request, carrito)
            return carrito

    carrito.append({"producto_id": producto.pk, "cantidad": 1})
    guardar_carrito(request, carrito)
    return carrito


def modificar_cantidad(request, producto_id, accion):
    """HU-08: suma, resta o quita un ítem del carrito."""
    carrito = leer_carrito(request)
    nuevo = []
    for fila in carrito:
        if fila["producto_id"] != producto_id:
            nuevo.append(fila)
            continue
        if accion == "quitar":
            continue
        if accion == "sumar":
            fila = {**fila, "cantidad": fila["cantidad"] + 1}
        elif accion == "restar":
            cantidad = fila["cantidad"] - 1
            if cantidad <= 0:
                continue
            fila = {**fila, "cantidad": cantidad}
        nuevo.append(fila)

    guardar_carrito(request, nuevo)
    return nuevo


def _parsear_monto(valor):
    """
    Acepta el formato del locale es-ar: coma decimal y, si lleva punto,
    el punto es de miles ("1.500,50" → 1500.50).
    """
    if valor in (None, ""):
        return None
    texto = str(valor).strip().replace("$", "").replace(" ", "")
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        monto = Decimal(texto).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        raise ErrorCobro("El monto entregado no es un número válido.")
    if monto < 0:
        raise ErrorCobro("El monto entregado no puede ser negativo.")
    return monto


def confirmar_venta(request, metodo_pago, monto_entregado):
    """
    HU-09: cierra la venta en una única transacción:
    crea Venta + DetalleVenta (precio y costo congelados), descuenta el stock
    y devuelve la Venta. Limpia el carrito solo si todo salió bien.
    """
    items = items_del_carrito(request)
    if not items:
        raise ErrorCobro("El carrito está vacío.")

    if metodo_pago not in METODOS_PAGO_VALIDOS:
        raise ErrorCobro("Elegí un método de pago válido (efectivo o tarjeta).")

    total = total_del_carrito(items)
    monto = _parsear_monto(monto_entregado)
    monto_final = None
    vuelto = None

    if metodo_pago == "efectivo":
        if monto is None:
            raise ErrorCobro("Ingresá el monto que entregó el cliente.")
        if monto < total:
            raise ErrorCobro(
                f"El monto entregado ({formatear_monto(monto)}) es menor "
                f"al total ({formatear_monto(total)})."
            )
        monto_final = monto
        vuelto = monto - total

    producto_ids = [item["producto"].pk for item in items]

    with transaction.atomic():
        # Bloqueo los productos para que dos cajeros no vendan el mismo stock.
        productos_bloqueados = {
            p.pk: p
            for p in Producto.objects.select_for_update().filter(
                pk__in=producto_ids
            )
        }

        for item in items:
            producto = productos_bloqueados.get(item["producto"].pk)
            if producto is None:
                raise ErrorCobro("Un producto del carrito ya no existe.")
            if producto.stock < item["cantidad"]:
                raise ErrorCobro(
                    f"Stock insuficiente de «{producto.nombre}»: "
                    f"quedan {producto.stock} unidades."
                )

        venta = Venta.objects.create(
            total=total,
            finalizada=True,
            metodo_pago=metodo_pago,
            usuario=request.user if request.user.is_authenticated else None,
            monto_entregado=monto_final,
            vuelto=vuelto,
        )

        for item in items:
            producto = productos_bloqueados[item["producto"].pk]
            DetalleVenta.objects.create(
                venta=venta,
                producto=producto,
                cantidad=item["cantidad"],
                precio_unitario=producto.precio,
                costo_unitario=producto.costo,
            )
            Producto.objects.filter(pk=producto.pk).update(
                stock=F("stock") - item["cantidad"]
            )

    vaciar_carrito(request)
    return venta
