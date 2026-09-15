from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """
    Comando de conveniencia para el Sprint 1.

    Crea:
      - Los grupos "Administrador" y "Cajero".
      - Un usuario administrador de prueba: admin / kiosco2024
      - Un usuario cajero de prueba: cajero1 / kiosco2024

    Uso:
        python manage.py setup_inicial

    Esto NO reemplaza a `createsuperuser`; es solo para poder probar
    rápido el login y la separación de roles sin cargar nada a mano.
    """

    help = "Crea los grupos Administrador/Cajero y usuarios de prueba para el Sprint 1"

    def handle(self, *args, **options):
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

        # Usuario administrador de prueba
        if not User.objects.filter(username="admin").exists():
            admin = User.objects.create_user(
                username="admin",
                password="kiosco2024",
                first_name="Carlos",
                is_staff=True,  # puede entrar al /admin/ de Django si hace falta
            )
            admin.groups.add(grupo_admin)
            self.stdout.write(
                self.style.SUCCESS("Usuario 'admin' (Administrador) creado. Clave: kiosco2024")
            )
        else:
            self.stdout.write(self.style.WARNING("Usuario 'admin' ya existía, no se modificó."))

        # Usuario cajero de prueba
        if not User.objects.filter(username="cajero1").exists():
            cajero = User.objects.create_user(
                username="cajero1",
                password="kiosco2024",
                first_name="Empleado",
            )
            cajero.groups.add(grupo_cajero)
            self.stdout.write(
                self.style.SUCCESS("Usuario 'cajero1' (Cajero) creado. Clave: kiosco2024")
            )
        else:
            self.stdout.write(self.style.WARNING("Usuario 'cajero1' ya existía, no se modificó."))

        self.stdout.write(self.style.SUCCESS("Setup inicial completo."))
