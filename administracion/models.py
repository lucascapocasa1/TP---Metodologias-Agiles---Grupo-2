from datetime import date

from django.contrib.auth.models import User
from django.db import models


class Empresa(models.Model):
    """Datos del kiosco / dueño (entidad propietaria del negocio)."""

    nombre = models.CharField("nombre", max_length=150)
    cuit = models.CharField("CUIT", max_length=11, unique=True)
    direccion = models.CharField("dirección", max_length=200, blank=True)
    telefono = models.CharField("teléfono", max_length=30, blank=True)
    email = models.EmailField("email", blank=True)
    fecha_creacion = models.DateTimeField("fecha de creación", auto_now_add=True)

    class Meta:
        verbose_name = "empresa"
        verbose_name_plural = "empresas"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Cargo(models.Model):
    """Puesto de trabajo dentro del kiosco (cajero, administrador, etc.)."""

    nombre = models.CharField("nombre", max_length=100, unique=True)
    descripcion = models.TextField("descripción", blank=True)

    class Meta:
        verbose_name = "cargo"
        verbose_name_plural = "cargos"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Empleado(models.Model):
    """Ficha del empleado, ligada 1 a 1 con el usuario de Django para el login."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="empleado",
        verbose_name="usuario",
    )
    cargo = models.ForeignKey(
        Cargo,
        on_delete=models.PROTECT,
        related_name="empleados",
        verbose_name="cargo",
    )
    nombre = models.CharField("nombre", max_length=100)
    apellido = models.CharField("apellido", max_length=100)
    dni = models.CharField("DNI", max_length=8, unique=True)
    cuil = models.CharField("CUIL", max_length=11, unique=True)
    telefono = models.CharField("teléfono", max_length=30, blank=True)
    email = models.EmailField("email", blank=True)
    direccion = models.CharField("dirección", max_length=200, blank=True)
    fecha_nacimiento = models.DateField("fecha de nacimiento", null=True, blank=True)
    fecha_ingreso = models.DateField("fecha de ingreso")
    activo = models.BooleanField("activo", default=True)

    class Meta:
        verbose_name = "empleado"
        verbose_name_plural = "empleados"
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


class Proveedor(models.Model):
    """Proveedor de mercadería del kiosco."""

    razon_social = models.CharField("razón social", max_length=150)
    cuit = models.CharField("CUIT", max_length=11, unique=True)
    telefono = models.CharField("teléfono", max_length=30, blank=True)
    email = models.EmailField("email", blank=True)
    direccion = models.CharField("dirección", max_length=200, blank=True)
    activo = models.BooleanField("activo", default=True)

    class Meta:
        verbose_name = "proveedor"
        verbose_name_plural = "proveedores"
        ordering = ["razon_social"]

    def __str__(self):
        return self.razon_social


class Producto(models.Model):
    """Artículo a la venta en el kiosco, con costos y stock."""

    nombre = models.CharField("nombre", max_length=150)
    codigo_barras = models.CharField("código de barras", max_length=50, unique=True, blank=True)
    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.PROTECT,
        related_name="productos",
        verbose_name="proveedor",
        null=True,
        blank=True,
    )
    precio_compra = models.DecimalField("precio de compra", max_digits=10, decimal_places=2)
    precio_venta = models.DecimalField("precio de venta", max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField("stock", default=0)
    stock_minimo = models.PositiveIntegerField("stock mínimo", default=0)
    activo = models.BooleanField("activo", default=True)

    class Meta:
        verbose_name = "producto"
        verbose_name_plural = "productos"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

    @property
    def stock_bajo(self):
        return self.stock <= self.stock_minimo


class Compra(models.Model):
    """Compra de mercadería a un proveedor."""

    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.PROTECT,
        related_name="compras",
        verbose_name="proveedor",
    )
    empleado = models.ForeignKey(
        Empleado,
        on_delete=models.PROTECT,
        related_name="compras",
        verbose_name="empleado responsable",
    )
    fecha = models.DateTimeField("fecha", auto_now_add=True)
    total = models.DecimalField("total", max_digits=12, decimal_places=2, default=0)
    observaciones = models.TextField("observaciones", blank=True)

    class Meta:
        verbose_name = "compra"
        verbose_name_plural = "compras"
        ordering = ["-fecha"]

    def __str__(self):
        return f"Compra #{self.pk} - {self.proveedor}"


class DetalleCompra(models.Model):
    """Renglón de una compra: producto, cantidad y precio acordado."""

    compra = models.ForeignKey(
        Compra,
        on_delete=models.CASCADE,
        related_name="detalles",
        verbose_name="compra",
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name="detalles_compra",
        verbose_name="producto",
    )
    cantidad = models.PositiveIntegerField("cantidad", default=1)
    precio_unitario = models.DecimalField("precio unitario", max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "detalle de compra"
        verbose_name_plural = "detalles de compra"

    def __str__(self):
        return f"{self.cantidad}x {self.producto}"

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario