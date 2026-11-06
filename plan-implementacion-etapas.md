# Plan de Implementación por Etapas — Norvex Multiempresa

**Estado:** Listo para ejecutar (Fase 3)  
**Base:** Diseño aprobado en `cambios-antes-de-entrega-final.md`  
**Regla de oro:** No escribir código hasta validar que las pruebas de la etapa anterior pasan. No reescribir funcionalidades existentes del POS.

---

## Cómo leer este plan

Cada etapa indica:

- **Qué se desarrolla** (objetivo)
- **Archivos nuevos a crear**
- **Archivos existentes a modificar**
- **Funcionalidades actuales que podrían verse afectadas**
- **Pruebas que deben ejecutarse antes de pasar a la siguiente etapa**

Las apps del proyecto son: `usuarios`, `ventas`, `clientes`, `pedidos`, `administracion`, `auditoria`, `config`.

Convenciones a respetar: nombres en español, comentarios en español, filtros `|montos` para dinero, estilo neón cian, `data-tema="neon"`.

---

## Etapa 1: Fundamento multiempresa — modelo Negocio, Empleado y FKs

**Estado:** ✅ COMPLETADA  
**Fecha:** 06/11/2026  

**Objetivo:** Crear la entidad `Negocio`, vincular empleados a un solo negocio, y agregar `negocio_id` a todos los modelos que necesitan aislamiento. Migrar los datos actuales ("Kiosco De Barrio") al primer negocio.

### Qué se hizo

**Archivos nuevos creados:**

| Archivo | Contenido |
|---------|-----------|
| `negocios/__init__.py` | Paquete Django de la nueva app |
| `negocios/apps.py` | Config de app `negocios` |
| `negocios/models.py` | Modelo `Negocio` (nombre, slug unique, logo, direccion, telefono, whatsapp, email, horarios, color_primario, activo, fecha_creacion) |
| `negocios/admin.py` | Registro de `Negocio` en el admin de Django |
| `negocios/migrations/__init__.py` | Paquete de migraciones |
| `negocios/migrations/0001_initial.py` | Migración inicial de `Negocio` |
| `usuarios/models.py` | Modelo `Empleado` (OneToOneField a User, FK a Negocio, activo) |
| `usuarios/migrations/0001_initial.py` | Migración inicial de `Empleado` |
| `usuarios/admin.py` | Registro de `Empleado` en el admin de Django |
| `negocios/management/__init__.py` | Paquete de comandos de gestión |
| `negocios/management/commands/__init__.py` | Paquete de comandos |
| `negocios/management/commands/migrar_a_multiempresa.py` | Comando para migrar datos existentes al esquema multiempresa |

**Archivos existentes modificados:**

| Archivo | Cambio |
|---------|--------|
| `config/settings.py` | Agregado `'negocios'` a `INSTALLED_APPS` |
| `ventas/models.py` | Agregada FK `negocio` a `Categoria`, `Producto`, `Venta`, `Turno`, `ConexionMercadoPago` (nullable temporalmente) |
| `clientes/models.py` | Agregada FK `negocio` a `PagoCuentaCorriente` (nullable temporalmente). **`Cliente` sin cambios** (compartido). |
| `pedidos/models.py` | Agregada FK `negocio` a `Pedido` (nullable temporalmente) |

**Datos migrados mediante `python manage.py migrar_a_multiempresa`:**

1. Negocio "Kiosco De Barrio" creado (`slug: de-barrio`, `activo=True`).
2. 11 categorías, 56 productos, 681 ventas, 9 turnos y 6 pedidos asignados a ese negocio.
3. Empleado creado para el usuario `admin` vinculado a "Kiosco De Barrio".
4. Negocio "Ferretería Martillito" creado (`slug: ferreteria-martillito`, vacío).
5. Negocio "Dietética Natural" creado (`slug: dietetica-natural`, vacío).

**Pruebas ejecutadas:** `python manage.py test --keepdb --noinput` → **400 tests OK**.

### Funcionalidades actuales afectadas

- Las vistas que hacen `Modelo.objects.all()` sin filtro de negocio ahora recibirán datos de todos los negocios (hasta que se implemente el middleware en la Etapa 2). Esto es esperado y se corregirá en la siguiente etapa.
- El admin de Django ahora muestra modelos con FK a Negocio; los superusuarios pueden ver todo.

### Pruebas obligatorias pasadas

