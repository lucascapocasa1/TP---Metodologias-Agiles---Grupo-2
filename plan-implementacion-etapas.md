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

**Objetivo:** Crear la entidad `Negocio`, vincular empleados a un solo negocio, y agregar `negocio_id` a todos los modelos que necesitan aislamiento. Migrar los datos actuales ("Kiosco De Barrio") al primer negocio.

### Archivos nuevos a crear

| Archivo | Contenido |
|---------|-----------|
| `negocios/__init__.py` | Paquete Django de la nueva app |
| `negocios/models.py` | Modelo `Negocio` (nombre, slug unique, logo, direccion, telefono, whatsapp, email, horarios, color_primario, activo, fecha_creacion) |
| `negocios/migrations/__init__.py` | Paquete de migraciones |
| `usuarios/models.py` | Modelo `Empleado` (OneToOneField a User, FK a Negocio, activo) |
| `negocios/admin.py` | Registro de `Negocio` en el admin de Django |
| `usuarios/admin.py` | Registro de `Empleado` en el admin de Django |
| `negocios/apps.py` | Config de app `negocios` |

### Archivos existentes a modificar

| Archivo | Cambio |
|---------|--------|
| `config/settings.py` | Agregar `'negocios'` y `'usuarios'` (si no está) a `INSTALLED_APPS`. `usuarios` ya debe estar. |
| `ventas/models.py` | Agregar `negocio = models.ForeignKey(Negocio, ...)` a: `Categoria`, `Producto`, `Venta`, `Turno`. También a `ConexionMercadoPago` y `PagoMercadoPago` (opcional, hereda de Venta pero útil para consultas directas). |
| `clientes/models.py` | Agregar `negocio` a `PagoCuentaCorriente`. **NO** a `Cliente` (compartido). |
| `pedidos/models.py` | Agregar `negocio = models.ForeignKey(Negocio, ...)` a `Pedido`. |
| `config/urls.py` | Incluir URLs de `negocios` si se crea `negocios/urls.py` (opcional en esta etapa). |

### Datos a migrar (comando o script único)

1. Crear `Negocio` "Kiosco De Barrio" (`slug: de-barrio`, `activo=True`).
2. Asignar `negocio_id` de ese negocio a todos los `Categoria`, `Producto`, `Venta`, `Turno`, `Pedido`, `PagoCuentaCorriente` existentes.
3. Crear `Empleado` para el usuario `admin` vinculado a "Kiosco De Barrio".
4. Crear `Negocio` "Ferretería Martillito" (`slug: ferreteria-martillito`, vacío).
5. Crear `Negocio` "Dietética Natural" (`slug: dietetica-natural`, vacío).

> Nota: esto se puede hacer con un comando de gestión `python manage.py migrar_a_multiempresa` o un script de migración de datos (`RunPython` en una migración de Django). Se recomienda comando de gestión para que sea reejecutable y testeable.

### Funcionalidades actuales afectadas

- Todas las vistas de `ventas`, `clientes`, `pedidos` que hacen `Modelo.objects.all()` sin filtro dejarán de funcionar correctamente una vez que haya más de un negocio (mezclarían datos). En esta etapa solo se agregan las FKs; el filtrado activo viene en la Etapa 2.
- El admin de Django ahora verá modelos con FK a Negocio; los superusuarios pueden ver todo.

### Pruebas obligatorias antes de continuar

1. `python manage.py makemigrations` y `python manage.py migrate` corren sin errores.
2. Existe un registro `Negocio` con slug `de-barrio` y todos los productos/ventas existentes tienen `negocio_id` asignado.
3. El usuario `admin` tiene un `Empleado` vinculado a "Kiosco De Barrio".
4. Existen los negocios "Ferretería Martillito" y "Dietética Natural" sin datos de ventas/stock.
5. `Cliente` sigue sin FK a `Negocio` (compartido).

---

## Etapa 2: Middleware de negocio y aislamiento de datos

**Objetivo:** Que cada request sepa de qué negocio se trata, y que todas las consultas del backend filtre por `negocio_id`. El aislamiento se garantiza desde el backend, nunca desde el frontend.

### Archivos nuevos a crear

| Archivo | Contenido |
|---------|-----------|
| `usuarios/middleware.py` | Clase `NegocioMiddleware`: resuelve `request.negocio` según la ruta y el usuario autenticado. |

### Archivos existentes a modificar

