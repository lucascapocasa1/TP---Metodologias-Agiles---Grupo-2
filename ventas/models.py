from django.conf import settings
from django.db import models


class Producto(models.Model):
    """Artículo que se vende en el kiosco."""

    nombre = models.CharField(max_length=120)
    descripcion = models.TextField(
        blank=True,
        help_text="Descripción corta que se muestra en el catálogo público.",
    )
    codigo_barras = models.CharField(
        max_length=32,
        unique=True,
        blank=True,
        help_text="Código EAN/GTIN que lee el escáner de barras.",
    )
    costo = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Precio de compra unitario. Lo ve solo el Administrador.",
    )
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(
        default=0,
        help_text="Unidades disponibles en el depósito.",
    )
    stock_minimo = models.PositiveIntegerField(
        default=5,
        help_text="Alerta de stock bajo: se marca cuando el stock actual "
        "es menor o igual a este valor.",
    )
    categoria = models.CharField(
        max_length=40,
        default="General",
        help_text="Grupo en el que aparece el producto en el POS (ej. Gaseosas).",
    )
    icono = models.CharField(
        max_length=8,
        default="🛒",
        help_text="Emoji que representa el producto en la grilla del POS.",
    )
    activo = models.BooleanField(
        default=True,
        help_text="Los productos inactivos no aparecen en la pantalla de cobro.",
    )
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nombre"]

    @property
    def stock_bajo(self):
        """True cuando el stock actual llegó al mínimo (HU-06)."""
        return self.stock <= self.stock_minimo

    @property
    def margen_porcentual(self):
        """Margen sobre el costo; 0 si todavía no se cargó el costo."""
        if not self.costo:
            return 0
        return ((self.precio - self.costo) / self.costo) * 100

    def __str__(self):
        return f"{self.nombre} — ${self.precio}"


class Venta(models.Model):
    """Un cobro completo hecho en la pantalla del cajero."""

    METODO_PAGO_CHOICES = [
        ("EFECTIVO", "Efectivo"),
        ("QR", "QR"),
        ("TARJETA", "Tarjeta"),
        ("TRANSFERENCIA", "Transferencia"),
    ]

    cajero = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="ventas",
        help_text="Usuario que atendió el mostrador.",
    )
    cliente = models.ForeignKey(
        "clientes.Cliente",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ventas",
        help_text="Cliente asociado a la venta (fidelidad). Vacío si es consumidor final.",
    )
    fecha = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    finalizada = models.BooleanField(
        default=True,
        help_text="Una venta registrada desde el cobro queda finalizada.",
    )
    puntos_ganados = models.PositiveIntegerField(
        default=0,
        help_text="Puntos que sumó esta venta al cliente: 1 cada $100.",
    )
    metodo_pago = models.CharField(
        max_length=20,
        choices=METODO_PAGO_CHOICES,
        default="EFECTIVO",
    )
    monto_recibido = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Dinero que entregó el cliente (efectivo) o igual al total (tarjeta).",
    )
    vuelto = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="monto_recibido - total. 0 cuando se paga exacto o con tarjeta.",
    )

    class Meta:
        ordering = ["-fecha"]

    def __str__(self):
        return f"Venta #{self.pk} — {self.fecha:%d/%m/%Y %H:%M} — ${self.total}"


class DetalleVenta(models.Model):
    """Una línea del carrito al momento del cobro."""

    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name="detalles")
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name="ventas_detalle",
    )
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Precio que tenía el producto al momento de vender (queda congelado).",
    )
    costo_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Costo de compra congelado al vender (reporte de márgenes).",
    )

    def subtotal(self):
        return self.precio_unitario * self.cantidad

    def __str__(self):
        return f"{self.cantidad}x {self.producto.nombre} — ${self.subtotal()}"
