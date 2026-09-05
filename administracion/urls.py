from django.urls import path

from . import views

app_name = "administracion"

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
]