1. ✅ Migraciones creadas y aplicadas sin errores.
2. ✅ Existe `Negocio` con slug `de-barrio` y todos los productos/ventas existentes tienen `negocio_id` asignado.
3. ✅ El usuario `admin` tiene un `Empleado` vinculado a "Kiosco De Barrio".
4. ✅ Existen los negocios "Ferretería Martillito" y "Dietética Natural" sin datos de ventas/stock.
5. ✅ `Cliente` sigue sin FK a `Negocio` (compartido).
6. ✅ 400 tests existentes pasan sin errores.

---

## Etapa 2: Middleware de negocio y aislamiento de datos

**Estado:** ✅ COMPLETADA  
**Fecha:** 06/11/2026  

**Objetivo:** Que cada request sepa de qué negocio se trata, y que todas las consultas del backend filtre por `negocio_id`. El aislamiento se garantiza desde el backend, nunca desde el frontend.

### Qué se hizo

**Archivos nuevos creados:**

| Archivo | Contenido |
|---------|-----------|
| (ninguno nuevo) | `NegocioMiddleware` se agregó al archivo existente `usuarios/middleware.py` |

**Archivos existentes modificados:**

| Archivo | Cambio |
|---------|--------|
| `config/settings.py` | Agregado `'usuarios.middleware.NegocioMiddleware'` a `MIDDLEWARE` (después de `AuthenticationMiddleware` y `ControlAdminDjangoMiddleware`). |
| `usuarios/middleware.py` | Agregada clase `NegocioMiddleware`: resuelve `request.negocio` por slug en `/t/<slug>/`, por `request.user.empleado.negocio` en rutas privadas, y `None` en `/superadmin/`. |
| `ventas/views.py` | `pantalla_cobro`, `cobro_buscar`, `lista_productos`, `agregar_producto`, `buscar_por_codigo`, `editar_producto`, `eliminar_producto`, `cierre_turno`: filtran por `negocio=request.negocio`. |
| `ventas/services.py` | `turno_abierto(usuario, negocio=None)`, `abrir_turno(usuario, negocio=None)`, `ventas_del_turno(turno)`: aceptan/filtran por negocio. |
| `clientes/views.py` | `listar_clientes` (filtra clientes con ventas en este negocio), `detalle_cliente` (filtra ventas por negocio), `registrar_pago` (asigna `negocio` al `PagoCuentaCorriente`). |
| `pedidos/views.py` | `lista_pedidos`, `detalle_pedido`, `entregar_pedido`, `cambiar_estado_pedido`: filtran por `negocio=request.negocio`. |
| `administracion/views.py` | `dashboard`, `listar_usuarios`, `reportes_ventas`, `reportes_stock`: filtran por `negocio=request.negocio` (superadmin con `request.negocio=None` ve todo). |
| `administracion/reportes.py` | Todas las funciones de reporte (`ventas_del_rango`, `deuda_otorgada`, `resumen_ventas`, `ventas_por_dia`, `top_productos`, `productos_mas_rentables`, `resumen_stock`, `stock_por_categoria`, `productos_bajo_margen`) aceptan parámetro opcional `negocio=None` y filtran internamente. |

**Middleware implementado (`NegocioMiddleware`):**

```python
def __call__(self, request):
    request.negocio = None
    path = request.path_info

    if path.startswith("/t/"):
        # Tienda pública: resolver por slug de la URL.
        partes = path.strip("/").split("/")
        if len(partes) >= 2:
            slug = partes[1]
            request.negocio = (
                Negocio.objects.filter(slug=slug, activo=True).first()
            )
    elif path.startswith("/superadmin/"):
        # Superadmin: no hay negocio único asociado al request.
        request.negocio = None
    elif request.user.is_authenticated:
        # Cualquier ruta privada: resolver por el empleado del usuario.
        try:
            request.negocio = request.user.empleado.negocio
        except Empleado.DoesNotExist:
            request.negocio = None

    return self.get_response(request)
```

### Funcionalidades actuales afectadas

- El dashboard de `administracion` muestra solo usuarios y productos del negocio del admin (excepto superadmin, que ve todo).
- El POS de cobro muestra solo productos del negocio del cajero.
- El cierre de turno considera solo ventas del negocio del usuario.
- Los reportes de administración filtran por negocio del usuario (superadmin ve todo).
- `Cliente` sigue siendo compartido (sin FK a `Negocio`); se filtran por clientes que tienen ventas en el negocio del usuario.

