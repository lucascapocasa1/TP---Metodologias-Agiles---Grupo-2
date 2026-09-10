from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver

from auditoria.utils import registrar_login, registrar_logout


@receiver(user_logged_in)
def al_iniciar_sesion(sender, request, user, **kwargs):
    registrar_login(user, request)


@receiver(user_logged_out)
def al_cerrar_sesion(sender, request, user, **kwargs):
    registrar_logout(user, request)
