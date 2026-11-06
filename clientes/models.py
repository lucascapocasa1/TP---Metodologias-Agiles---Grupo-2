from decimal import Decimal

from django.conf import settings
from django.db import models


class Cliente(models.Model):
    """Cliente del kiosco: datos básicos + fidelidad (HU-12) y cuenta
    corriente (HU-14).

    Los puntos se acumulan al confirmar cada venta (1 punto cada $100) y
    nunca se recalculan: `Venta.puntos_ganados` guarda lo que sumó cada
    compra para el historial.

    La cuenta corriente funciona igual de acumulativa: `limite_credito` es
    el máximo que el Administrador le autoriza fiarse y `saldo_deuda` es lo
    que debe hoy. El saldo se **guarda** (no se recalcula) para poder
    auditarlo: cada fianza lo sube y cada pago lo baja, siempre dentro de
    una transacción con bloqueo de fila.
    """

    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    dni = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="DNI/CUIT",
        help_text="Sin puntos ni guiones. No puede repetirse.",
    )
    telefono = models.CharField(
        max_length=30, blank=True, verbose_name="Teléfono"
    )
    email = models.EmailField(blank=True)
    fecha_registro = models.DateTimeField(
        auto_now_add=True, verbose_name="Fecha de registro"
    )
    puntos = models.PositiveIntegerField(
        default=0, verbose_name="Puntos de fidelidad"
    )
    limite_credito = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Límite de crédito",
        help_text="Máximo que se le puede fiar en cuenta corriente (HU-14). "
                  "0 = no tiene cuenta corriente habilitada.",
    )
    saldo_deuda = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Saldo de deuda",
        help_text="Lo que el cliente debe hoy por compras fiadas menos los "
                  "pagos que hizo. Lo actualiza el sistema, no se edita a mano.",
    )
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["apellido", "nombre"]
        verbose_name = "cliente"
        verbose_name_plural = "clientes"

    def __str__(self):
        return f"{self.nombre_completo} · DNI {self.dni}"

    @property
    def nombre_completo(self):
        return f"{self.nombre} {self.apellido}".strip()

    @property
    def tiene_cuenta_corriente(self):
        """True si el Administrador le habilitó un límite mayor a cero."""
        return self.limite_credito > 0

    @property
    def credito_disponible(self):
        """Cuánto más se le puede fiar sin pasarse del límite (nunca < 0)."""
        disponible = self.limite_credito - self.saldo_deuda
        return disponible if disponible > 0 else Decimal("0.00")

    @property
    def saldo_al_limite(self):
        """True si ya debe el límite (o más) y no se le puede fiar nada."""
        return self.saldo_deuda >= self.limite_credito

    def puede_fiar(self, monto):
        """True si `monto` cabe dentro del crédito disponible del cliente."""
        return self.tiene_cuenta_corriente and monto <= self.credito_disponible


class PagoCuentaCorriente(models.Model):
    """Pago parcial o total de la deuda de un cliente (HU-14).

    Cada pago deja su registro para poder mostrar el historial en la ficha
    del cliente: cuánto pagó, cuándo y quién lo recibió. El saldo del
    cliente (`Cliente.saldo_deuda`) es el acumulado de todo esto.
    """

    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE,
        related_name="pagos",
        verbose_name="Cliente",
    )
    negocio = models.ForeignKey(
        "negocios.Negocio",
        on_delete=models.CASCADE,
        related_name="pagos_cuenta_corriente",
        verbose_name="Negocio",
        null=True,
        blank=True,
    )
    monto = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Monto pagado"
    )
    fecha = models.DateTimeField(auto_now_add=True, verbose_name="Fecha")
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pagos_cuenta_corriente",
        verbose_name="Cobrado por",
    )
    observacion = models.CharField(
        max_length=200, blank=True, verbose_name="Observación",
        help_text="Detalle opcional del pago (por ejemplo, 'pagó en dos partes').",
    )

    class Meta:
        ordering = ["-fecha"]
        verbose_name = "pago de cuenta corriente"
        verbose_name_plural = "pagos de cuenta corriente"

    def __str__(self):
        return f"Pago {self.pk} de {self.cliente.nombre_completo}: ${self.monto}"
