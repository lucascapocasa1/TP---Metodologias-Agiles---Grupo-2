"""Datos de demostración de clientes y pedidos (HU-12 / HU-13 / HU-14).

La idea es que **todo lo que está cargado tenga respaldo real**:

* Cada cliente del kiosco tiene compras hechas en el mostrador: ventas con
  detalle, stock descontado, puntos acumulados y deuda coherente con el
  límite de crédito.
* Los pedidos que llegan por WhatsApp desde el catálogo público son de
  clientes que después retiran en el local. Los que ya se retiraron se
  cobraron con el flujo real de entrega, así que tienen su venta, su stock
  descontado y su cliente en la ficha de fidelidad.
* Los pedidos que siguen pendientes **no** son clientes todavía: el cliente
  todavía no pasó por el kiosco. Por eso no están en la lista de clientes.

Los perfiles de pago Armada la demo para que se vea un caso de cada uno:

===============  =========================================================
perfil           qué muestra
===============  =========================================================
``debe``         tiene cuenta corriente, debe plata y le queda crédito
``limite``       debe exactamente su límite: no se le puede fiar más
``al_dia``       no tiene cuenta corriente (o la tiene y debe $0)
``al_dia_cc``    tiene cuenta corriente habilitada pero debe $0
===============  =========================================================
"""
from datetime import date, timedelta
from decimal import Decimal

# Primer día del historial (el mismo que usa `cargar_demo`).
FECHA_INICIO = date(2026, 9, 20)

# ===== Clientes del mostrador =====

CLIENTES_DEMO = [
    {
        "nombre": "Javier",
        "apellido": "Pérez",
        "dni": "27111222",
        "telefono": "1145556677",
        "perfil": "debe",
        "compras": [
            (0, "efectivo", [("Coca Cola 1.5L", 2), ("Alfajor Triple", 3)]),
            (5, "efectivo", [("Papas Fritas 115g", 2), ("Leche La Serenísima 1L", 1)]),
            (11, "efectivo", [("Queso Port Salut 500g", 1), ("Pan Blanco Lactal 550g", 1)]),
            (18, "cuenta_corriente", [("Yerba Playadito 1kg", 2)]),
            (26, "cuenta_corriente", [("Café Torrado Meloni 250g", 1), ("Aceite Natura 1.5L", 1)]),
        ],
    },
    {
        "nombre": "Lucía",
        "apellido": "Fernández",
        "dni": "30123456",
        "telefono": "1145551122",
        "perfil": "debe",
        "compras": [
            (2, "efectivo", [("Coca Cola 500ml", 3), ("Chicle Beldent x10", 1)]),
            (8, "efectivo", [("Galletitas Criollas 150g", 2), ("Bizcochitos de Grasa x6", 1)]),
            (14, "efectivo", [("Fanta Naranja 500ml", 2), ("Papas Fritas 45g", 2)]),
            (20, "cuenta_corriente", [("Yogur Ser Natural 190g", 2), ("Flan Ser 170g", 1)]),
            (27, "cuenta_corriente", [("Café La Virginia 250g", 1), ("Té Marolio 20 sobs", 1)]),
        ],
    },
    {
        "nombre": "Sofía",
        "apellido": "Rodríguez",
        "dni": "34555666",
        "telefono": "1145553344",
        "perfil": "limite",
        "compras": [
            (3, "efectivo", [("Pepsi 500ml", 2), ("Pirulí x20", 1)]),
            (12, "efectivo", [("Maní La Campagnola 100g", 1), ("Nachos Dulces 100g", 2)]),
            (24, "cuenta_corriente", [("Queso Untar Havarti 200g", 1), ("Manteca La Serenísima 200g", 1)]),
        ],
    },
    {
        "nombre": "Diego",
        "apellido": "Martínez",
        "dni": "22333444",
        "telefono": "1145555566",
        "perfil": "debe",
        "compras": [
            (1, "efectivo", [("Agua Villavicencio 600ml", 6), ("Té Marolio 20 sobs", 1)]),
            (9, "efectivo", [("Cofler Block", 1), ("Alfajor Havanna 80g", 1)]),
            (16, "efectivo", [("Medialunas Frescas x6", 2)]),
            (22, "cuenta_corriente", [("Detergente Magistral 750ml", 1), ("Lavandina Ayudín 1L", 1)]),
        ],
    },
    {
        "nombre": "Agustina",
        "apellido": "Torres",
        "dni": "40123123",
        "telefono": "1145557788",
        "perfil": "debe",
        "compras": [
            (4, "efectivo", [("Palitos Salados 150g", 1), ("Pretzeltín 120g", 3)]),
            (13, "efectivo", [("Bombones Mogul 300g", 1), ("Caramelos Felices 500g", 1)]),
            (19, "efectivo", [("Pan Molde Integral 550g", 1), ("Leche La Serenísima 1L", 1)]),
            (25, "cuenta_corriente", [("Café Torrado Meloni 250g", 1), ("Té Marolio 20 sobs", 1)]),
        ],
    },
    {
        "nombre": "Ramiro",
        "apellido": "Díaz",
        "dni": "25444333",
        "telefono": "1145559900",
        "perfil": "limite",
        "compras": [
            (6, "efectivo", [("Coca Cola 500ml", 2), ("Chicle Beldent x10", 2)]),
            (15, "efectivo", [("Galletitas Criollas 150g", 1), ("Bizcochitos de Grasa x6", 2)]),
            (23, "cuenta_corriente", [("Aceite Natura 1.5L", 1), ("Arroz Gallo Oro 1kg", 1), ("Fideos Matarazzo 500g", 1)]),
        ],
    },
    {
        "nombre": "Marcos",
        "apellido": "Gómez",
        "dni": "28987654",
        "telefono": "1155551212",
        "perfil": "al_dia_cc",
        "compras": [
            (7, "efectivo", [("Coca Cola 500ml", 1), ("Alfajor Triple", 2)]),
            (17, "efectivo", [("Papas Fritas 45g", 3)]),
            (21, "tarjeta", [("Café Torrado Meloni 250g", 1), ("Té Marolio 20 sobs", 1)]),
            (28, "efectivo", [("Leche La Serenísima 1L", 2), ("Pan Blanco Lactal 550g", 1)]),
        ],
    },
    {
        "nombre": "Camila",
        "apellido": "Sosa",
        "dni": "36777888",
        "telefono": "1155553434",
        "perfil": "al_dia",
        "compras": [
            (10, "efectivo", [("Coca Cola 500ml", 2), ("Chicle Beldent x10", 1)]),
            (25, "efectivo", [("Galletitas Criollas 150g", 1)]),
        ],
    },
    {
        "nombre": "Valentina",
        "apellido": "López",
        "dni": "38999000",
        "telefono": "1155555656",
        "perfil": "al_dia",
        "compras": [
            (29, "efectivo", [("Alfajor Triple", 2), ("Coca Cola 500ml", 1)]),
        ],
    },
]

