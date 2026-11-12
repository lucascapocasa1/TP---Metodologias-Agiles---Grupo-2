"""Cambia la clave de admin_martillito. Solo se guarda el hash."""
from django.db import migrations


def cambiar(apps, schema_editor):
    User = apps.get_model("auth", "User")
    User.objects.filter(username="admin_martillito").update(
        password="pbkdf2_sha256$1500000$v43GchMwuhNbCOPy54d4GY$gN28QwNaQHorSV9uXdlNntFVnv4LaWmYTZ/ag2LOTpY="
    )


class Migration(migrations.Migration):
    dependencies = [("usuarios", "0003_claves_faciles")]

    operations = [migrations.RunPython(cambiar, migrations.RunPython.noop)]
