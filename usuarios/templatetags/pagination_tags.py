from django import template
from django.core.paginator import Paginator

register = template.Library()


@register.inclusion_tag("usuarios/tags/paginacion.html")
def paginacion(objetos, por_pagina=20):
    """Renderiza controles de paginación."""
    paginator = Paginator(objetos, por_pagina)
    return {"paginator": paginator}


@register.simple_tag(takes_context=True)
def param(context, **kwargs):
    """Preserva parámetros de query al paginar."""
    request = context["request"]
    params = request.GET.copy()
    for key, value in kwargs.items():
        if value is None:
            params.pop(key, None)
        else:
            params[key] = value
    return params.urlencode()
