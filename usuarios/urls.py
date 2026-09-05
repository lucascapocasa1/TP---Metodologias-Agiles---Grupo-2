from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = "usuarios"

urlpatterns = [
    path("login/", views.LoginKioscoView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("post-login/", views.post_login, name="post_login"),
    path("sin-rol/", views.sin_rol, name="sin_rol"),
]
