from django.urls import path

from . import views_superadmin

app_name = "superadmin"

urlpatterns = [
    path("", views_superadmin.lista_negocios, name="lista_negocios"),
    path("crear-negocio/", views_superadmin.crear_negocio, name="crear_negocio"),
    path(
        "<int:negocio_id>/editar-negocio/",
        views_superadmin.editar_negocio,
        name="editar_negocio",
    ),
    path(
        "crear-empleado/",
        views_superadmin.crear_empleado,
        name="crear_empleado",
    ),
    path(
        "usuario/<int:user_id>/asignar-negocio/",
        views_superadmin.asignar_negocio_usuario,
        name="asignar_negocio_usuario",
    ),
]
