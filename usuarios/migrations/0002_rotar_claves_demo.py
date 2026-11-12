"""Rota las claves de los usuarios demo: dejan de ser todas `kiosco2024`.

Solo se guardan los hashes (PBKDF2), nunca las claves: el repo es público.
Las claves nuevas se pasan por privado al equipo.
Si el usuario no existe (DB local, tests) no hace nada.
"""
from django.db import migrations

HASHES = {
    "admin": "pbkdf2_sha256$1500000$NpHdb1wUWk6Iw2GyQPbueE$NLpV/93nwfwG8oMrku1n2J+u6uBNKkiCB575Zh/YbF8=",
    "cajero1": "pbkdf2_sha256$1500000$s71UabqGSvMj3a4BuScLyr$D8lVebWTsWC2dX+88MVwWUEF9JzbWl/mytzRW3IRe8I=",
    "admin_barrio": "pbkdf2_sha256$1500000$dO4SBmA25aBIb0lCA11v5z$fK79DqoAHjXSK5cOKQ32g0elRF4UJc90EjmkrgyiY3E=",
    "cajero_barrio_1": "pbkdf2_sha256$1500000$7cWxVTCiVSdqQg77w0dlG8$Egs2seHgq7CRnHFdvNRyOniEAubmUlmmgsr4tNfzIQ4=",
    "cajero_barrio_2": "pbkdf2_sha256$1500000$Q88uEzHT1ElnaDGzl6WWzi$uCHuaV5KKDFXtwsEUaH5zcFRUb1YCWKNA4D37ZVs4DU=",
    "admin_martillito": "pbkdf2_sha256$1500000$gaxerX92cJ8O6kmK7rTuIm$axrDKjuLwFPJHf/Cdibt+9re7M1Xv6LsI4hDh7x67mY=",
    "cajero_martillito_1": "pbkdf2_sha256$1500000$WwSwfKhaU6ZTqReJc5r3oQ$crk00ms4G2eyvLOn8B0MZCYPs/kJpoicALLpQealJ2s=",
    "cajero_martillito_2": "pbkdf2_sha256$1500000$IiM9JNsWSoPPocov3TcOo4$isUGjxBennbH54kLGR+AVxRI+bjzpnq+pORfYYesRp4=",
    "admin_natural": "pbkdf2_sha256$1500000$j82Mv3oeYFYuEEvK3X1Y7q$Ioj+8NQ3KHsXCPKm6Q32eIwxokQweug1h3p6dadwIe4=",
    "cajero_natural_1": "pbkdf2_sha256$1500000$ta7MpvThrgoLDlzpsLRVJ4$ZJ0Xq9I463Jaql2vSOQFK29pn/UWh+dT9koqbgXM6kA=",
    "cajero_natural_2": "pbkdf2_sha256$1500000$WH4h2mzjdzhLK11xXWxPW5$oSlpO/y300vYON1p4DH3epAE75K8npT0q8COzUY31/8=",
}


def rotar(apps, schema_editor):
    User = apps.get_model("auth", "User")
    for username, hash_clave in HASHES.items():
        User.objects.filter(username=username).update(password=hash_clave)


class Migration(migrations.Migration):
    dependencies = [
        ("usuarios", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [migrations.RunPython(rotar, migrations.RunPython.noop)]
