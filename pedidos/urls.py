from django.urls import path

from . import views

app_name = "pedidos"

urlpatterns = [
    # Público (sin login)
    path("", views.catalogo, name="catalogo"),
    path("agregar/", views.pedido_agregar, name="pedido_agregar"),
    path("quitar/", views.pedido_quitar, name="pedido_quitar"),
    path("confirmar/", views.pedido_confirmar, name="pedido_confirmar"),
    # Panel interno (solo Administrador)
    path("panel/", views.lista_pedidos, name="lista_pedidos"),
    path("panel/<int:pedido_id>/", views.detalle_pedido, name="detalle_pedido"),
    path(
        "panel/clientes/buscar/",
        views.buscar_cliente_pedido,
        name="buscar_cliente",
    ),
    path(
        "panel/<int:pedido_id>/entregar/",
        views.entregar_pedido,
        name="entregar",
    ),
    path(
        "panel/<int:pedido_id>/estado/<str:estado>/",
        views.cambiar_estado_pedido,
        name="cambiar_estado",
    ),
]
