from django import forms

from .models import Categoria, Producto


class ProductoForm(forms.ModelForm):
    """Formulario para dar de alta, editar y dar de baja productos (HU-04)."""

    class Meta:
        model = Producto
        fields = [
            "nombre",
            "codigo_barras",
            "descripcion",
            "costo",
            "precio",
            "stock",
            "stock_minimo",
            "categoria",
            "activo",
        ]
        widgets = {
            "nombre": forms.TextInput(
                attrs={"class": "kiosco-input", "placeholder": "Nombre del producto"}
            ),
            "codigo_barras": forms.TextInput(
                attrs={
                    "class": "kiosco-input",
                    "placeholder": "Ej: 7791234567890",
                    "inputmode": "numeric",
                    "autocomplete": "off",
                }
            ),
            "descripcion": forms.Textarea(
                attrs={
                    "class": "kiosco-input",
                    "placeholder": "Descripción (opcional)",
                    "rows": 3,
                }
            ),
            "costo": forms.NumberInput(
                attrs={
                    "class": "kiosco-input",
                    "placeholder": "0.00",
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "precio": forms.NumberInput(
                attrs={
                    "class": "kiosco-input",
                    "placeholder": "0.00",
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "stock": forms.NumberInput(
                attrs={"class": "kiosco-input", "placeholder": "0", "min": "0"}
            ),
            "stock_minimo": forms.NumberInput(
                attrs={"class": "kiosco-input", "placeholder": "5", "min": "0"}
            ),
            "categoria": forms.Select(attrs={"class": "kiosco-input"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        labels = {
            "codigo_barras": "Código de barras",
            "costo": "Precio de costo",
            "precio": "Precio de venta",
            "stock_minimo": "Stock mínimo (alerta)",
            "activo": "Producto activo",
        }

    def __init__(self, *args, **kwargs):
        self.producto = kwargs.pop("producto", None)
        super().__init__(*args, **kwargs)
        self.fields["categoria"].empty_label = "Seleccionar categoría"
        self.fields["codigo_barras"].required = False
        self.fields["descripcion"].required = False

    def clean_codigo_barras(self):
        """HU-04: si el código de barras ya existe, no se permite duplicar."""
        codigo = self.cleaned_data.get("codigo_barras")
        if not codigo:
            return codigo
        en_uso = Producto.objects.filter(codigo_barras=codigo)
        if self.producto:
            en_uso = en_uso.exclude(pk=self.producto.pk)
        if en_uso.exists():
            raise forms.ValidationError(
                "Ese código de barras ya está registrado en otro producto."
            )
        return codigo

    def clean_precio(self):
        precio = self.cleaned_data["precio"]
        if precio <= 0:
            raise forms.ValidationError("El precio de venta debe ser mayor a 0.")
        return precio
