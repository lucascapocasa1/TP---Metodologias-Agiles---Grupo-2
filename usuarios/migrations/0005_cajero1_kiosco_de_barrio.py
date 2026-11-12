from django.db import migrations


def vincular(apps, schema_editor):
    """cajero1 quedó sin negocio al pasar a multiempresa: sin catálogo en Cobro ni cierre de turno."""
    User = apps.get_model("auth", "User")
    Empleado = apps.get_model("usuarios", "Empleado")
    Negocio = apps.get_model("negocios", "Negocio")
    usuario = User.objects.filter(username="cajero1").first()
    negocio = Negocio.objects.filter(slug="de-barrio").first()
    if usuario and negocio and not Empleado.objects.filter(usuario=usuario).exists():
        Empleado.objects.create(usuario=usuario, negocio=negocio)


class Migration(migrations.Migration):
    dependencies = [
        ("usuarios", "0004_clave_admin_martillito"),
        ("negocios", "0006_archivoguardado"),
    ]

    operations = [migrations.RunPython(vincular, migrations.RunPython.noop)]
