from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render

from auditoria.utils import registrar_accion
from usuarios.decorators import rol_requerido
from ventas.services import formatear_monto
from ventas.views import contexto_cobro

from . import services
from .forms import ClienteForm, ClienteRapidoForm, PagoCuentaCorrienteForm
from .models import Cliente


def _con_estadisticas(clientes):
    """Agrega compras y gasto total de fidelidad (solo ventas finalizadas)."""
    return clientes.annotate(
        total_compras=Count("ventas", filter=Q(ventas__finalizada=True)),
        total_gastado=Coalesce(
            Sum("ventas__total", filter=Q(ventas__finalizada=True)),
            Value(Decimal("0.00")),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        ),
    )


# ========== GESTIÓN DE CLIENTES (HU-12: CRUD del Administrador) ==========
@rol_requerido("Administrador")
def listar_clientes(request):
    """Lista clientes con búsqueda, filtros y estadísticas de fidelidad."""
    busqueda = request.GET.get("buscar", "").strip()
    filtro_estado = request.GET.get("estado", "")

    clientes = Cliente.objects.all()

    if busqueda:
        clientes = clientes.filter(
            Q(nombre__icontains=busqueda)
            | Q(apellido__icontains=busqueda)
            | Q(dni__icontains=busqueda)
            | Q(email__icontains=busqueda)
        )

    if filtro_estado == "activos":
        clientes = clientes.filter(activo=True)
    elif filtro_estado == "inactivos":
        clientes = clientes.filter(activo=False)

    contexto = {
        "clientes": _con_estadisticas(clientes).order_by("apellido", "nombre"),
        "busqueda": busqueda,
        "filtro_estado": filtro_estado,
        "puntos_regla": services.PUNTOS_POR_PESO,
    }

    if request.headers.get("HX-Request"):
        return render(request, "clientes/_clientes_tabla.html", contexto)
    return render(request, "clientes/listar_clientes.html", contexto)


@rol_requerido("Administrador")
def crear_cliente(request):
    """Alta de un cliente nuevo."""
    if request.method == "POST":
        form = ClienteForm(request.POST)
        if form.is_valid():
            cliente = form.save()
            registrar_accion(
                request.user,
                "Cliente creado",
                f"Se creó el cliente '{cliente.nombre_completo}' "
                f"(DNI {cliente.dni})",
                request,
            )
            messages.success(
                request,
                f"Cliente «{cliente.nombre_completo}» dado de alta correctamente.",
            )
            return redirect("clientes:listar_clientes")
    else:
        form = ClienteForm()

    return render(request, "clientes/crear_cliente.html", {"form": form})


@rol_requerido("Administrador")
def editar_cliente(request, cliente_id):
    """Edita los datos de un cliente existente."""
    cliente = get_object_or_404(Cliente, pk=cliente_id)

    if request.method == "POST":
        form = ClienteForm(request.POST, instance=cliente, cliente=cliente)
        if form.is_valid():
            cliente = form.save()
            registrar_accion(
                request.user,
                "Cliente editado",
                f"Se editó el cliente '{cliente.nombre_completo}' "
                f"(DNI {cliente.dni})",
                request,
            )
            messages.success(
                request,
                f"Cliente «{cliente.nombre_completo}» actualizado correctamente.",
            )
            return redirect("clientes:listar_clientes")
    else:
        form = ClienteForm(instance=cliente, cliente=cliente)

    return render(
        request, "clientes/editar_cliente.html", {"form": form, "cliente": cliente}
    )


@rol_requerido("Administrador")
def eliminar_cliente(request, cliente_id):
    """Baja lógica del cliente: las ventas y los puntos quedan intactos."""
    cliente = get_object_or_404(Cliente, pk=cliente_id)

    if request.method == "POST":
        cliente.activo = False
        cliente.save(update_fields=["activo"])
        if request.session.get(services.CLAVE_CLIENTE) == cliente.pk:
            services.quitar_cliente_de_sesion(request)
        registrar_accion(
            request.user,
            "Cliente dado de baja",
            f"Se dio de baja el cliente '{cliente.nombre_completo}' "
            f"(DNI {cliente.dni})",
            request,
        )
        messages.success(
            request,
            f"Cliente «{cliente.nombre_completo}» dado de baja (quedó inactivo).",
        )
        return redirect("clientes:listar_clientes")

    return render(request, "clientes/eliminar_cliente.html", {"cliente": cliente})


