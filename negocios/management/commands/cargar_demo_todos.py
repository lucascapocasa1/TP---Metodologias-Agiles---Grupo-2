"""
Comando de datos de demostración para los 3 comercios de Noruega:
- Kiosco De Barrio (slug: de-barrio) - ya tenía datos previos
- Ferretería Martillito (slug: ferreteria-martillito)
- Dietética Natural (slug: dietetica-natural)

Crea categorías, productos, usuarios (admin + cajeros por negocio),
clientes, ventas con detalle, turnos, pedidos y pagos de cuenta
corriente para cada negocio, desde el 20/09/2026 hasta hoy.

Uso:
    python manage.py cargar_demo_todos --limpiar   # borra y regenera todo
    python manage.py cargar_demo_todos             # solo completa lo que falta

Las ventas del período no se duplican: si existen ventas desde 20/09/2026,
el comando avisa y no las genera de nuevo (salvo --limpiar).
"""
import random
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from clientes.models import Cliente, PagoCuentaCorriente
from negocios.models import Negocio
from pedidos.models import ItemPedido, Pedido, ReservaStock
from ventas.models import Categoria, DetalleVenta, Producto, Turno, Venta

# Primer día del historial de ventas (definido por el TP).
FECHA_INICIO = date(2026, 9, 20)
# Semilla fija para reproducibilidad.
SEMILLA = 20260920
random.seed(SEMILLA)

# ---------------------------------------------------------------------------
# CATÁLOGOS DE PRODUCTOS POR NEGOCIO
# (nombre, categoría, precio, costo, stock, stock_minimo)
# ---------------------------------------------------------------------------

