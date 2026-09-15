from django.contrib import admin

from auditoria.models import RegistroAuditoria


@admin.register(RegistroAuditoria)
class RegistroAuditoriaAdmin(admin.ModelAdmin):
    list_display = ("fecha", "usuario", "accion", "ip")
    list_filter = ("accion", "fecha")
    search_fields = ("accion", "detalle", "usuario__username")
    readonly_fields = ("usuario", "accion", "detalle", "fecha", "ip")
    ordering = ("-fecha",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
