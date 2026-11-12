"""Asigna el negocio a los datos que quedaron sin él por el bug multiempresa.

Antes del fix, las ventas del POS se creaban con negocio=None y los pedidos
del catálogo general (/catalogo/) también: quedaban invisibles en caja,
reportes y panel. Este comando repara esos datos ya existentes.

Reglas (mismas que usa el sistema en caliente):
- Venta sin negocio  -> negocio del empleado de su usuario.
- Pedido sin negocio -> negocio de sus ítems, si todos son del mismo comercio.

Idempotente: solo rellena NULL, nunca toca un registro que ya tiene negocio.
Uso (una vez en producción, p. ej. en Render Shell):

    python manage.py backfill_negocios
"""
from django.core.management.base import BaseCommand

from pedidos.models import Pedido
from usuarios.models import Empleado
from ventas.models import Venta


class Command(BaseCommand):
    help = (
        "Asigna negocio a ventas y pedidos que quedaron sin negocio "
        "(rellena solo NULL; se puede correr varias veces)."
    )

    def handle(self, *args, **options):
        # Mapa usuario -> negocio de su empleado, en una sola consulta.
        empleados = dict(
            Empleado.objects.values_list("usuario_id", "negocio_id")
        )

        ventas_ok, ventas_omitidas = self._backfill_ventas(empleados)
        pedidos_ok, pedidos_omitidos = self._backfill_pedidos()

        self.stdout.write(
            self.style.SUCCESS(
                f"Backfill de negocios: {ventas_ok} ventas y "
                f"{pedidos_ok} pedidos asignados."
            )
        )
        if ventas_omitidas:
            self.stdout.write(
                self.style.WARNING(
                    f"  {ventas_omitidas} ventas sin resolver (sin usuario "
                    "o usuario sin empleado): quedan sin negocio y no se "
                    "contarán en caja ni en reportes."
                )
            )
        if pedidos_omitidos:
            self.stdout.write(
                self.style.WARNING(
                    f"  {pedidos_omitidos} pedidos sin resolver (ítems de "
                    "distintos negocios, sin producto o sin ítems): quedan "
                    "sin negocio; el panel los muestra igual."
                )
            )

    def _backfill_ventas(self, empleados):
        ok = 0
        omitidas = 0
        sin_negocio = Venta.objects.filter(negocio__isnull=True).only(
            "pk", "usuario_id"
        )
        for venta in sin_negocio:
            negocio_id = empleados.get(venta.usuario_id)
            if negocio_id is None:
                omitidas += 1
                continue
            Venta.objects.filter(pk=venta.pk).update(negocio_id=negocio_id)
            ok += 1
        return ok, omitidas

    def _backfill_pedidos(self):
        ok = 0
        omitidos = 0
        sin_negocio = Pedido.objects.filter(
            negocio__isnull=True
        ).prefetch_related("detalles__producto")
        for pedido in sin_negocio:
            negocios = set()
            incompleto = False
            for item in pedido.detalles.all():
                if item.producto_id is None:
                    incompleto = True
                    break
                negocios.add(item.producto.negocio_id)
            if incompleto or len(negocios) != 1:
                omitidos += 1
                continue
            negocio_id = negocios.pop()
            if negocio_id is None:
                omitidos += 1
                continue
            pedido.negocio_id = negocio_id
            pedido.save(update_fields=["negocio"])
            ok += 1
        return ok, omitidos
