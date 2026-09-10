from auditoria.models import RegistroAuditoria


def registrar_login(usuario, request):
    RegistroAuditoria.objects.create(
        usuario=usuario,
        accion="Inicio de sesión",
        ip=_obtener_ip(request),
    )


def registrar_logout(usuario, request):
    RegistroAuditoria.objects.create(
        usuario=usuario,
        accion="Cierre de sesión",
        ip=_obtener_ip(request),
    )


def registrar_accion(usuario, accion, detalle="", request=None):
    RegistroAuditoria.objects.create(
        usuario=usuario,
        accion=accion,
        detalle=detalle,
        ip=_obtener_ip(request) if request else None,
    )


def _obtener_ip(request):
    x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded:
        return x_forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")
