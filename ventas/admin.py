from django.contrib import admin

from .models import Cliente, Contacto, DetalleVenta, Venta


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nombre", "apellido", "cuit", "edad", "telefono", "email")
    search_fields = ("nombre", "apellido", "cuit")


@admin.register(Contacto)
class ContactoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "proveedor", "empresa", "cargo", "telefono", "es_principal")
    list_filter = ("es_principal",)
    search_fields = ("nombre", "cargo")


class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    extra = 1


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ("pk", "empleado", "cliente", "fecha", "total", "forma_pago")
    list_filter = ("fecha", "forma_pago")
    inlines = [DetalleVentaInline]
    readonly_fields = ("fecha", "total")


@admin.register(DetalleVenta)
class DetalleVentaAdmin(admin.ModelAdmin):
    list_display = ("venta", "producto", "cantidad", "precio_unitario", "subtotal")