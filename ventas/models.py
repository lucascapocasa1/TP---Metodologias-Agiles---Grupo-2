from datetime import date

from django.db import models

from administracion.models import Empresa, Empleado, Producto, Proveedor


class Cliente(models.Model):
    """Cliente del kiosco (para facturación opcional)."""

    nombre = models.CharField("nombre", max_length=100)
    apellido = models.CharField("apellido", max_length=100)
    cuit = models.CharField("CUIT", max_length=11, unique=True, blank=True, null=True)
    telefono = models.CharField("teléfono", max_length=30, blank=True)
    email = models.EmailField("email", blank=True)
    direccion = models.CharField("dirección", max_length=200, blank=True)
    fecha_nacimiento = models.DateField("fecha de nacimiento", null=True, blank=True)
    fecha_registro = models.DateTimeField("fecha de registro", auto_now_add=True)

    class Meta:
        verbose_name = "cliente"
        verbose_name_plural = "clientes"
        ordering = ["apellido", "nombre"]

    def __str__(self):
        return f"{self.nombre} {self.apellido}"

    @property
    def edad(self):
        if not self.fecha_nacimiento:
            return None
        hoy = date.today()
        return (
            hoy.year
            - self.fecha_nacimiento.year
            - ((hoy.month, hoy.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day))
        )


class Contacto(models.Model):
    """Persona de contacto de un proveedor/empresa."""

    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.SET_NULL,
        related_name="contactos",
        verbose_name="proveedor",
        null=True,
        blank=True,
    )
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.SET_NULL,
        related_name="contactos",
        verbose_name="empresa",
        null=True,
        blank=True,
    )
    nombre = models.CharField("nombre", max_length=100)
    cargo = models.CharField("cargo", max_length=100, blank=True)
    telefono = models.CharField("teléfono", max_length=30, blank=True)
    email = models.EmailField("email", blank=True)
    es_principal = models.BooleanField("contacto principal", default=False)

    class Meta:
        verbose_name = "contacto"
        verbose_name_plural = "contactos"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Venta(models.Model):
    """Venta de mercadería a un cliente (factura opcional)."""

    EFECTIVO = "efectivo"
    TARJETA = "tarjeta"
    TRANSFERENCIA = "transferencia"
    OTRO = "otro"

    FORMA_PAGO_CHOICES = [
        (EFECTIVO, "Efectivo"),
        (TARJETA, "Tarjeta"),
        (TRANSFERENCIA, "Transferencia"),
        (OTRO, "Otro"),
    ]

    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.SET_NULL,
        related_name="ventas",
        verbose_name="cliente",
        null=True,
        blank=True,
    )
    empleado = models.ForeignKey(
        Empleado,
        on_delete=models.PROTECT,
        related_name="ventas",
        verbose_name="cajero",
    )
    fecha = models.DateTimeField("fecha", auto_now_add=True)
    total = models.DecimalField("total", max_digits=12, decimal_places=2, default=0)
    forma_pago = models.CharField(
        "forma de pago",
        max_length=20,
        choices=FORMA_PAGO_CHOICES,
        default=EFECTIVO,
    )
    observaciones = models.TextField("observaciones", blank=True)

    class Meta:
        verbose_name = "venta"
        verbose_name_plural = "ventas"
        ordering = ["-fecha"]

    def __str__(self):
        return f"Venta #{self.pk} - {self.fecha:%d/%m/%Y %H:%M}"


class DetalleVenta(models.Model):
    """Renglón de una venta: producto, cantidad y precio al que salió."""

    venta = models.ForeignKey(
        Venta,
        on_delete=models.CASCADE,
        related_name="detalles",
        verbose_name="venta",
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name="detalles_venta",
        verbose_name="producto",
    )
    cantidad = models.PositiveIntegerField("cantidad", default=1)
    precio_unitario = models.DecimalField("precio unitario", max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "detalle de venta"
        verbose_name_plural = "detalles de venta"

    def __str__(self):
        return f"{self.cantidad}x {self.producto}"

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario