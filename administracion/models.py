from django.db import models
from django.contrib.auth.models import User
 

    
     
class Bitacora(models.Model):
     usuario = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Usuario")
     accion = models.CharField(max_length=150, verbose_name="Acción realizada")
     fecha_hora = models.DateTimeField(auto_now_add=True, verbose_name="Fecha y Hora")
     class Meta:
         ordering = ['-fecha_hora']
         verbose_name = "Registro de Bitácora"
         verbose_name_plural = "Bitácora de Ingresos y Ventas"
     def __str__(self):
         # Mostramos el nombre del cajero si lo tiene
         nombre_cajero = self.usuario.perfil_cajero.nombre if hasattr(self.usuario, 'perfil_cajero') else self.usuario.username
         return f"{nombre_cajero} → {self.accion} → {self.fecha_hora.strftime('%d/%m %H:%M')}"
# Create your models here.
