# Evolución de Norvex: Arquitectura Multiempresa (Implementado)

**Proyecto:** Norvex (antes "Sistema Kiosco") — Django 6.1.1 + PostgreSQL  
**Estado:** Implementado y verificado  
**Objetivo:** Convertir el punto de venta actual en una plataforma SaaS multiempresa sin reemplazar funcionalidades existentes.

---

## 1. Contexto y objetivo general

Norvex ya funciona como POS para un solo comercio. Tiene:
- Gestión de productos y categorías (`ventas`)
- Control de stock y alerta de stock bajo
- Registro de ventas presenciales con carrito en sesión
- Cierre de turno y caja
- Gestión de clientes, fidelidad y cuenta corriente "FIAR" (`clientes`)
- Pedidos online desde catálogo público sin login (`pedidos`)
- Cobro con QR de Mercado Pago
- Usuarios y roles vía Django Groups (`Administrador`, `Cajero`)

**Meta:** Que varios comercios puedan usar Norvex simultáneamente, cada uno con sus propios productos, clientes, ventas, pedidos y configuración, sin que los datos se mezclen. Cada comercio tendrá:
- **Norvex Gestión** (privado, con login): administración del local.
- **Norvex Online** (público, sin login): tienda online generada automáticamente.

**Restricción crítica:** No reescribir nada desde cero. Reutilizar todo lo que ya funciona (`_crear_venta`, `registrar_venta_desde_items`, lógica de puntos/fiado, etc.).

---

## 2. Decisiones clave (resumen ejecutivo)

| Punto | Decisión tomada | Motivo |
|-------|----------------|--------|
| Arquitectura | Single database + shared schema (una sola BD, esquema compartido) | Más simple, gratis en Render, no requiere infraestructura compleja |
| Identificación del negocio | Por **path** en la URL, no por subdominio | Render gratis no da wildcard subdominios sobre `onrender.com`. Paths funcionan sin gastar en dominios ni DNS |
| Modelo `Usuario` | `auth.User` por defecto, **sin custom user model** | No romper compatibilidad existente |
| Relación Usuario → Negocio | Nuevo modelo `Empleado` (OneToOne con `User`, FK a `Negocio`) | Un empleado trabaja en un solo comercio |
| Cliente | **Compartido** (sin FK a Negocio) | Un mismo cliente (mismo DNI) puede comprar en varios comercios; cada negocio ve solo sus propias ventas de ese cliente |
| Superadmin | Usuario con `is_superuser=True` | Puede crear negocios y administrar la plataforma |
| Precios POS vs Online | **Mismo precio** (`producto.precio`) | Menos complejidad inicial |
| Envío | Opcional ($1000 si elige domicilio, $0 si retira en local) | Definido por el cliente al confirmar el pedido |
| Stock en pedidos online | Reserva al **confirmar pedido**, con expiración de 48 horas | Evita reservar stock en carritos abandonados |
| Datos actuales | Migran al negocio "Kiosco De Barrio" (slug `de-barrio`) | No se pierde nada; luego se crean "Ferretería Martillito" y "Dietética Natural" |

---

## 3. Arquitectura técnica

```
┌─────────────────────────────────────────────────────────┐
│              Render (plan gratuito)                     │
│  norvex.onrender.com  (un solo servicio web, una BD)   │
└─────────────────────────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
   / (landing)    /t/<slug>/      /app/
   (pública)    (tienda online)  (gestión privada)
   de todos     por negocio      login requerido
   los negocios (catálogo,      (POS, productos,
   de recuadros  carrito, pedido)  clientes, turnos)
```

- **Middleware `NegocioMiddleware`**: resuelve `request.negocio` para cada request.
- **Aislamiento de datos**: todas las consultas de modelos sensibles filtran por `negocio = request.negocio`. Nunca confiar en un `negocio_id` enviado por el frontend.
- **Superadmin**: ve todos los negocios; no aplica filtro de negocio único.

---

## 4. Modelo de datos (entidades y relaciones)

### 4.1 Modelo nuevo: `Negocio` (app `negocios` o `administracion`)

| Campo | Tipo | Detalle |
|-------|------|---------|
| `nombre` | CharField(100) | Nombre del comercio (ej. "Ferretería Martillito") |
| `slug` | SlugField, unique | Para la URL: `ferreteria-martillito` |
| `logo` | ImageField/URLField, blank | Logo de la tienda online |
| `direccion` | CharField, blank | Dirección física |
| `telefono` | CharField, blank | Teléfono de contacto |
| `whatsapp` | CharField, blank | WhatsApp del negocio |
| `email` | EmailField, blank | Email de contacto del negocio |
| `horarios` | TextField, blank | Ej. "Lun a Vie 9:00-18:00" |
| `color_primario` | CharField, default="#00FFFF" | Color tema de su tienda online |
| `activo` | Boolean, default=True | Si el negocio está habilitado |
| `fecha_creacion` | DateTime, auto_now_add | |

