"""
Control de acceso al panel de Django admin (/admin/).

Dos candados, como pidió el dueño:

  1. Para el resto del mundo el panel no existe: anónimos, cajeros y
     usuarios "staff" sin rol Administrador ven un 404 (con el
     templates/404.html del sistema), nunca el login de Django ni un 403
     que delate que la URL está viva.
  2. Un Administrador logueado en la app todavía tiene que confirmar su
     contraseña en usuarios/confirmar_acceso_admin/ antes de entrar. La
     confirmación dura ADMIN_CONFIRMACION_TTL_SEGUNDOS (por .env) y se
     pierde al hacer logout.

Después de pasar los candados, Django aplica su chequeo normal de
is_staff en cada vista del admin.
"""
import time
from urllib.parse import urlencode

from django.conf import settings
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.views.defaults import page_not_found

from .decorators import es_administrador

# Clave de la sesión donde se guarda el timestamp de la última confirmación.
CLAVE_CANDADO = "admin_acceso_ts"


def puede_entrar_al_admin(user):
    """Cuenta completa habilitada para el panel de Django."""
    return user.is_authenticated and user.is_active and user.is_staff and es_administrador(user)


def candado_admin_valido(session):
    """True si la contraseña se confirmó y el candado no venció."""
    timestamp = session.get(CLAVE_CANDADO)
    if not timestamp:
        return False
    ttl = getattr(settings, "ADMIN_CONFIRMACION_TTL_SEGUNDOS", 1800)
    return (time.time() - timestamp) <= ttl


def activar_candado_admin(session):
    """Marca en la sesión que el usuario acaba de confirmar su contraseña."""
    session[CLAVE_CANDADO] = time.time()


class ControlAdminDjangoMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/admin/"):
            respuesta = self._chequear_acceso(request)
            if respuesta is not None:
                return respuesta
        return self.get_response(request)

    def _chequear_acceso(self, request):
        """Devuelve una respuesta si hay que frenar el acceso, o None
        para dejar pasar la petición al panel de Django."""
        # Candado 1: sin cuenta completa no existe nada acá.
        if not puede_entrar_al_admin(request.user):
            # page_not_found ya devuelve el 404.html renderizado.
            return page_not_found(request, Http404())

        # Candado 2: falta confirmar la contraseña (o venció).
        if not candado_admin_valido(request.session):
            url = reverse("usuarios:confirmar_acceso_admin")
            query = urlencode({"next": request.get_full_path()})
            return redirect(f"{url}?{query}")

        # Administrador confirmado que pidió el login de Django: al panel.
        if request.path == reverse("admin:login"):
            return redirect("admin:index")

        return None
