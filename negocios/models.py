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
