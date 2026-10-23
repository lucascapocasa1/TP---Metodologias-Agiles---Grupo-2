import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
 
class Categoria(models.Model):
     nombre = models.CharField(max_length=100)
     descripcion = models.TextField(blank=True, null=True)
     def __str__(self):
         return self.nombre
class Producto(models.Model):
     nombre = models.CharField(max_length=150)
     descripcion = models.TextField(blank=True, null=True)
     codigo_barras = models.CharField(
         max_length=50,
         unique=True,
         blank=True,
         null=True,
         verbose_name="Código de barras",
         help_text="Se lee con el lector del kiosco. No puede repetirse.",
     )
     precio = models.DecimalField(max_digits=10, decimal_places=2)
     costo = models.DecimalField(
         max_digits=10,
         decimal_places=2,
         default=Decimal("0.00"),
         help_text="Precio de compra unitario. Lo ve solo el Administrador.",
     )
     stock = models.IntegerField(default=0)
     stock_minimo = models.PositiveIntegerField(
         default=5,
         help_text="Alerta de stock bajo (HU-06): se marca cuando el stock "
                   "actual es menor o igual a este valor.",
     )
     categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, related_name='productos')
     activo = models.BooleanField(default=True)
     def __str__(self):
         return f"{self.nombre} - ${self.precio}"

     @property
     def stock_bajo(self):
         """True si hay que marcar el producto por stock bajo (HU-06)."""
         return self.stock <= self.stock_minimo


     @property
     def margen_unitario(self):
         """Ganancia por unidad (precio de venta menos costo)."""
         return self.precio - self.costo

     @property
     def margen_porcentual(self):
         """Margen sobre el costo, en porcentaje. 0 si el costo es 0."""
         if not self.costo:
             return Decimal("0.00")
         return (self.margen_unitario / self.costo) * Decimal("100")

     @property
     def valor_stock_costo(self):
         """Cuánto dinero del negocio está parado en este producto, a costo."""
         return self.costo * self.stock

     @property
     def valor_stock_venta(self):
         """Lo mismo, pero al precio de venta (capital potencial)."""
         return self.precio * self.stock
     
class Venta(models.Model):
     METODO_PAGO = [
         ("efectivo", "Efectivo"),
         ("tarjeta", "Tarjeta"),
         ("cuenta_corriente", "Cuenta corriente (FIAR)"),
         ("mercado_pago", "Mercado Pago (QR)"),
     ]

     fecha = models.DateTimeField(auto_now_add=True)
     total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
     finalizada = models.BooleanField(default=False)
     metodo_pago = models.CharField(
         max_length=20,
         choices=METODO_PAGO,
         default="efectivo",
         verbose_name="Método de pago",
     )
     usuario = models.ForeignKey(
         settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ventas_realizadas",
        verbose_name="Cajero responsable",
     )
     monto_entregado = models.DecimalField(
         max_digits=10,
         decimal_places=2,
         null=True,
         blank=True,
         verbose_name="Monto entregado",
         help_text="Solo para pagos en efectivo.",
     )
     vuelto = models.DecimalField(
         max_digits=10,
         decimal_places=2,
         null=True,
         blank=True,
         help_text="Monto entregado menos el total. Solo para efectivo.",
     )
     cliente = models.ForeignKey(
         "clientes.Cliente",
         on_delete=models.SET_NULL,
         null=True,
         blank=True,
         related_name="ventas",
         verbose_name="Cliente asociado",
         help_text="Cliente de la fidelidad (HU-12). Vacío si es consumidor final.",
     )
     puntos_ganados = models.PositiveIntegerField(
         default=0,
         verbose_name="Puntos de fidelidad ganados",
         help_text="Puntos que sumó esta venta al cliente: 1 cada $100.",
     )

     def __str__(self):
         return f"Venta N° {self.id} - {self.fecha.strftime('%d/%m/%Y')}"
class DetalleVenta(models.Model):
     venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles')
     producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
     cantidad = models.IntegerField(default=1)
     precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
     costo_unitario = models.DecimalField(
         max_digits=10,
         decimal_places=2,
         default=Decimal("0.00"),
         help_text="Costo congelado al momento de la venta, para que el margen "
                   "histórico no cambie si después se actualiza el precio de compra.",
     )
     def subtotal(self):
         return self.cantidad * self.precio_unitario
     def costo_total(self):
         return self.cantidad * self.costo_unitario
     def ganancia(self):
         return self.subtotal() - self.costo_total()
     def __str__(self):
         return f"{self.cantidad}x {self.producto.nombre}"