### 4.2 Modelo nuevo: `Empleado` (app `usuarios`)

| Campo | Tipo | Detalle |
|-------|------|---------|
| `usuario` | OneToOneField(User) | Usuario de Django |
| `negocio` | FK(Negocio) | El único comercio donde trabaja |
| `activo` | Boolean, default=True | |

**Regla:** Un usuario = un solo negocio. El rol sigue siendo vía Django Groups (`Administrador`, `Cajero`).

### 4.3 Modelos existentes — agregar `negocio = FK(Negocio)`

| Modelo | ¿Agrega FK negocio? | Notas |
|--------|---------------------|-------|
| `Categoria` | ✅ Sí | Cada negocio tiene sus propias categorías |
| `Producto` | ✅ Sí | Stock, precio y pertenencia por negocio |
| `Venta` | ✅ Sí | Para saber de qué negocio es cada venta |
| `Turno` | ✅ Sí | Cierre de caja por negocio |
| `Pedido` | ✅ Sí | Pedido online de un negocio específico |
| `PagoCuentaCorriente` | ✅ Sí | Para saber en qué negocio se registró el pago |
| `ConexionMercadoPago` | ✅ Sí | Una conexión por negocio (reemplaza el comentario del futuro en el modelo actual) |
| `Cliente` | ❌ No | **Compartido**: un mismo DNI puede comprar en varios comercios |
| `DetalleVenta` | ❌ No | Hereda el negocio de su `Venta` padre |
| `ItemPedido` | ❌ No | Hereda el negocio de su `Pedido` padre |
| `PagoMercadoPago` | ❌ No | Hereda de `Venta` |

### 4.4 Modelo nuevo: `ReservaStock` (para el plazo de 48 horas)

| Campo | Tipo | Detalle |
|-------|------|---------|
| `producto` | FK(Producto) | Producto reservado |
| `cantidad` | IntegerField | Unidades reservadas |
| `fecha_reserva` | DateTime, auto_now_add | Cuándo se reservó |
| `fecha_expiracion` | DateTimeField | `fecha_reserva + 48 horas` |
| `estado` | CharField | `reservada`, `liberada`, `convertida` |
| `session_key` | CharField, blank | Para clientes sin login (sesión del navegador) |
| `cliente` | FK(Cliente), null, blank | Si el cliente está identificado |
| `pedido` | FK(Pedido), null, blank | Cuando se confirma el pedido, se vincula aquí |

**Regla de stock disponible:** `stock_disponible = producto.stock - sum(cantidad de reservas estado='reservada' y no expiradas)`. Si pasa la expiración sin convertirse en pedido, la reserva se libera (estado `liberada`) y el stock vuelve al disponible.

---

## 5. Reglas de negocio críticas (no negociables)

1. **Un usuario trabaja en un solo negocio.** No se puede ser cajero de dos comercios al mismo tiempo con la misma cuenta.
2. **El superadmin (`is_superuser=True`) crea negocios.** Luego otorga poder de admin del negocio al dueño (grupo `Administrador` + `Empleado.negocio = ese negocio`).
3. **Un cliente puede comprar en varios negocios.** `Cliente` es compartido. Cada negocio ve solo las `Venta` y `Pedido` de su propio `negocio_id`.
4. **Reserva de stock se crea al confirmar el pedido**, no al agregar al carrito. Plazo máximo: 48 horas. Si no se retira, el stock se devuelve.
5. **Mismo precio en POS y online.** `producto.precio` se usa en ambos canales.
6. **Envío opcional.** El cliente elige retiro en local ($0) o envío a domicilio ($1000 extra). Esta lógica se agrega al flujo de pedido, no se hardcodea para todos.
7. **Entregar un pedido es cobrarlo.** No existe "marcar entregado" sin venta. `registrar_entrega()` (lógica existente) crea la `Venta`, vincula al `Pedido`, descuenta stock y marca `estado='entregado'`.
8. **Aislamiento desde el backend.** Nunca confiar en identificadores de negocio enviados libremente desde el frontend para determinar a qué comercio pertenece un usuario autenticado.

---

## 6. Estrategia de aislamiento de datos (MUY IMPORTANTE — leer antes de tocar cualquier consulta)

### 6.1 Middleware `NegocioMiddleware`

Debe agregarse a `MIDDLEWARE` en `config/settings.py` (después de `AuthenticationMiddleware`).

Resuelve `request.negocio` así:

