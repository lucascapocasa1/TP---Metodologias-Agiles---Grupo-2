from django.contrib import admin

from .models import Empleado


@admin.register(Empleado)
class EmpleadoAdmin(admin.ModelAdmin):
    list_display = ["usuario", "negocio", "activo"]
    list_filter = ["activo", "negocio"]
    search_fields = ["usuario__username", "negocio__nombre"]