CATALOGO_FERRETERIA = [
    # Herramientas manuales
    ("Martillo cabeza de bola 22 oz", "Herramientas manuales", "8500.00", "5200.00", 18, 5),
    ("Destornillador Phillips 3x100 mm", "Herramientas manuales", "4500.00", "2800.00", 25, 8),
    ("Alicate de corte 6\"", "Herramientas manuales", "6500.00", "4100.00", 15, 5),
    ("Llave inglesa 8\"", "Herramientas manuales", "9500.00", "6200.00", 12, 4),
    ("Cinta métrica 5 m", "Herramientas manuales", "7200.00", "4500.00", 20, 6),
    ("Nivel de burbuja 60 cm", "Herramientas manuales", "11000.00", "7200.00", 8, 3),
    ("Cepillo de alambre", "Herramientas manuales", "3800.00", "2200.00", 15, 6),
    ("Cúter retráctil", "Herramientas manuales", "3200.00", "1900.00", 20, 8),
    ("Juego de llaves Allen", "Herramientas manuales", "5800.00", "3600.00", 14, 5),
    ("Pinza de presión 10\"", "Herramientas manuales", "8500.00", "5400.00", 10, 4),
    # Herramientas eléctricas
    ("Taladro percutor 650 W", "Herramientas eléctricas", "45000.00", "28500.00", 6, 2),
    ("Sierra circular 7.25\"", "Herramientas eléctricas", "62000.00", "39500.00", 4, 1),
    ("Esmeril angular 4.5\"", "Herramientas eléctricas", "28000.00", "17800.00", 5, 2),
    ("Lijadora orbital", "Herramientas eléctricas", "35000.00", "22000.00", 3, 1),
    ("Pistola de calor", "Herramientas eléctricas", "18000.00", "11500.00", 4, 2),
    ("Taladro atornillador 12 V", "Herramientas eléctricas", "38000.00", "24000.00", 5, 2),
    # Pintura
    ("Pintura esmalte sintético blanco 1 L", "Pintura", "6500.00", "4100.00", 20, 6),
    ("Pintura látex blanco 4 L", "Pintura", "18500.00", "11800.00", 10, 4),
    ("Brocha 2\" cerdas naturales", "Pintura", "2500.00", "1500.00", 25, 8),
    ("Rodillo 9\" con mango", "Pintura", "4200.00", "2600.00", 18, 6),
    ("Bandeja para pintura", "Pintura", "3500.00", "2100.00", 15, 5),
    ("Cinta de enmascarar 48 mm", "Pintura", "2800.00", "1700.00", 30, 10),
    # Electricidad
    ("Cable eléctrico 2.5 mm 50 m", "Electricidad", "15500.00", "9800.00", 8, 3),
    ("Disyuntor 10 A", "Electricidad", "4500.00", "2800.00", 20, 6),
    ("Enchufe doble superficie", "Electricidad", "3200.00", "2000.00", 25, 8),
    ("Interruptor simple", "Electricidad", "2800.00", "1700.00", 30, 10),
    ("Cinta aislante PVC", "Electricidad", "1500.00", "900.00", 40, 12),
    ("Portalámparas E27", "Electricidad", "2200.00", "1400.00", 25, 8),
    ("Lámpara LED 10 W", "Electricidad", "5500.00", "3400.00", 18, 6),
    ("Regleta 4 tomas", "Electricidad", "6800.00", "4300.00", 12, 4),
    # Fontanería
    ("Tubería PVC 1/2\" 3 m", "Fontanería", "4800.00", "3000.00", 15, 5),
    ("Codo PVC 1/2\" 90°", "Fontanería", "800.00", "500.00", 40, 12),
    ("Grifo lavatorio cromo", "Fontanería", "12500.00", "7900.00", 8, 3),
    ("Llave de paso 1/2\"", "Fontanería", "5500.00", "3500.00", 18, 6),
    ("Cinta de teflón", "Fontanería", "900.00", "550.00", 50, 15),
    ("Silicona sanitaria transparente", "Fontanería", "3200.00", "2000.00", 20, 6),
    ("Sifón lavatorio PVC", "Fontanería", "7800.00", "4900.00", 10, 4),
    ("Ducha flexible cromada", "Fontanería", "11000.00", "6900.00", 6, 3),
    # Ferretería general
    ("Clavo 2\" 500 g", "Ferretería general", "3500.00", "2200.00", 30, 10),
    ("Tornillo madera 4 x 40 mm 100 u", "Ferretería general", "5800.00", "3700.00", 20, 6),
    ("Taco + tornillo 6 mm 100 u", "Ferretería general", "6200.00", "3900.00", 18, 6),
    ("Juego de brocas 1-10 mm", "Ferretería general", "9500.00", "6000.00", 12, 4),
    ("Candado latón 40 mm", "Ferretería general", "8500.00", "5400.00", 15, 5),
    ("Cadena para candado 1 m", "Ferretería general", "9500.00", "6000.00", 8, 3),
    ("Abrazadera metálica", "Ferretería general", "1200.00", "750.00", 60, 20),
    ("Cepillo para piso", "Ferretería general", "4500.00", "2800.00", 12, 4),
    ("Escoba de fibra", "Ferretería general", "5200.00", "3300.00", 15, 5),
    ("Guantes de trabajo", "Ferretería general", "3800.00", "2400.00", 25, 8),
]