# ===== Pedidos del catálogo público (WhatsApp) =====

PEDIDOS_DEMO = [
    {
        "nombre": "Ana Ruiz",
        "telefono": "1155551001",
        "comentario": "Retiro a la tarde, después de las 18.",
        "estado": "pendiente",
        "items": [
            ("Coca Cola 500ml", 2),
            ("Alfajor Triple", 3),
            ("Galletitas Criollas 150g", 1),
        ],
    },
    {
        "nombre": "Federico Silva",
        "telefono": "1155551002",
        "comentario": "Paso a buscarlo al mediodía.",
        "estado": "pendiente",
        "items": [
            ("Café Torrado Meloni 250g", 1),
            ("Té Marolio 20 sobs", 1),
            ("Fideos Matarazzo 500g", 1),
        ],
    },
    {
        "nombre": "Micaela Vera",
        "telefono": "1155551003",
        "comentario": "",
        "estado": "pendiente",
        "items": [
            ("Papas Fritas 115g", 2),
            ("Leche La Serenísima 1L", 2),
            ("Bizcochitos de Grasa x6", 1),
        ],
    },
    {
        # Ya retiró y pagó: por eso es cliente del kiosco.
        "nombre": "Pablo Méndez",
        "telefono": "1155551005",
        "comentario": "Pago con tarjeta.",
        "estado": "entregado",
        "cliente": {
            "nombre": "Pablo",
            "apellido": "Méndez",
            "dni": "33777888",
        },
        "metodo": "tarjeta",
        "items": [
            ("Coca Cola 500ml", 2),
            ("Alfajor Havanna 80g", 1),
        ],
    },
    {
        # Retiró pero no tenía plata: quedó fiado (HU-14).
        "nombre": "Julieta Costa",
        "telefono": "1155551006",
        "comentario": "Retiro ahora, lo pago después.",
        "estado": "entregado",
        "cliente": {
            "nombre": "Julieta",
            "apellido": "Costa",
            "dni": "34888999",
        },
        "metodo": "cuenta_corriente",
        "items": [
            ("Queso Cremoso 300g", 1),
            ("Leche La Serenísima 1L", 1),
            ("Galletitas Criollas 150g", 2),
        ],
    },
    {
        "nombre": "Tomás Ibarra",
        "telefono": "1155551007",
        "comentario": "Se arrepintió del pedido.",
        "estado": "cancelado",
        "items": [("Alfajor Triple", 1)],
    },
]

# Días extra de margen para los perfiles que "deben" plata: el límite nunca
# es menor que lo fiado, así que el cliente siempre puede volver a comprar.
MARGEN_CREDITO = Decimal("10000.00")
REDONDEO_CREDITO = Decimal("1000.00")
LIMITE_AL_DIA = Decimal("20000.00")


def dia_del_demo(dias_desde_inicio):
    """Fecha del historial para un offset dado (nunca en el futuro)."""
    from django.utils import timezone

    dia = FECHA_INICIO + timedelta(days=dias_desde_inicio)
    hoy = timezone.localdate()
    return dia if dia <= hoy else hoy
