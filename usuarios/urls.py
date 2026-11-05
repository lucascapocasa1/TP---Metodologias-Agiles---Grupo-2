from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = "usuarios"

urlpatterns = [
    path("login/", views.LoginKioscoView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("post-login/", views.post_login, name="post_login"),
    path("sin-rol/", views.sin_rol, name="sin_rol"),
    path("registro/", views.registro_usuario, name="registro"),
    
    # Recuperación de contraseña con Resend
    path(
        "recuperar-password/",
        auth_views.PasswordResetView.as_view(
            template_name="usuarios/password_reset_form.html",
            # Sin estos templates propios, Django usa los de
            # `django.contrib.admin`, que arman el link con
            # `{% url 'password_reset_confirm' %}` (sin namespace) y el envío
            # termina en NoReverseMatch.
            subject_template_name="usuarios/password_reset_subject.txt",
            email_template_name="usuarios/password_reset_email.txt",
            html_email_template_name="usuarios/password_reset_email.html",
            success_url="/usuarios/recuperar-password/enviado/",
        ),
        name="password_reset",
    ),
    path(
        "recuperar-password/enviado/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="usuarios/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "recuperar-password/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="usuarios/password_reset_confirm.html",
            success_url="/usuarios/recuperar-password/completado/",
        ),
        name="password_reset_confirm",
    ),
    path(
        "recuperar-password/completado/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="usuarios/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
]