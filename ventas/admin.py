from django.contrib import admin
from .models import Categoria, Producto, Venta, DetalleVenta
class DetalleVentaInline(admin.TabularInline):
     model = DetalleVenta
     extra = 0
class VentaAdmin(admin.ModelAdmin):
     list_display = ['id', 'usuario', 'fecha', 'total'] # ✅ Solo campos que SÍ existen
     list_filter = ['fecha', 'usuario'] # ✅ Campos reales
     inlines = [DetalleVentaInline]
class ProductoAdmin(admin.ModelAdmin):
     list_display = ['nombre', 'precio', 'categoria', 'stock']
     list_filter = ['categoria']
admin.site.register(Categoria)
admin.site.register(Producto, ProductoAdmin)
admin.site.register(Venta, VentaAdmin)





# Register your models here.
