from django.contrib import admin

from .models import Cargo, Compra, DetalleCompra, Empresa, Empleado, Producto, Proveedor


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "cuit", "telefono", "email")
    search_fields = ("nombre", "cuit")


@admin.register(Cargo)
class CargoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "descripcion")
    search_fields = ("nombre",)


@admin.register(Empleado)
class EmpleadoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "apellido", "dni", "cargo", "edad", "activo")
    list_filter = ("cargo", "activo")
    search_fields = ("nombre", "apellido", "dni", "cuil")


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ("razon_social", "cuit", "telefono", "email", "activo")
    search_fields = ("razon_social", "cuit")


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "codigo_barras", "proveedor", "precio_venta", "stock", "stock_minimo", "activo")
    list_filter = ("proveedor", "activo")
    search_fields = ("nombre", "codigo_barras")


class DetalleCompraInline(admin.TabularInline):
    model = DetalleCompra
    extra = 1


@admin.register(Compra)
class CompraAdmin(admin.ModelAdmin):
    list_display = ("pk", "proveedor", "empleado", "fecha", "total")
    list_filter = ("fecha",)
    inlines = [DetalleCompraInline]
    readonly_fields = ("fecha", "total")


@admin.register(DetalleCompra)
class DetalleCompraAdmin(admin.ModelAdmin):
    list_display = ("compra", "producto", "cantidad", "precio_unitario", "subtotal")