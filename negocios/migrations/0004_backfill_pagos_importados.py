"""Backfill: crea un PagoDocumento por cada Documento con monto_pagado > 0.

Cada factura que ya tuviera un saldo pagado (caché) se representa como un
pago histórico con nota "Saldo importado", para que la historia de pagos
no se pierda al pasar a PagoDocumento. Es reversible: borra solo esos
pagos importados.
"""
import uuid

from django.db import migrations


def backfill_pagos_importados(apps, schema_editor):
    Documento = apps.get_model("negocios", "Documento")
    PagoDocumento = apps.get_model("negocios", "PagoDocumento")

    documentos = Documento.objects.exclude(monto_pagado=0)
    for documento in documentos.iterator():
        PagoDocumento.objects.create(
            documento=documento,
            negocio=documento.negocio,
            fecha=documento.fecha_emision,
            monto=documento.monto_pagado,
            metodo="otro",
            nota="Saldo importado",
            usuario=None,
            grupo_pago=uuid.uuid4(),
        )


def eliminar_pagos_importados(apps, schema_editor):
    PagoDocumento = apps.get_model("negocios", "PagoDocumento")
    PagoDocumento.objects.filter(nota="Saldo importado").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("negocios", "0003_pagodocumento_documento_motivo_anulacion_and_more"),
    ]

    operations = [
        migrations.RunPython(
            backfill_pagos_importados,
            reverse_code=eliminar_pagos_importados,
        ),
    ]
