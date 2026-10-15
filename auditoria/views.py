from datetime import datetime, time

from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render
from django.utils import timezone

from usuarios.decorators import rol_requerido

from .models import RegistroAuditoria

# Agrupación de eventos para la UI (RF-45). `accion` es texto libre: lo escribe
# quien llama a `registrar_accion()`, así que el mapeo es por igualdad exacta y
# todo lo que no entra acá cae en "otras".
CATEGORIAS = {
    "ventas": {
        "etiqueta": "Ventas",
        "acciones": ("Venta confirmada",),
    },
    "usuarios": {
        "etiqueta": "Usuarios",
        "acciones": (
            "Usuario creado",
            "Usuario editado",
            "Usuario eliminado",
            "Roles actualizados",
            "Usuario activado",
            "Usuario desactivado",
        ),
    },
    "sesiones": {
        "etiqueta": "Sesiones",
        "acciones": ("Inicio de sesión", "Cierre de sesión"),
    },
}

_ACCION_A_CATEGORIA = {
    accion: clave
    for clave, datos in CATEGORIAS.items()
    for accion in datos["acciones"]
}

# Registros por página y ventanita de números de página alrededor de la actual.
POR_PAGINA = 20
VENTANA_PAGINAS = 3


@rol_requerido("Administrador")
def historial(request):
    """
    Listado paginado de la auditoría con filtros (RF-45).

    A diferencia del reporte de ventas, el rango de fechas es opcional: sin
    filtros se ve el historial completo, porque un registro viejo también
    puede ser lo que se está buscando.
    """
    busqueda = request.GET.get("q", "").strip()
    tipo = request.GET.get("tipo", "")
    if tipo not in CATEGORIAS:
        tipo = ""

    registros, f_desde, f_hasta = _aplicar_rango(
        RegistroAuditoria.objects.select_related("usuario"),
        request.GET.get("desde"),
        request.GET.get("hasta"),
    )

    # Los contadores del encabezado se calculan solo con el rango de fechas
    # (sin tipo ni búsqueda) para que sirvan de accesos rápidos a un filtro.
    totales = {"total": registros.count()}
    for clave, datos in CATEGORIAS.items():
        totales[clave] = registros.filter(accion__in=datos["acciones"]).count()

    if tipo:
        registros = registros.filter(accion__in=CATEGORIAS[tipo]["acciones"])
    if busqueda:
        registros = registros.filter(
            Q(accion__icontains=busqueda)
            | Q(detalle__icontains=busqueda)
            | Q(usuario__username__icontains=busqueda)
        )

    paginador = Paginator(registros, POR_PAGINA)
    pagina = paginador.get_page(request.GET.get("page"))

    # La categoría decide el color del badge en el template.
    for registro in pagina.object_list:
        registro.categoria = _ACCION_A_CATEGORIA.get(registro.accion, "otras")

    primera = max(1, pagina.number - VENTANA_PAGINAS)
    ultima = min(paginador.num_pages, pagina.number + VENTANA_PAGINAS)

    context = {
        "desde": f_desde,
        "hasta": f_hasta,
        "busqueda": busqueda,
        "tipo": tipo,
        "hay_filtros": bool(tipo or busqueda or f_desde or f_hasta),
        "categorias": [
            {"clave": clave, "etiqueta": datos["etiqueta"], "total": totales[clave]}
            for clave, datos in CATEGORIAS.items()
        ],
        "totales": totales,
        "registros": pagina.object_list,
        "page_obj": pagina,
        "paginas": range(primera, ultima + 1),
    }
    return render(request, "auditoria/historial.html", context)


def _aplicar_rango(registros, desde, hasta):
    """Filtra por rango de fechas (opcional e invertible)."""
    f_desde = _parsear_fecha(desde)
    f_hasta = _parsear_fecha(hasta)

    if f_desde and f_hasta and f_desde > f_hasta:
        f_desde, f_hasta = f_hasta, f_desde

    if f_desde:
        registros = registros.filter(
            fecha__gte=timezone.make_aware(datetime.combine(f_desde, time.min))
        )
    if f_hasta:
        registros = registros.filter(
            fecha__lte=timezone.make_aware(datetime.combine(f_hasta, time.max))
        )
    return registros, f_desde, f_hasta


def _parsear_fecha(valor):
    """Convierte un string 'YYYY-MM-DD' en date, o None si no es válido."""
    if not valor:
        return None
    try:
        return datetime.strptime(valor, "%Y-%m-%d").date()
    except ValueError:
        return None
