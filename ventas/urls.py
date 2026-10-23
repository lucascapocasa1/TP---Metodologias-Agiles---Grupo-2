from django.urls import path

from . import views, views_conexion, views_qr

app_name = "ventas"


urlpatterns = [
    path("cobro/", views.pantalla_cobro, name="pantalla_cobro"),
    path("cobro/buscar/", views.cobro_buscar, name="cobro_buscar"),
    path("cobro/agregar/", views.cobro_agregar, name="cobro_agregar"),
    path("cobro/cantidad/", views.cobro_cantidad, name="cobro_cantidad"),
    path("cobro/confirmar/", views.cobro_confirmar, name="cobro_confirmar"),
    path("turno/cierre/", views.cierre_turno, name="cierre_turno"),
    # Cobro con QR de Mercado Pago
    path("cobro/qr/<int:pago_id>/estado/", views_qr.pago_estado, name="pago_estado"),
    path("cobro/qr/<int:pago_id>/cancelar/", views_qr.pago_cancelar, name="pago_cancelar"),
    path("display/", views_qr.display, name="display"),
    path("display/estado/", views_qr.display_estado, name="display_estado"),
    path("pagar/<uuid:token>/", views_qr.pago_simulado, name="pago_simulado"),
    path("mercadopago/webhook/", views_qr.mercadopago_webhook, name="mercadopago_webhook"),
    # Conectar la cuenta de Mercado Pago del negocio (OAuth)
    path("mercadopago/", views_conexion.mercadopago_config, name="mercadopago_config"),
    path("mercadopago/conectar/", views_conexion.mercadopago_conectar, name="mercadopago_conectar"),
    path("mercadopago/callback/", views_conexion.mercadopago_callback, name="mercadopago_callback"),
    path("mercadopago/desconectar/", views_conexion.mercadopago_desconectar, name="mercadopago_desconectar"),
    path("productos/", views.lista_productos, name="lista_productos"),
    path(
        "productos/buscar-por-codigo/",
        views.buscar_por_codigo,
        name="buscar_por_codigo",
    ),
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

