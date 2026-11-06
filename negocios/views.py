"""Vistas de la app negocios.

Incluye la vista de landing pública que lista los negocios activos
para que los compradores elijan a cuál entrar.
"""
from django.shortcuts import render

from .models import Negocio


def landing(request):
    """
    Página institucional de Noruega.

    Muestra un listado de todos los negocios activos con recuadros
    (nombre, logo, WhatsApp, botón "Entrar a la tienda").
    Cada recuadro lleva a la tienda online del negocio en /t/<slug>/.
    """
    negocios = Negocio.objects.filter(activo=True).order_by("nombre")
    return render(
        request,
        "landing.html",
        {"negocios": negocios},
    )
