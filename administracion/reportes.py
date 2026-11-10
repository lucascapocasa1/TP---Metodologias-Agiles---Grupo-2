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
from clientes.models import Cliente
from negocios.models import Documento

# Stock igual o por debajo de esto se considera "bajo" para el reporte.
UMBRAL_STOCK_BAJO = 5

# Cuántos días mira hacia atrás la serie de ventas por día.
DIAS_SERIE = 14

# Ventana por defecto de la analítica del dashboard.
DIAS_DASHBOARD = 30

# Opciones del selector de período del dashboard.
PERIODOS_DASHBOARD = [
    ("7", "Últimos 7 días"),
    ("30", "Últimos 30 días"),
    ("90", "Últimos 90 días"),
]


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


def resolver_rango(desde=None, hasta=None, dias_por_defecto=DIAS_SERIE):
    """
    Normaliza los filtros de fecha del querystring.

    Si vienen invertidos los interchangea, y si falta alguno usa el rango
    por defecto de los últimos `dias_por_defecto` días. Devuelve
    (desde_date, hasta_date, desde_dt, hasta_dt) donde los dos últimos son
    datetimes listos para filtrar `Venta.fecha`.
    """
    f_desde = _parsear_fecha(desde)
    f_hasta = _parsear_fecha(hasta)

    if f_desde and f_hasta and f_desde > f_hasta:
        f_desde, f_hasta = f_hasta, f_desde

    if not f_desde and not f_hasta:
        f_desde, f_hasta = _rango_por_defecto(dias_por_defecto)

    if f_desde and not f_hasta:
        f_hasta = timezone.localdate()
    if f_hasta and not f_desde:
        f_desde = f_hasta - timedelta(days=dias_por_defecto - 1)

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

    # Las unidades se agregan aparte de los ingresos: si se sumaran en la
    # misma consulta, el join con los detalles multiplicaría el total de la
    # venta por la cantidad de renglones.
    unidades = (
        DetalleVenta.objects.filter(venta__in=ventas)
        .annotate(dia=TruncDate("venta__fecha"))
        .values("dia")
        .annotate(unidades=Coalesce(Sum("cantidad"), 0))
    )
    unidades_por_dia = {fila["dia"]: fila["unidades"] for fila in unidades}

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
                "unidades": unidades_por_dia.get(dia, 0),
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
                    "unidades": 0,
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