| Ruta | Cómo se resuelve el negocio |
|------|----------------------------|
| `/t/<slug>/...` (público) | Lee el `slug` de la URL → `Negocio.objects.get(slug=slug, activo=True)` |
| `/app/...` (gestión privada) | Lee `request.user` → `Empleado.objects.get(usuario=request.user).negocio` |
| `/superadmin/...` | No hay negocio único (o se selecciona uno explícitamente) |
| Cualquier otra | `request.negocio = None` |

### 6.2 Cómo usarlo en las vistas

**Correcto (filtrado por negocio):**
```python
productos = Producto.objects.filter(negocio=request.negocio, activo=True)
ventas = Venta.objects.filter(negocio=request.negocio, finalizada=True)
clientes_del_negocio = Cliente.objects.filter(ventas__negocio=request.negocio).distinct()
```

**Incorrecto (sin filtro, mezclar datos de todos los comercios):**
```python
productos = Producto.objects.all()  # ❌ NUNCA hacer esto en vistas de negocio
ventas = Venta.objects.all()        # ❌ NUNCA hacer esto
```

### 6.3 Managers personalizados (recomendado)

Para evitar olvidos, crear managers que filtren automáticamente por `negocio`:

```python
class NegocioQuerySet(models.QuerySet):
    def para_negocio(self, negocio):
        return self.filter(negocio=negocio)

class ProductoManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(negocio=...)
```

**Ojo:** esto solo aplica a modelos que tengan FK `negocio`. `Cliente` no la tiene.

---

## 7. URLs y rutas (paths, no subdominios)

| Ruta | Público/Privado | Propósito |
|------|----------------|-----------|
| `/` | Público | Landing institucional: listado de negocios activos con recuadros (logo, nombre, botón "Entrar a la tienda") |
| `/t/<slug>/` | Público | Catálogo público del negocio (sin login). Ver productos, agregar al carrito, confirmar pedido |
| `/t/<slug>/carrito/` | Público | Ver carrito del pedido online |
| `/t/<slug>/confirmar/` | Público | Confirmar pedido (elige retiro o envío, crea `Pedido` estado `pendiente`) |
| `/app/` | Privado (login) | Dashboard de gestión (redirect según rol) |
| `/app/ventas/` | Privado | POS del negocio (solo sus productos) |
| `/app/productos/` | Privado | CRUD de productos del negocio |
| `/app/clientes/` | Privado | Clientes (compartidos, pero filtrados por ventas de este negocio) |
| `/app/pedidos/` | Privado | Pedidos pendientes del negocio (para entregar y cobrar) |
| `/app/turno/` | Privado | Cierre de turno del negocio |
| `/superadmin/` | Privado (superadmin) | Panel de plataforma: crear negocios, crear empleados, ver todos los negocios |

Las URLs existentes (`/ventas/`, `/clientes/`, `/pedidos/`) se mantienen para compatibilidad, pero el middleware las filtra por `request.negocio` del usuario autenticado.

---

## 8. Flujo completo: compra online y retiro en local

1. **Superadmin** crea negocio "Ferretería Martillito" (`slug: ferreteria-martillito`).
2. **Superadmin** crea usuario dueño, le asigna grupo `Administrador` y `Empleado.negocio = Martillito`.
3. **Dueño** entra a `/app/`, carga productos y categorías (quedan asociados a Martillito).
4. **Cliente** entra a `norvex.onrender.com/t/ferreteria-martillito/`, ve el catálogo de Martillito.
5. **Cliente** agrega productos al carrito online (no hay reserva todavía, solo carrito en sesión).
6. **Cliente** confirma el pedido. Elige retiro en local o envío a domicilio (+$1000). Se crea:
   - `Pedido` (estado `pendiente`, total congelado, `negocio = Martillito`).
   - `ItemPedido` con precio congelado.
   - `ReservaStock` (estado `reservada`, `fecha_expiracion = ahora + 48h`).
7. **Dueño/empleado** ve el pedido en `/app/pedidos/` de Martillito.
8. **Cliente** retira en el local y paga (efectivo, tarjeta, MP o fiado).
9. `registrar_entrega()` (lógica existente, reusada):
   - Bloquea el pedido (`select_for_update`).
   - Crea `Venta` con `negocio = Martillito`, precio congelado, stock descontado definitivamente.
   - Vincula `Pedido.venta = Venta`, `Pedido.estado = 'entregado'`, `ReservaStock.estado = 'convertida'`.
   - Si es cuenta corriente, valida límite y suma deuda.
10. **Si pasan 48h** y el cliente no retiró: la reserva expira (`liberada`) y el stock vuelve al disponible general del negocio.

---

## 9. Integración con el POS existente (qué se reusa y qué se toca)

