"""
Agregaciones para los reportes del Administrador.

Todo vive acá separado de `views.py` a propósito: las vistas solo arma el
contexto y renderiza, y las cuentas (KPIs, ventas por día, top de productos,
valorización de stock) quedan en funciones testeables.

Dos criterios guían estas cuentas:

1. Los costos son información sensible. Los precios de compra solo se miran
   desde acá, y siempre bajo el rol "Administrador" (ver `views.py`).
2. El costo se congela en `DetalleVenta.costo_unitario` al vender. Si se
   usara `Producto.costo` hoy, cambiar el costo de un producto reescribiría
   la historia de márgenes de ventas viejas.
"""
from datetime import datetime, timedelta
from decimal import Decimal

from django.db.models import Count, F, Sum
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone

from pedidos.models import ItemPedido, Pedido
from ventas.models import DetalleVenta, Producto, Venta

# Stock igual o por debajo de esto se considera "bajo" para el reporte.
UMBRAL_STOCK_BAJO = 5

# Cuántos días mira hacia atrás la serie de ventas por día.
DIAS_SERIE = 14


# ========== Utilidades de rango ==========


def _rango_por_defecto(dias=DIAS_SERIE):
    """(desde, hasta) como date: hoy y los `dias` anteriores."""
    hoy = timezone.localdate()
    return hoy - timedelta(days=dias - 1), hoy


def _parsear_fecha(valor):
    """Convierte un string 'YYYY-MM-DD' en date, o None si no es válido."""
    if not valor:
        return None
    try:
        return datetime.strptime(valor, "%Y-%m-%d").date()
    except ValueError:
        return None


def resolver_rango(desde=None, hasta=None):
    """
    Normaliza los filtros de fecha del querystring.

    Si vienen invertidos los interchangea, y si falta alguno usa el rango
    por defecto de los últimos `DIAS_SERIE` días. Devuelve
    (desde_date, hasta_date, desde_dt, hasta_dt) donde los dos últimos son
    datetimes listos para filtrar `Venta.fecha`.
    """
    f_desde = _parsear_fecha(desde)
    f_hasta = _parsear_fecha(hasta)

    if f_desde and f_hasta and f_desde > f_hasta:
        f_desde, f_hasta = f_hasta, f_desde

    if not f_desde and not f_hasta:
        f_desde, f_hasta = _rango_por_defecto()

    if f_desde and not f_hasta:
        f_hasta = timezone.localdate()
    if f_hasta and not f_desde:
        f_desde = f_hasta - timedelta(days=DIAS_SERIE - 1)

    # dt_gt_lt: incluye todo el día final hasta las 23:59:59.999999
    desde_dt = timezone.make_aware(
        datetime.combine(f_desde, datetime.min.time())
    )
    hasta_dt = timezone.make_aware(
        datetime.combine(f_hasta, datetime.max.time())
    )
    return f_desde, f_hasta, desde_dt, hasta_dt


def ventas_del_rango(desde_dt, hasta_dt, solo_finalizadas=False, incluir_fiado=True, negocio=None):
    """Queryset de ventas del período, ya filtrado.

    HU-14: las ventas a cuenta corriente no son plata que entró, así que
    los reportes de ingresos las excluyen (`incluir_fiado=False`). Se
    informan aparte como "deuda otorgada".

    Si se pasa `negocio`, filtra solo las ventas de ese negocio.
    """
    ventas = Venta.objects.filter(fecha__gte=desde_dt, fecha__lte=hasta_dt)
    if negocio is not None:
        ventas = ventas.filter(negocio=negocio)
    if solo_finalizadas:
        ventas = ventas.filter(finalizada=True)
    if not incluir_fiado:
        ventas = ventas.exclude(metodo_pago="cuenta_corriente")
    return ventas


def deuda_otorgada(desde_dt, hasta_dt, solo_finalizadas=False, negocio=None):
    """Total fiado a cuenta corriente en el período (HU-14)."""
    return ventas_del_rango(
        desde_dt, hasta_dt, solo_finalizadas, incluir_fiado=True, negocio=negocio
    ).filter(metodo_pago="cuenta_corriente").aggregate(
        total=Coalesce(Sum("total"), Decimal("0.00"))
    )["total"]


