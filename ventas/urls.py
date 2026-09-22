from django.urls import path

from . import views

app_name = "ventas"


urlpatterns = [
    path("cobro/", views.pantalla_cobro, name="pantalla_cobro"),
    path("productos/", views.lista_productos, name="lista_productos"),
    path("productos/agregar/", views.agregar_producto, name="agregar_producto"),
]

