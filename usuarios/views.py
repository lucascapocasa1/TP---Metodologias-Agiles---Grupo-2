from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .decorators import es_administrador, es_cajero
from .forms import LoginKioscoForm, RegistroUsuarioForm


class LoginKioscoView(LoginView):
    """Pantalla de login. Usamos el LoginView de Django tal cual (Django Auth),
    solo le cambiamos el template y el form (estilos Bootstrap)."""

    template_name = "usuarios/login.html"
    authentication_form = LoginKioscoForm
    redirect_authenticated_user = True


def registro_usuario(request):
    """
    Registro de usuario nuevo. Cualquiera puede crear su cuenta.
    El rol (Administrador/Cajero) lo asigna el administrador después
    desde el panel de Django admin o el manager de usuarios.
    """
    if request.user.is_authenticated:
        return redirect("usuarios:post_login")

    if request.method == "POST":
        form = RegistroUsuarioForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(
                request,
                f"¡Cuenta creada! Ahora podés ingresar con el usuario «{user.username}».",
            )
            return redirect("usuarios:login")
    else:
        form = RegistroUsuarioForm()

    return render(request, "usuarios/registro.html", {"form": form})


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
        return redirect("ventas:cobro")

    # Usuario logueado pero sin rol asignado todavía (caso de borde:
    # el admin creó el usuario pero se olvidó de meterlo en un grupo).
    return redirect("usuarios:sin_rol")


@login_required
def sin_rol(request):
    return render(request, "usuarios/sin_rol.html")
