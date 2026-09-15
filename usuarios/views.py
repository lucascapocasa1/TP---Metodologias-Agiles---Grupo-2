from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .decorators import es_administrador, es_cajero
from .forms import LoginKioscoForm


class LoginKioscoView(LoginView):
    """Pantalla de login. Usamos el LoginView de Django tal cual (Django Auth),
    solo le cambiamos el template y el form (estilos Bootstrap)."""

    template_name = "usuarios/login.html"
    authentication_form = LoginKioscoForm
    redirect_authenticated_user = True


@login_required
def post_login(request):
    """
    A dónde mandamos al usuario justo después de loguearse, según su rol.
    Esto resuelve el pedido: cada uno cae directo en su propia pantalla,
    sin ver la del otro.
    """
    user = request.user
    if es_administrador(user):
        return redirect("administracion:dashboard")
    if es_cajero(user):
        return redirect("ventas:pantalla_cobro")

    # Usuario logueado pero sin rol asignado todavía (caso de borde:
    # el admin creó el usuario pero se olvidó de meterlo en un grupo).
    return redirect("usuarios:sin_rol")


@login_required
def sin_rol(request):
    return render(request, "usuarios/sin_rol.html")