### Pruebas obligatorias pasadas

1. ✅ `python manage.py test --keepdb --noinput` → **400 tests OK**.
2. ✅ Middleware `NegocioMiddleware` registrado y activo.
3. ✅ Todas las vistas de gestión filtran por `request.negocio`.

---

## Etapa 3: Modelo ReservaStock y lógica de expiración 48 horas

**Estado:** ✅ COMPLETADA  
**Fecha:** 06/11/2026  

**Objetivo:** Permitir reservar stock al confirmar un pedido online, con expiración automática a las 48 horas si no se retira.

### Qué se hizo

**Archivos nuevos creados:**

| Archivo | Contenido |
|---------|-----------|
| `pedidos/migrations/0004_reservastock.py` | Migración para crear el modelo `ReservaStock` |

**Archivos existentes modificados:**

| Archivo | Cambio |
|---------|--------|
| `pedidos/models.py` | Agregado modelo `ReservaStock` (producto FK, cantidad, fecha_reserva, fecha_expiracion, estado: reservada/convertida/expirada, session_key, cliente FK nullable, pedido FK nullable). Propiedades `esta_vigente` y `esta_expirada`. |
| `pedidos/services.py` | `crear_pedido()`: al crear el pedido, crea `ReservaStock` por cada item con `estado='reservada'` y `fecha_expiracion = ahora + 48h`. Valida stock disponible considerando reservas vigentes. `registrar_entrega()`: marca reservas del pedido como `convertida` al entregar. |
| `ventas/services.py` | `_crear_venta()`: valida stock disponible (restando reservas vigentes) antes de descontar. Agregada función auxiliar `stock_disponible(producto)`: `producto.stock - sum(cantidad de reservas estado='reservada' y fecha_expiracion > ahora)`. |

**Reglas de negocio implementadas:**

- La reserva se crea **al confirmar el pedido**, no al agregar al carrito (carrito sigue en sesión sin tocar stock).
- El stock disponible considera reservas vigentes (no expiradas).
- Las reservas expiradas no cuentan en el stock disponible (liberación lazy).
- Al entregar el pedido (`registrar_entrega`), las reservas pasan a `convertida`.

### Pruebas obligatorias pasadas

1. ✅ `python manage.py test --keepdb --noinput` → **400 tests OK**.
2. ✅ Migración `pedidos.0004_reservastock` aplicada sin errores.
3. ✅ `stock_disponible()` funciona correctamente (ignora reservas expiradas).

---

## Etapa 4: Tienda online pública por negocio (`/t/<slug>/`)

**Estado:** ✅ COMPLETADA  
**Fecha:** 06/11/2026  

**Objetivo:** Catálogo público sin login, carrito de pedido online, confirmación de pedido con elección de retiro/envío.

### Qué se hizo

**Archivos nuevos creados:**

| Archivo | Contenido |
|---------|-----------|
| `pedidos/views_publicos.py` | Vistas públicas: `catalogo_negocio`, `pedido_agregar_publico`, `pedido_quitar_publico`, `pedido_carrito_publico`, `pedido_confirmar_publico`. |
| `templates/pedidos/catalogo_publico.html` | Catálogo de productos por negocio (hereda base.html, sin login). |
| `templates/pedidos/_carrito_pedido_publico.html` | Carrito del pedido online con rutas por slug. |
| `templates/pedidos/pedido_confirmado_publico.html` | Confirmación de pedido con WhatsApp y detalle de envío. |

**Archivos existentes modificados:**

| Archivo | Cambio |
|---------|--------|
| `pedidos/models.py` | Agregado `tipo_entrega` (retiro/domicilio) y `costo_envio` (Decimal, default 0) a `Pedido`. |
| `pedidos/migrations/0005_*.py` | Migración para `tipo_entrega` y `costo_envio`. |
| `pedidos/views.py` | Las rutas del panel interno (`panel/`, `panel/<id>/`, etc.) se movieron ANTES que las rutas con `<slug:slug>/` para evitar que `slug` capture "panel". |
| `pedidos/urls.py` | Agregadas rutas públicas por slug: `<slug:slug>/`, `<slug:slug>/agregar/`, etc. |
| `config/urls.py` | Agregadas rutas directas `/t/<slug:slug>/`, `/t/<slug:slug>/agregar/`, etc. apuntando a `views_publicos`. |
| `pedidos/services.py` | `crear_pedido()` acepta parámetros `negocio`, `tipo_entrega`, `costo_envio` y los asigna al `Pedido`. |

