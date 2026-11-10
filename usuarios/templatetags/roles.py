"""Etiquetas de plantilla para el menú lateral y los roles."""
from django import template

from usuarios.decorators import es_administrador

register = template.Library()


@register.simple_tag
def usuario_admin(user):
    """True si el usuario es Administrador o superusuario."""
    return es_administrador(user)


@register.simple_tag(takes_context=True)
def menu_activo(context, *nombres):
    """Devuelve 'active' si el endpoint actual es alguno de los indicados."""
    match = getattr(context.get("request"), "resolver_match", None)
    if match is not None and match.url_name in nombres:
        return "active"
    return ""


@register.simple_tag(takes_context=True)
def menu_activo_documentos(context, grupo):
    """
    Marca el ítem Facturas o Proveedores del menú lateral.

    Las listas tienen URL propia; las pantallas de crear/editar/subir/pagar
    se resuelven por el documento o por el parámetro `grupo` de la URL.
    """
    request = context.get("request")
    match = getattr(request, "resolver_match", None)
    if request is None or match is None:
        return ""

    url_name = getattr(match, "url_name", "")
    if url_name == "lista_facturas" and grupo == "servicios":
        return "active"
    if url_name in ("lista_proveedores", "pagar_proveedor") and grupo == "proveedores":
        return "active"

    if url_name in (
        "crear_documento",
        "editar_documento",
        "subir_pdf",
        "marcar_pagada",
    ):
        documento = context.get("documento")
        grupo_documento = None
        if documento is not None:
            grupo_documento = (
                "proveedores"
                if documento.categoria == "proveedor"
                else "servicios"
            )
        if request.GET.get("grupo") == grupo or grupo_documento == grupo:
            return "active"
    return ""
