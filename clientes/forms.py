from django import forms

from .models import Cliente


def _dni_normalizado(valor, cliente=None):
    """Limpia el DNI/CUIT (puntos, guiones, espacios) y valida duplicados."""
    dni = (
        (valor or "")
        .strip()
        .replace(".", "")
        .replace("-", "")
        .replace(" ", "")
    )
    if not dni:
        raise forms.ValidationError("Ingresá el DNI o CUIT del cliente.")
    if not dni.isdigit() or not (7 <= len(dni) <= 11):
        raise forms.ValidationError(
            "El DNI/CUIT debe tener entre 7 y 11 dígitos (sin puntos ni guiones)."
        )
    en_uso = Cliente.objects.filter(dni=dni)
    if cliente:
        en_uso = en_uso.exclude(pk=cliente.pk)
    if en_uso.exists():
        raise forms.ValidationError(
            "Ese DNI/CUIT ya está registrado en otro cliente."
        )
    return dni


class ClienteForm(forms.ModelForm):
    """Alta y edición de clientes (HU-12)."""

    class Meta:
        model = Cliente
        fields = ["nombre", "apellido", "dni", "telefono", "email", "activo"]
        widgets = {
            "nombre": forms.TextInput(
                attrs={"class": "kiosco-input", "placeholder": "Nombre"}
            ),
            "apellido": forms.TextInput(
                attrs={"class": "kiosco-input", "placeholder": "Apellido"}
            ),
            "dni": forms.TextInput(
                attrs={
                    "class": "kiosco-input",
                    "placeholder": "Ej: 30123456",
                    "inputmode": "numeric",
                    "autocomplete": "off",
                }
            ),
            "telefono": forms.TextInput(
                attrs={
                    "class": "kiosco-input",
                    "placeholder": "Ej: 11 5555-5555 (opcional)",
                    "autocomplete": "off",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "kiosco-input",
                    "placeholder": "email@ejemplo.com (opcional)",
                    "autocomplete": "off",
                }
            ),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        labels = {
            "dni": "DNI/CUIT",
            "activo": "Cliente activo",
        }

    def __init__(self, *args, **kwargs):
        self.cliente = kwargs.pop("cliente", None)
        super().__init__(*args, **kwargs)
        # El subclass de alta rápida no trae todos los campos.
        for campo in ("telefono", "email"):
            if campo in self.fields:
                self.fields[campo].required = False

    def clean_dni(self):
        return _dni_normalizado(self.cleaned_data.get("dni"), self.cliente)


class ClienteRapidoForm(ClienteForm):
    """Ventanita rápida del cobro (HU-12): solo lo imprescindible."""

    class Meta(ClienteForm.Meta):
        fields = ["nombre", "apellido", "dni"]
        widgets = {
            campo: widget
            for campo, widget in ClienteForm.Meta.widgets.items()
            if campo in ("nombre", "apellido", "dni")
        }