**Flujo del cliente en la tienda pública:**

1. Entra a `/t/ferreteria-martillito/`.
2. Ve productos activos de ese negocio (filtrado por `negocio` del slug).
3. Agrega items al carrito (sesión `request.session["pedido"]`).
4. Confirma pedido: elige retiro en local ($0) o envío a domicilio (+$1000).
5. Se crea `Pedido` (estado `pendiente`, `negocio` correcto, `tipo_entrega`, `costo_envio`) y `ReservaStock`.

### Pruebas obligatorias pasadas

1. ✅ `python manage.py test --keepdb --noinput` → **400 tests OK** (incluyendo las 4 que fallaban por orden de URLs).
2. ✅ Rutas `/t/<slug>/` funcionan sin conflicto con `/catalogo/panel/`.
3. ✅ `crear_pedido()` acepta `negocio`, `tipo_entrega`, `costo_envio`.

---

## Etapa 5: Panel de superadmin (`/superadmin/`)

**Objetivo:** El superadmin (`is_superuser=True`) puede crear negocios, crear empleados, asignar negocios a usuarios, y ver listado de todos los negocios.

### Archivos nuevos a crear

| Archivo | Contenido |
|---------|-----------|
| `administracion/views_superadmin.py` | Vistas: `lista_negocios`, `crear_negocio`, `editar_negocio`, `crear_empleado`, `asignar_negocio_usuario`. |
| `templates/administracion/superadmin/` | Templates para gestión de negocios y empleados. |

### Archivos existentes a modificar

| Archivo | Cambio |
|---------|--------|
| `administracion/urls.py` | Agregar rutas `/superadmin/...` con decorador `superadmin_requerido` o chequeo `is_superuser`. |
| `config/urls.py` | Incluir `administracion.urls` bajo `/superadmin/` o ruta directa. |
| `usuarios/decorators.py` | Agregar `superadmin_requerido` (chequea `user.is_superuser`). |
| `usuarios/views.py` | Registro de usuario: opcional, permitir seleccionar negocio al crear. |

### Reglas de acceso

- Solo `is_superuser=True` puede entrar a `/superadmin/`.
- Un empleado con rol `Administrador` de un negocio **no** puede ver `/superadmin/` ni negocios ajenos.

### Funcionalidades actuales afectadas

- `administracion` ya maneja CRUD de usuarios; ahora agrega gestión de negocios y la asociación usuario-negocio.

### Pruebas obligatorias antes de continuar

1. Superadmin puede crear un negocio nuevo (slug único validado).
2. Superadmin puede crear un empleado y asignarle un negocio.
3. Empleado de Martillito intenta acceder a `/superadmin/` → recibe 403.
4. Superadmin puede ver listado de todos los negocios (De Barrio, Martillito, Natural).

---

## Etapa 6: Landing pública (`/`) y envío opcional

**Objetivo:** Página institucional con recuadros de los negocios activos. Cada recuadro lleva a su tienda online `/t/<slug>/`.

### Archivos nuevos a crear

| Archivo | Contenido |
|---------|-----------|
| `templates/landing.html` | Landing con listado de negocios activos (nombre, logo, logo, botón "Entrar a la tienda"). |
| `usuarios/views.py` (o `negocios/views.py`) | Vista `landing` que consulta `Negocio.objects.filter(activo=True)`. |

### Archivos existentes a modificar

| Archivo | Cambio |
|---------|--------|
| `config/urls.py` | Ruta `/` apunta a vista `landing` (en lugar del redirect actual a login, o mantener redirect pero agregar enlace a landing). |
| `pedidos/models.py` | Si no se hizo en Etapa 4, agregar `tipo_entrega` y `costo_envio` a `Pedido`. |
| `pedidos/services.py` | `crear_pedido()` acepta `tipo_entrega` y calcula `costo_envio` (0 si retiro, 1000 si domicilio). |

### Reglas del envío

- Opcional: cliente elige al confirmar.
- Retiro en local: costo_envio = 0.
- Envío a domicilio: costo_envio = 1000 (se suma al total del pedido).

### Funcionalidades actuales afectadas

- La raíz `/` actualmente redirige a `usuarios:post_login`. Cambiar a landing o mantener ambas (landing en `/`, login en `/login/`).

### Pruebas obligatorias antes de continuar

