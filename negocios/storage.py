"""Storage de Django que guarda los archivos subidos en la base de datos.

El disco de Render es efímero (se borra en cada deploy y al reiniciar), así
que los adjuntos no pueden vivir en MEDIA_ROOT. Son PDFs/imágenes chicos:
entran bien en PostgreSQL y se sirven con `negocios.views.ver_archivo`.
"""
import mimetypes

from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.urls import reverse
from django.utils.deconstruct import deconstructible


@deconstructible
class BaseDeDatosStorage(Storage):
    def _modelo(self):
        from .models import ArchivoGuardado

        return ArchivoGuardado

    def _open(self, name, mode="rb"):
        archivo = self._modelo().objects.get(nombre=name)
        return ContentFile(bytes(archivo.contenido), name=name)

    def _save(self, name, content):
        if hasattr(content, "seek"):
            content.seek(0)
        datos = content.read()
        tipo = getattr(content, "content_type", "") or mimetypes.guess_type(name)[0] or ""
        self._modelo().objects.create(nombre=name, contenido=datos, tipo=tipo)
        return name

    def exists(self, name):
        return self._modelo().objects.filter(nombre=name).exists()

    def delete(self, name):
        self._modelo().objects.filter(nombre=name).delete()

    def size(self, name):
        return len(self._modelo().objects.get(nombre=name).contenido)

    def url(self, name):
        return reverse("ver_archivo", args=[name])
