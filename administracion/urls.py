from django.urls import path

from . import views, views_superadmin
from usuarios.decorators import superadmin_requerido

app_name = "administracion"

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("usuarios/", views.listar_usuarios, name="listar_usuarios"),
    path("usuarios/crear/", views.crear_usuario, name="crear_usuario"),
    path("usuarios/<int:user_id>/editar/", views.editar_usuario, name="editar_usuario"),
    path("usuarios/<int:user_id>/eliminar/", views.eliminar_usuario, name="eliminar_usuario"),
    path("usuarios/<int:user_id>/roles/", views.asignar_roles, name="asignar_roles"),
    path("usuarios/<int:user_id>/toggle/", views.toggle_usuario, name="toggle_usuario"),
    path("reportes/ventas/", views.reportes_ventas, name="reportes_ventas"),
    path("reportes/stock/", views.reportes_stock, name="reportes_stock"),
    path(
        "reportes/stock/exportar-excel/",
        views.exportar_stock_excel,
        name="exportar_stock_excel",
    ),
    path(
        "reportes/productos-sin-movimiento/",
        views.productos_sin_movimiento,
        name="productos_sin_movimiento",
    ),
    # Panel de superadmin (solo is_superuser=True)
    path("superadmin/", views_superadmin.lista_negocios, name="lista_negocios"),
    path(
        "superadmin/crear-negocio/",
        views_superadmin.crear_negocio,
        name="crear_negocio",
    ),
    path(
        "superadmin/<int:negocio_id>/editar-negocio/",
        views_superadmin.editar_negocio,
        name="editar_negocio",
    ),
    path(
        "superadmin/crear-empleado/",
        views_superadmin.crear_empleado,
        name="crear_empleado",
    ),
    path(
        "superadmin/usuario/<int:user_id>/asignar-negocio/",
        views_superadmin.asignar_negocio_usuario,
        name="asignar_negocio_usuario",
    ),
]
