from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from clientes.models import PagoCuentaCorriente
from negocios.models import Negocio
from pedidos.models import Pedido
from usuarios.models import Empleado
from ventas.models import Categoria, Producto, Turno, Venta


class Command(BaseCommand):
    """
    Migra los datos existentes del esquema de un solo comercio al esquema
    multiempresa.

    Acciones:
    1. Crea el Negocio "Kiosco De Barrio" (slug: de-barrio, activo=True).
    2. Asigna a ese negocio todos los Producto, Categoria, Venta, Turno,
       Pedido y PagoCuentaCorriente existentes que aún no tengan negocio.
    3. Crea un Empleado para el usuario "admin" vinculado a "Kiosco De Barrio".
    4. Crea el Negocio "Ferretería Martillito" (slug: ferreteria-martillito,
       vacío, activo=True).
    5. Crea el Negocio "Dietética Natural" (slug: dietetica-natural, vacío,
       activo=True).

    Este comando es idempotente: si se ejecuta varias veces, no duplica
    negocios ni asignaciones.
    """

    help = "Migra los datos existentes al esquema multiempresa de Norvex."

    def handle(self, *args, **options):
        # 1. Crear o recuperar el negocio principal con los datos existentes
        negocio_barrio, creado = Negocio.objects.get_or_create(
            slug="de-barrio",
            defaults={
                "nombre": "Kiosco De Barrio",
                "whatsapp": "",
                "email": "",
                "activo": True,
            },
        )
        if creado:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Negocio creado: "{negocio_barrio.nombre}" '
                    f'(slug: {negocio_barrio.slug})'
                )
            )
        else:
            self.stdout.write(
                f'Negocio ya existente: "{negocio_barrio.nombre}" '
                f'(slug: {negocio_barrio.slug})'
            )

        # 2. Asignar todos los registros existentes sin negocio a este negocio
        modelos_a_asignar = [
            (Categoria.objects, "categorías"),
            (Producto.objects, "productos"),
            (Venta.objects, "ventas"),
            (Turno.objects, "turnos"),
            (Pedido.objects, "pedidos"),
            (PagoCuentaCorriente.objects, "pagos de cuenta corriente"),
        ]

        for manager, nombre_plural in modelos_a_asignar:
            sin_negocio = manager.filter(negocio__isnull=True)
            cantidad = sin_negocio.count()
            if cantidad > 0:
                sin_negocio.update(negocio=negocio_barrio)
                self.stdout.write(
                    f"  {cantidad} {nombre_plural} asignados a "
                    f'"{negocio_barrio.nombre}"'
                )
            else:
                self.stdout.write(
                    f"  No hay {nombre_plural} sin negocio para asignar."
                )

        # 3. Crear Empleado para el usuario admin vinculado a Kiosco De Barrio
        try:
            usuario_admin = User.objects.get(username="admin")
            empleado, creado_emp = Empleado.objects.get_or_create(
                usuario=usuario_admin,
                defaults={
                    "negocio": negocio_barrio,
                    "activo": True,
                },
            )
            if creado_emp:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Empleado creado: {usuario_admin.username} -> '
                        f'"{negocio_barrio.nombre}"'
                    )
                )
            else:
                self.stdout.write(
                    f'Empleado ya existente: {usuario_admin.username} '
                    f'-> "{empleado.negocio.nombre}"'
                )
        except User.DoesNotExist:
            self.stdout.write(
                self.style.WARNING(
                    "El usuario 'admin' no existe. Se omite la creación del "
                    "empleado asociado."
                )
            )

        # 4. Crear Ferretería Martillito (vacío)
        negocio_ferre, creado_f = Negocio.objects.get_or_create(
            slug="ferreteria-martillito",
            defaults={
                "nombre": "Ferretería Martillito",
                "whatsapp": "",
                "email": "",
                "activo": True,
            },
        )
        if creado_f:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Negocio creado: "{negocio_ferre.nombre}" '
                    f'(slug: {negocio_ferre.slug})'
                )
            )
        else:
            self.stdout.write(
                f'Negocio ya existente: "{negocio_ferre.nombre}" '
                f'(slug: {negocio_ferre.slug})'
            )

        # 5. Crear Dietética Natural (vacío)
        negocio_dieta, creado_d = Negocio.objects.get_or_create(
            slug="dietetica-natural",
            defaults={
                "nombre": "Dietética Natural",
                "whatsapp": "",
                "email": "",
                "activo": True,
            },
        )
        if creado_d:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Negocio creado: "{negocio_dieta.nombre}" '
                    f'(slug: {negocio_dieta.slug})'
                )
            )
        else:
            self.stdout.write(
                f'Negocio ya existente: "{negocio_dieta.nombre}" '
                f'(slug: {negocio_dieta.slug})'
            )

        self.stdout.write(
            self.style.SUCCESS("Migración a multiempresa completada.")
        )
