from django.contrib import admin

from .models import Cliente


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "nombre",
        "apellido",
        "dni",
        "puntos",
        "fecha_registro",
        "activo",
    ]
    list_filter = ["activo", "fecha_registro"]
    search_fields = ["nombre", "apellido", "dni", "email"]