CATALOGO_DIETETICA = [
    # Semillas
    ("Semilla de chía 500 g", "Semillas", "6800.00", "4300.00", 25, 8),
    ("Semilla de lino 500 g", "Semillas", "5200.00", "3300.00", 20, 6),
    ("Avena en hojuelas 1 kg", "Semillas", "4500.00", "2800.00", 30, 10),
    ("Quinoa 500 g", "Semillas", "7800.00", "5000.00", 18, 6),
    ("Sésamo 500 g", "Semillas", "5400.00", "3400.00", 20, 6),
    ("Girasol 500 g", "Semillas", "4800.00", "3000.00", 20, 6),
    # Harinas
    ("Harina de trigo integral 1 kg", "Harinas", "3800.00", "2400.00", 35, 12),
    ("Harina de avena 1 kg", "Harinas", "4200.00", "2600.00", 30, 10),
    ("Harina de arroz 1 kg", "Harinas", "3900.00", "2500.00", 25, 8),
    ("Harina de garbanzo 500 g", "Harinas", "4200.00", "2700.00", 20, 6),
    ("Harina de lenteja 500 g", "Harinas", "4100.00", "2600.00", 20, 6),
    ("Harina de maíz 1 kg", "Harinas", "3200.00", "2000.00", 30, 10),
    # Endulzantes
    ("Azúcar morena 1 kg", "Endulzantes", "3200.00", "2000.00", 40, 12),
    ("Stevia 100 g", "Endulzantes", "8500.00", "5400.00", 15, 5),
    ("Miel de abejas 500 g", "Endulzantes", "8900.00", "5600.00", 20, 6),
    ("Azúcar de coco 500 g", "Endulzantes", "5800.00", "3700.00", 18, 6),
    ("Miel de maple 250 ml", "Endulzantes", "11500.00", "7300.00", 10, 4),
    # Tés e infusiones
    ("Té verde 50 g", "Tés e infusiones", "4800.00", "3000.00", 25, 8),
    ("Té negro 50 g", "Tés e infusiones", "4200.00", "2600.00", 25, 8),
    ("Manzanilla 30 g", "Tés e infusiones", "3800.00", "2400.00", 20, 6),
    ("Menta 30 g", "Tés e infusiones", "3600.00", "2300.00", 20, 6),
    ("Jengibre en bolsitas 20 g", "Tés e infusiones", "4200.00", "2700.00", 18, 6),
    ("Rooibos 50 g", "Tés e infusiones", "5800.00", "3700.00", 15, 5),
    # Frutos secos
    ("Almendras 200 g", "Frutos secos", "9500.00", "6000.00", 20, 6),
    ("Nueces 200 g", "Frutos secos", "11000.00", "7000.00", 15, 5),
    ("Maní tostado 500 g", "Frutos secos", "6800.00", "4300.00", 25, 8),
    ("Pasas de uva 200 g", "Frutos secos", "5400.00", "3400.00", 20, 6),
    ("Arándanos secos 100 g", "Frutos secos", "8500.00", "5400.00", 15, 5),
    ("Pistachos 100 g", "Frutos secos", "12000.00", "7600.00", 12, 4),
    # Suplementos
    ("Vitamina C 1000 mg 60 caps", "Suplementos", "12500.00", "7900.00", 15, 5),
    ("Magnesio 60 caps", "Suplementos", "9800.00", "6200.00", 18, 6),
    ("Omega 3 60 caps", "Suplementos", "14500.00", "9200.00", 12, 4),
    ("Proteína de suero 500 g", "Suplementos", "24500.00", "15500.00", 10, 4),
    ("Proteína vegetal 500 g", "Suplementos", "22500.00", "14200.00", 8, 3),
    # Productos sin TACC
    ("Galletas de avena sin TACC 200 g", "Productos sin TACC", "6800.00", "4300.00", 20, 6),
    ("Pan de arroz 100 g", "Productos sin TACC", "2800.00", "1800.00", 30, 10),
    ("Fideos de arroz 500 g", "Productos sin TACC", "4500.00", "2900.00", 20, 6),
    ("Harina de almendras 250 g", "Productos sin TACC", "8500.00", "5400.00", 15, 5),
    # Otros
    ("Aceite de oliva 500 ml", "Otros", "12500.00", "7900.00", 15, 5),
    ("Aceite de coco 500 ml", "Otros", "9800.00", "6200.00", 15, 5),
    ("Vinagre de manzana 500 ml", "Otros", "5800.00", "3700.00", 20, 6),
    ("Vinagre de vino tinto 500 ml", "Otros", "5200.00", "3300.00", 20, 6),
    ("Canela en polvo 50 g", "Especias", "4200.00", "2700.00", 25, 8),
    ("Jengibre en polvo 50 g", "Especias", "4500.00", "2900.00", 25, 8),
    ("Cúrcuma en polvo 50 g", "Especias", "4800.00", "3100.00", 25, 8),
]

# ---------------------------------------------------------------------------
# USUARIOS POR NEGOCIO
# (username, password, first_name, last_name, email, grupo)
# ---------------------------------------------------------------------------

