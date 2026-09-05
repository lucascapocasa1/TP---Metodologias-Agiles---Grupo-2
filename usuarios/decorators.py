"""
Utilidades de autorización por rol para el Sprint 1.

El negocio define dos roles (Grupos de Django):
    - "Administrador": acceso total (stock, costos, reportes, precios).
    - "Cajero": acceso único a la pantalla de cobro.

En vez de usar permisos individuales (que se verán en sprints futuros
para acciones más finas, ej. "puede_modificar_precio"), en este sprint
alcanza con chequear pertenencia a grupo, que es lo que pidió el dueño:
"el cajero entra con su usuario para cobrar y punto".
"""
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def es_administrador(user):
    """True si el usuario pertenece al grupo Administrador (o es superusuario)."""
    return user.is_authenticated and (
        user.is_superuser or user.groups.filter(name="Administrador").exists()
    )


def es_cajero(user):
    """True si el usuario pertenece al grupo Cajero."""
    return user.is_authenticated and user.groups.filter(name="Cajero").exists()


def rol_requerido(*roles_permitidos):
    """
    Decorador para vistas basadas en función.
    Uso: @rol_requerido("Administrador")

    Si el usuario no está logueado, Django lo manda al login (login_required).
    Si está logueado pero no tiene el rol, se lanza 403 (Forbidden), que es
    justo lo que pidió el dueño: que el cajero NO pueda ni entrar a esas
    pantallas, no que se le oculte un botón nada más.
    """

    def decorador(vista):
        @wraps(vista)
        @login_required
        def _envoltorio(request, *args, **kwargs):
            if request.user.is_superuser:
                return vista(request, *args, **kwargs)
            if request.user.groups.filter(name__in=roles_permitidos).exists():
                return vista(request, *args, **kwargs)
            raise PermissionDenied(
                "No tenés permisos para acceder a esta sección del sistema."
            )

        return _envoltorio

    return decorador


class RolRequeridoMixin:
    """
    Igual que rol_requerido pero para Class-Based Views (útil en sprints
    siguientes cuando administracion tenga vistas tipo ListView/CreateView).
    Definir en la vista: roles_permitidos = ["Administrador"]
    """

    roles_permitidos: list[str] = []

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login

            return redirect_to_login(request.get_full_path())

        if request.user.is_superuser or request.user.groups.filter(
            name__in=self.roles_permitidos
        ).exists():
            return super().dispatch(request, *args, **kwargs)

        raise PermissionDenied(
            "No tenés permisos para acceder a esta sección del sistema."
        )
