from django.db import models


class Cliente(models.Model):
    """Cliente del kiosco: datos básicos + fidelidad (HU-12).

    Los puntos se acumulan al confirmar cada venta (1 punto cada $100) y
    nunca se recalculan: `Venta.puntos_ganados` guarda lo que sumó cada
    compra para el historial.
    """

    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    dni = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="DNI/CUIT",
        help_text="Sin puntos ni guiones. No puede repetirse.",
    )
    telefono = models.CharField(
        max_length=30, blank=True, verbose_name="Teléfono"
    )
    email = models.EmailField(blank=True)
    fecha_registro = models.DateTimeField(
        auto_now_add=True, verbose_name="Fecha de registro"
    )
    puntos = models.PositiveIntegerField(
        default=0, verbose_name="Puntos de fidelidad"
    )
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["apellido", "nombre"]
        verbose_name = "cliente"
        verbose_name_plural = "clientes"

    def __str__(self):
        return f"{self.nombre_completo} · DNI {self.dni}"

    @property
    def nombre_completo(self):
        return f"{self.nombre} {self.apellido}".strip()