| Archivo | Cambio |
|---------|--------|
| `config/settings.py` | Agregar `'usuarios.middleware.NegocioMiddleware'` a `MIDDLEWARE` (después de `AuthenticationMiddleware`). |
| `usuarios/views.py` | `post_login`: al autenticar, buscar `Empleado` del usuario y guardar `request.session['negocio_id']` o establecer `request.negocio`. Redirigir al dashboard del negocio. |
| `ventas/views.py` | `lista_productos`, `pantalla_cobro`, `agregar_producto`, `editar_producto`, `eliminar_producto`: filtrar por `negocio=request.negocio` (o `request.user.empleado.negocio`). |
| `clientes/views.py` | `listar_clientes`, `crear_cliente`, etc.: los clientes son compartidos, pero las vistas de creación deben registrar qué usuario/negocio lo está gestionando (opcional, para auditoría). |
| `pedidos/views.py` | `lista_pedidos`, `detalle_pedido`, `entregar_pedido`: filtrar pedidos por `negocio=request.negocio`. |
| `administracion/views.py` | CRUD de usuarios: al crear/editar un empleado, obligar a seleccionar su `Negocio`. |
| `usuarios/decorators.py` | Opcional: agregar `negocio_requerido` para vistas que necesiten negocio obligatorio. |

### Lógica del middleware (`NegocioMiddleware`)

```python
# Pseudológica, no implementar aún
def __call__(self, request):
    request.negocio = None
    path = request.path_info
    
    if path.startswith('/t/'):
        # Tienda pública: resolver por slug de la URL
        slug = path.split('/')[2]  # /t/<slug>/...
        request.negocio = Negocio.objects.filter(slug=slug, activo=True).first()
    elif path.startswith('/app/'):
        # Gestión privada: resolver por usuario autenticado
        if request.user.is_authenticated:
            try:
                request.negocio = request.user.empleado.negocio
            except Empleado.DoesNotExist:
                request.negocio = None
    elif path.startswith('/superadmin/'):
        # Superadmin: no hay negocio único
        request.negocio = None
    
    return self.get_response(request)
```

### Funcionalidades actuales afectadas

- El dashboard de `administracion` debe mostrar solo usuarios del negocio del admin (excepto superadmin).
- El POS de cobro debe mostrar solo productos del negocio del cajero.
- El cierre de turno debe considerar solo ventas del negocio del usuario.

### Pruebas obligatorias antes de continuar

1. Iniciar sesión como `admin` (Administrador de De Barrio) → solo ve productos de De Barrio en `/app/productos/`.
2. Crear un usuario cajero asociado a "Ferretería Martillito" → al iniciar sesión, solo ve productos de Martillito.
3. Intento de acceso manual a `/ventas/productos/` con `?negocio_id=otro` no debe filtrar por ese parámetro (el negocio viene del middleware/sesión, no del frontend).
4. `python manage.py test` de las apps existentes aún pasa (no se rompió nada existente).

---

## Etapa 3: Modelo ReservaStock y lógica de expiración 48 horas

**Objetivo:** Permitir reservar stock al confirmar un pedido online, con expiración automática a las 48 horas si no se retira.

### Archivos nuevos a crear

| Archivo | Contenido |
|---------|-----------|
| `pedidos/migrations/000X_reservastock.py` | Migración para crear el modelo `ReservaStock` |

### Archivos existentes a modificar

| Archivo | Cambio |
|---------|--------|
| `pedidos/models.py` | Agregar modelo `ReservaStock` (producto FK, cantidad, fecha_reserva auto_now_add, fecha_expiracion, estado: reservada/liberada/convertida, session_key, cliente FK nullable, pedido FK nullable). |
| `pedidos/services.py` | `crear_pedido()`: al crear el pedido, crear `ReservaStock` por cada item con `estado='reservada'` y `fecha_expiracion = ahora + 48h`. |
| `ventas/services.py` | `_crear_venta()`: al registrar venta desde pedido, marcar las `ReservaStock` asociadas como `estado='convertida'`. |
| `ventas/services.py` | Función auxiliar `stock_disponible(producto)`: `producto.stock - sum(cantidad de reservas estado='reservada' y fecha_expiracion > ahora)`. |

### Reglas de negocio de reserva

