from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
class Categoria(models.Model):
     nombre = models.CharField(max_length=100)
     def __str__(self):
         return self.nombre
class Producto(models.Model):
     nombre = models.CharField(max_length=100)
     precio = models.DecimalField(max_digits=10, decimal_places=2)
     categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)
     stock = models.IntegerField(default=0)
     codigo_barras = models.CharField(max_length=50, blank=True, null=True)
     def __str__(self):
         return f"{self.nombre} - ${self.precio}"
class Venta(models.Model):
     usuario = models.ForeignKey(User, on_delete=models.CASCADE)
     fecha = models.DateTimeField(default=timezone.now)
     total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
     def __str__(self):
         return f"Venta {self.id} - ${self.total}"
class DetalleVenta(models.Model):
     venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles')
     producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
     cantidad = models.IntegerField(default=1)
     subtotal = models.DecimalField(max_digits=10, decimal_places=2)
     def save(self, *args, **kwargs):
         self.subtotal = self.producto.precio * self.cantidad
         super().save(*args, **kwargs)
     def __str__(self):
         return f"{self.cantidad}x {self.producto.nombre}"
     
     
# Create your models here.
