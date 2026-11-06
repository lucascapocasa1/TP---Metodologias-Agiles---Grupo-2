from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render

from .decorators import es_administrador, es_cajero
from .forms import LoginKioscoForm, RegistroUsuarioForm
from .middleware import activar_candado_admin, puede_entrar_al_admin


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
        return redirect("ventas:pantalla_cobro")

    # Usuario logueado pero sin rol asignado todavía (caso de borde:
    # el admin creó el usuario pero se olvidó de meterlo en un grupo).
    return redirect("usuarios:sin_rol")


@login_required
def sin_rol(request):
    return render(request, "usuarios/sin_rol.html")


def confirmar_acceso_admin(request):
    """
    Segundo candado del panel de Django (/admin/): pide la contraseña
    de nuevo aunque el usuario ya esté logueado en la app (HU pedida
    por el dueño). La pantalla también está oculta: quien no debería
    entrar acá recibe 404.

    Si la contraseña es correcta, guarda el candado en la sesión y
    redirige a la ruta /admin/... que venía en el parámetro next.
    """
    if not puede_entrar_al_admin(request.user):
        raise Http404

    # next solo puede apuntar al panel de Django (evita open redirect).
    next_url = request.POST.get("next") or request.GET.get("next") or "/admin/"
    if not next_url.startswith("/admin/"):
        next_url = "/admin/"

    error = False
    if request.method == "POST":
        password = request.POST.get("password", "")
        if request.user.check_password(password):
            activar_candado_admin(request.session)
            return redirect(next_url)
        error = True

    return render(
        request,
        "usuarios/confirmar_admin.html",
        {"next": next_url, "error": error, "usuario": request.user},
    )
