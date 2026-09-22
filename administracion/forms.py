from django import forms
from django.contrib.auth.models import Group, User


class UsuarioForm(forms.ModelForm):
    """Formulario para crear y editar usuarios."""

    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": "kiosco-input", "placeholder": "Contraseña"}
        ),
        min_length=6,
        label="Contraseña",
        required=False,
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": "kiosco-input", "placeholder": "Repetir contraseña"}
        ),
        label="Confirmar contraseña",
        required=False,
    )

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "is_active",
            "is_staff",
        ]
        widgets = {
            "username": forms.TextInput(
                attrs={"class": "kiosco-input", "placeholder": "Usuario"}
            ),
            "first_name": forms.TextInput(
                attrs={"class": "kiosco-input", "placeholder": "Nombre"}
            ),
            "last_name": forms.TextInput(
                attrs={"class": "kiosco-input", "placeholder": "Apellido"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "kiosco-input", "placeholder": "Email"}
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_staff": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        self.es_edicion = kwargs.pop("es_edicion", False)
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = True
        self.fields["last_name"].required = False
        self.fields["email"].required = False

        if self.es_edicion:
            self.fields["password"].help_text = "Dejar en blanco para no cambiar la contraseña"
        else:
            self.fields["password"].required = True
            self.fields["password2"].required = True

    def clean_password2(self):
        p1 = self.cleaned_data.get("password")
        p2 = self.cleaned_data.get("password2")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Las contraseñas no coinciden.")
        return p2

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user


class AsignarRolForm(forms.Form):
    """Formulario para asignar roles (grupos) a un usuario."""

    grupos = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
        label="Roles",
        required=False,
    )

    def __init__(self, *args, **kwargs):
        usuario = kwargs.pop("usuario", None)
        super().__init__(*args, **kwargs)
        if usuario:
            self.fields["grupos"].initial = usuario.groups.all()
