from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LogoutView
from django.urls import path, reverse_lazy

from . import views
from .forms import NuevaClaveForm, RecuperarClaveForm

app_name = "usuarios"

urlpatterns = [
    path("login/", views.LoginKioscoView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("post-login/", views.post_login, name="post_login"),
    path("sin-rol/", views.sin_rol, name="sin_rol"),
    # Recuperación de contraseña por email
    path(
        "recuperar/",
        auth_views.PasswordResetView.as_view(
            template_name="usuarios/recuperar_clave.html",
            form_class=RecuperarClaveForm,
            email_template_name="usuarios/email_recuperacion.txt",
            subject_template_name="usuarios/email_recuperacion_subject.txt",
            success_url=reverse_lazy("usuarios:recuperacion_enviada"),
        ),
        name="recuperar_clave",
    ),
    path(
        "recuperar/enviada/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="usuarios/recuperacion_enviada.html"
        ),
        name="recuperacion_enviada",
    ),
    path(
        "recuperar/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="usuarios/resetear_clave.html",
            form_class=NuevaClaveForm,
            success_url=reverse_lazy("usuarios:recuperacion_completada"),
        ),
        name="resetear_clave",
    ),
    path(
        "recuperar/completada/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="usuarios/recuperacion_completada.html"
        ),
        name="recuperacion_completada",
    ),
]
