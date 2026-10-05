from django.urls import path

from . import views

app_name = "ventas"


urlpatterns = [
    path("cobro/", views.pantalla_cobro, name="pantalla_cobro"),
    path("cobro/buscar/", views.cobro_buscar, name="cobro_buscar"),
    path("cobro/agregar/", views.cobro_agregar, name="cobro_agregar"),
    path("cobro/cantidad/", views.cobro_cantidad, name="cobro_cantidad"),
    path("cobro/confirmar/", views.cobro_confirmar, name="cobro_confirmar"),
    path("productos/", views.lista_productos, name="lista_productos"),
    path("productos/agregar/", views.agregar_producto, name="agregar_producto"),
    path(
        "productos/<int:producto_id>/editar/",
        views.editar_producto,
        name="editar_producto",
    ),
    path(
        "productos/<int:producto_id>/eliminar/",
        views.eliminar_producto,
        name="eliminar_producto",
    ),
]

