from django.shortcuts import render

from usuarios.decorators import rol_requerido


@rol_requerido("Administrador")
def dashboard(request):
    """
    Panel del dueño. SOLO accesible por el grupo "Administrador".
    Cualquier usuario Cajero que intente entrar acá recibe un 403
    (ver usuarios/decorators.py -> rol_requerido).

    En sprints siguientes acá van: gestión de stock, precios de costo,
    reportes de ventas y el cierre de caja con el detalle por turno.
    """
    return render(request, "administracion/dashboard.html")
