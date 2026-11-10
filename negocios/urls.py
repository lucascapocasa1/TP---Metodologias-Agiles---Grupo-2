from django.urls import path

from . import views

app_name = "negocios"

urlpatterns = [
    # Landing pública
    path("", views.landing, name="landing"),
    # Documentos (facturas) del negocio
    path(
        "documentos/",
        views.lista_documentos,
        name="lista_documentos",
    ),
    path(
        "documentos/facturas/",
        views.lista_documentos,
        {"grupo_fijo": "servicios"},
        name="lista_facturas",
    ),
    path(
        "documentos/proveedores/",
        views.lista_documentos,
        {"grupo_fijo": "proveedores"},
        name="lista_proveedores",
    ),
    path(
        "documentos/crear/",
        views.crear_documento,
        name="crear_documento",
    ),
    path(
        "documentos/<int:documento_id>/editar/",
        views.editar_documento,
        name="editar_documento",
    ),
    path(
        "documentos/<int:documento_id>/subir-pdf/",
        views.subir_pdf,
        name="subir_pdf",
    ),
    path(
        "documentos/<int:documento_id>/marcar-pagada/",
        views.marcar_pagada,
        name="marcar_pagada",
    ),
    path(
        "documentos/proveedor/<int:proveedor_id>/pagar/",
        views.pagar_proveedor,
        name="pagar_proveedor",
    ),
]
