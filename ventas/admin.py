from django.contrib import admin

from .models import DetalleVenta, Producto, Venta


class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    extra = 0
    readonly_fields = ["subtotal"]

    def subtotal(self, obj):
        return f"${obj.subtotal()}"

    subtotal.short_description = "Subtotal"


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ["icono", "nombre", "categoria", "codigo_barras", "precio", "activo"]
    list_filter = ["activo", "categoria"]
    search_fields = ["nombre", "codigo_barras", "categoria"]


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "cajero",
        "fecha",
        "total",
        "metodo_pago",
        "vuelto",
    ]
    list_filter = ["metodo_pago", "fecha"]
    readonly_fields = ["fecha"]
    inlines = [DetalleVentaInline]
