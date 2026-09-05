from django.urls import path

from . import views

app_name = "ventas"

urlpatterns = [
    path("cobro/", views.pantalla_cobro, name="pantalla_cobro"),
]
