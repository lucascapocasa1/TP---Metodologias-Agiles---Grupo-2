from django.contrib import admin
from .models import Categoria, Producto, Venta, DetalleVenta

class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    extra = 1

@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    inlines = [DetalleVentaInline]
    list_display = ['id', 'fecha', 'total', 'finalizada']
    list_filter = ['finalizada', 'fecha']

admin.site.register(Categoria)
admin.site.register(Producto)

# Register your models here.


from .models import PagoMercadoPago  # noqa: E402


@admin.register(PagoMercadoPago)
class PagoMercadoPagoAdmin(admin.ModelAdmin):
    list_display = ("venta", "estado", "simulado", "payment_id", "creado")
    list_filter = ("estado", "simulado")
    readonly_fields = ("token", "creado", "actualizado")