# ========== KPIs de cabecera ==========


def resumen_ventas(desde_dt, hasta_dt, solo_finalizadas=False, negocio=None):
    """
    Totales del período: cuántas ventas, cuánto entra, cuánto sale el
    producto y cuál es la ganancia y el ticket promedio.

    El costo sale de los detalles vía `Coalesce`: usa el costo congelado en
    la venta y, para las ventas hechas antes de que existiera ese campo,
    cae al costo actual del producto en vez de largar 0.

    HU-14: los ingresos y los costos excluyen las ventas a cuenta corriente
    (no es plata que entró a la caja). La deuda fiada se informa aparte.

    Si se pasa `negocio`, filtra solo las ventas de ese negocio.
    """
    ventas = ventas_del_rango(
        desde_dt, hasta_dt, solo_finalizadas, incluir_fiado=False, negocio=negocio
    )

    agregados = ventas.aggregate(
        cantidad_ventas=Count("id"),
        ingresos=Coalesce(Sum("total"), Decimal("0.00")),
    )

    detalles = DetalleVenta.objects.filter(venta__in=ventas).aggregate(
        costo=Coalesce(
            Sum(F("cantidad") * Coalesce(F("costo_unitario"), F("producto__costo"))),
            Decimal("0.00"),
        ),
    )
    costo_total = detalles["costo"]

    # `total` de Venta es el precio de venta; el costo viene de los detalles.
    # Si una venta quedó sin detalles, el costo es 0 y la ganancia es el total.
    ingresos = agregados["ingresos"]
    cantidad = agregados["cantidad_ventas"]

    return {
        "cantidad_ventas": cantidad,
        "ingresos": ingresos,
        "costo": costo_total,
        "ganancia": ingresos - costo_total,
        "ticket_promedio": (
            ingresos / cantidad if cantidad else Decimal("0.00")
        ),
        "margen_porcentual": (
            ((ingresos - costo_total) / ingresos) * Decimal("100")
            if ingresos
            else Decimal("0.00")
        ),
        "unidades_vendidas": DetalleVenta.objects.filter(venta__in=ventas).aggregate(
            total=Coalesce(Sum("cantidad"), 0)
        )["total"],
    }


# ========== Series y rankings ==========


def ventas_por_dia(desde_dt, hasta_dt, solo_finalizadas=False, negocio=None):
    """
    Serie diaria (una fila por día) para dibujar el gráfico.

    Cubre todo el rango pedido, no solo los días con ventas: si el lunes no
    se vendió nada, el gráfico tiene que mostrar ese lunes en cero. Si lo
    saltara, un día flojo se leería como "no pasó nada" en lugar de
    "no vendimos".

    Trae también el costo y la ganancia del día, no solo el total, porque
    un día con muchas ventas puede ser el que más plata deja o el que menos.

    HU-14: excluye lo fiado (no es plata que entró); la deuda otorgada del
    período se muestra aparte con `deuda_otorgada()`.

    Si se pasa `negocio`, filtra solo las ventas de ese negocio.
    """
    ventas = ventas_del_rango(
        desde_dt, hasta_dt, solo_finalizadas, incluir_fiado=False, negocio=negocio
    )

    ingresos = (
        ventas.annotate(dia=TruncDate("fecha"))
        .values("dia")
        .annotate(
            ingresos=Coalesce(Sum("total"), Decimal("0.00")),
            ventas=Count("id"),
        )
        .order_by("dia")
    )

    costos = (
        DetalleVenta.objects.filter(venta__in=ventas)
        .annotate(dia=TruncDate("venta__fecha"))
        .values("dia")
        .annotate(
            costo=Coalesce(
                Sum(
                    F("cantidad")
                    * Coalesce(F("costo_unitario"), F("producto__costo"))
                ),
                Decimal("0.00"),
            )
        )
    )
    costo_por_dia = {fila["dia"]: fila["costo"] for fila in costos}

    serie = []
    for fila in ingresos:
        dia = fila["dia"]
        costo_dia = costo_por_dia.get(dia, Decimal("0.00"))
        serie.append(
            {
                "dia": dia,
                "ingresos": fila["ingresos"],
                "costo": costo_dia,
                "ganancia": fila["ingresos"] - costo_dia,
                "ventas": fila["ventas"],
            }
        )

    # Rellena los días sin ventas con ceros: un hueco en la serie se lee
    # como "no hubo ventas", que es lo que pasó de verdad. El relleno va
    # del primer día del rango al último, no entre la primera y la última
    # venta: si solo se vendió el lunes, igual tiene que aparecer el martes.
    mapa = {fila["dia"]: fila for fila in serie}

    relleno = []
    dia = desde_dt.date()
    ultimo = hasta_dt.date()
    while dia <= ultimo:
        relleno.append(
            mapa.get(
                dia,
                {
                    "dia": dia,
                    "ingresos": Decimal("0.00"),
                    "costo": Decimal("0.00"),
                    "ganancia": Decimal("0.00"),
                    "ventas": 0,
                },
            )
        )
        dia += timedelta(days=1)

    return relleno