def productos_mas_rentables(
    desde_dt, hasta_dt, limite=5, solo_finalizadas=False, negocio=None,
    por_unidad=False,
):
    """Productos ordenados por ganancia, con montos totales y por unidad.

    La ganancia total mezcla precio con cantidad vendida: un producto que
    se vende mucho puede tapar a otro con mejor margen unitario. Por eso
    cada fila trae los dos juegos de números y `por_unidad` decide por cuál
    se ordena (el template deja cambiar la vista sin recalcular nada).

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
        # Promedio por unidad vendida: si un producto se vendió a precios
        # distintos en el período, esto da el precio y el costo medios.
        unidades = fila["unidades"] or 1
        fila["ingresos_unitarios"] = (fila["ingresos"] / unidades).quantize(
            Decimal("0.01")
        )
        fila["costo_unitario"] = (fila["costo"] / unidades).quantize(
            Decimal("0.01")
        )
        fila["ganancia_unitaria"] = fila["ganancia"] / unidades

    if por_unidad:
        filas.sort(key=lambda f: f["ganancia_unitaria"], reverse=True)
    else:
        filas.sort(key=lambda f: f["ganancia"], reverse=True)

    # Calcular margen porcentual para cada producto
    for fila in filas:
        if fila["costo"] > 0:
            fila["margen_porcentual"] = round((fila["ganancia"] / fila["costo"]) * 100, 2)
        else:
            fila["margen_porcentual"] = 0
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

    # Calcular margen de ganancia del stock
    margen_pct = 0
    if agregados["valor_costo"] > 0:
        margen_pct = round(
            (agregados["valor_venta"] - agregados["valor_costo"])
            / agregados["valor_costo"]
            * 100,
            2,
        )

    return {
        "cantidad_productos": agregados["cantidad_productos"],
        "unidades": agregados["unidades"],
        "valor_costo": agregados["valor_costo"],
        "valor_venta": agregados["valor_venta"],
        "ganancia_potencial": agregados["valor_venta"] - agregados["valor_costo"],
        "margen_porcentual": margen_pct,
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


# ========== Dashboard: analítica ==========


def resolver_periodo_dashboard(periodo=None, desde=None, hasta=None):
    """
    Normaliza el selector de período del dashboard.

    Devuelve (periodo, desde, hasta, desde_dt, hasta_dt, dias), donde
    `periodo` es "7", "30", "90" o "personalizado". Un período válido
    siempre gana sobre las fechas sueltas del querystring (el formulario
    manda desde/hasta aunque estén ocultas). Si piden "personalizado" se
    usan las fechas; si no son válidas cae a 30 días.
    """
    if periodo in dict(PERIODOS_DASHBOARD):
        f_desde, f_hasta, desde_dt, hasta_dt = resolver_rango(
            dias_por_defecto=int(periodo)
        )
    elif periodo == "personalizado" or desde or hasta:
        periodo = "personalizado"
        f_desde, f_hasta, desde_dt, hasta_dt = resolver_rango(
            desde, hasta, dias_por_defecto=DIAS_DASHBOARD
        )
    else:
        periodo = "30"
        f_desde, f_hasta, desde_dt, hasta_dt = resolver_rango(
            dias_por_defecto=DIAS_DASHBOARD
        )

    dias = (f_hasta - f_desde).days + 1
    return periodo, f_desde, f_hasta, desde_dt, hasta_dt, dias


def resumen_periodo(desde_dt, hasta_dt, negocio=None):
    """Totales de ventas del período + deuda fiada otorgada en el mismo rango."""
    resumen = resumen_ventas(
        desde_dt, hasta_dt, solo_finalizadas=True, negocio=negocio
    )
    resumen["deuda_otorgada"] = deuda_otorgada(
        desde_dt, hasta_dt, solo_finalizadas=True, negocio=negocio
    )
    return resumen


def variacion_ventas(desde_dt, hasta_dt, negocio=None):
    """
    Compara los ingresos del período con el anterior de igual duración.

    Devuelve el porcentaje (o None si el período anterior no tuvo ingresos)
    y la dirección del cambio para pintar la flecha.
    """
    dias = (hasta_dt.date() - desde_dt.date()).days + 1
    hasta_ant = desde_dt.date() - timedelta(days=1)
    desde_ant = hasta_ant - timedelta(days=dias - 1)
    desde_ant_dt = timezone.make_aware(
        datetime.combine(desde_ant, datetime.min.time())
    )
    hasta_ant_dt = timezone.make_aware(
        datetime.combine(hasta_ant, datetime.max.time())
    )

    actual = resumen_ventas(
        desde_dt, hasta_dt, solo_finalizadas=True, negocio=negocio
    )["ingresos"]
    anterior = resumen_ventas(
        desde_ant_dt, hasta_ant_dt, solo_finalizadas=True, negocio=negocio
    )["ingresos"]

    if anterior > 0:
        porcentaje = ((actual - anterior) / anterior) * Decimal("100")
        porcentaje = porcentaje.quantize(Decimal("0.1"))
        hay_base = True
    else:
        porcentaje = None
        hay_base = False

    if actual > anterior:
        direccion = "sube"
    elif actual < anterior:
        direccion = "baja"
    else:
        direccion = "igual"

    return {
        "actual": actual,
        "anterior": anterior,
        "porcentaje": porcentaje,
        "hay_base": hay_base,
        "direccion": direccion,
    }


def clientes_fiar(negocio, limite=5):
    """
    Clientes con cuenta corriente que compraron en el negocio.

    `Cliente` es compartido entre negocios: para no mezclar carteras se
    cuentan solo los clientes con ventas en este negocio. El saldo que se
    muestra es el `saldo_deuda` actual de cada cliente.
    """
    vacio = {
        "cantidad": 0,
        "deuda": Decimal("0.00"),
        "con_saldo": 0,
        "al_limite": 0,
        "top": [],
    }
    if negocio is None:
        return vacio

    clientes = Cliente.objects.filter(
        limite_credito__gt=0, ventas__negocio=negocio
    ).distinct()

    return {
        "cantidad": clientes.count(),
        "deuda": clientes.aggregate(
            total=Coalesce(Sum("saldo_deuda"), Decimal("0.00"))
        )["total"],
        "con_saldo": clientes.filter(saldo_deuda__gt=0).count(),
        "al_limite": clientes.filter(
            saldo_deuda__gte=F("limite_credito")
        ).count(),
        "top": list(
            clientes.filter(saldo_deuda__gt=0).order_by(
                "-saldo_deuda", "nombre"
            )[:limite]
        ),
    }


def pedidos_pendientes(negocio, limite=5):
    """Pedidos del catálogo público que todavía no se entregaron."""
    vacio = {
        "cantidad": 0,
        "monto": Decimal("0.00"),
        "vencidos": 0,
        "top": [],
    }
    if negocio is None:
        return vacio

    pendientes = Pedido.objects.filter(negocio=negocio, estado="pendiente")
    # La reserva de stock dura 48 h: más que eso es un pedido que quedó
    # viejo y conviene revisar antes de que el cliente lo reclame.
    limite_reserva = timezone.now() - timedelta(hours=48)

    return {
        "cantidad": pendientes.count(),
        "monto": pendientes.aggregate(
            total=Coalesce(Sum("total"), Decimal("0.00"))
        )["total"],
        "vencidos": pendientes.filter(fecha__lt=limite_reserva).count(),
        "top": list(
            pendientes.select_related("cliente").order_by("fecha")[:limite]
        ),
    }


def rotacion_productos(desde_dt, hasta_dt, negocio, dias, limite=5):
    """
    Los más vendidos del período y los que no tuvieron movimiento.

    Los "lentos" usan la misma definición que el reporte de productos sin
    movimiento (sin ventas ni pedidos entregados en los últimos `dias`).
    """
    return {
        "top": top_productos(
            desde_dt,
            hasta_dt,
            limite=limite,
            solo_finalizadas=True,
            negocio=negocio,
        ),
        "lentos": productos_sin_movimiento(negocio=negocio, dias=dias)[:limite],
    }


def ingresos_por_metodo_pago(desde_dt, hasta_dt, negocio=None):
    """
    Ingresos del período agrupados por método de pago.

    Igual que los reportes, excluye lo fiado (no es plata que entró) y las
    ventas sin finalizar (carritos a medio armar). La deuda fiada se
    devuelve aparte para mostrarla como nota.
    """
    ventas = ventas_del_rango(
        desde_dt, hasta_dt, True, incluir_fiado=False, negocio=negocio
    )
    filas = {
        fila["metodo_pago"]: fila
        for fila in ventas.values("metodo_pago").annotate(
            total=Coalesce(Sum("total"), Decimal("0.00")),
            cantidad=Count("id"),
        )
    }

    metodos = []
    for clave, etiqueta in Venta.METODO_PAGO:
        if clave == "cuenta_corriente":
            continue
        fila = filas.get(clave, {})
        metodos.append(
            {
                "clave": clave,
                "etiqueta": etiqueta,
                "total": fila.get("total", Decimal("0.00")),
                "cantidad": fila.get("cantidad", 0),
            }
        )

    total = sum((metodo["total"] for metodo in metodos), Decimal("0.00"))
    for metodo in metodos:
        if total:
            metodo["porcentaje"] = (
                (metodo["total"] / total) * Decimal("100")
            ).quantize(Decimal("0.1"))
        else:
            metodo["porcentaje"] = Decimal("0.0")

    return {
        "metodos": metodos,
        "total": total,
        "maximo": max(
            (metodo["total"] for metodo in metodos), default=Decimal("0.00")
        ),
        "fiado": deuda_otorgada(
            desde_dt, hasta_dt, solo_finalizadas=True, negocio=negocio
        ),
    }


def proximos_vencimientos(negocio, dias=7, limite=5):
    """Facturas y servicios pendientes que vencen dentro de `dias`."""
    vacio = {
        "cantidad": 0,
        "total": Decimal("0.00"),
        "items": [],
        "dias": dias,
    }
    if negocio is None:
        return vacio

    hoy = timezone.localdate()
    limite_fecha = hoy + timedelta(days=dias)
    documentos = Documento.objects.filter(
        negocio=negocio,
        estado="pendiente",
        fecha_vencimiento__gte=hoy,
        fecha_vencimiento__lte=limite_fecha,
    )

    items = list(documentos.order_by("fecha_vencimiento", "pk")[:limite])
    for documento in items:
        documento.dias_restantes = (documento.fecha_vencimiento - hoy).days

    return {
        "cantidad": documentos.count(),
        "total": sum(
            (documento.monto_pendiente for documento in documentos),
            Decimal("0.00"),
        ),
        "items": items,
        "dias": dias,
    }


def serie_dashboard(desde_dt, hasta_dt, negocio, dias):
    """
    Serie para el gráfico del dashboard.

    Hasta 31 días se muestra día por día; para rangos más largos se agrupa
    por semana para que las barras sigan siendo legibles.
    """
    serie = ventas_por_dia(
        desde_dt, hasta_dt, solo_finalizadas=True, negocio=negocio
    )

    if dias <= 31:
        for fila in serie:
            fila["etiqueta"] = fila["dia"].strftime("%d/%m")
        return serie, "día"

    semanas = {}
    for fila in serie:
        iso = fila["dia"].isocalendar()
        clave = (iso[0], iso[1])
        bucket = semanas.get(clave)
        if bucket is None:
            semanas[clave] = {
                "dia": fila["dia"],
                "etiqueta": f"Sem {iso[1]}",
                "ingresos": fila["ingresos"],
                "costo": fila["costo"],
                "ganancia": fila["ganancia"],
                "ventas": fila["ventas"],
                "unidades": fila["unidades"],
            }
        else:
            bucket["ingresos"] += fila["ingresos"]
            bucket["costo"] += fila["costo"]
            bucket["ganancia"] += fila["ganancia"]
            bucket["ventas"] += fila["ventas"]
            bucket["unidades"] += fila["unidades"]

    return list(semanas.values()), "semana"


def _analitica_vacia():
    """Estructura con ceros para el superadmin sin negocio seleccionado."""
    return {
        "resumen_periodo": {
            "cantidad_ventas": 0,
            "ingresos": Decimal("0.00"),
            "costo": Decimal("0.00"),
            "ganancia": Decimal("0.00"),
            "ticket_promedio": Decimal("0.00"),
            "margen_porcentual": Decimal("0.00"),
            "unidades_vendidas": 0,
            "deuda_otorgada": Decimal("0.00"),
        },
        "variacion": {
            "actual": Decimal("0.00"),
            "anterior": Decimal("0.00"),
            "porcentaje": None,
            "hay_base": False,
            "direccion": "igual",
        },
        "clientes_fiar": clientes_fiar(None),
        "pedidos_pendientes": pedidos_pendientes(None),
        "rotacion_top": [],
        "rotacion_lentos": [],
        "metodos_pago": {
            "metodos": [],
            "total": Decimal("0.00"),
            "maximo": Decimal("0.00"),
            "fiado": Decimal("0.00"),
        },
        "vencimientos": proximos_vencimientos(None),
        "serie": [],
        "granularidad": "día",
        "max_ingresos": Decimal("0.00"),
        "max_ganancia": Decimal("0.00"),
    }


def analitica_dashboard(desde_dt, hasta_dt, negocio, dias):
    """Todo el bloque de analítica del dashboard en un solo dict."""
    if negocio is None:
        return _analitica_vacia()

    serie, granularidad = serie_dashboard(desde_dt, hasta_dt, negocio, dias)
    rotacion = rotacion_productos(desde_dt, hasta_dt, negocio, dias)

    return {
        "resumen_periodo": resumen_periodo(desde_dt, hasta_dt, negocio),
        "variacion": variacion_ventas(desde_dt, hasta_dt, negocio),
        "clientes_fiar": clientes_fiar(negocio),
        "pedidos_pendientes": pedidos_pendientes(negocio),
        "rotacion_top": rotacion["top"],
        "rotacion_lentos": rotacion["lentos"],
        "metodos_pago": ingresos_por_metodo_pago(desde_dt, hasta_dt, negocio),
        "vencimientos": proximos_vencimientos(negocio),
        "serie": serie,
        "granularidad": granularidad,
        "max_ingresos": max(
            (fila["ingresos"] for fila in serie), default=Decimal("0.00")
        ),
        "max_ganancia": max(
            (fila["ganancia"] for fila in serie), default=Decimal("0.00")
        ),
    }