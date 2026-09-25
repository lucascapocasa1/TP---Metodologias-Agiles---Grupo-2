from django.urls import path

from . import views

app_name = "ventas"


urlpatterns = [
    path("cobro/", views.cobro, name="cobro"),
    path("productos/", views.lista_productos, name="lista_productos"),
    path("productos/agregar/", views.agregar_producto, name="agregar_producto"),
]

