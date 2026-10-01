from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordResetForm,
    SetPasswordForm,
)


class LoginKioscoForm(AuthenticationForm):
    """AuthenticationForm de Django Auth, solo con clases de Bootstrap
    para que los inputs se vean bien sin escribir CSS a mano."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update(
            {"class": "kiosco-input", "autofocus": True, "placeholder": "Usuario"}
        )
        self.fields["password"].widget.attrs.update(
            {"class": "kiosco-input", "placeholder": "Contraseña"}
        )


class RecuperarClaveForm(PasswordResetForm):
    """PasswordResetForm de Django con los estilos del kiosco, para que
    el campo de email ocupe todo el ancho de la tarjeta."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].widget.attrs.update(
            {
                "class": "kiosco-input",
                "placeholder": "nombre@correo.com",
                "autocomplete": "email",
                "autofocus": True,
            }
        )


class NuevaClaveForm(SetPasswordForm):
    """SetPasswordForm de Django con los estilos del kiosco para los
    dos campos de contraseña."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in ("new_password1", "new_password2"):
            self.fields[campo].widget.attrs.update({"class": "kiosco-input"})