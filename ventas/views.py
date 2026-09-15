from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def pantalla_cobro(request):
    """
    Pantalla de cobro (POS). En este Sprint 1 es solo la cáscara protegida
    por login: el flujo real de "escanear código -> vuela al carrito",
    el vuelto rápido con billetes y el cierre de caja son de sprints
    siguientes (ver README).

    Acceso: Cajero y Administrador (el dueño también puede pararse
    a cobrar en el mostrador).
    """
    return render(request, "ventas/pantalla_cobro.html")
