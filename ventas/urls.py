from django.urls import path

from . import views

app_name = "ventas"

urlpatterns = [
    path("cobro/", views.pantalla_cobro, name="pantalla_cobro"),
    path("cobro/agregar/", views.agregar_al_carrito, name="agregar_al_carrito"),
    path("cobro/actualizar/<int:producto_id>/", views.actualizar_cantidad, name="actualizar_cantidad"),
    path("cobro/quitar/<int:producto_id>/", views.quitar_producto, name="quitar_producto"),
    path("cobro/vaciar/", views.vaciar_carrito, name="vaciar_carrito"),
    path("cobro/registrar/", views.registrar_venta, name="registrar_venta"),
]
