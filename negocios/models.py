from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import models


class Negocio(models.Model):
    """
    Representa a un comercio que utiliza Norvex.

    Cada negocio tiene sus propios productos, categorías, ventas, pedidos,
    empleados y configuración. El aislamiento de datos se garantiza
    filtrando siempre por este modelo desde el backend.
    """

    nombre = models.CharField(
        max_length=100,
        verbose_name="Nombre del negocio",
        help_text="Nombre comercial que verán los clientes y empleados.",
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
        verbose_name="Slug (URL)",
        help_text="Identificador único para la URL de la tienda online. "
        "Ejemplo: ferreteria-martillito",
    )
    logo = models.URLField(
        blank=True,
        null=True,
        verbose_name="Logo",
        help_text="URL del logo que se mostrará en la tienda online del negocio.",
    )
    direccion = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Dirección",
    )
    telefono = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="Teléfono",
    )
    whatsapp = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="WhatsApp",
        help_text="Número de WhatsApp del negocio, solo dígitos.",
    )
    email = models.EmailField(
        blank=True,
        verbose_name="Email de contacto",
    )
    horarios = models.TextField(
        blank=True,
        verbose_name="Horarios de atención",
        help_text="Ejemplo: Lun a Vie 9:00-18:00, Sáb 9:00-13:00",
    )
    color_primario = models.CharField(
        max_length=7,
        default="#00FFFF",
        verbose_name="Color primario",
        help_text="Color tema de la tienda online (formato hexadecimal).",
    )
    activo = models.BooleanField(
        default=True,
        verbose_name="Activo",
        help_text="Si está desmarcado, la tienda online no estará disponible.",
    )
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación",
    )

    class Meta:
        verbose_name = "negocio"
        verbose_name_plural = "negocios"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Proveedor(models.Model):
    """
    Proveedor de un negocio. Puede ser usado en documentos (facturas)
    para saber de quién se compró algo y cuánto se le debe.
    """

    nombre = models.CharField(
        max_length=100,
        verbose_name="Nombre del proveedor",
        help_text="Nombre del proveedor (ej. EDENOR, Sancor, etc.).",
    )
    negocio = models.ForeignKey(
        Negocio,
        on_delete=models.CASCADE,
        related_name="proveedores",
        verbose_name="Negocio",
    )
    telefono = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="Teléfono",
    )
    email = models.EmailField(
        blank=True,
        verbose_name="Email",
    )
    activo = models.BooleanField(
        default=True,
        verbose_name="Activo",
    )
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación",
    )

    class Meta:
        verbose_name = "proveedor"
        verbose_name_plural = "proveedores"
        ordering = ["nombre"]
        unique_together = [("nombre", "negocio")]

    def __str__(self):
        return self.nombre


class Documento(models.Model):
    """
    Factura o documento de pago de un negocio.

    Representa una factura que el negocio debe pagar (luz, gas, seguridad
    e higiene, proveedores, etc.). Puede tener pagos parciales y un archivo
    PDF adjunto como comprobante.
    """

    CATEGORIAS = [
        ("luz", "Luz"),
        ("gas", "Gas"),
        ("seguridad", "Seguridad e Higiene"),
        ("proveedor", "Proveedor"),
        ("otro", "Otro"),
    ]

    ESTADOS = [
        ("pendiente", "Pendiente"),
        ("pagada", "Pagada"),
        ("anulada", "Anulada"),
    ]

    negocio = models.ForeignKey(
        Negocio,
        on_delete=models.CASCADE,
        related_name="documentos",
        verbose_name="Negocio",
    )
    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documentos",
        verbose_name="Proveedor",
        help_text="Proveedor al que se le debe. Opcional si es gasto general.",
    )
    nombre_proveedor = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Nombre del proveedor",
        help_text="Si no se selecciona un proveedor de la lista, escribí el nombre aquí.",
    )
    categoria = models.CharField(
        max_length=20,
        choices=CATEGORIAS,
        default="otro",
        verbose_name="Categoría",
    )
    numero_factura = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Número de factura",
        help_text="Número de factura o comprobante.",
    )
    monto = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Monto total",
        help_text="Monto total de la factura.",
    )
    monto_pagado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Monto pagado",
        help_text="Cuánto se ya pagó de esta factura.",
    )
    fecha_emision = models.DateField(
        verbose_name="Fecha de emisión",
    )
    fecha_vencimiento = models.DateField(
        verbose_name="Fecha de vencimiento",
    )
    estado = models.CharField(
        max_length=12,
        choices=ESTADOS,
        default="pendiente",
        verbose_name="Estado",
    )
    archivo_pdf = models.FileField(
        upload_to="documentos/facturas/",
        blank=True,
        null=True,
        verbose_name="Archivo PDF",
        help_text="PDF de la factura (opcional).",
    )
    observaciones = models.TextField(
        blank=True,
        verbose_name="Observaciones",
    )
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación",
    )

    class Meta:
        verbose_name = "documento"
        verbose_name_plural = "documentos"
        ordering = ["-fecha_vencimiento"]

    @property
    def monto_pendiente(self):
        """Cuánto queda por pagar de este documento."""
        return self.monto - self.monto_pagado

    @property
    def esta_vencida(self):
        """True si la factura venció y aún no está pagada."""
        if self.estado != "pendiente":
            return False
        from django.utils import timezone

        return self.fecha_vencimiento < timezone.localdate()

    @property
    def esta_por_vencer(self):
        """True si vence en los próximos 7 días y aún no está pagada."""
        if self.estado != "pendiente":
            return False
        from django.utils import timezone

        hoy = timezone.localdate()
        return hoy <= self.fecha_vencimiento <= hoy + timedelta(days=7)

    def __str__(self):
        return f"{self.numero_factura or self.nombre_proveedor or 'Sin nombre'} - ${self.monto}"
