from decimal import Decimal

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
     costo = models.DecimalField(
         max_digits=10,
         decimal_places=2,
         default=Decimal("0.00"),
         help_text="Precio de compra unitario. Lo ve solo el Administrador.",
     )
     stock = models.IntegerField(default=0)
     categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, related_name='productos')
     activo = models.BooleanField(default=True)
     def __str__(self):
         return f"{self.nombre} - ${self.precio}"

     @property
     def margen_unitario(self):
         """Ganancia por unidad (precio de venta menos costo)."""
         return self.precio - self.costo

     @property
     def margen_porcentual(self):
         """Margen sobre el costo, en porcentaje. 0 si el costo es 0."""
         if not self.costo:
             return Decimal("0.00")
         return (self.margen_unitario / self.costo) * Decimal("100")

     @property
     def valor_stock_costo(self):
         """Cuánto dinero del negocio está parado en este producto, a costo."""
         return self.costo * self.stock

     @property
     def valor_stock_venta(self):
         """Lo mismo, pero al precio de venta (capital potencial)."""
         return self.precio * self.stock
     
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
     costo_unitario = models.DecimalField(
         max_digits=10,
         decimal_places=2,
         default=Decimal("0.00"),
         help_text="Costo congelado al momento de la venta, para que el margen "
                   "histórico no cambie si después se actualiza el precio de compra.",
     )
     def subtotal(self):
         return self.cantidad * self.precio_unitario
     def costo_total(self):
         return self.cantidad * self.costo_unitario
     def ganancia(self):
         return self.subtotal() - self.costo_total()
     def __str__(self):
         return f"{self.cantidad}x {self.producto.nombre}"
     
     
# Create your models here.
