from django.contrib.auth.forms import AuthenticationForm


class LoginKioscoForm(AuthenticationForm):
    """AuthenticationForm de Django Auth, solo con clases de Bootstrap
    para que los inputs se vean bien sin escribir CSS a mano."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update(
            {"class": "kiosco-input", "autofocus": True, "placeholder": "Tu usuario"}
        )
        self.fields["password"].widget.attrs.update(
            {"class": "kiosco-input", "placeholder": "Tu contraseña"}
        )