1. Entrar a `/` muestra recuadros de todos los negocios activos.
2. Click en un recuadro lleva a `/t/<slug>/` correspondiente.
3. Un negocio con `activo=False` no aparece en la landing.
4. Pedido con envío a domicilio tiene `costo_envio = 1000`; con retiro, `costo_envio = 0`.

---

## Etapa 7: Pruebas de aislamiento, flujo completo y documentación

**Objetivo:** Validar que todo funciona junto, que no hay fuga de datos entre negocios, y documentar cambios.

### Pruebas de aislamiento (obligatorias)

1. Crear venta en De Barrio (POS) → verificar que no aparece en los pedidos de Martillito.
2. Cajero de De Barrio intenta acceder a `/app/productos/` y solo ve productos de De Barrio.
3. Cliente Lucas Pérez compra en De Barrio y en Martillito → es el mismo registro `Cliente`, pero cada negocio ve solo sus propias `Venta`.
4. Stock de un producto en Martillito no afecta al stock del mismo producto (si existe) en De Barrio.

### Prueba de flujo completo (e2e)

1. Superadmin crea negocio "Test Comercio".
2. Dueño carga productos en `/app/productos/`.
3. Cliente entra a `/t/test-comercio/`, agrega producto, confirma pedido (retiro en local).
4. Dueño ve pedido en `/app/pedidos/` de Test Comercio.
5. Cliente retira y paga en el local → `registrar_entrega()` crea `Venta`, vincula pedido, descuenta stock, marca pedido `entregado`.
6. Verificar que la venta aparece en el cierre de turno del negocio.

### Pruebas automatizadas

| App | Qué probar |
|-----|------------|
| `negocios` | Crear negocio, slug único, activo/inactivo. |
| `usuarios` | Empleado vinculado a un solo negocio; superadmin bypassea. |
| `ventas` | Venta filtrada por negocio; stock descontado por negocio. |
| `pedidos` | Pedido con reserva 48h; expiración de reserva; `registrar_entrega` crea venta. |
| `clientes` | Cliente compartido entre negocios; `buscar_clientes` ignora acentos. |
| `administracion` | Superadmin crea negocio y empleado; empleado no accede a `/superadmin/`. |

Comando: `python manage.py test` (todas las apps).

### Documentación a actualizar

| Archivo | Qué agregar |
|---------|-------------|
| `AGENTS.md` | Documentar modelo `Negocio`, `Empleado`, middleware de aislamiento, rutas `/t/<slug>/`, reserva de stock 48h. |
| `README.md` | Instrucciones para crear un nuevo negocio, cómo funciona el aislamiento, variables de entorno nuevas (si las hay). |
| `cambios-antes-de-entrega-final.md` | Ya existe; mantener como contrato de diseño. |

---

## Cronograma sugerido (órden estricto)

| Etapa | Dependencia | Tiempo estimado |
|-------|-------------|-----------------|
| 1. Fundamento (Negocio, Empleado, FKs, migración) | Ninguna | 1-2 días |
| 2. Middleware y aislamiento | Etapa 1 | 1-2 días |
| 3. ReservaStock (48h) | Etapa 1 | 1 día |
| 4. Tienda pública `/t/<slug>/` | Etapas 1, 2, 3 | 2-3 días |
| 5. Panel superadmin | Etapa 1, 2 | 1-2 días |
| 6. Landing y envío opcional | Etapa 4 | 1 día |
| 7. Pruebas y documentación | Todas | 1-2 días |

**Regla:** No pasar a la siguiente etapa si las pruebas de la actual fallan.

---

## Checklist final de aceptación (del cliente)

1. [ ] Registrar dos comercios diferentes en Norvex.
2. [ ] Crear usuarios asociados a cada comercio.
3. [ ] Iniciar sesión y comprobar que cada comercio accede exclusivamente a su información.
4. [ ] Cargar productos desde Noruega Gestión.
5. [ ] Ver esos mismos productos automáticamente en la tienda online correspondiente.
6. [ ] Realizar una venta presencial y comprobar que el stock se actualiza.
7. [ ] Realizar un pedido online y visualizarlo desde Noruega Gestión.
8. [ ] Preparar y entregar el pedido.
9. [ ] Registrar correctamente la venta y el pago.
10. [ ] Comprobar que las operaciones de un comercio no afectan los datos de otro.

---

**Nota:** Este es el plan de implementación. Una vez aprobado, se procede a escribir código etapa por etapa. No se modificó ningún archivo aún.
