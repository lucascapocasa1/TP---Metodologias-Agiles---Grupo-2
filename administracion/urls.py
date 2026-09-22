from django.urls import path

from . import views

app_name = "administracion"

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("usuarios/", views.listar_usuarios, name="listar_usuarios"),
    path("usuarios/crear/", views.crear_usuario, name="crear_usuario"),
    path("usuarios/<int:user_id>/editar/", views.editar_usuario, name="editar_usuario"),
    path("usuarios/<int:user_id>/eliminar/", views.eliminar_usuario, name="eliminar_usuario"),
    path("usuarios/<int:user_id>/roles/", views.asignar_roles, name="asignar_roles"),
    path("usuarios/<int:user_id>/toggle/", views.toggle_usuario, name="toggle_usuario"),
]