@rol_requerido("Administrador")
def detalle_cliente(request, cliente_id):
    """Ficha de fidelidad: puntos, compras, cuenta corriente e historial."""
    cliente = get_object_or_404(Cliente, pk=cliente_id)

    ventas = (
        cliente.ventas.filter(finalizada=True)
        .select_related("usuario")
        .order_by("-fecha")
    )
    total_gastado = (
        ventas.aggregate(
            gasto=Coalesce(
                Sum("total"),
                Value(Decimal("0.00")),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        )["gasto"]
    )

    cliente.refresh_from_db(fields=["saldo_deuda", "limite_credito"])

    contexto = {
        "cliente": cliente,
        "total_compras": ventas.count(),
        "total_gastado": total_gastado,
        "ventas": ventas[:100],
        "puntos_regla": services.PUNTOS_POR_PESO,
        "pagos": cliente.pagos.all()[:100],
        "form_pago": PagoCuentaCorrienteForm(cliente=cliente),
    }
    return render(request, "clientes/detalle_cliente.html", contexto)


@rol_requerido("Administrador")
def registrar_pago(request, cliente_id):
    """HU-14: cobra un pago de la deuda del cliente y lo registra."""
    cliente = get_object_or_404(Cliente, pk=cliente_id)

    if request.method != "POST":
        return redirect("clientes:detalle_cliente", cliente_id=cliente.pk)

    form = PagoCuentaCorrienteForm(request.POST, cliente=cliente)
    if form.is_valid():
        try:
            pago = services.registrar_pago(
                cliente,
                form.cleaned_data["monto"],
                usuario=request.user,
                observacion=form.cleaned_data.get("observacion", ""),
            )
        except services.ErrorCuentaCorriente as exc:
            messages.error(request, str(exc))
            return redirect("clientes:detalle_cliente", cliente_id=cliente.pk)

        registrar_accion(
            request.user,
            "Pago de cuenta corriente",
            f"Se cobró {formatear_monto(pago.monto)} a "
            f"'{cliente.nombre_completo}' (DNI {cliente.dni}). "
            f"Saldo restante: {formatear_monto(cliente.saldo_deuda)}",
            request,
        )
        messages.success(
            request,
            f"Pago de {formatear_monto(pago.monto)} registrado. "
            f"Saldo de {cliente.nombre_completo}: "
            f"{formatear_monto(cliente.saldo_deuda)}.",
        )
        return redirect("clientes:detalle_cliente", cliente_id=cliente.pk)

    for errores in form.errors.values():
        for error in errores:
            messages.error(request, error)
    return redirect("clientes:detalle_cliente", cliente_id=cliente.pk)


# ========== CLIENTE EN LA PANTALLA DE COBRO (HU-12: el cajero lo asocia) ==========
@login_required
def buscar_cliente(request):
    """Búsqueda en tiempo real del cobro (HTMX) por DNI, nombre o apellido."""
    consulta = request.GET.get("q", "").strip()
    coincidencias = services.buscar_clientes(consulta)

    return render(
        request,
        "clientes/_resultados_cobro.html",
        {"consulta": consulta, "coincidencias": coincidencias},
    )


@login_required
def asociar_cliente(request):
    """Asocia un cliente a la venta en curso (queda en la sesión)."""
    if request.method != "POST":
        return redirect("ventas:pantalla_cobro")

    cliente = get_object_or_404(
        Cliente, pk=request.POST.get("cliente_id"), activo=True
    )
    services.guardar_cliente_en_sesion(request, cliente)
    return _respuesta_cobro(request)


@login_required
def quitar_cliente(request):
    """Desasocia el cliente de la venta en curso."""
    if request.method != "POST":
        return redirect("ventas:pantalla_cobro")

    services.quitar_cliente_de_sesion(request)
    return _respuesta_cobro(request)


@login_required
def alta_rapida(request):
    """Ventanita rápida (CA del HU-12): crea el cliente y lo asocia al cobro."""
    if request.method != "POST":
        return redirect("ventas:pantalla_cobro")

    form = ClienteRapidoForm(request.POST)
    if form.is_valid():
        cliente = form.save()
        services.guardar_cliente_en_sesion(request, cliente)
        registrar_accion(
            request.user,
            "Cliente creado",
            f"Alta rápida en el cobro: '{cliente.nombre_completo}' "
            f"(DNI {cliente.dni})",
            request,
        )
        messages.success(
            request,
            f"Cliente «{cliente.nombre_completo}» creado y asociado a la venta.",
        )
        return _respuesta_cobro(request)

    return _respuesta_cobro(
        request, contexto=contexto_cobro(request, form_rapido=form)
    )


def _respuesta_cobro(request, contexto=None):
    """Con HTMX devuelve solo el partial del carrito; sin HTMX, la pantalla."""
    if contexto is None:
        contexto = contexto_cobro(request)
    if request.headers.get("HX-Request"):
        return render(request, "ventas/_carrito.html", contexto)
    return render(request, "ventas/pantalla_cobro.html", contexto)
