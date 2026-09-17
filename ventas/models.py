from django.db import models
 
class Categoria(models.Model):
     nombre = models.CharField(max_length=100)
     descripcion = models.TextField(blank=True, null=True)
     def __str__(self):
         return self.nombre
class Producto(models.Model):
     nombre = models.CharField(max_length=150)
     descripcion = models.TextField(blank=True, null=True)
     precio = models.DecimalField(max_digits=10, decimal_places=2)
     stock = models.IntegerField(default=0)
     categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, related_name='productos')
     activo = models.BooleanField(default=True)
     def __str__(self):
         return f"{self.nombre} - ${self.precio}"
     
class Venta(models.Model):
     fecha = models.DateTimeField(auto_now_add=True)
     total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
     finalizada = models.BooleanField(default=False)
     def __str__(self):
         return f"Venta N° {self.id} - {self.fecha.strftime('%d/%m/%Y')}"
class DetalleVenta(models.Model):
     venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles')
     producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
     cantidad = models.IntegerField(default=1)
     precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
     def subtotal(self):
         return self.cantidad * self.precio_unitario
     def __str__(self):
         return f"{self.cantidad}x {self.producto.nombre}"
     
     
# Create your models here.
