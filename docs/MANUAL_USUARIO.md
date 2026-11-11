# Manual de Usuario — Norvex

Guía rápida para el uso diario del sistema. Dirigido a dueños (Administrador) y cajeros.

---

## 1. Primeros pasos

### 1.1 Acceder al sistema

- URL local: `http://127.0.0.1:8000/`
- URL en producción: `https://norvex.onrender.com/`

Al entrar, se te pedirá iniciar sesión con usuario y contraseña.

### 1.2 Usuarios de prueba (datos de demo)

| Usuario | Contraseña | Rol | Puede hacer |
|---------|-----------|-----|-------------|
| `admin` | `kiosco2024` | Superadmin | Todo: crear negocios, empleados, ver todos los comercios |
| `admin_barrio` | `kiosco2024` | Administrador | Kiosco De Barrio: gestionar su negocio completo |
| `cajero_barrio_1` | `kiosco2024` | Cajero | Kiosco De Barrio: solo pantalla de cobro |
| `admin_martillito` | `kiosco2024` | Administrador | Ferretería Martillito: gestionar su negocio completo |
| `cajero_martillito_1` | `kiosco2024` | Cajero | Ferretería Martillito: solo pantalla de cobro |
| `admin_natural` | `kiosco2024` | Administrador | Dietética Natural: gestionar su negocio completo |
| `cajero_natural_1` | `kiosco2024` | Cajero | Dietética Natural: solo pantalla de cobro |

---

## 2. Pantalla de cobro (POS)

Es la pantalla principal del cajero. Desde aquí se hacen las ventas del día.

### 2.1 Vender un producto

1. Ingresá con un usuario de rol **Cajero** o **Administrador**.
2. En la pantalla de cobro, escribí el **código de barras** o el **nombre del producto** en el buscador.
3. Seleccioná el producto de la lista de sugerencias.
4. Si necesitás cambiar la cantidad, usá los botones `+` y `-` al lado del ítem en el carrito.
5. Elegí el **método de pago**: Efectivo, Tarjeta o Cuenta Corriente (FIAR).
   - Si pagó en **efectivo**, ingresá el monto entregado y el sistema calculará el vuelto automáticamente.
6. Hacé clic en **Confirmar venta**.
7. El sistema descuenta el stock, registra la venta y muestra el comprobante.

### 2.2 Cobrar a cuenta corriente (FIAR)

Solo para clientes registrados con cuenta corriente habilitada:

1. En el carrito, asociá un cliente (buscá por DNI o nombre).
2. Elegí **Cuenta Corriente** como método de pago.
3. El sistema validará que el monto no supere el límite de crédito del cliente.
4. Confirmá la venta. La deuda queda registrada en la ficha del cliente.

### 2.3 Cobro con QR de Mercado Pago

1. Elegí **Mercado Pago (QR)** como método de pago.
2. El sistema genera un QR que el cliente puede escanear con su celular.
3. La venta queda como **pendiente** hasta que el pago se apruebe.
4. Cuando el pago se confirma, la venta se finaliza automáticamente y se muestra el comprobante.
5. Si se cancela, el stock vuelve y los productos regresan al carrito.

---

## 3. Gestión de productos (solo Administrador)

### 3.1 Alta de producto

1. Ve a **Gestionar productos** (menú lateral).
2. Hacé clic en **Nuevo producto**.
3. Completá: nombre, categoría, código de barras, precio de venta, precio de costo, stock y stock mínimo.
4. Guardá.

### 3.2 Editar y dar de baja

- Desde la lista de productos podés editar cualquier dato o dar de baja un producto (baja lógica: desaparece del catálogo pero se conserva en ventas históricas).
- Los productos con **stock bajo** (igual o menor al stock mínimo) se marcan automáticamente.

---

## 4. Cierre de turno (arqueo de caja)

Al final del día, el cajero o administrador cierra el turno:

1. Ve a **Cierre de turno** (menú lateral).
2. Ingresá los montos físicos contados: **efectivo, tarjeta y Mercado Pago**.
3. El sistema compara con los totales registrados y calcula la diferencia (sobrante o faltante).
4. Guardá el arqueo. Queda registrado vinculado al turno.

---

## 5. Gestión de clientes y cuenta corriente FIAR

### 5.1 Clientes frecuentes

Desde **Gestionar clientes** podés crear, editar y buscar clientes por DNI o nombre.

### 5.2 Cuenta corriente (FIAR)

En la ficha de cada cliente podés:
- Ver su **límite de crédito** y su **deuda actual**.
- Registrar pagos de su deuda (pago parcial o total).
- Ver el historial de pagos y compras fiadas.

Desde el POS, al cobrar con **Cuenta Corriente**, la deuda del cliente aumenta automáticamente dentro del límite asignado.

---

## 6. Facturas y Proveedores (módulo separado)

El sistema tiene dos módulos separados en el menú lateral: **Facturas** y **Proveedores**.

### 6.1 Facturas (servicios y gastos)

Sirve para luz, gas, seguridad e higiene, y otros gastos del negocio.

- **Crear factura:** completá monto, fecha de vencimiento, categoría y opcionalmente un archivo adjunto (PDF o imagen).
- **Registrar pago:** podés hacer un pago parcial o total. El saldo se actualiza automáticamente.
- **Anular:** si una factura se anuló, podés anularla para que deje de contar como deuda.
- **Vencimientos:** las facturas vencidas se muestran en rojo; las que vencen en 7 días o menos se marcan con alerta.

### 6.2 Proveedores (cuentas corrientes de mercadería)

Sirve para llevar la deuda con proveedores de mercadería.

- **Crear proveedor:** desde el módulo Proveedores podés dar de alta un proveedor nuevo.
- **Ver deuda:** cada proveedor muestra su saldo pendiente, cuánto está vencido y cuál es el próximo vencimiento.
- **Pagar a proveedor (FIFO):** al registrar un pago, el sistema lo aplica automáticamente a las facturas más antiguas primero. Antes de confirmar, se muestra una **previsualización** de cómo se repartirá el pago.
- **Convertir en proveedor:** si tenés facturas viejas con el nombre del proveedor escrito a mano, podés convertir ese nombre en un proveedor registrado de a uno, con confirmación.
- **Historial de pagos:** en la ficha de cada proveedor ves todos los pagos realizados, agrupados por operación.

---

## 7. Reportes y dashboard

Desde el **Dashboard** (menú lateral) podés ver:

- Ventas del período con variación contra el período anterior.
- Clientes con cuenta corriente (FIAR) y su deuda.
- Pedidos pendientes con más de 48 horas.
- Productos más vendidos y productos sin movimiento.
- Ingresos por medio de pago (efectivo, tarjeta, Mercado Pago).
- Próximos vencimientos de facturas.

También podés exportar el **stock a Excel** desde el reporte de stock.

---

## 8. Tienda online pública

Cada negocio tiene su propia tienda online en `/t/<slug>/` (por ejemplo, `/t/kiosco-de-barrio/`).

- Los clientes pueden ver el catálogo sin iniciar sesión.
- Pueden armar un pedido y enviarlo por WhatsApp al local.
- El dueño ve el pedido en su panel y lo cobra al retirar.

---

## 9. Comandos útiles (para el administrador del sistema)

Desde la terminal del proyecto:

```powershell
# Crear usuarios iniciales
python manage.py setup_inicial

# Cargar datos de demo (50+ productos y ventas)
python manage.py cargar_demo --limpiar

# Cargar clientes y pedidos de WhatsApp
python manage.py cargar_demo_clientes --limpiar

# Correr todos los tests
python manage.py test

# Ejecutar el servidor
python manage.py runserver 8000
```

---

## 10. Soporte y soporte técnico

- Si el cajero no ve alguna pantalla, es porque no tiene el rol necesario (recibe 403).
- Si olvidaste la contraseña, usá el enlace "¿Olvidaste tu contraseña?" en el login.
- Los datos se guardan en PostgreSQL; el sistema está publicado en Render (`https://norvex.onrender.com/`).

---

**Última actualización:** 11 de noviembre de 2026  
**Versión:** 1.0
