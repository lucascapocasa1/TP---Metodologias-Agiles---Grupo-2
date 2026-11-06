from django.urls import path

from . import views, views_publicos

app_name = "pedidos"

urlpatterns = [
    # Público (sin login) - catálogo general (HU-13, mantiene compatibilidad)
    path("", views.catalogo, name="catalogo"),
    path("agregar/", views.pedido_agregar, name="pedido_agregar"),
    path("quitar/", views.pedido_quitar, name="pedido_quitar"),
    path("confirmar/", views.pedido_confirmar, name="pedido_confirmar"),
    # Panel interno (solo Administrador) - DEBE ir antes que las rutas con slug
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
    # Público por negocio (/t/<slug>/)
    path("<slug:slug>/", views_publicos.catalogo_negocio, name="catalogo_negocio"),
    path("<slug:slug>/agregar/", views_publicos.pedido_agregar_publico, name="pedido_agregar_publico"),
    path("<slug:slug>/quitar/", views_publicos.pedido_quitar_publico, name="pedido_quitar_publico"),
    path("<slug:slug>/carrito/", views_publicos.pedido_carrito_publico, name="pedido_carrito_publico"),
    path("<slug:slug>/confirmar/", views_publicos.pedido_confirmar_publico, name="pedido_confirmar_publico"),
]
