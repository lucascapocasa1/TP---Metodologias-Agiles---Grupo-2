"""Cambia las claves demo por unas más fáciles de recordar (una por usuario).

Solo se guardan los hashes, nunca las claves. Se pasan por privado.
Si el usuario no existe (DB local, tests) no hace nada.
"""
from django.db import migrations

HASHES = {
    "admin": "pbkdf2_sha256$1500000$Bg9R9xKkch5Oa3yJEpoz4X$qECPiGHRyrAHRTNNi5ubtfpx5nw82MEPIq9fSdkkGIU=",
    "cajero1": "pbkdf2_sha256$1500000$Rlc0o6tcdT9dSe2tNYxFt6$PCJ/MMOe9hnPIiGzBEik1aety9XNNrEkfB3BfNQBlL8=",
    "admin_barrio": "pbkdf2_sha256$1500000$1mzvRH7SdFQHNEXpNG90vj$Wgy4xMVNVKnCbgQze0sdz5aI1pLrnOejRQcUmuMKMQI=",
    "cajero_barrio_1": "pbkdf2_sha256$1500000$yMXVhJkJzrfAVVsZVJ85kz$vc0ZsEDJ2gSkbgLiyiZ8jfL88ph5QrGPoWjp7kCSJ3A=",
    "cajero_barrio_2": "pbkdf2_sha256$1500000$Pu6hcMlc8JQzkbDFweKMX6$uDNsgd8h/3SNKU7VZ5T6eODtFWBB14Tz4rLpBVdklYY=",
    "admin_martillito": "pbkdf2_sha256$1500000$lYFSjGDEPF7CjOQNzGtBOT$lWlcu7asinzI8k54RmodZ7ohWUcjt6fSwr9tT/Rr4Ew=",
    "cajero_martillito_1": "pbkdf2_sha256$1500000$iAjCDFVWehN1wLx8kAuTou$keo1Gw/81rhOjIdebTcupUrIkLC9iEhBv8PDvWVQfA0=",
    "cajero_martillito_2": "pbkdf2_sha256$1500000$uHp2ofrCNBNae7vjwSbTNY$ZWhz6jSnEfZ2eOsew9uUdZ1akqATu8xYEon53QgMG5E=",
    "admin_natural": "pbkdf2_sha256$1500000$lJaVeldMk4QAfIMpV2aKzk$Tta2GHdEVabJChneXV4ZlK+QrVnRK3+DCNCeSRkTbPQ=",
    "cajero_natural_1": "pbkdf2_sha256$1500000$oKOw4JZPkzbMVs1eUwAvaj$FkuuBZ0g2ElAZ4DyPfxY9gD+lo57dmNOY6Vb9oBsEp8=",
    "cajero_natural_2": "pbkdf2_sha256$1500000$AxPNu3qtXSc4noPIAZjz0Z$Z4TU2NdarMdOvtoWfpVjODqxrrZl0X7joX77OxgVukg=",
}


def cambiar(apps, schema_editor):
    User = apps.get_model("auth", "User")
    for username, hash_clave in HASHES.items():
        User.objects.filter(username=username).update(password=hash_clave)


class Migration(migrations.Migration):
    dependencies = [("usuarios", "0002_rotar_claves_demo")]

    operations = [migrations.RunPython(cambiar, migrations.RunPython.noop)]