| Componente | ¿Se reusa? | ¿Qué cambia? |
|------------|------------|--------------|
| `ventas/services.py::_crear_venta()` | ✅ Sí | Ahora también guarda `venta.negocio` |
| `ventas/services.py::registrar_venta_desde_items()` | ✅ Sí | Ya lo usa `pedidos`. Ahora el `Pedido` trae su `negocio` |
| `clientes/services.py` (puntos, fiado, validar_fiado) | ✅ Sí | Sin cambios de lógica; `Cliente` sigue siendo compartido |
| `pedidos/services.py::crear_pedido()` | ✅ Sí | Ahora asigna `pedido.negocio` según el negocio de la URL pública |
| `pedidos/services.py::registrar_entrega()` | ✅ Sí | Sin cambios; la venta queda vinculada al negocio del pedido |
| `ventas/views.pantalla_cobro` | ⚠️ Parcial | Filtra productos solo del negocio del cajero (`request.user.empleado.negocio`) |
| Catálogo público `/catalogo/` | ⚠️ Parcial | Se reemplaza/mueve a `/t/<slug>/` con filtro por negocio del slug |
| Admin de Django (`/admin/`) | ⚠️ Parcial | Superadmin ve todo; empleados solo ven su negocio (filtro en vistas propias) |

**No se duplica ninguna regla de negocio.** El núcleo de venta sigue siendo `_crear_venta`.

---

## 10. Migración de datos existentes

1. Crear `Negocio` "Kiosco De Barrio" (`slug: de-barrio`, `activo=True`).
2. Asignar a ese negocio todos los `Producto`, `Categoria`, `Venta`, `Turno`, `Pedido` existentes.
3. Crear `Empleado` para el usuario `admin` vinculado a "De Barrio".
4. Crear `Negocio` "Ferretería Martillito" (vacío, solo categorías después).
5. Crear `Negocio` "Dietética Natural" (vacío, solo categorías después).

Esto no borra nada; solo etiqueta los datos existentes como del primer negocio.

---

## 11. Reglas para el equipo (qué hacer y qué NO hacer)

### ✅ SÍ hacer

- Siempre filtrar por `negocio=request.negocio` en consultas de `Producto`, `Categoria`, `Venta`, `Pedido`, `Turno`, `PagoCuentaCorriente`, `ConexionMercadoPago`.
- Usar `select_for_update()` al tocar stock, cliente o pedidos para evitar condiciones de carrera.
- Mantener las convenciones del proyecto: nombres en español, comentarios en español, filtros `|montos` para dinero, estilo neón cian en frontend.
- Crear migraciones seguras (`makemigrations`, revisar antes de `migrate`).
- Agregar pruebas automatizadas para cada nueva funcionalidad.
- Probar que el aislamiento funciona: crear dos negocios, verificar que el comercio A no ve productos del comercio B.

### ❌ NO hacer

- **NO** hacer `Producto.objects.all()` sin filtro de negocio en vistas de gestión (mezcla datos de todos los comercios).
- **NO** confiar en `request.POST.get('negocio_id')` o cualquier ID de negocio enviado desde el frontend para determinar el negocio del usuario.
- **NO** crear un `custom user model` (rompería compatibilidad con `auth.User` y todo lo existente).
- **NO** duplicar lógica de ventas en `pedidos` o `ventas` (reusar `_crear_venta` y `registrar_venta_desde_items`).
- **NO** eliminar funcionalidades existentes del POS (cierre de turno, QR, fiado, etc.).
- **NO** cambiar `Cliente.dni` a `unique=True` global si se decide aislar clientes por negocio en el futuro (hoy `Cliente` es compartido).

---

## 12. Plan de implementación por etapas (resumen)

1. **Etapa 1:** Crear modelo `Negocio`, modelo `Empleado`, agregar FK `negocio` a modelos existentes, migración de datos (Kiosco De Barrio → negocio #1).
2. **Etapa 2:** Middleware `NegocioMiddleware`, filtros por negocio en vistas existentes, ajustar login para asignar `Empleado.negocio`.
3. **Etapa 3:** Modelo `ReservaStock`, lógica de expiración 48h, integración con carrito online.
4. **Etapa 4:** Rutas públicas `/t/<slug>/`, catálogo público por negocio, carrito de pedido online, confirmar pedido.
5. **Etapa 5:** Panel de superadmin (`/superadmin/`), creación de negocios y empleados.
6. **Etapa 6:** Landing pública `/` con recuadros de negocios, envío opcional ($1000).
7. **Etapa 7:** Pruebas de aislamiento, pruebas de flujo completo (venta POS → stock online → pedido online → entrega → cobro), documentación final.

---

**Nota:** Este documento es el contrato de diseño. Si un compañero o una IA va a implementar, debe leerlo completo antes de escribir código. Cualquier desviación debe discutirse primero.