class Turno(models.Model):
    """HU-10: turno de caja. Registra quién estaba a cargo y, al cerrar,
    congela los totales (efectivo, tarjeta y operaciones) para poder
    contar la plata aunque después se registren más ventas.
    """

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="turnos",
        verbose_name="Usuario a cargo",
    )
    fecha_apertura = models.DateTimeField(auto_now_add=True)
    fecha_cierre = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Vacío mientras el turno sigue abierto.",
    )
    total_efectivo = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    total_tarjeta = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    deuda_otorgada = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Deuda otorgada (cuenta corriente)",
        help_text="HU-14: lo fiado en el turno. No es plata en la caja, "
                  "por eso se informa aparte de efectivo y tarjeta.",
    )
    total_mercado_pago = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        db_default=Decimal("0.00"),
        verbose_name="Total Mercado Pago (QR)",
        help_text="Lo cobrado con QR de Mercado Pago en el turno.",
    )
    cantidad_operaciones = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-fecha_apertura"]
        verbose_name = "turno"
        verbose_name_plural = "turnos"

    @property
    def activo(self):
        """True mientras no se registró el cierre."""
        return self.fecha_cierre is None

    @property
    def total_general(self):
        """Lo que entró en el turno: efectivo, tarjeta y Mercado Pago."""
        return self.total_efectivo + self.total_tarjeta + self.total_mercado_pago

    def __str__(self):
        estado = "abierto" if self.activo else "cerrado"
        nombre = self.usuario.username if self.usuario else "sin usuario"
        return f"Turno de {nombre} - {self.fecha_apertura:%d/%m/%Y %H:%M} ({estado})"


class PagoMercadoPago(models.Model):
    """
    Cobro con QR de Mercado Pago de una venta.

    Mientras el cliente paga, la Venta queda con `finalizada=False` (no cuenta
    en reportes ni en el turno) y el stock ya está reservado. Al aprobarse el
    pago la venta pasa a finalizada; si se cancela, el stock vuelve.
    """

    PENDIENTE = "pendiente"
    APROBADO = "aprobado"
    CANCELADO = "cancelado"

    ESTADOS = [
        (PENDIENTE, "Esperando pago"),
        (APROBADO, "Aprobado"),
        (CANCELADO, "Cancelado"),
    ]

    venta = models.OneToOneField(
        Venta,
        on_delete=models.CASCADE,
        related_name="pago_mp",
        verbose_name="venta",
    )
    # Identificador público para el link del pago simulado (no expone el id).
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    preference_id = models.CharField("ID de preferencia", max_length=100, blank=True)
    link_pago = models.CharField("link de pago", max_length=500)
    simulado = models.BooleanField(
        default=False,
        help_text="Creado sin credenciales de Mercado Pago, solo para probar.",
    )
    estado = models.CharField(max_length=20, choices=ESTADOS, default=PENDIENTE)
    payment_id = models.CharField("ID de pago en Mercado Pago", max_length=50, blank=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-creado"]
        verbose_name = "pago con Mercado Pago"
        verbose_name_plural = "pagos con Mercado Pago"

    def __str__(self):
        return f"Pago MP de la venta N° {self.venta_id} ({self.get_estado_display()})"


class ConexionMercadoPago(models.Model):
    """
    Cuenta de Mercado Pago del negocio, conectada con el botón "Conectar con
    Mercado Pago" (OAuth). Los cobros con QR se hacen a nombre de esta cuenta,
    así la plata le llega directo al negocio.

    Hay una sola por instalación de Norvex: cada negocio tiene su propia
    instalación, así que las cuentas no se pueden mezclar. Si en el futuro el
    sistema pasa a multi-negocio, alcanza con agregar acá un FK al negocio.
    """

    # Credenciales que entrega Mercado Pago al autorizar. Son secretas: no se
    # muestran en ninguna pantalla ni en el admin de Django.
    access_token = models.CharField(max_length=255)
    refresh_token = models.CharField(max_length=255, blank=True)
    expira = models.DateTimeField(
        null=True, blank=True, help_text="Cuándo vence el access token."
    )
    mp_user_id = models.CharField("ID de usuario en Mercado Pago", max_length=50)
    nombre_cuenta = models.CharField(
        "Cuenta de Mercado Pago", max_length=200, blank=True,
        help_text="Nombre o email de la cuenta, para mostrar en el panel.",
    )
    produccion = models.BooleanField(
        default=False, help_text="False = cuenta de prueba (sandbox, plata ficticia)."
    )
    conectada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    conectada = models.DateTimeField(auto_now_add=True)
    actualizada = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "conexión con Mercado Pago"
        verbose_name_plural = "conexión con Mercado Pago"

    def __str__(self):
        return f"Mercado Pago: {self.nombre_cuenta or self.mp_user_id}"

    @classmethod
    def actual(cls):
        """La cuenta conectada, o None."""
        return cls.objects.order_by("-conectada").first()