def top_productos(desde_dt, hasta_dt, limite=10, solo_finalizadas=False, negocio=None):
    """Productos más vendidos por unidades, con su margen (excluye fiado).

    Si se pasa `negocio`, filtra solo las ventas de ese negocio.
    """
    ventas = ventas_del_rango(
        desde_dt, hasta_dt, solo_finalizadas, incluir_fiado=False, negocio=negocio
    )

    return list(
        DetalleVenta.objects.filter(venta__in=ventas)
        .values("producto__id", "producto__nombre", "producto__categoria__nombre")
        .annotate(
            unidades=Sum("cantidad"),
            ingresos=Sum(F("cantidad") * F("precio_unitario")),
            costo=Sum(
                F("cantidad")
                * Coalesce(F("costo_unitario"), F("producto__costo"))
            ),
        )
        .order_by("-unidades", "producto__nombre")[:limite]
    )


def productos_mas_rentables(desde_dt, hasta_dt, limite=5, solo_finalizadas=False, negocio=None):
    """Productos ordenados por ganancia total, no por unidades vendidas.

    Si se pasa `negocio`, filtra solo las ventas de ese negocio.
    """
    ventas = ventas_del_rango(
        desde_dt, hasta_dt, solo_finalizadas, incluir_fiado=False, negocio=negocio
    )

    filas = list(
        DetalleVenta.objects.filter(venta__in=ventas)
        .values("producto__id", "producto__nombre")
        .annotate(
            unidades=Sum("cantidad"),
            ingresos=Sum(F("cantidad") * F("precio_unitario")),
            costo=Sum(
                F("cantidad")
                * Coalesce(F("costo_unitario"), F("producto__costo"))
            ),
        )
    )

    for fila in filas:
        fila["ganancia"] = fila["ingresos"] - fila["costo"]

    filas.sort(key=lambda f: f["ganancia"], reverse=True)
    return filas[:limite]


# ========== Stock ==========


