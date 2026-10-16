from django.urls import path

from . import views

app_name = "clientes"

urlpatterns = [
    # Gestión del Administrador
    path("", views.listar_clientes, name="listar_clientes"),
    path("crear/", views.crear_cliente, name="crear_cliente"),
    path(
        "<int:cliente_id>/editar/",
        views.editar_cliente,
        name="editar_cliente",
    ),
    path(
        "<int:cliente_id>/eliminar/",
        views.eliminar_cliente,
        name="eliminar_cliente",
    ),
    path(
        "<int:cliente_id>/",
        views.detalle_cliente,
        name="detalle_cliente",
    ),
    # Asociación a la venta desde la pantalla de cobro
    path("buscar/", views.buscar_cliente, name="buscar"),
    path("asociar/", views.asociar_cliente, name="asociar"),
    path("quitar/", views.quitar_cliente, name="quitar"),
    path("alta-rapida/", views.alta_rapida, name="alta_rapida"),
]
