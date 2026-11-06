from django.contrib import admin

from .models import Negocio


@admin.register(Negocio)
class NegocioAdmin(admin.ModelAdmin):
    list_display = ["nombre", "slug", "activo", "fecha_creacion"]
    list_filter = ["activo"]
    search_fields = ["nombre", "slug"]
    prepopulated_fields = {"slug": ("nombre",)}