USUARIOS_POR_NEGOCIO = {
    "de-barrio": [
        ("admin_barrio", "kiosco2024", "Carlos", "Pérez", "carlos@debarrio.com", "Administrador"),
        ("cajero_barrio_1", "kiosco2024", "María", "González", "maria@debarrio.com", "Cajero"),
        ("cajero_barrio_2", "kiosco2024", "Lucía", "Fernández", "lucia@debarrio.com", "Cajero"),
    ],
    "ferreteria-martillito": [
        ("admin_martillito", "kiosco2024", "Roberto", "Silva", "roberto@martillito.com", "Administrador"),
        ("cajero_martillito_1", "kiosco2024", "Andrea", "Ruiz", "andrea@martillito.com", "Cajero"),
        ("cajero_martillito_2", "kiosco2024", "Diego", "Morales", "diego@martillito.com", "Cajero"),
    ],
    "dietetica-natural": [
        ("admin_natural", "kiosco2024", "Sofía", "Díaz", "sofia@natural.com", "Administrador"),
        ("cajero_natural_1", "kiosco2024", "Valentina", "Castillo", "valentina@natural.com", "Cajero"),
        ("cajero_natural_2", "kiosco2024", "Martín", "Ibañez", "martin@natural.com", "Cajero"),
    ],
}

# ---------------------------------------------------------------------------
# CLIENTES COMPARTIDOS (se usan en varios negocios)
# (nombre, apellido, dni, telefono, limite_credito, saldo_deuda, activo)
# ---------------------------------------------------------------------------

CLIENTES_COMPARTIDOS = [
    ("Lucas", "Pérez", "30111222", "1155556666", "10000.00", "3000.00", True),
    ("María", "González", "27456789", "1166677778", "15000.00", "0.00", True),
    ("Juan", "Rodríguez", "33890123", "1177788899", "8000.00", "5000.00", True),
    ("Lucía", "Fernández", "29345678", "1188899900", "12000.00", "2000.00", True),
    ("Martín", "López", "34123456", "1199900011", "5000.00", "0.00", True),
    ("Ana", "Martínez", "31567890", "1122233344", "20000.00", "8000.00", True),
    ("Pedro", "Sánchez", "32901234", "1133344455", "10000.00", "10000.00", True),  # al límite
    ("Carla", "Gómez", "35678901", "1144455566", "7000.00", "0.00", True),
    ("Julián", "Díaz", "28234567", "1155566677", "9000.00", "1500.00", True),
    ("Florencia", "Romero", "33789012", "1166677788", "6000.00", "6000.00", True),  # al límite
]

# ---------------------------------------------------------------------------
# MÉTODOS DE PAGO Y PROBABILIDADES
# ---------------------------------------------------------------------------

METODOS_PAGO = ["efectivo", "tarjeta", "cuenta_corriente", "mercado_pago"]
PESOS_METODOS = [0.60, 0.25, 0.10, 0.05]

# ---------------------------------------------------------------------------
# FUNCIONES AUXILIARES
# ---------------------------------------------------------------------------


def fecha_aleatoria():
    """Fecha aleatoria entre FECHA_INICIO y hoy."""
    hoy = date.today()
    dias = (hoy - FECHA_INICIO).days
    return FECHA_INICIO + timedelta(days=random.randint(0, dias))


def hora_aleatoria():
    """Hora aleatoria en horario comercial (8:00 - 21:00)."""
    return time(
        random.randint(8, 20),
        random.randint(0, 59),
        random.randint(0, 59),
    )


def monto_aleatorio(minimo=500, maximo=15000):
    """Monto redondeado a enteros realistas."""
    return Decimal(str(random.randint(minimo, maximo)))


