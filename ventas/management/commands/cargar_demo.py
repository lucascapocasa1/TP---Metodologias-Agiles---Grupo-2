"""
Comando de datos de demostración para el reporte de ventas (Sprint 3+).

Crea un catálogo realista de un kiosco de barrio (~57 productos en 7
categorías, con código de barras, precio, costo, stock y stock mínimo) y un
historial de ventas desde el 20 de septiembre de 2026 hasta hoy, para que el
Reporte de Ventas (KPIs, ventas por día, top 10, ticket promedio) y el de
Stock tengan con qué trabajar.

Uso:
    python manage.py cargar_demo --limpiar     # recomendado: recarga todo
    python manage.py cargar_demo               # solo completa lo que falta

Reglas:
  - Los productos se crean solo si no existe otro con el mismo nombre, así
    nunca se pisan productos cargados a mano.
  - Las ventas del período no se generan dos veces: o pasás --limpiar (borra
    las ventas desde el 20/09/2026 y las regenera) o, si hay ventas en el
    período, el comando avisa y no duplica.
  - Las fechas de las ventas se fijan después de crearlas porque
    `Venta.fecha` es auto_now_add. La semilla aleatoria es fija: dos
    ejecuciones con --limpiar producen exactamente los mismos datos.
"""
import random
from datetime import date, datetime, time, timedelta
from decimal import ROUND_CEILING, Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from ventas.models import DetalleVenta, Producto, Venta

# Primer día del historial de ventas (definido por el TP).
FECHA_INICIO = date(2026, 9, 20)

# Semilla fija: los datos de demo son siempre los mismos.
SEMILLA = 20260920

# (nombre, categoría, precio, costo, stock, stock_minimo)
CATALOGO = [
    # Bebidas
    ("Coca Cola 500ml", "Bebidas", "2800.00", "1900.00", 24, 6),
    ("Coca Cola 1.5L", "Bebidas", "4500.00", "3100.00", 15, 6),
    ("Pepsi 500ml", "Bebidas", "2600.00", "1750.00", 18, 6),
    ("Sprite 500ml", "Bebidas", "2500.00", "1700.00", 12, 6),
    ("Agua Villavicencio 600ml", "Bebidas", "1500.00", "900.00", 30, 8),
    ("Agua Villavicencio 2L", "Bebidas", "2600.00", "1700.00", 10, 6),
    ("Fanta Naranja 500ml", "Bebidas", "2500.00", "1700.00", 9, 6),
    ("Hierro Malbec 1L", "Bebidas", "5200.00", "3600.00", 8, 4),
    ("Cepita Naranja 1L", "Bebidas", "4200.00", "2900.00", 6, 5),
    ("Powerade 500ml", "Bebidas", "2900.00", "2000.00", 4, 5),
    ("Volt Energy 269ml", "Bebidas", "3200.00", "2200.00", 3, 5),
    # Golosinas
    ("Alfajor Triple", "Golosinas", "1800.00", "1100.00", 40, 10),
    ("Alfajor Havanna 80g", "Golosinas", "3500.00", "2400.00", 15, 6),
    ("Cofler Block", "Golosinas", "2900.00", "2000.00", 20, 8),
    ("Chocolate Milka 90g", "Golosinas", "4800.00", "3300.00", 12, 6),
    ("Caramelos Felices 500g", "Golosinas", "3600.00", "2500.00", 10, 5),
    ("Chicle Beldent x10", "Golosinas", "1900.00", "1200.00", 25, 8),
    ("Golovinas Mix 200g", "Golosinas", "3300.00", "2300.00", 14, 6),
    ("Pirulí x20", "Golosinas", "3100.00", "2100.00", 5, 5),
    ("Bombones Mogul 300g", "Golosinas", "5200.00", "3600.00", 9, 5),
    # Snacks
    ("Papas Fritas 45g", "Snacks", "2200.00", "1400.00", 30, 10),
    ("Papas Fritas 115g", "Snacks", "4600.00", "3100.00", 16, 6),
    ("Maní La Campagnola 100g", "Snacks", "3400.00", "2300.00", 11, 5),
    ("Nachos Dulces 100g", "Snacks", "2800.00", "1900.00", 13, 6),
    ("Pretzeltín 120g", "Snacks", "3100.00", "2100.00", 7, 5),
    ("Palitos Salados 150g", "Snacks", "2600.00", "1750.00", 2, 5),
    ("Cracker Águila 100g", "Snacks", "2400.00", "1600.00", 0, 5),
    ("Maní Crocante 500g", "Snacks", "7500.00", "5200.00", 6, 4),
    # Lácteos
    ("Leche La Serenísima 1L", "Lácteos", "2900.00", "2300.00", 20, 8),
    ("Yogur Ser Natural 190g", "Lácteos", "3300.00", "2400.00", 14, 6),
    ("Queso Cremoso 300g", "Lácteos", "9800.00", "7600.00", 8, 4),
    ("Queso Port Salut 500g", "Lácteos", "13500.00", "10500.00", 5, 4),
    ("Manteca La Serenísima 200g", "Lácteos", "6200.00", "4900.00", 7, 4),
    ("Flan Ser 170g", "Lácteos", "3100.00", "2200.00", 3, 5),
    ("Queso Untar Havarti 200g", "Lácteos", "7800.00", "6100.00", 4, 5),
    # Panadería
    ("Pan Blanco Lactal 550g", "Panadería", "3800.00", "2800.00", 12, 5),
    ("Pan Molde Integral 550g", "Panadería", "4200.00", "3100.00", 8, 5),
    ("Galletitas Criollas 150g", "Panadería", "2500.00", "1700.00", 15, 6),
    ("Bizcochitos de Grasa x6", "Panadería", "3200.00", "2200.00", 9, 5),
    ("Medialunas Frescas x6", "Panadería", "4500.00", "3200.00", 6, 4),
    # Almacén
    ("Yerba Playadito 1kg", "Almacén", "9800.00", "7400.00", 10, 5),
    ("Café La Virginia 250g", "Almacén", "8200.00", "6300.00", 9, 5),
    ("Azúcar Ledesma 1kg", "Almacén", "3400.00", "2700.00", 14, 6),
    ("Harina 000 Cañuelas 1kg", "Almacén", "2900.00", "2200.00", 12, 6),
    ("Aceite Natura 1.5L", "Almacén", "12500.00", "9800.00", 6, 4),
    ("Fideos Matarazzo 500g", "Almacén", "3100.00", "2300.00", 13, 6),
    ("Arroz Gallo Oro 1kg", "Almacén", "5400.00", "4200.00", 11, 5),
    ("Salsa de Tomate Arcor 520g", "Almacén", "3900.00", "2900.00", 2, 5),
    # Limpieza
    ("Detergente Magistral 750ml", "Limpieza", "5200.00", "3900.00", 10, 5),
    ("Lavandina Ayudín 1L", "Limpieza", "2800.00", "2000.00", 12, 6),
    ("Papel Higiénico Higienol x8", "Limpieza", "9900.00", "7500.00", 7, 4),
    ("Lava Platillos Fairy 500ml", "Limpieza", "6100.00", "4600.00", 1, 5),
    ("Esponja Scotch-Brite x3", "Limpieza", "3800.00", "2800.00", 8, 4),
    # Cafetería
    ("Café Torrado Meloni 250g", "Cafetería", "7900.00", "6100.00", 6, 4),
    ("Mate Cocido Rosamonte 25 sobs", "Cafetería", "5200.00", "3900.00", 8, 4),
    ("Té Marolio 20 sobs", "Cafetería", "3500.00", "2600.00", 5, 5),
]


