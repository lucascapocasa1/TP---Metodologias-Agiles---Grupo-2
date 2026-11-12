from datetime import timedelta
from decimal import Decimal
import uuid

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
    motivo_anulacion = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Motivo de anulación",
        help_text="Motivo por el cual se anuló este documento.",
    )
    archivo = models.FileField(
        upload_to="documentos/adjuntos/",
        blank=True,
        null=True,
        verbose_name="Adjunto",
        help_text="PDF o imagen de la factura como comprobante (opcional).",
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
        indexes = [
            models.Index(
                fields=["negocio", "estado", "fecha_vencimiento"],
                name="doc_neg_estado_venc_idx",
            ),
        ]

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

    @property
    def esta_por_vencer_lejos(self):
        """True si vence entre 8 y 15 días y aún no está pagada."""
        if self.estado != "pendiente":
            return False
        from django.utils import timezone

        hoy = timezone.localdate()
        dias = (self.fecha_vencimiento - hoy).days
        return 8 <= dias <= 15

    @property
    def dias_restantes(self):
        """Días que faltan para el vencimiento (negativo si ya venció)."""
        from django.utils import timezone

        if hasattr(self, "_dias_restantes_cache"):
            return self._dias_restantes_cache
        return (self.fecha_vencimiento - timezone.localdate()).days

    @dias_restantes.setter
    def dias_restantes(self, valor):
        self._dias_restantes_cache = valor

    @property
    def dias_vencida(self):
        """Días que lleva vencida (valor absoluto de dias_restantes si venció)."""
        if self.esta_vencida:
            return abs(self.dias_restantes)
        return 0

    @property
    def es_archivo_imagen(self):
        """True si el archivo adjunto es una imagen (jpg, jpeg, png)."""
        if not self.archivo:
            return False
        nombre = self.archivo.name.lower()
        return nombre.endswith((".jpg", ".jpeg", ".png"))

    @property
    def es_archivo_pdf(self):
        """True si el archivo adjunto es un PDF."""
        if not self.archivo:
            return False
        return self.archivo.name.lower().endswith(".pdf")

    @property
    def icono_archivo(self):
        """Devuelve la clase de ícono de Bootstrap según el tipo de archivo."""
        if self.es_archivo_imagen:
            return "bi bi-file-earmark-image"
        if self.es_archivo_pdf:
            return "bi bi-file-earmark-pdf"
        return "bi bi-file-earmark"

    def __str__(self):
        return f"{self.numero_factura or self.nombre_proveedor or 'Sin nombre'} - ${self.monto}"


class PagoDocumento(models.Model):
    """
    Registro de un pago aplicado a un documento (factura).

    Es la fuente de verdad de cuánto y cuándo se pagó cada factura.
    `monto_pagado` en Documento se mantiene como caché y se actualiza
    desde acá mediante los services, para no degradar los listados.

    Un mismo `grupo_pago` agrupa los pagos de una operación FIFO (pago a
    un proveedor repartido en varias facturas), así se puede mostrar como
    un solo movimiento y deshacerlo completo si es necesario.
    """

    METODOS = [
        ("efectivo", "Efectivo"),
        ("transferencia", "Transferencia"),
        ("cheque", "Cheque"),
        ("tarjeta", "Tarjeta"),
        ("otro", "Otro"),
    ]

    documento = models.ForeignKey(
        Documento,
        on_delete=models.CASCADE,
        related_name="pagos_registrados",
        verbose_name="Documento",
    )
    negocio = models.ForeignKey(
        Negocio,
        on_delete=models.CASCADE,
        related_name="pagos_documentos",
        verbose_name="Negocio",
    )
    fecha = models.DateField(verbose_name="Fecha del pago")
    monto = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Monto pagado",
    )
    metodo = models.CharField(
        max_length=20,
        choices=METODOS,
        default="efectivo",
        verbose_name="Método de pago",
    )
    comprobante = models.FileField(
        upload_to="documentos/pagos/",
        blank=True,
        null=True,
        verbose_name="Comprobante",
        help_text="PDF o imagen del comprobante de pago (opcional).",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Usuario que registró el pago",
    )
    nota = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Nota",
        help_text="Observaciones sobre este pago (opcional).",
    )
    grupo_pago = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Grupo de pago",
        help_text="Agrupa los pagos de una misma operación (p. ej. FIFO a un proveedor).",
    )
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación",
    )

    class Meta:
        verbose_name = "pago de documento"
        verbose_name_plural = "pagos de documentos"
        ordering = ["-fecha", "-fecha_creacion"]
        indexes = [
            models.Index(
                fields=["documento", "-fecha"],
                name="pago_doc_fecha_idx",
            ),
            models.Index(
                fields=["grupo_pago"],
                name="pago_grupo_idx",
            ),
        ]

    def __str__(self):
        return f"Pago ${self.monto} a {self.documento} ({self.fecha})"


class ArchivoGuardado(models.Model):
    """Contenido de los adjuntos (facturas, comprobantes) guardado en la base.

    Render borra el disco en cada deploy, así que los FileField usan
    `negocios.storage.BaseDeDatosStorage`, que guarda los bytes acá.
    """

    nombre = models.CharField(max_length=255, unique=True)
    contenido = models.BinaryField()
    tipo = models.CharField(max_length=100, blank=True)
    creado = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre
