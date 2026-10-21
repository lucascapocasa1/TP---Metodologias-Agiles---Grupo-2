"""
Lógica de negocio del cobro (Sprint 3 - HU-07/08/09) y del cierre de
turno (Sprint 4 - HU-10).

El carrito vive en la sesión del navegador (`request.session["carrito"]`),
como una lista de {"producto_id": ..., "cantidad": ...}. No se crea ninguna
Venta hasta que el cajero confirma el cobro: así no quedan ventas "a medias"
ensuciando los reportes (que sí filtran por `finalizada`).
"""
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import F, Count, Q, Sum
from django.utils import timezone

from clientes import services as fidelidad

from .models import DetalleVenta, Producto, Turno, Venta

CLAVE_CARRITO = "carrito"
METODOS_PAGO_VALIDOS = {"efectivo", "tarjeta", "cuenta_corriente"}
# HU-14: lo fiado no es plata que entra a la caja, así que no engrosa los
# totales de un turno. Solo efectivo y tarjeta se cuentan en el cierre.
METODOS_EN_CAJA = ("efectivo", "tarjeta")


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


def _precio_de_item(item, producto):
    """Precio unitario a cobrar de un item.

    Si el item trae "precio" se cobra ese (el congelado: es lo que el
    cliente vio cuando armó el pedido de WhatsApp); si no, se cobra el
    precio actual del producto, como en el POS.
    """
    precio = item.get("precio")
    if precio is None:
        return producto.precio
    return Decimal(str(precio))


def _crear_venta(items, metodo_pago, cliente, usuario, monto_entregado):
    """
    Núcleo de la venta: valida el cobro, crea la Venta con sus DetalleVenta
    (precio y costo congelados), descuenta el stock y acumula los puntos
    (y la deuda, si es cuenta corriente).

    NO abre su propia transacción: la tiene que abrir quien la llama, para
    que el bloqueo de filas del cliente y de los productos valga para todo
    el cobro. `cliente` tiene que venir ya bloqueado (`select_for_update`).

    `items` es una lista de dicts {"producto", "cantidad"} y, opcionalmente,
    "precio" (el congelado, que usa el pedido de WhatsApp).
    """
    if metodo_pago not in METODOS_PAGO_VALIDOS:
        raise ErrorCobro(
            "Elegí un método de pago válido (efectivo, tarjeta o cuenta "
            "corriente)."
        )

    total = sum(
        (
            _precio_de_item(item, item["producto"]) * item["cantidad"]
            for item in items
        ),
        Decimal("0.00"),
    )

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

    # HU-12: 1 punto cada $100 comprados.
    puntos_ganados = fidelidad.puntos_por_monto(total) if cliente else 0

    # HU-14: a cuenta corriente solo se puede cobrar con cliente y dentro
    # de su límite. Se valida con el cliente ya bloqueado.
    if metodo_pago == "cuenta_corriente":
        try:
            fidelidad.validar_fiado(cliente, total)
        except fidelidad.ErrorCuentaCorriente as exc:
            raise ErrorCobro(str(exc))

    # Bloqueo los productos para que dos cajeros no vendan el mismo stock.
    producto_ids = [item["producto"].pk for item in items]
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
        usuario=usuario if (usuario and usuario.is_authenticated) else None,
        monto_entregado=monto_final,
        vuelto=vuelto,
        cliente=cliente,
        puntos_ganados=puntos_ganados,
    )

    for item in items:
        producto = productos_bloqueados[item["producto"].pk]
        DetalleVenta.objects.create(
            venta=venta,
            producto=producto,
            cantidad=item["cantidad"],
            precio_unitario=_precio_de_item(item, producto),
            costo_unitario=producto.costo,
        )
        Producto.objects.filter(pk=producto.pk).update(
            stock=F("stock") - item["cantidad"]
        )

    if cliente is not None:
        fidelidad.sumar_puntos(cliente, puntos_ganados)
        # HU-14: lo fiado engrosa la deuda del cliente en la misma
        # transacción. Si algo falla después, la venta y la deuda se
        # revierten juntas.
        if metodo_pago == "cuenta_corriente":
            fidelidad.sumar_deuda(cliente, total)

    return venta


def confirmar_venta(request, metodo_pago, monto_entregado):
    """
    HU-09: cierra la venta en una única transacción:
    crea Venta + DetalleVenta (precio y costo congelados), descuenta el stock
    y devuelve la Venta. Si había un cliente asociado (HU-12), lo vincula y
    le acumula los puntos de fidelidad de la compra.
    HU-14: si el pago es a cuenta corriente, valida el límite del cliente y
    le suma la deuda (todo dentro de la misma transacción).
    Limpia el carrito solo si todo salió bien.
    """
    items = items_del_carrito(request)
    if not items:
        raise ErrorCobro("El carrito está vacío.")

    with transaction.atomic():
        # Cliente de la fidelidad (HU-12): bloqueado para que dos cobros
        # simultáneos no acumen los puntos pisándose entre sí.
        cliente = fidelidad.cliente_para_venta(request)
        venta = _crear_venta(
            items, metodo_pago, cliente, request.user, monto_entregado
        )

    vaciar_carrito(request)
    fidelidad.quitar_cliente_de_sesion(request)
    return venta


