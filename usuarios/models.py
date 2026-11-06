from django.conf import settings
from django.db import models


class Empleado(models.Model):
    """
    Vincula un usuario de Django a un único negocio.

    Un empleado siempre trabaja en un solo comercio (o en la ferretería,
    o en la dietética, etc.). El rol (Administrador, Cajero) sigue
    gestionándose vía Django Groups.
    """

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="empleado",
        verbose_name="Usuario",
    )
    negocio = models.ForeignKey(
        "negocios.Negocio",
        on_delete=models.CASCADE,
        related_name="empleados",
        verbose_name="Negocio",
        help_text="El único comercio donde trabaja este empleado.",
    )
    activo = models.BooleanField(
        default=True,
        verbose_name="Activo",
    )

    class Meta:
        verbose_name = "empleado"
        verbose_name_plural = "empleados"
        ordering = ["usuario__username"]

    def __str__(self):
        return f"{self.usuario.username} · {self.negocio.nombre}"
