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
        "documentos/<int:documento_id>/subir-adjunto/",
        views.subir_adjunto,
        name="subir_adjunto",
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
    # Proveedores: CRUD, detalle y conversión de nombre suelto.
    path(
        "proveedores/crear/",
        views.crear_proveedor,
        name="crear_proveedor",
    ),
    path(
        "proveedores/<int:proveedor_id>/editar/",
        views.editar_proveedor,
        name="editar_proveedor",
    ),
    path(
        "proveedores/<int:proveedor_id>/",
        views.detalle_proveedor,
        name="detalle_proveedor",
    ),
    # Acciones sobre documentos.
    path(
        "documentos/<int:documento_id>/anular/",
        views.anular_documento,
        name="anular_documento",
    ),
    path(
        "documentos/<int:documento_id>/reactivar/",
        views.reactivar_documento,
        name="reactivar_documento",
    ),
    path(
        "documentos/<int:documento_id>/convertir-proveedor/",
        views.convertir_en_proveedor,
        name="convertir_en_proveedor",
    ),
    # Deshacer una operación de pago (grupo_pago).
    path(
        "pagos/<uuid:grupo_pago>/deshacer/",
        views.deshacer_pago_grupo,
        name="deshacer_pago_grupo",
    ),
]