class Command(BaseCommand):
    help = "Puebla la base de datos con datos de demostración para los 3 comercios de Noruega."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limpiar",
            action="store_true",
            help="Borra ventas, pedidos y datos de demo anteriores antes de cargar.",
        )

    def handle(self, *args, **options):
        limpiar = options["limpiar"]
        self.stdout.write(self.style.NOTICE("=== Poblado de datos de demostración para los 3 negocios ==="))

        # 1. Asegurar grupos
        grupo_admin, _ = Group.objects.get_or_create(name="Administrador")
        grupo_cajero, _ = Group.objects.get_or_create(name="Cajero")
        self.stdout.write("Grupos 'Administrador' y 'Cajero' verificados.")

        # 2. Asegurar superadmin (ya existe de setup_inicial, pero lo reafirmamos)
        superadmin, creado = User.objects.get_or_create(
            username="admin",
            defaults={
                "password": "kiosco2024",
                "first_name": "Superadmin",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        if creado:
            superadmin.set_password("kiosco2024")
            superadmin.save()
            self.stdout.write(self.style.SUCCESS("Superadmin 'admin' creado. Clave: kiosco2024"))
        else:
            self.stdout.write("Superadmin 'admin' ya existía.")

        # 3. Asegurar negocios
        negocios = {}
        for slug, datos in [
            ("de-barrio", {"nombre": "Kiosco De Barrio", "whatsapp": "5491155554444", "email": "barrio@example.com"}),
            ("ferreteria-martillito", {"nombre": "Ferretería Martillito", "whatsapp": "5491166667777", "email": "martillito@example.com"}),
            ("dietetica-natural", {"nombre": "Dietética Natural", "whatsapp": "5491177778888", "email": "natural@example.com"}),
        ]:
            negocio, creado = Negocio.objects.get_or_create(
                slug=slug,
                defaults={
                    "nombre": datos["nombre"],
                    "whatsapp": datos["whatsapp"],
                    "email": datos["email"],
                    "direccion": f"Dirección ficticia {slug}",
                    "horarios": "Lun a Vie 9:00-18:00, Sáb 9:00-13:00",
                    "color_primario": "#00C8E0",
                    "activo": True,
                },
            )
            negocios[slug] = negocio
            if creado:
                self.stdout.write(self.style.SUCCESS(f"Negocio '{negocio.nombre}' creado."))
            else:
                self.stdout.write(f"Negocio '{negocio.nombre}' ya existía.")

        # 4. Crear usuarios y empleados por negocio
        for slug, usuarios in USUARIOS_POR_NEGOCIO.items():
            negocio = negocios[slug]
            for username, password, first, last, email, grupo_nombre in usuarios:
                user, creado = User.objects.get_or_create(
                    username=username,
                    defaults={
                        "password": password,
                        "first_name": first,
                        "last_name": last,
                        "email": email,
                        "is_staff": grupo_nombre == "Administrador",
                    },
                )
                if creado:
                    user.set_password(password)
                    user.save()
                    grupo = grupo_admin if grupo_nombre == "Administrador" else grupo_cajero
                    user.groups.add(grupo)
                    self.stdout.write(self.style.SUCCESS(f"Usuario '{username}' creado ({grupo_nombre}). Clave: {password}"))
                else:
                    # Actualizar grupo por si cambió
                    user.groups.clear()
                    grupo = grupo_admin if grupo_nombre == "Administrador" else grupo_cajero
                    user.groups.add(grupo)
                    self.stdout.write(f"Usuario '{username}' ya existía, grupo actualizado a {grupo_nombre}.")

                # Crear Empleado vinculando usuario y negocio
                Empleado = __import__("usuarios.models", fromlist=["Empleado"]).Empleado
                Empleado.objects.get_or_create(usuario=user, negocio=negocio, defaults={"activo": True})

        # 5. Crear categorías y productos por negocio
        catalogo_por_negocio = {
            "ferreteria-martillito": CATALOGO_FERRETERIA,
            "dietetica-natural": CATALOGO_DIETETICA,
        }
        # Para de-barrio, usamos los productos existentes del kiosco (ya cargados por cargar_demo)
        # Aquí solo creamos si no existen productos para ese negocio.

        for slug, productos_lista in catalogo_por_negocio.items():
            negocio = negocios[slug]
            for nombre, categoria_nombre, precio, costo, stock, stock_min in productos_lista:
                categoria, _ = Categoria.objects.get_or_create(
                    nombre=categoria_nombre,
                    negocio=negocio,
                )
                codigo_barras = f"{slug[:3].upper()}{random.randint(100000, 999999)}"
                producto, creado = Producto.objects.get_or_create(
                    nombre=nombre,
                    negocio=negocio,
                    defaults={
                        "descripcion": f"{nombre} - {categoria_nombre}",
                        "codigo_barras": codigo_barras,
                        "precio": Decimal(precio),
                        "costo": Decimal(costo),
                        "stock": random.randint(stock // 2, stock),
                        "stock_minimo": stock_min,
                        "categoria": categoria,
                        "activo": True,
                    },
                )
                if creado:
                    self.stdout.write(self.style.SUCCESS(f"Producto '{nombre}' creado para {negocio.nombre}."))

        # 6. Crear clientes compartidos (si no existen)
        clientes_creados = []
        for nombre, apellido, dni, telefono, limite, saldo, activo in CLIENTES_COMPARTIDOS:
            cliente, creado = Cliente.objects.get_or_create(
                dni=dni,
                defaults={
                    "nombre": nombre,
                    "apellido": apellido,
                    "telefono": telefono,
                    "limite_credito": Decimal(limite),
                    "saldo_deuda": Decimal(saldo),
                    "activo": activo,
                },
            )
            clientes_creados.append(cliente)
            if creado:
                self.stdout.write(self.style.SUCCESS(f"Cliente '{nombre} {apellido}' (DNI {dni}) creado."))

        # 7. Limpiar ventas anteriores si se pidió
        if limpiar:
            for slug in negocios:
                negocio = negocios[slug]
                Venta.objects.filter(negocio=negocio, fecha__gte=FECHA_INICIO).delete()
                Pedido.objects.filter(negocio=negocio, fecha__gte=FECHA_INICIO).delete()
                ReservaStock.objects.filter(fecha_reserva__gte=FECHA_INICIO).delete()
                PagoCuentaCorriente.objects.filter(negocio=negocio, fecha__gte=FECHA_INICIO).delete()
                Turno.objects.filter(negocio=negocio, fecha_apertura__gte=FECHA_INICIO).delete()
                self.stdout.write(self.style.WARNING(f"Datos anteriores de {negocio.nombre} borrados."))

        # 8. Generar ventas por negocio
        hoy = date.today()
        total_ventas_por_negocio = 500

        for slug, negocio in negocios.items():
            productos = list(Producto.objects.filter(negocio=negocio, activo=True))
            if not productos:
                self.stdout.write(self.style.WARNING(f"No hay productos para {negocio.nombre}, saltando ventas."))
                continue

            # Obtener usuarios de este negocio para asignar como vendedores
            empleados = list(Empleado.objects.filter(negocio=negocio, activo=True).select_related("usuario"))
            if not empleados:
                self.stdout.write(self.style.WARNING(f"No hay empleados para {negocio.nombre}, saltando ventas."))
                continue

            usuarios_vendedores = [e.usuario for e in empleados]

            # Verificar si ya hay ventas en el período
            ventas_existentes = Venta.objects.filter(negocio=negocio, fecha__gte=FECHA_INICIO).count()
            if ventas_existentes > 0 and not limpiar:
                self.stdout.write(
                    self.style.WARNING(
                        f"{negocio.nombre}: ya hay {ventas_existentes} ventas desde {FECHA_INICIO}. Saltando generación."
                    )
                )
                continue

            self.stdout.write(self.style.NOTICE(f"Generando {total_ventas_por_negocio} ventas para {negocio.nombre}..."))

            clientes_activos = [c for c in clientes_creados if c.activo]

            with transaction.atomic():
                for i in range(total_ventas_por_negocio):
                    fecha = datetime.combine(fecha_aleatoria(), hora_aleatoria())
                    fecha = timezone.make_aware(fecha)

                    usuario = random.choice(usuarios_vendedores)
                    metodo = random.choices(METODOS_PAGO, weights=PESOS_METODOS)[0]

                    # Decidir si asociar cliente (70% de las veces)
                    cliente = random.choice(clientes_activos) if random.random() < 0.7 else None

                    # Crear venta (sin total aún, se calcula después)
                    venta = Venta.objects.create(
                        total=Decimal("0.00"),
                        finalizada=True,
                        metodo_pago=metodo,
                        usuario=usuario,
                        cliente=cliente,
                        negocio=negocio,
                        puntos_ganados=0,
                    )
                    # Fijar fecha después de crear (auto_now_add)
                    Venta.objects.filter(pk=venta.pk).update(fecha=fecha)

                    # Generar ítems
                    num_items = random.randint(1, 5)
                    items_seleccionados = random.sample(productos, min(num_items, len(productos)))
                    total_venta = Decimal("0.00")

                    for producto in items_seleccionados:
                        cantidad = random.randint(1, 3)
                        precio = producto.precio
                        subtotal = precio * cantidad
                        total_venta += subtotal

                        DetalleVenta.objects.create(
                            venta=venta,
                            producto=producto,
                            cantidad=cantidad,
                            precio_unitario=precio,
                            costo_unitario=producto.costo,
                        )

                        # Descontar stock
                        Producto.objects.filter(pk=producto.pk).update(
                            stock=max(0, producto.stock - cantidad)
                        )
                        producto.stock = max(0, producto.stock - cantidad)

                    venta.total = total_venta
                    venta.monto_entregado = total_venta if metodo == "efectivo" else None
                    venta.vuelto = Decimal("0.00") if metodo == "efectivo" else None

                    # Puntos y deuda
                    if cliente:
                        venta.puntos_ganados = int(total_venta // 100)
                        if metodo == "cuenta_corriente":
                            # Verificar límite
                            if cliente.credito_disponible >= total_venta:
                                cliente.saldo_deuda += total_venta
                                cliente.save(update_fields=["saldo_deuda"])
                                PagoCuentaCorriente.objects.create(
                                    cliente=cliente,
                                    negocio=negocio,
                                    monto=total_venta,
                                    usuario=usuario,
                                    observacion="Venta fiada (demo)",
                                )
                            else:
                                # Si no puede fiar, cambiar a efectivo
                                venta.metodo_pago = "efectivo"
                                venta.monto_entregado = total_venta
                                venta.vuelto = Decimal("0.00")
                        venta.save(update_fields=["total", "monto_entregado", "vuelto", "puntos_ganados", "metodo_pago"])

                        if venta.puntos_ganados > 0:
                            cliente.puntos = (cliente.puntos or 0) + venta.puntos_ganados
                            cliente.save(update_fields=["puntos"])
                    else:
                        venta.save(update_fields=["total", "monto_entregado", "vuelto"])

            self.stdout.write(self.style.SUCCESS(f"{negocio.nombre}: {total_ventas_por_negocio} ventas generadas."))

        # 9. Crear turnos por negocio (al menos uno cerrado y uno abierto)
        for slug, negocio in negocios.items():
            empleados = list(Empleado.objects.filter(negocio=negocio, activo=True))
            if not empleados:
                continue

            # Turno cerrado
            empleado = random.choice(empleados)
            fecha_apertura = datetime.combine(FECHA_INICIO, time(8, 0))
            fecha_cierre = datetime.combine(FECHA_INICIO, time(18, 0))
            turno = Turno.objects.create(
                usuario=empleado.usuario,
                negocio=negocio,
                fecha_apertura=timezone.make_aware(fecha_apertura),
                fecha_cierre=timezone.make_aware(fecha_cierre),
                total_efectivo=Decimal("45000.00"),
                total_tarjeta=Decimal("32000.00"),
                total_mercado_pago=Decimal("8000.00"),
                deuda_otorgada=Decimal("5000.00"),
                cantidad_operaciones=25,
            )
            self.stdout.write(self.style.SUCCESS(f"Turno cerrado creado para {negocio.nombre}."))

            # Turno abierto (hoy)
            turno_abierto = Turno.objects.create(
                usuario=random.choice(empleados).usuario,
                negocio=negocio,
                fecha_apertura=timezone.now(),
                fecha_cierre=None,
            )
            self.stdout.write(self.style.SUCCESS(f"Turno abierto creado para {negocio.nombre}."))

        # 10. Crear pedidos para cada negocio (algunos pendientes, algunos entregados)
        for slug, negocio in negocios.items():
            productos = list(Producto.objects.filter(negocio=negocio, activo=True))
            if not productos:
                continue

            empleados = list(Empleado.objects.filter(negocio=negocio, activo=True))
            if not empleados:
                continue

            usuarios_vendedores = [e.usuario for e in empleados]
            clientes_activos = [c for c in clientes_creados if c.activo]

            for i in range(30):  # 30 pedidos por negocio
                fecha = datetime.combine(fecha_aleatoria(), hora_aleatoria())
                fecha = timezone.make_aware(fecha)

                num_items = random.randint(1, 4)
                items_seleccionados = random.sample(productos, min(num_items, len(productos)))
                total = sum(item.precio * random.randint(1, 2) for item in items_seleccionados)

                tipo_entrega = random.choice(["retiro", "domicilio"])
                costo_envio = Decimal("1000.00") if tipo_entrega == "domicilio" else Decimal("0.00")
                total += costo_envio

                cliente_obj = random.choice(clientes_activos) if random.random() < 0.6 else None

                pedido = Pedido.objects.create(
                    nombre_cliente=f"{cliente_obj.nombre} {cliente_obj.apellido}" if cliente_obj else "Consumidor Final",
                    telefono=cliente_obj.telefono if cliente_obj else "",
                    comentario="Pedido de demostración",
                    estado=random.choice(["pendiente", "entregado", "cancelado"]),
                    total=total,
                    negocio=negocio,
                    cliente=cliente_obj,
                    tipo_entrega=tipo_entrega,
                    costo_envio=costo_envio,
                )
                Pedido.objects.filter(pk=pedido.pk).update(fecha=fecha)

                for producto in items_seleccionados:
                    cantidad = random.randint(1, 2)
                    ItemPedido.objects.create(
                        pedido=pedido,
                        producto=producto,
                        nombre_producto=producto.nombre,
                        cantidad=cantidad,
                        precio_unitario=producto.precio,
                    )

                # Si está entregado, crear venta vinculada
                if pedido.estado == "entregado":
                    metodo_pago = random.choice(["efectivo", "tarjeta", "cuenta_corriente"])
                    venta = Venta.objects.create(
                        total=total,
                        finalizada=True,
                        metodo_pago=metodo_pago,
                        usuario=random.choice(usuarios_vendedores),
                        cliente=cliente_obj,
                        negocio=negocio,
                        puntos_ganados=int(total // 100) if cliente_obj else 0,
                    )
                    Venta.objects.filter(pk=venta.pk).update(fecha=fecha)

                    for ip in pedido.detalles.all():
                        DetalleVenta.objects.create(
                            venta=venta,
                            producto=ip.producto,
                            cantidad=ip.cantidad,
                            precio_unitario=ip.precio_unitario,
                            costo_unitario=ip.producto.costo,
                        )

                    pedido.venta = venta
                    pedido.save(update_fields=["venta"])

                    # Descontar stock
                    for ip in pedido.detalles.all():
                        Producto.objects.filter(pk=ip.producto.pk).update(
                            stock=max(0, ip.producto.stock - ip.cantidad)
                        )

            self.stdout.write(self.style.SUCCESS(f"{negocio.nombre}: 30 pedidos generados."))

        self.stdout.write(self.style.SUCCESS("=== Poblado completo ==="))
        self.stdout.write("")
        self.stdout.write("USUARIOS DE PRUEBA (todos con clave 'kiosco2024'):")
        self.stdout.write("  Superadmin: admin / kiosco2024")
        for slug, usuarios in USUARIOS_POR_NEGOCIO.items():
            negocio = negocios[slug]
            self.stdout.write(f"  {negocio.nombre} ({slug}):")
            for username, password, first, last, email, grupo in usuarios:
                self.stdout.write(f"    - {username} / {password} ({grupo})")