def registrar_venta_desde_items(
    items, metodo_pago, cliente, usuario, monto_entregado=None
):
    """
    Crea una venta a partir de una lista de items ya armada.

    La usa el pedido de WhatsApp (HU-13): el cliente armó el pedido desde el
    catálogo público y al retirar en el local se le cobra lo que pidió, con
    el precio que quedó congelado en el pedido. Es el mismo núcleo del POS,
    así que el stock, los puntos y el fiado se comportan exactamente igual.
    """
    with transaction.atomic():
        cliente_bloqueado = fidelidad.cliente_bloqueado(cliente)
        return _crear_venta(
            items, metodo_pago, cliente_bloqueado, usuario, monto_entregado
        )


# ========== CIERRE DE TURNO (Sprint 4 - HU-10) ==========


def turno_abierto(usuario):
    """El turno del usuario que todavía no se cerró, si existe."""
    return Turno.objects.filter(
        usuario=usuario, fecha_cierre__isnull=True
    ).first()


def abrir_turno(usuario):
    """
    Abre un turno para el usuario. Si ya tiene uno abierto devuelve ese:
    no puede haber dos turnos activos de la misma persona.
    """
    existente = turno_abierto(usuario)
    if existente:
        return existente
    return Turno.objects.create(usuario=usuario)


def ventas_del_turno(turno):
    """
    Ventas finalizadas del responsable del turno dentro de su franja:
    desde la apertura hasta el cierre (o hasta ahora si sigue abierto).
    """
    ventas = Venta.objects.filter(
        finalizada=True,
        usuario=turno.usuario,
        fecha__gte=turno.fecha_apertura,
    )
    if turno.fecha_cierre:
        ventas = ventas.filter(fecha__lte=turno.fecha_cierre)
    return ventas


def totales_del_turno(turno):
    """
    Efectivo, tarjeta y cantidad de operaciones del turno.
    Con el turno cerrado devuelve el snapshot congelado en el cierre;
    mientras está abierto calcula en vivo para mostrar en pantalla.

    HU-14: lo fiado a cuenta corriente **no** entra al efectivo ni a la
    tarjeta (no es plata que hay en la caja). Se informa aparte como
    "deuda otorgada" para que el cajero sepa cuánto se fió en el turno.
    """
    if not turno.activo:
        return {
            "total_efectivo": turno.total_efectivo,
            "total_tarjeta": turno.total_tarjeta,
            "total_general": turno.total_general,
            "deuda_otorgada": turno.deuda_otorgada,
            "cantidad_operaciones": turno.cantidad_operaciones,
        }

    agregados = ventas_del_turno(turno).aggregate(
        efectivo=Sum("total", filter=Q(metodo_pago="efectivo")),
        tarjeta=Sum("total", filter=Q(metodo_pago="tarjeta")),
        fiado=Sum("total", filter=Q(metodo_pago="cuenta_corriente")),
        operaciones=Count("pk"),
    )
    efectivo = agregados["efectivo"] or Decimal("0.00")
    tarjeta = agregados["tarjeta"] or Decimal("0.00")
    return {
        "total_efectivo": efectivo,
        "total_tarjeta": tarjeta,
        "total_general": efectivo + tarjeta,
        "deuda_otorgada": agregados["fiado"] or Decimal("0.00"),
        "cantidad_operaciones": agregados["operaciones"],
    }


def cerrar_turno(turno):
    """
    HU-10: cierra el turno guardando un snapshot de los totales del momento,
    para que el histórico no cambie si después se registran más ventas.
    Lanza ErrorCobro si el turno ya estaba cerrado.
    """
    with transaction.atomic():
        turno = Turno.objects.select_for_update().get(pk=turno.pk)
        if not turno.activo:
            raise ErrorCobro("Ese turno ya está cerrado.")

        totales = totales_del_turno(turno)
        turno.fecha_cierre = timezone.now()
        turno.total_efectivo = totales["total_efectivo"]
        turno.total_tarjeta = totales["total_tarjeta"]
        turno.deuda_otorgada = totales["deuda_otorgada"]
        turno.cantidad_operaciones = totales["cantidad_operaciones"]
        turno.save(
            update_fields=[
                "fecha_cierre",
                "total_efectivo",
                "total_tarjeta",
                "deuda_otorgada",
                "cantidad_operaciones",
            ]
        )
    return turno
