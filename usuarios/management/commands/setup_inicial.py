from datetime import date

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand

from administracion.models import Cargo, Empleado, Empresa


class Command(BaseCommand):
    """
    Comando de conveniencia para dejar el sistema listo para operar.

    Crea:
      - Los grupos "Administrador" y "Cajero".
      - Los cargos "Administrador" y "Cajero".
      - La empresa (kiosco) con un CUIT de ejemplo.
      - Los usuarios de prueba:
          * admin / kiosco2024  (grupo y cargo Administrador)
          * cajero1 / kiosco2024 (grupo y cargo Cajero)
      - La ficha de empleado ligada a cada usuario (necesaria para poder
        cargar ventas y compras).

    Uso:
        python manage.py setup_inicial

    Es idempotente: si ya existe, no duplica. No reemplaza a
    `createsuperuser`; es solo para poder probar rápido el sistema.
    """

    help = "Crea grupos, cargos, empresa, usuarios y sus fichas de empleado"

    def handle(self, *args, **options):
        # 1. Grupos de permisos (Sprint 1)
        grupo_admin, creado_admin = Group.objects.get_or_create(name="Administrador")
        grupo_cajero, creado_cajero = Group.objects.get_or_create(name="Cajero")
        self.stdout.write(
            self.style.SUCCESS(
                f"Grupo 'Administrador' {'creado' if creado_admin else 'ya existía'}."
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Grupo 'Cajero' {'creado' if creado_cajero else 'ya existía'}."
            )
        )

        # 2. Cargos del kiosco
        cargo_admin, creado_cargo_admin = Cargo.objects.get_or_create(
            nombre="Administrador",
            defaults={"descripcion": "Dueño/administrador con acceso total."},
        )
        cargo_cajero, creado_cargo_cajero = Cargo.objects.get_or_create(
            nombre="Cajero",
            defaults={"descripcion": "Encargado del punto de venta."},
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Cargo 'Administrador' {'creado' if creado_cargo_admin else 'ya existía'}."
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Cargo 'Cajero' {'creado' if creado_cargo_cajero else 'ya existía'}."
            )
        )

        # 3. Empresa (el kiosco) con CUIT de ejemplo editable después
        empresa, creada_empresa = Empresa.objects.get_or_create(
            nombre="Kiosco UNAB",
            defaults={
                "cuit": "30111111111",
                "direccion": "Av. de Mayo 1234",
                "telefono": "1122334455",
                "email": "kiosco@unab.com",
            },
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Empresa '{empresa.nombre}' {'creada' if creada_empresa else 'ya existía'}."
            )
        )

        # 4. Usuarios de prueba + fichas de empleado ligadas
        admin, creado_user_admin = User.objects.get_or_create(
            username="admin",
            defaults={
                "first_name": "Carlos",
                "is_staff": True,  # puede entrar al /admin/ de Django
            },
        )
        if creado_user_admin:
            admin.set_password("kiosco2024")
            admin.save()
        admin.groups.add(grupo_admin)
        _, creado_emp_admin = self._get_or_create_empleado(
            admin,
            cargo_admin,
            nombre="Carlos",
            apellido="González",
            dni="12345678",
            cuil="20123456782",
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Usuario 'admin' {'creado' if creado_user_admin else 'ya existía'}."
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Empleado 'Carlos González' {'creado' if creado_emp_admin else 'ya existía'}."
            )
        )

        cajero, creado_user_cajero = User.objects.get_or_create(
            username="cajero1",
            defaults={"first_name": "Empleado"},
        )
        if creado_user_cajero:
            cajero.set_password("kiosco2024")
            cajero.save()
        cajero.groups.add(grupo_cajero)
        _, creado_emp_cajero = self._get_or_create_empleado(
            cajero,
            cargo_cajero,
            nombre="Empleado",
            apellido="Pérez",
            dni="87654321",
            cuil="20876543210",
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Usuario 'cajero1' {'creado' if creado_user_cajero else 'ya existía'}."
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Empleado 'Empleado Pérez' {'creado' if creado_emp_cajero else 'ya existía'}."
            )
        )

        self.stdout.write(self.style.SUCCESS("Setup inicial completo."))

    def _get_or_create_empleado(
        self, user, cargo, nombre, apellido, dni, cuil
    ):
        return Empleado.objects.get_or_create(
            user=user,
            defaults={
                "cargo": cargo,
                "nombre": nombre,
                "apellido": apellido,
                "dni": dni,
                "cuil": cuil,
                "fecha_ingreso": date.today(),
                "activo": True,
            },
        )