class Command(BaseCommand):
    help = (
        "Carga ~57 productos de demo y ventas desde el 20/09/2026 "
        "para alimentar los reportes"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--limpiar",
            action="store_true",
            help="Borra las ventas desde el 20/09/2026 antes de regenerarlas",
        )
        parser.add_argument(
            "--ventas-por-dia",
            type=int,
            default=0,
            help="Rango fijo de ventas por día (para tests); 0 = azar real",
        )

    # ---------- Productos ----------

    def cargar_productos(self):
        """Crea los productos que falten (nunca pisa los ya cargados)."""
        creados = 0
        for indice, (nombre, cat_nombre, precio, costo, stock, stock_minimo) in enumerate(
            CATALOGO, start=1
        ):
            _, creado = Producto.objects.get_or_create(
                nombre=nombre,
                defaults={
                    "precio": Decimal(precio),
                    "costo": Decimal(costo),
                    "stock": stock,
                    "stock_minimo": stock_minimo,
                    "categoria": cat_nombre,
                    # Prefijo 779 (Argentina) + índice: determinístico y único.
                    "codigo_barras": f"779{indice:010d}",
                    "activo": True,
                },
            )
            if creado:
                creados += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"Productos: {len(CATALOGO)} en catálogo ({creados} nuevos)."
            )
        )

    # ---------- Ventas ----------

    def _crear_venta(self, rng, productos, cajeros, dia, hora=None):
        """Una venta aleatoria (1 a 5 ítems) con su detalle y totales."""
        cantidad_items = rng.randint(1, 5)
        elegidos = rng.sample(productos, k=cantidad_items)

        detalles = []
        total = Decimal("0.00")
        for producto in elegidos:
            cantidad = rng.randint(1, 3)
            subtotal = producto.precio * cantidad
            total += subtotal
            detalles.append(
                DetalleVenta(
                    producto=producto,
                    cantidad=cantidad,
                    precio_unitario=producto.precio,
                    costo_unitario=producto.costo,
                )
            )

        efectivo = rng.random() < 0.65
        metodo = "EFECTIVO" if efectivo else "TARJETA"

        monto_recibido = total
        vuelto = Decimal("0.00")
        if efectivo:
            # Billetes reales del kiosco: pago exacto, o redondeo hacia arriba.
            billetes = [Decimal("1000"), Decimal("2000"), Decimal("5000"),
                        Decimal("10000"), Decimal("20000")]
            if rng.random() < 0.25:
                # Pago exacto: el vuelto es 0, no queda vacío.
                monto_recibido = total
                vuelto = Decimal("0.00")
            else:
                # Redondeo hacia arriba al billete de $1000 más cercano.
                # (Nunca con un while: si el total no es múltiplo de 100,
                #  ej. $123 → 223, 323… se en loop infinito.)
                miles = (total / 1000).to_integral_value(rounding=ROUND_CEILING)
                monto_recibido = miles * 1000
                if monto_recibido == 0:
                    monto_recibido = Decimal("1000")
                if rng.random() < 0.5:
                    for billete in billetes:
                        if monto_recibido <= billete:
                            monto_recibido = billete
                            break
                vuelto = monto_recibido - total

        venta = Venta.objects.create(
            total=total,
            finalizada=True,
            metodo_pago=metodo,
            cajero=rng.choice(cajeros),
            monto_recibido=monto_recibido,
            vuelto=vuelto,
        )
        for detalle in detalles:
            detalle.venta = venta
        DetalleVenta.objects.bulk_create(detalles)

        # `fecha` es auto_now_add: hay que fijarla con update posterior.
        if hora is None:
            hora = time(rng.randint(8, 21), rng.randint(0, 59))
        fecha_local = timezone.make_aware(datetime.combine(dia, hora))
        Venta.objects.filter(pk=venta.pk).update(fecha=fecha_local)

    def cargar_ventas(self, rng, limpiar, ventas_por_dia):
        desde = datetime.combine(FECHA_INICIO, time.min)
        if timezone.is_naive(desde):
            desde = timezone.make_aware(desde)

        existentes = Venta.objects.filter(fecha__gte=desde).count()
        if existentes and not limpiar:
            self.stdout.write(
                self.style.WARNING(
                    f"Ya hay {existentes} ventas desde el {FECHA_INICIO:%d/%m/%Y}: "
                    "no se generan nuevas para no duplicar. Usá --limpiar para "
                    "borrarlas y regenerar el historial."
                )
            )
            return

        if limpiar and existentes:
            borradas = Venta.objects.filter(fecha__gte=desde).delete()
            self.stdout.write(f"Ventas borradas: {borradas[0]}.")
            self.stdout.write("Productos: no se tocan (solo ventas).")

        productos = list(Producto.objects.filter(activo=True))
        cajeros = list(User.objects.filter(groups__name="Cajero")) or list(
            User.objects.all()
        )

        hoy = timezone.localdate()
        creadas = 0
        dia = FECHA_INICIO
        while dia <= hoy:
            if ventas_por_dia:
                cantidad = ventas_por_dia
            elif dia.weekday() >= 5:  # fin de semana: el kiosco está más lleno
                cantidad = rng.randint(12, 24)
            else:
                cantidad = rng.randint(6, 18)

            for _ in range(cantidad):
                # Hoy no se inventan ventas de horas que aún no pasaron:
                # la hora se elige UNA sola vez y se pasa a _crear_venta
                # (si no, ésta elegiría otra distinta que podría ser futura).
                hora = None
                if dia == hoy:
                    hora = self._hora_pasada(rng)
                    if hora is None:
                        continue
                self._crear_venta(rng, productos, cajeros, dia, hora=hora)
                creadas += 1
            dia += timedelta(days=1)

        self.stdout.write(
            self.style.SUCCESS(
                f"Ventas creadas: {creadas}, desde el {FECHA_INICIO:%d/%m/%Y} "
                f"hasta el {hoy:%d/%m/%Y}."
            )
        )

    def _hora_pasada(self, rng):
        """Hora de hoy que ya pasó, o None si todavía son menos de las 8."""
        ahora = timezone.localtime().time()
        for _ in range(20):  # probamos 20 intentos y si no, no hay venta hoy
            hora = time(rng.randint(8, 21), rng.randint(0, 59))
            if hora <= ahora:
                return hora
        return None

    # ---------- main ----------

    def handle(self, *args, **options):
        rng = random.Random(SEMILLA)
        self.cargar_productos()
        self.cargar_ventas(rng, options["limpiar"], options["ventas_por_dia"])
        self.stdout.write(self.style.SUCCESS("Datos de demo cargados."))