def resumen_stock(solo_activos=True, negocio=None):
    """
    Foto del inventario: cuántos productos hay, cuántas unidades, cuánto
    vale el stock a costo y cuánto a precio de venta, y qué está por
    terminarse.

    Los productos sin costo cargado cuentan como 0 en la valorización a
    costo: es preferible mostrar un número claramente incompleto que
    inventar un valor.

    Si se pasa `negocio`, filtra solo los productos de ese negocio.
    """
    productos = Producto.objects.all()
    if negocio is not None:
        productos = productos.filter(negocio=negocio)
    if solo_activos:
        productos = productos.filter(activo=True)

    agregados = productos.aggregate(
        cantidad_productos=Count("id"),
        unidades=Coalesce(Sum("stock"), 0),
        valor_costo=Coalesce(
            Sum(F("stock") * Coalesce(F("costo"), Decimal("0.00"))),
            Decimal("0.00"),
        ),
        valor_venta=Coalesce(
            Sum(F("stock") * Coalesce(F("precio"), Decimal("0.00"))),
            Decimal("0.00"),
        ),
    )

    stock_bajo = list(
        productos.filter(stock__lte=UMBRAL_STOCK_BAJO).order_by("stock", "nombre")
    )

    return {
        "cantidad_productos": agregados["cantidad_productos"],
        "unidades": agregados["unidades"],
        "valor_costo": agregados["valor_costo"],
        "valor_venta": agregados["valor_venta"],
        "ganancia_potencial": agregados["valor_venta"] - agregados["valor_costo"],
        "stock_bajo": stock_bajo,
        "cantidad_stock_bajo": len(stock_bajo),
        "sin_stock": productos.filter(stock=0).count(),
        "sin_costo": productos.filter(costo=0).count(),
    }


def stock_por_categoria(negocio=None):
    """Valorización del stock agrupada por categoría.

    Si se pasa `negocio`, filtra solo los productos de ese negocio.
    """
    productos = Producto.objects.filter(activo=True)
    if negocio is not None:
        productos = productos.filter(negocio=negocio)
    return list(
        productos.values("categoria__nombre")
        .annotate(
            productos=Count("id"),
            unidades=Coalesce(Sum("stock"), 0),
            valor_costo=Coalesce(
                Sum(F("stock") * Coalesce(F("costo"), Decimal("0.00"))),
                Decimal("0.00"),
            ),
        )
        .order_by("-valor_costo")
    )


# ========== Margen del catálogo ==========


def productos_bajo_margen(umbral=Decimal("20.00"), limite=10, negocio=None):
    """
    Productos cuyo margen sobre el costo está por debajo del umbral.

    Solo tiene sentido sobre productos con costo cargado: sin costo el
    margen es 0 y todos los productos nuevos entrarían en la lista como
    "malos" cuando en realidad es que todavía no se cargó su precio de compra.

    Si se pasa `negocio`, filtra solo los productos de ese negocio.
    """
    candidatos = Producto.objects.filter(activo=True, costo__gt=0)
    if negocio is not None:
        candidatos = candidatos.filter(negocio=negocio)

    filas = []
    for producto in candidatos:
        if producto.margen_porcentual < umbral:
            filas.append(producto)

    filas.sort(key=lambda p: p.margen_porcentual)
    return filas[:limite]


# ========== Productos sin movimiento ==========


def productos_sin_movimiento(negocio=None, dias=30):
    """
    Productos activos que NO tuvieron ventas ni pedidos entregados
    en los últimos `dias` días.

    Se consideran tanto ventas presenciales (Venta finalizada)
    como pedidos online entregados (Pedido estado='entregado').

    Si se pasa `negocio`, filtra solo los productos de ese negocio.

    Devuelve una lista de objetos Producto ordenados por nombre.
    """
    fecha_limite = timezone.now() - timedelta(days=dias)

    # IDs de productos que SÍ tuvieron movimiento en el período
    productos_con_movimiento = set()

    # Ventas finalizadas en el período
    ventas_recientes = Venta.objects.filter(
        negocio=negocio,
        finalizada=True,
        fecha__gte=fecha_limite,
    ).values_list("detalles__producto_id", flat=True).distinct()
    productos_con_movimiento.update(ventas_recientes)

    # Pedidos entregados en el período
    pedidos_entregados = Pedido.objects.filter(
        negocio=negocio,
        estado="entregado",
        fecha__gte=fecha_limite,
    ).values_list("detalles__producto_id", flat=True).distinct()
    productos_con_movimiento.update(pedidos_entregados)

    # Productos activos del negocio que NO tuvieron movimiento
    sin_movimiento = Producto.objects.filter(
        negocio=negocio,
        activo=True,
    ).exclude(id__in=productos_con_movimiento)

    return list(sin_movimiento.order_by("nombre"))