- La reserva se crea **al confirmar el pedido**, no al agregar al carrito (carrito sigue en sesión sin tocar stock).
- Si pasa la expiración (48h) y el pedido no se entrega, la reserva pasa a `estado='liberada'` y el stock vuelve al disponible.
- La liberación puede ser **lazy** (al calcular `stock_disponible`, ignorar reservas expiradas) o mediante un comando de gestión periódico. Se recomienda lazy para no depender de Celery/cron en esta etapa.

### Funcionalidades actuales afectadas

- `registrar_entrega()` en `pedidos/services.py` ya usa `registrar_venta_desde_items`; ahora también debe manejar el estado de las reservas vinculadas.
- El stock mostrado en el catálogo público debe ser `stock_disponible`, no `producto.stock` crudo.

### Pruebas obligatorias antes de continuar

1. Crear un pedido con 3 unidades de un producto con stock 10 → se crea `ReservaStock` con 3 unidades, estado `reservada`, expiración +48h.
2. `stock_disponible` del producto ahora muestra 7.
3. Crear una reserva con `fecha_expiracion` en el pasado → `stock_disponible` la ignora (vuelve a estar disponible).
4. Al entregar el pedido (`registrar_entrega`), la reserva pasa a `convertida` y el stock se descuenta definitivamente.

---

## Etapa 4: Tienda online pública por negocio (`/t/<slug>/`)

**Objetivo:** Catálogo público sin login, carrito de pedido online, confirmación de pedido con elección de retiro/envío.

### Archivos nuevos a crear

| Archivo | Contenido |
|---------|-----------|
| `pedidos/views_publicos.py` | Vistas: `catalogo_negocio`, `pedido_agregar_publico`, `pedido_quitar_publico`, `pedido_carrito_publico`, `pedido_confirmar_publico`. |
| `templates/pedidos/catalogo_publico.html` | Catálogo de productos del negocio (hereda base.html, sin login requerido). |
| `templates/pedidos/carrito_publico.html` | Carrito del pedido online. |
| `templates/pedidos/confirmar_pedido.html` | Formulario: nombre, teléfono, comentario, tipo_entrega (retiro/domicilio). |
| `templates/pedidos/pedido_confirmado.html` | Confirmación mostrada al cliente. |

### Archivos existentes a modificar

| Archivo | Cambio |
|---------|--------|
| `pedidos/urls.py` | Agregar rutas públicas: `path('<slug:slug>/', ...)`, `path('<slug:slug>/agregar/', ...)`, etc. O crear urls separados para público. |
| `config/urls.py` | Incluir rutas de `/t/<slug>/` (puede ser `path('t/<slug:slug>/', include('pedidos.urls_publicos'))`). |
| `pedidos/models.py` | Agregar a `Pedido`: `tipo_entrega` (retiro/domicilio), `costo_envio` (Decimal, default 0 o 1000), `slug_negocio` o usar FK `negocio`. |
| `pedidos/services.py` | `crear_pedido()`: aceptar parámetro `negocio` y asignarlo al `Pedido`. `items_del_pedido()`: filtrar productos por `negocio`. |
| `ventas/services.py` | `formatear_monto()` ya existe; reusar para mostrar precios en la tienda pública. |

### Flujo del cliente en la tienda pública

1. Entra a `/t/ferreteria-martillito/`.
2. Ve productos activos de ese negocio (filtrado por `negocio` del slug).
3. Agrega items al carrito (sesión `request.session["pedido"]`, igual que ahora pero separado del carrito del POS).
4. Ve carrito, confirma pedido.
5. Al confirmar: elige retiro en local ($0) o envío a domicilio (+$1000). Se crea `Pedido` (estado `pendiente`, `negocio = ferreteria-martillito`) y `ReservaStock`.

### Funcionalidades actuales afectadas

- El catálogo público existente en `/catalogo/` (HU-13) debe coexistir o migrarse a `/t/<slug>/`. Se recomienda mantener `/catalogo/` para compatibilidad pero que el nuevo estándar sea `/t/<slug>/`.
- El carrito del pedido público usa la misma clave de sesión que el actual (`pedido`), pero ahora está asociado a un negocio.

### Pruebas obligatorias antes de continuar

1. Entrar a `/t/ferreteria-martillito/` muestra solo productos de Martillito (no de De Barrio ni de Natural).
2. Agregar producto al carrito y confirmar crea un `Pedido` con `estado='pendiente'` y `negocio` correcto.
3. Se crea `ReservaStock` vinculada al pedido.
4. El precio mostrado es `producto.precio` (mismo que POS).
5. Si elige envío a domicilio, el total incluye $1000.

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
