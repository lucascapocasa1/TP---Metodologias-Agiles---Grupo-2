from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User


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


class RegistroUsuarioForm(forms.ModelForm):
    """Formulario para que un usuario nuevo se cree su cuenta.
    El rol lo asigna el administrador después desde el panel de Django."""

    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": "kiosco-input", "placeholder": "Contraseña"}
        ),
        min_length=6,
        label="Contraseña",
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": "kiosco-input", "placeholder": "Repetir contraseña"}
        ),
        label="Confirmar contraseña",
    )

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name"]
        widgets = {
            "username": forms.TextInput(
                attrs={"class": "kiosco-input", "placeholder": "Elegí un usuario"}
            ),
            "first_name": forms.TextInput(
                attrs={"class": "kiosco-input", "placeholder": "Tu nombre"}
            ),
            "last_name": forms.TextInput(
                attrs={"class": "kiosco-input", "placeholder": "Tu apellido (opcional)"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = True
        self.fields["last_name"].required = False

    def clean_password2(self):
        p1 = self.cleaned_data.get("password")
        p2 = self.cleaned_data.get("password2")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Las contraseñas no coinciden.")
        return p2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user
