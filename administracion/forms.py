from django import forms
from django.contrib.auth.models import Group, User

from negocios.models import Negocio
from usuarios.models import Empleado


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


class NegocioForm(forms.ModelForm):
    """Formulario para crear y editar un negocio (superadmin)."""

    class Meta:
        model = Negocio
        fields = [
            "nombre",
            "slug",
            "logo",
            "direccion",
            "telefono",
            "whatsapp",
            "email",
            "horarios",
            "color_primario",
            "activo",
        ]
        widgets = {
            "nombre": forms.TextInput(
                attrs={"class": "kiosco-input", "placeholder": "Nombre del negocio"}
            ),
            "slug": forms.TextInput(
                attrs={"class": "kiosco-input", "placeholder": "ej: ferreteria-martillito"}
            ),
            "logo": forms.URLInput(
                attrs={"class": "kiosco-input", "placeholder": "https://ejemplo.com/logo.png"}
            ),
            "direccion": forms.TextInput(
                attrs={"class": "kiosco-input", "placeholder": "Dirección física"}
            ),
            "telefono": forms.TextInput(
                attrs={"class": "kiosco-input", "placeholder": "Teléfono"}
            ),
            "whatsapp": forms.TextInput(
                attrs={"class": "kiosco-input", "placeholder": "5491155554444"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "kiosco-input", "placeholder": "email@negocio.com"}
            ),
            "horarios": forms.Textarea(
                attrs={"class": "kiosco-input", "rows": 3, "placeholder": "Lun a Vie 9:00-18:00"}
            ),
            "color_primario": forms.TextInput(
                attrs={"class": "kiosco-input", "type": "color"}
            ),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class AsignarNegocioForm(forms.Form):
    """Formulario para crear un empleado: usuario + negocio + rol."""

    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(
            attrs={"class": "kiosco-input", "placeholder": "Nombre de usuario"}
        ),
        label="Usuario",
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": "kiosco-input", "placeholder": "Contraseña"}
        ),
        min_length=6,
        label="Contraseña",
    )
    first_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "kiosco-input", "placeholder": "Nombre"}
        ),
        label="Nombre",
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "kiosco-input", "placeholder": "Apellido"}
        ),
        label="Apellido",
    )
    negocio = forms.ModelChoiceField(
        queryset=Negocio.objects.filter(activo=True).order_by("nombre"),
        widget=forms.Select(attrs={"class": "kiosco-input"}),
        label="Negocio",
    )
    rol = forms.ModelChoiceField(
        queryset=Group.objects.filter(name__in=["Administrador", "Cajero"]).order_by(
            "name"
        ),
        widget=forms.Select(attrs={"class": "kiosco-input"}),
        label="Rol",
    )
