from django.conf import settings
from django.db import models


class RegistroAuditoria(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registros_auditoria",
    )
    accion = models.CharField(max_length=255)
    detalle = models.TextField(blank=True, default="")
    fecha = models.DateTimeField(auto_now_add=True)
    ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-fecha"]
        verbose_name = "registro de auditoría"
        verbose_name_plural = "registros de auditoría"

    def __str__(self):
        usuario = self.usuario.username if self.usuario else "Sistema"
        return f"[{self.fecha:%d/%m/%Y %H:%M}] {usuario}: {self.accion}"
