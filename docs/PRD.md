# PRD — Documento de Requerimientos de Producto

## Sistema Kiosco

| Campo | Valor |
|---|---|
| Documento | PRD v2.8 |
| Fecha | 05/11/2026 |
| Versión del código documentado | `main` @ `ef1dd93` (incluye fix: `init_point` también con cuentas de prueba) |
| Proyecto | Sistema Kiosco (Norvex) — TP Metodologías Ágiles (UNAB) |
| Estado del producto | **Sprint 1 ✅ · Sprint 2 ✅ · Sprint 3 ✅ · Sprint 4 ✅ · HU-13 ✅ (catálogo público + WhatsApp con cobro de la entrega) · HU-14 ✅ (cuenta corriente "FIAR") · HU-15 ✅ (cobro QR Mercado Pago) · HU-16 ✅ (pantalla del cliente) · recuperación de contraseña ✅ (Resend) · publicación en Render ✅ · 472 tests en verde** |
| Documento relacionado | [ARD — Arquitectura y requerimientos técnicos](ARD.md) |

> Historial: v1.0 cubre Sprints 1 y 2 en curso. v2.0-v2.6 agregan progresivamente el Sprint 2 (catálogo + HTMX), el Sprint 3 (caja), la fidelidad (HU-12), el cierre de turno (HU-10), el catálogo público + WhatsApp (HU-13), la cuenta corriente "FIAR" (HU-14) y el cierre del flujo con **entregar es cobrar**. v2.7 suma los extras: cobro QR (HU-15), pantalla del cliente (HU-16), OAuth "Conectar con Mercado Pago", recuperación de contraseña con Resend y publicación en Render, con demo idempotente. v2.8 suma el fix `ef1dd93` (siempre `init_point` en el QR, incluso con cuentas de prueba) y la documentación de cuentas sandbox para facultad.

---

## 1. Introducción

### 1.1 Propósito del documento

Este PRD define **qué** debe hacer el Sistema Kiosco: usuarios, alcance,
requerimientos funcionales y no funcionales, criterios de aceptación y
restricciones. Es la referencia de producto contra la cual se valida lo que se
entrega sprint a sprint. El **cómo** (stack, modelo de datos, endpoints,
decisiones de diseño) está en el [ARD](ARD.md).

### 1.2 Contexto y problema

Un kiosco de barrio necesita digitalizar su operación diaria: hoy la gestión de
productos, precios y cobros se hace de forma manual o con planillas, lo que
provoca:

- Errores de precio y falta de control sobre quién modificó qué.
- Sin registro de quién atendió la caja ni de qué se vendió.
- El dueño no tiene visibilidad de stock ni de lo que más se vende.
- Cualquier empleado podría entrar a la parte sensible del negocio (costos,
  reportes) si no hay control de acceso.

### 1.3 Objetivos del producto

| # | Objetivo | Medible | Estado |
|---|---|---|---|
| O1 | Acceso restringido por roles (dueño vs. cajero) | 100% de las rutas críticas verificadas server-side (403), con tests | ✅ Alcanzado |
| O2 | Carga y consulta rápida de productos | Alta/edición/baja y búsqueda sin salir de la interfaz | ✅ Alcanzado (Sprint 2) |
| O3 | Trazabilidad de acciones sensibles | Login/logout y operaciones sobre usuarios registrados con usuario, fecha e IP | ✅ Alcanzado |
| O4 | Interfaz clara y personalizable para el local | Identidad propia + modo oscuro, contraste AA | ✅ Alcanzado (estilo neón fijo + dark) |
| O5 | Visibilidad del negocio | Reportes de ventas, stock, costos y rentabilidad | ✅ Alcanzado (entrega adelantada del Sprint 4) |
| O6 | Base sólida para caja y reportes | Modelos de venta normalizados y testeados | ✅ Alcanzado (Sprint 3) |
| O7 | Reconocer al cliente frecuente | Cliente identificado por DNI con historial y puntos acumulados | ✅ Alcanzado |
| O8 | Cobrar sin efectivo ni tarjeta física | QR de Mercado Pago integrado a la caja, con confirmación automática del pago | ✅ Alcanzado |
| O9 | Poner el sistema en producción sin tocar código | Publicación con `render.yaml`, variables de entorno y estáticos servidos por WhiteNoise | ✅ Alcanzado |
| O10 | Que el dueño no dependa del soporte para recuperar su cuenta | Recuperación de contraseña autoservicio por correo electrónico | ✅ Alcanzado |

### 1.4 Glosario

| Término | Significado |
|---|---|
| Kiosco | Comercio minorista de barrio; usuario final del sistema |
| Rol | Grupo de Django (`Administrador`, `Cajero`) que define qué ve y puede hacer un usuario |
| Categoría | Agrupación de productos (ej. Golosinas, Bebidas) |
| Baja lógica | Desactivar un producto (`activo=False`) sin borrar el registro para no romper ventas históricas |
| Stock bajo | `stock ≤ stock_minimo` (umbral configurable por producto, default 5) |
| Venta / Detalle | Cabecera de una operación de cobro y sus líneas de producto |
| Cliente | Consumidor registrado del kiosco (nombre, DNI/CUIT único, teléfono, email) al que se le pueden asociar ventas y acumular puntos |
| Puntos de fidelidad | Saldo del cliente que suma 1 punto por cada $100 comprados; cada `Venta` guarda los que otorgó |
| Cuenta corriente (FIAR) | Saldo de deuda de un cliente frecuente con un límite máximo definido por el administrador; lo fiado no entra a la caja hasta que se cobra el pago |
| Catálogo público | Vista sin login donde los vecinos ven stock (solo "Disponible"/"Agotado") y precios y arman un pedido para retirar, enviado por WhatsApp |
| Deuda otorgada | Total fiado a cuenta corriente en un turno o rango; se informa aparte porque **no** es plata que entró a la caja |
| Mercado Pago (QR) | Método de pago digital: la caja genera un link de pago (Checkout Pro) y lo muestra como QR; el cliente lo escanea y paga desde su celular |
| Venta pendiente (QR) | `Venta` con `finalizada=False`: el stock ya está reservado, pero no cuenta en reportes ni en el turno hasta que el pago se aprueba |
| Webhook | Aviso que Mercado Pago envía al sistema cuando cambia un pago; el sistema no confía en el aviso y vuelve a consultar el pago a la API |
| OAuth (conectar Mercado Pago) | Autorización de la cuenta del negocio: el dueño toca "Conectar", autoriza en Mercado Pago y el sistema guarda las credenciales para cobrar a esa cuenta |
| Modo de prueba (QR) | Sin credenciales de Mercado Pago, el QR abre una pantalla de pago simulado del propio sistema, sin plata real |
| Pantalla del cliente (display) | Vista en un celular del mostrador que muestra el QR del cobro y se actualiza sola al aprobarse el pago |
| Resend | Servicio de envío de correo usado para la recuperación de contraseña; en desarrollo, sin API key, el mail se imprime en la consola |
| Publicación | Despliegue del sistema en un hosting (Render) con `DEBUG=False`, `SECRET_KEY` propia y base PostgreSQL |
| Auditoría | Registro inmutable de acciones relevantes (usuario, acción, fecha, IP) |
| Sprint | Iteración con entrega demostrable (4 sprints planificados + consignas nuevas de la cátedra) |

---

## 2. Alcance

### 2.1 Dentro del alcance (entregado)

| Bloque | Contenido | Sprint |
|---|---|---|
| **Autenticación y roles** | Login/logout, registro público, redirección por rol, denegación 403 server-side | 1 |
| **Gestión de usuarios** | Dashboard con métricas de usuarios; listar con búsqueda y filtros; crear, editar, eliminar, activar/desactivar, asignar/quitar roles | 2 |
| **Catálogo de productos** | CRUD completo (alta, edición, baja lógica), código de barras único, costo/precio separados, stock mínimo con alerta, búsqueda en tiempo real con HTMX, solo para Administrador | 2 |
| **Auditoría** | Registro automático de login/logout con IP; registro de operaciones CRUD de usuarios; lectura en solo lectura vía Django admin | transversal |
| **Reportes de negocio** | Ventas (KPIs, serie de 14 días, top 10, más rentables) y stock (valorizado, bajo, por categoría, margen bajo) | 4 (adelantado) |
| **Caja y cobro** | Carrito con lector de código de barras, edición de cantidades, cobro efectivo/tarjeta con vuelto, descuento de stock, comprobante y auditoría de la venta | 3 |
| **Fidelidad de clientes** | Modelo `Cliente` (DNI/CUIT único y normalizado, baja lógica), CRUD para el Administrador, búsqueda y alta rápida desde el cobro, asociación de la venta al cliente y puntos (1 cada $100) con historial | 4 |
| **Pedidos online** | Catálogo público sin login (solo "Disponible"/"Agotado"), carrito de pedido, registro del `Pedido` y envío por WhatsApp; panel interno para ver y cambiar el estado | consigna |
| **Cuenta corriente** | Cliente con límite de crédito, cobro fiado desde el POS, saldo de deuda con historial de pagos y deuda otorgada informada aparte de la caja y de los ingresos | consigna |
| **Cobro con QR (Mercado Pago)** | Método `mercado_pago` en la caja: venta pendiente con stock reservado, QR de Checkout Pro (`init_point` siempre), webhook + consulta periódica, cancelación con devolución del stock y "Total Mercado Pago" en el cierre de turno | extra |
| **Pantalla del cliente** | Vista `/ventas/display/` para un celular del mostrador: espera → QR → "¡Pago aprobado!", actualizada sola | extra |
| **Conectar Mercado Pago** | Botón OAuth en Panel → Mercado Pago: el negocio autoriza su cuenta y los cobros le llegan directo; renovación automática del token y desconexión auditada | extra |
| **Recuperación de contraseña** | Flujo completo por correo (pedir enlace → mail con Resend → elegir contraseña nueva), con páginas propias y enlace inválido controlado | extra |
| **Publicación** | `render.yaml` con gunicorn + WhiteNoise, migraciones y `setup_inicial` en el build; `DEBUG`, `SECRET_KEY`, `ALLOWED_HOSTS` y CSRF desde el entorno | extra |
| **Datos de demo** | Comandos `cargar_demo` (56 productos y ventas desde el 20/09/2026 con semilla fija) y `cargar_demo_clientes` (clientes y pedidos); ambos `--limpiar` son **idempotentes** y reponen el stock | 4 |
| **Experiencia de usuario** | Identidad "toldo de barrio" con estilo neón cian fijo, marca **Norvex**, modo oscuro, responsive, accesibilidad, formato de dinero unificado (`montos`) | transversal |

### 2.2 Estado de lo planificado y fuera del alcance actual

- **Sprint 4 — Cierres (entrega 05-11):** ✅ **Completo.** HU-10 (cierre de
  turno), HU-11 (top 10 y reportes) y HU-12 (clientes frecuentes) entregadas.
- **Consignas nuevas de la cátedra** ✅ **Completas**:
  - **Integración externa (HU-13):** ✅ **Completo.** Catálogo online
    público con armado de pedido para retiro ("take away"), pedido registrado
    en el sistema y envío por WhatsApp al local.
  - **Cuenta corriente ("FIAR", HU-14):** ✅ **Completo.** Saldo de
    deuda por cliente frecuente con límite máximo definido por el
    administrador, cobro a cuenta corriente en la pantalla del POS, registro
    de pagos (solo Administrador) y deuda otorgada excluida de la caja y de
    los ingresos.
- **Extras de producto:** ✅ **Completos.**
  Cobro con QR de Mercado Pago (HU-15) y pantalla para el cliente (HU-16);
  botón "Conectar con Mercado Pago" (OAuth) y publicación en Render;
  recuperación de contraseña por mail con Resend.
- **Por definir:** multi-negocio (varias sucursales en una misma instalación),
  comercio configurable en colores/logo desde la interfaz, facturación
  electrónica y una interfaz propia para consultar la auditoría.
  *(El logo propio ya está: marca **Norvex**.)*

### 2.3 Restricciones

- Entregas fijas: Sprint 1 (24-09) ✅ · Sprint 2 (01-10) ✅ · Sprint 3 (15-10) ✅ · Sprint 4 (05-11) ✅.
- Aplicación **web** (navegador), sin app nativa; se usa en PC del kiosco y
  eventualmente en celular/tablet.
- Trabajo en equipo con merge a `main`; los artefactos deben poder integrarse
  sin romper los tests existentes (379 en verde).
- Idioma y formato argentinos: español rioplatense, moneda ARS, horario
  `America/Argentina/Buenos_Aires`.
- El servidor de desarrollo corre en el puerto **8001** (conservar ese puerto
  en todas las máquinas del equipo).
- **Dependencias externas:** PostgreSQL como base principal; Mercado Pago para
  el cobro con QR (sin credenciales se degrada a modo de prueba) y Resend para
  el correo (sin API key se imprime en la consola). El sistema no debe romperse
  si esas credenciales faltan.
- **Publicación:** Render con plan gratis; el sitio "duerme" sin uso y la base
  gratuita vence a los 30 días.

---

## 3. Usuarios / personas

| Persona | Rol en el sistema | Qué necesita | Qué **no** debe ver |
|---|---|---|---|
| **Dueño / Administrador** | Grupo `Administrador` (o superuser) | Gestionar usuarios, cargar y consultar productos, ver reportes, stock, costos y auditoría | — (acceso total) |
| **Cajero** | Grupo `Cajero` | Entrar al sistema y usar la pantalla de cobro | Costos, precios de compra, catálogo, reportes, administración de usuarios (recibe 403) |
| **Usuario sin rol** | Autenticado sin grupo | Ver un aviso de que aún no tiene permisos | Cualquier pantalla operativa |
| **Cliente frecuente** | Registro en `clientes` (no es usuario del sistema, no inicia sesión) | Ser identificado en el cobro por DNI, acumular puntos y (si tiene cuenta corriente) llevarse productos fiados hasta su límite | No accede a ninguna pantalla; solo existe como registro asociado a ventas |
| **Público (no autenticado)** | — | Ver el catálogo público y armar un pedido para retirar (HU-13); el resto lo redirige al login | Todo el resto (redirigido al login) |

---

## 4. Requerimientos funcionales

Prioridad: **M** = Must (imprescindible), **S** = Should, **C** = Could.
Estado verificado contra el código (`main` @ `ef1dd93`).

### 4.1 Autenticación y control de acceso

| ID | Requerimiento | Prioridad | HU | Estado |
|---|---|---|---|---|
| RF-01 | Login con usuario y contraseña; error claro con credenciales inválidas | M | HU-01 | ✅ Hecho |
| RF-02 | Logout seguro (solo POST) que destruye la sesión | M | HU-01 | ✅ Hecho |
| RF-03 | Registro público de cuentas; el usuario nace **sin rol** | S | — | ✅ Hecho |
| RF-04 | Redirección post-login según rol: admin → dashboard, cajero → cobro, sin rol → aviso `sin_rol` | M | — | ✅ Hecho |
| RF-05 | Restricción **server-side** por rol: las URLs fuera del rol devuelven 403 (no basta ocultar botones) | M | HU-02 | ✅ Hecho |
| RF-06 | El Administrador accede tanto al panel de administración como a la pantalla de cobro | M | HU-03 | ✅ Hecho |
| RF-07 | Todo acceso a pantallas operativas exige login (anónimos → redirect al login) | M | HU-01/02 | ✅ Hecho |

### 4.2 Gestión de usuarios (solo Administrador)

| ID | Requerimiento | Prioridad | Estado |
|---|---|---|---|
| RF-08 | Listar usuarios con búsqueda por nombre/usuario/email | M | ✅ Hecho |
| RF-09 | Filtrar la lista por estado (activo/inactivo) y por rol | S | ✅ Hecho |
| RF-10 | Crear usuario con contraseña y rol asignado | M | ✅ Hecho |
| RF-11 | Editar datos del usuario, con contraseña opcional | M | ✅ Hecho |
| RF-12 | Activar/desactivar usuarios sin borrar la cuenta | S | ✅ Hecho |
| RF-13 | Eliminar usuario con paso de confirmación | S | ✅ Hecho |
| RF-14 | Asignar/quitar roles (grupos) desde la interfaz | M | ✅ Hecho |
| RF-15 | Protecciones: no se puede eliminar ni desactivar la cuenta propia ni un superusuario | M | ✅ Hecho |
| RF-16 | Dashboard con métricas de usuarios (total, activos, inactivos, por rol, sin rol) | S | ✅ Hecho |
| RF-17 | Paginación de listados largos | C | ⚠️ Parcial (tag `{% paginacion %}` existe; los templates aún listan todo de una vez) |
| RF-18 | Cada operación de escritura sobre usuarios queda auditada | S | ✅ Hecho |

### 4.3 Catálogo de productos (solo Administrador)

| ID | Requerimiento | Prioridad | HU | Estado |
|---|---|---|---|---|
| RF-19 | Modelos de Categoría y Producto con precio, costo, stock y estado activo | M | HU-04 | ✅ Hecho (migraciones 0001-0003) |
| RF-20 | **Alta** de producto con `ProductoForm` y creación/reuso de categoría nueva | M | HU-04 | ✅ Hecho |
| RF-21 | **Edición** de producto desde la interfaz | M | HU-04 | ✅ Hecho (`productos/<id>/editar/`) |
| RF-22 | **Baja lógica** reversible (`activo=False`), sin romper ventas históricas | M | HU-04 | ✅ Hecho (`productos/<id>/eliminar/`) |
| RF-23 | Código de barras con **validación de duplicado** (error si ya existe) | M | HU-04 | ✅ Hecho (`unique` + `clean_codigo_barras`) |
| RF-24 | Precio de costo y precio de venta separados; el costo **solo lo ve el admin** | M | HU-04 | ✅ Hecho (403 al cajero con test) |
| RF-25 | Stock mínimo por producto (default 5) | S | HU-04 | ✅ Hecho (`stock_minimo`) |
| RF-26 | **Lista de productos con búsqueda en tiempo real sin recarga (HTMX)** por nombre, descripción o código | M | HU-05 | ✅ Hecho (debounce 300 ms + partial `_productos_tabla.html`) |
| RF-27 | **Alerta de stock bajo** con marca de color (`stock ≤ stock_minimo`) | S | HU-06 | ✅ Hecho (`stock_bajo` + `.badge-stock-bajo`) |
| RF-28 | Las 4 vistas del catálogo exigen rol Administrador (cajero → 403) | M | HU-02 | ✅ Hecho |
| RF-29 | Mensajes de éxito/error (`django.messages`) en cada operación | S | — | ✅ Hecho |

### 4.4 Reportes de negocio (solo Administrador)

| ID | Requerimiento | Prioridad | HU | Estado |
|---|---|---|---|---|
| RF-30 | Reporte de ventas con rango de fechas configurable: cantidad, ingresos, costo, ganancia, ticket promedio y margen % | M | HU-11 | ✅ Hecho |
| RF-31 | Serie de ventas de los últimos 14 días | S | HU-11 | ✅ Hecho |
| RF-32 | Top 10 de productos más vendidos en el período | M | HU-11 | ✅ Hecho |
| RF-33 | Productos más rentables (por ganancia total) | S | HU-11 | ✅ Hecho |
| RF-34 | Reporte de stock: inventario valorado a costo y a venta, listado de stock bajo y sin stock, stock por categoría | M | — | ✅ Hecho |
| RF-35 | Productos con margen bajo (umbral 20%) | C | — | ✅ Hecho |
| RF-36 | Ambos reportes protegidos con rol Administrador (cajero → 403) | M | HU-02 | ✅ Hecho |

### 4.5 Pantalla de cobro (Sprint 3)

| ID | Requerimiento | Prioridad | HU | Estado |
|---|---|---|---|---|
| RF-37 | Pantalla de cobro accesible con login (Cajero y Administrador) | M | HU-07 | ✅ Hecho (`pantalla_cobro`, ambos roles) |
| RF-38 | Modelos `Venta`/`DetalleVenta` como base del carrito, con `precio_unitario` y `costo_unitario` congelados al momento de la venta | M | HU-07/08/09 | ✅ Hecho (migración `0004`) |
| RF-39 | Lugar reservado en la UI para el lector de código de barras (mock visible) | S | HU-07 | ✅ Hecho (input escáner + mock) |
| RF-40 | Carga de productos al carrito, edición de cantidades, cobro con vuelto/pago exacto y descuento de stock | M | HU-07/08/09 | ✅ Hecho (`ventas/services.py`, HTMX) + búsqueda en tiempo real desde 3 caracteres |
| RF-41 | Método de pago (efectivo, tarjeta, cuenta corriente y Mercado Pago QR) y cajero responsable en `Venta` | M | HU-09/10/15 | ✅ Hecho (`metodo_pago`, `usuario`, `monto_entregado`, `vuelto`) |
| RF-42 | Ordenar la lista de productos por columna (nombre, precio, stock, código) de forma ascendente/descendente | S | HU-05 | ✅ Hecho (`?orden=&direccion=` con whitelist `CAMPOS_ORDEN`) |
| RF-43 | Datos de demo reproducibles: catálogo cargado y ventas históricas para probar reportes | C | — | ✅ Hecho (`cargar_demo`, semilla fija `20260920`, `--limpiar`) |
| RF-44 | Todos los importes de la UI con un único formato de pesos (`$30.500`) | S | — | ✅ Hecho (filtro `montos`) |

### 4.6 Clientes frecuentes (Sprint 4)

| ID | Requerimiento | Prioridad | HU | Estado |
|---|---|---|---|---|
| RF-45 | Modelo `Cliente`: nombre, apellido, DNI/CUIT **único**, teléfono, email, fecha de registro, puntos y baja lógica | M | HU-12 | ✅ Hecho (app `clientes`, migración `0001`) |
| RF-46 | DNI/CUIT normalizado al guardar (se aceptan puntos y guiones; se rechazan letras) y sin duplicados | S | HU-12 | ✅ Hecho (`ClienteForm.clean_dni`) |
| RF-47 | CRUD de clientes (listar con búsqueda/estadísticas, crear, editar, eliminar como baja lógica, ficha con historial) reservado al Administrador | M | HU-12 | ✅ Hecho (cajero → 403) |
| RF-48 | El cajero busca un cliente por DNI desde la pantalla de cobro y lo asocia al carrito; puede quitar la asociación | M | HU-12 | ✅ Hecho (`clientes:buscar`/`asociar`/`quitar`, carrito en sesión) |
| RF-49 | Alta rápida de un cliente nuevo sin salir del cobro, asociándolo en el mismo paso | S | HU-12 | ✅ Hecho (`clientes:alta_rapida`) |
| RF-50 | La venta guarda el cliente asociado y los puntos que otorgó (1 cada $100) | M | HU-12 | ✅ Hecho (`Venta.cliente`, `Venta.puntos_ganados`, migración `0005`) |
| RF-51 | El comprobante muestra el cliente y los puntos sumados; la venta sin cliente sigue funcionando igual | S | HU-12 | ✅ Hecho |
| RF-52 | Venta a **cuenta corriente ("FIAR")** para clientes registrados, con saldo de deuda contra un **límite máximo** definido por el administrador | M | HU-14 | ✅ Hecho (`Venta.metodo_pago = cuenta_corriente`, `Cliente.limite_credito`/`saldo_deuda`) |
| RF-53 | *(Integración externa)* Catálogo público sin login con stock y precios, armado de pedido para retiro y envío por WhatsApp al local | M | HU-13 | ✅ Hecho (app `pedidos`) |

### 4.7 Cierre de turno (Sprint 4)

| ID | Requerimiento | Prioridad | HU | Estado |
|---|---|---|---|---|
| RF-54 | Modelo `Turno`: usuario a cargo, fecha de apertura, fecha de cierre y snapshot de totales | M | HU-10 | ✅ Hecho (migración `0006`) |
| RF-55 | Abrir el turno (uno activo por persona) y ver los totales en vivo: efectivo, tarjeta, **Mercado Pago (QR)** y cantidad de operaciones; lo fiado se informa aparte como **deuda otorgada** | M | HU-10/14/15 | ✅ Hecho (`abrir_turno`, `totales_del_turno`, `Turno.total_mercado_pago`) |
| RF-56 | Cerrar el turno congelando los totales (no cambian si después se registran más ventas) | M | HU-10 | ✅ Hecho (`cerrar_turno`, transacción + `select_for_update`) |
| RF-57 | Solo el responsable (o el Administrador) puede ver/cerrar el turno; el turno ajeno da 403 | S | HU-10 | ✅ Hecho (`es_administrador`) |
| RF-58 | El cierre queda auditado y los montos se muestran con el formato de la UI | S | HU-10 | ✅ Hecho (`registrar_accion` + `formatear_monto`) |

### 4.8 Auditoría

| ID | Requerimiento | Prioridad | Estado |
|---|---|---|---|
| RF-59 | Registro automático de login y logout con usuario, acción, fecha e IP | M | ✅ Hecho |
| RF-60 | Registro de acciones de administración (crear/editar/eliminar/asignar rol/toggle de usuarios), de cliente (alta/edición/baja) y del cierre de turno | S | ✅ Hecho |
| RF-61 | Registros de solo lectura (no editables ni eliminables desde la interfaz) | M | ✅ Hecho (Django admin en solo lectura) |
| RF-62 | Interfaz propia para consultar la auditoría | C | ⏳ Pendiente (hasta ahora solo vía Django admin) |

### 4.9 Experiencia de usuario y presentación

| ID | Requerimiento | Prioridad | Estado |
|---|---|---|---|
| RF-63 | Identidad visual propia ("toldo de barrio"), coherente en todas las pantallas | S | ✅ Hecho |
| RF-64 | Estilo visual consistente persistido por navegador | C | ✅ Hecho (neón cian fijo en `data-tema`; se eliminaron Cartelera y Ticket) |
| RF-65 | Modo oscuro persistente, sin destello al cargar, respetando `prefers-color-scheme` | C | ✅ Hecho |
| RF-66 | Diseño responsive (PC, celular) | S | ✅ Hecho |
| RF-67 | Accesibilidad: contraste AA, navegación por teclado (`focus-visible`), `prefers-reduced-motion`, `aria-label` en controles de tema | S | ✅ Hecho |
| RF-68 | Páginas de error amigables 403 y 404 | S | ✅ Hecho |
| RF-69 | Marcar el stock bajo en rojo fijo (no el color de la paleta) para que no se confunda con el neón | C | ✅ Hecho (`.status-bajo` / `.badge-stock-bajo`) |

### 4.10 Catálogo público y pedidos (integración externa, HU-13)

| ID | Requerimiento | Prioridad | HU | Estado |
|---|---|---|---|---|
| RF-70 | Catálogo público **sin login** en `/catalogo/` con productos activos, precios y categorías | M | HU-13 | ✅ Hecho (`pedidos:catalogo`) |
| RF-71 | La vitrina pública muestra solo **"Disponible" / "Agotado"**: nunca la cantidad exacta de stock | M | HU-13 | ✅ Hecho |
| RF-72 | El visitante arma su pedido (agregar/quitar ítems) y lo confirma con su nombre; el pedido queda **registrado en el sistema** (`Pedido` + `ItemPedido`, con total y precios congelados) | M | HU-13 | ✅ Hecho |
| RF-73 | Al confirmar se arma el mensaje y el link a **WhatsApp** con el teléfono del local configurable (`KIOSCO_WHATSAPP`); si no está configurado, se avisa en vez de abrir un chat falso | M | HU-13 | ✅ Hecho (`pedidos/config.py`) |
| RF-74 | Panel interno de pedidos (`/catalogo/panel/`, solo Administrador): listar, filtrar por estado, ver el detalle y marcar **entregado/cancelado** (acciones auditadas) | M | HU-13 | ✅ Hecho |

### 4.11 Cuenta corriente — "FIAR" (HU-14)

| ID | Requerimiento | Prioridad | HU | Estado |
|---|---|---|---|---|
| RF-75 | `Cliente` con **límite de crédito** (`limite_credito`, 0 = sin cuenta corriente) y **saldo de deuda** persistido (`saldo_deuda`) | M | HU-14 | ✅ Hecho (migración `clientes/0002`) |
| RF-76 | El Administrador define/edita el límite desde el alta y la edición de clientes; se rechazan valores negativos | M | HU-14 | ✅ Hecho (`ClienteForm.clean_limite_credito`) |
| RF-77 | El **cajero cobra "FIAR"** (método `cuenta_corriente`) desde el POS, solo si hay un cliente con cuenta corriente asociado al carrito | M | HU-14 | ✅ Hecho (`METODOS_PAGO_VALIDOS`, opción condicional en `_carrito.html`) |
| RF-78 | El cobro fiado se **rechaza** si supera el límite (deuda actual + total), indicando cuánto debe, el límite y cuánto le queda; el carrito no se vacía | M | HU-14 | ✅ Hecho (`clientes.services.validar_fiado` dentro de la transacción de `confirmar_venta`) |
| RF-79 | Al fiar, la deuda del cliente sube en la misma transacción de la venta (bloqueo de fila, sin pisar valores) | M | HU-14 | ✅ Hecho (`sumar_deuda` con `F()`) |
| RF-80 | **Solo el Administrador** registra pagos de la deuda; cada pago queda en el historial (`PagoCuentaCorriente`) con monto, fecha, usuario y observación | M | HU-14 | ✅ Hecho (`clientes:registrar_pago` @rol Administrador; cajero → 403) |
| RF-81 | Un pago de monto ≤ 0 o mayor a la deuda se rechaza (no baja el saldo) | M | HU-14 | ✅ Hecho (`registrar_pago` transaccional + `select_for_update`) |
| RF-82 | La ficha del cliente muestra el estado de la cuenta corriente: límite, deuda, crédito disponible, aviso de "al límite" e historial de pagos | M | HU-14 | ✅ Hecho (`detalle_cliente.html`) |
| RF-83 | El listado de clientes muestra la cuenta corriente (deuda o "al día" con el límite) | S | HU-14 | ✅ Hecho (`_clientes_tabla.html`) |
| RF-84 | Lo fiado **no** cuenta como ingreso ni entra a la caja del turno: se informa aparte como **"Deuda otorgada"**, guardada también en el cierre del turno (`Turno.deuda_otorgada`) | M | HU-14 | ✅ Hecho (`METODOS_EN_CAJA`, `reportes.deuda_otorgada`, `totales_del_turno`/`cerrar_turno`) |

### 4.12 Entrega del pedido: del WhatsApp a la venta (cierre de HU-13)

| ID | Requerimiento | Prioridad | HU | Estado |
|---|---|---|---|---|
| RF-85 | Un pedido **no se puede marcar como entregado a mano**: entregar es cobrar. El pedido entregado genera una `Venta` con su cliente, su método de pago y su total, y queda **vinculado** al pedido (`Pedido.venta`, `Pedido.cliente`) | M | HU-13 | ✅ Hecho (`pedidos.services.registrar_entrega`, `pedidos:entregar`) |
| RF-86 | Al entregar se cobra **el precio congelado del pedido** (lo que el cliente vio cuando lo armó), no el precio actual del catálogo | M | HU-13 | ✅ Hecho (`ventas.services._precio_de_item` + `ItemPedido.precio_unitario`) |
| RF-87 | La entrega usa **el mismo núcleo de venta del POS**: descuenta stock, suma los puntos de fidelidad y, si es cuenta corriente, valida el límite y suma la deuda — todo en una sola transacción | M | HU-13 | ✅ Hecho (`ventas.services.registrar_venta_desde_items`) |
| RF-88 | La entrega es **atómica**: o se cobra y el pedido queda entregado, o no pasa nada (si falla el cobro, el pedido sigue pendiente) | M | HU-13 | ✅ Hecho (`transaction.atomic()` + `select_for_update` del pedido) |
| RF-89 | El panel de pedidos permite **asociar un cliente** al cobrar (búsqueda por DNI, nombre o apellido, **sin depender de los acentos**) o entregar como **consumidor final** (sin puntos ni deuda) | M | HU-13 | ✅ Hecho (`pedidos:buscar_cliente`, `clientes.services.buscar_clientes`) |
| RF-90 | Un pedido ya entregado o cancelado **no se puede volver a cobrar** | M | HU-13 | ✅ Hecho (`registrar_entrega` valida el estado con el pedido bloqueado) |
| RF-91 | La entrega queda **auditada** (quién entregó, qué se cobró, con qué cliente y cuántos puntos) | S | HU-13 | ✅ Hecho (`registrar_accion` en `pedidos:entregar`) |
| RF-92 | Los pedidos **pendientes no son clientes**: el cliente del kiosco recién existe cuando retira y paga; los que retiraron quedaron con su ficha, sus puntos y su venta | M | HU-13 | ✅ Hecho (`cargar_demo_clientes` + `Pedido.cliente`) |
| RF-93 | La demo de clientes y pedidos es **reproducible con un comando** (`manage.py cargar_demo_clientes`), no a mano: todo cliente cargado tiene compras reales, los pedidos entregados se cobran con el flujo real y `--limpiar` borra, repone el stock y recarga | M | HU-13 | ✅ Hecho (`clientes/management/commands/cargar_demo_clientes.py` + `clientes/demo_data.py`) |

### 4.13 Cobro con QR de Mercado Pago (HU-15)

| ID | Requerimiento | Prioridad | HU | Estado |
| RF-94 | La caja ofrece **Mercado Pago (QR)** como método de pago, además de efectivo, tarjeta y cuenta corriente; el cajero confirma y el sistema genera el QR | M | HU-15 | ✅ Hecho (`ventas/cobro_qr.py`, `cobro_confirmar`) |
| RF-95 | Al iniciar el cobro se crea la `Venta` con `finalizada=False` usando el **mismo núcleo** de venta del POS: el stock queda **reservado**, pero la venta no cuenta en reportes ni en el turno y los puntos se suman recién al aprobarse el pago | M | HU-15 | ✅ Hecho (`services._crear_venta(..., finalizada=False)`) |
| RF-96 | El servidor pide a Mercado Pago (Checkout Pro) una preferencia con los ítems de la venta, referencia `norvex-venta-<id>`, vencimiento a 30 minutos y nombre en el resumen de la tarjeta. Se usa siempre **`init_point`** (también con cuentas de prueba, fix `ef1dd93`) | M | HU-15 | ✅ Hecho (`mercadopago.crear_preferencia`) |
| RF-97 | El pago se confirma por **webhook** (el aviso no se cree a ciegas: se vuelve a consultar el pago a la API) y, si no hay webhook, la caja consulta cada pocos segundos si hay un pago aprobado para esa referencia | M | HU-15 | ✅ Hecho (`mercadopago_webhook`, `pago_estado`, `buscar_pago_aprobado`) |
| RF-98 | Al aprobarse el pago la venta pasa a `finalizada=True` y el cliente de fidelidad suma sus puntos; al cancelarse, el **stock vuelve** y los productos regresan al carrito para cobrar de otra forma | M | HU-15 | ✅ Hecho (`aprobar_pago`, `cancelar_cobro`) |
| RF-99 | Un cobro ya aprobado **no se puede cancelar**; un cajero no puede tener dos cobros QR pendientes a la vez | M | HU-15 | ✅ Hecho (`pago_pendiente`, validación de estado con `select_for_update`) |
| RF-100 | Sin credenciales de Mercado Pago el sistema funciona en **modo de prueba** con pago simulado (sin plata real); con token `TEST-...` usa el sandbox. Nunca cobra de verdad sin una cuenta configurada | M | HU-15 | ✅ Hecho (`esta_configurado`, `usa_sandbox`, `/ventas/pagar/<token>/`) |
| RF-101 | El cierre de turno informa **"Total Mercado Pago (QR)"** como parte de la caja, separado de efectivo y tarjeta, y mantiene la deuda otorgada aparte | M | HU-15 | ✅ Hecho (`Turno.total_mercado_pago`, `total_en_caja`) |
| RF-102 | Iniciar y cancelar un cobro QR queda **auditado** | S | HU-15 | ✅ Hecho (`registrar_accion`) |
| RF-103 | El botón **"Conectar con Mercado Pago"** (OAuth) permite que la plata llegue a la cuenta del negocio: cuenta conectada → `MP_ACCESS_TOKEN` del entorno → modo de prueba; renueva el token antes de vencer y la desconexión vuelve al modo anterior | M | HU-15 | ✅ Hecho (`ConexionMercadoPago`, `views_conexion.py`, migración `ventas/0009`) |

> **Cuentas de prueba (sandbox, para facultad):** comprador Norvex (ID 3809513038, usuario `TESTUSER5602888735222767984`, clave `QX5FnVgdxg`, verificación 513038) y vendedor Norvex (ID 3809513042, usuario `TESTUSER4734636893281846594`, clave `x7CWpT5XWB`, verificación 513042). El vendedor conecta la cuenta por OAuth y el comprador paga el QR desde la app. Con cuentas de prueba se usa `init_point` (fix `ef1dd93`). Ver README para el detalle.
> **Tecnologías (resumen):** frontend DTL + Bootstrap 5 + HTMX + CSS/JS puros sin build; backend Django 6.1.1 + PostgreSQL; ver ARD §2 para el stack completo.

### 4.14 Pantalla para el cliente en un celular (HU-16)

| ID | Requerimiento | Prioridad | HU | Estado |
|---|---|---|---|---|
| RF-104 | `/ventas/display/` es una vista con login para dejar un celular en el mostrador mirando al cliente: muestra el cobro pendiente del cajero, el total y el QR | S | HU-16 | ✅ Hecho (`views_qr.display`, `display_estado`) |
| RF-105 | La pantalla se actualiza sola (espera → QR → "¡Pago aprobado!") sin que nadie la toque y deja de mostrar el QR al aprobarse | S | HU-16 | ✅ Hecho (consulta periódica a `display_estado`) |
| RF-106 | Las URLs para el celular reemplazan `localhost`/`127.0.0.1` por la **IP de la PC en la red local**, para que el celular pueda entrar | S | HU-16 | ✅ Hecho (`url_para_celular`) |

### 4.15 Recuperación de contraseña por correo

| ID | Requerimiento | Prioridad | Estado |
|---|---|---|---|
| RF-107 | Cualquier usuario puede pedir un enlace de recuperación desde el login ingresando su correo; la respuesta no revela si el correo existe | M | ✅ Hecho (`usuarios:password_reset`) |
| RF-108 | El mail se envía con **Resend** (HTML estilizado + texto plano) y el enlace apunta al formulario de contraseña nueva con el namespace correcto; sin `RESEND_API_KEY` el mail se imprime en la consola del servidor y el flujo no rompe | M | ✅ Hecho (`usuarios/email_backend.py`, `templates/usuarios/password_reset_*`) |
| RF-109 | El formulario de contraseña nueva usa los validadores de Django, pide la contraseña dos veces y permite iniciar sesión con la nueva al terminar | M | ✅ Hecho (`PasswordResetConfirmView` + template propio) |
| RF-110 | Un enlace **vencido o ya usado** muestra una pantalla amigable con la opción de pedir uno nuevo, en vez de un error 500 | S | ✅ Hecho (`validlink` en `password_reset_confirm.html`) |
| RF-111 | Todo el flujo (pedir, enviado, nueva contraseña, completado) usa páginas propias con la identidad **Norvex** | S | ✅ Hecho (`templates/usuarios/`) |

### 4.16 Publicación y operación en la nube

| ID | Requerimiento | Prioridad | Estado |
|---|---|---|---|
| RF-112 | `render.yaml` publica el sitio y una base PostgreSQL en Render: instala dependencias, junta estáticos, migra, ejecuta `setup_inicial` y arranca con **gunicorn** | S | ✅ Hecho |
| RF-113 | En producción `DEBUG=False`, `SECRET_KEY` propia y `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS` desde el entorno; cookies seguras y proxy SSL para que funcionen el login y el OAuth de Mercado Pago | M | ✅ Hecho (`config/settings.py`) |
| RF-114 | **WhiteNoise** sirve los archivos estáticos en producción, sin depender de un servidor web aparte | S | ✅ Hecho (`requirements.txt`, middleware condicional) |
| RF-115 | El despliegue es **reproducible**: dependencias fijadas en `requirements.txt` (UTF-8) y variables documentadas en `.env.example` | S | ✅ Hecho |

---

## 5. Requerimientos no funcionales

| ID | Categoría | Requerimiento |
|---|---|---|
| RNF-01 | Seguridad | Autorización verificada **en servidor**; nunca depender solo de ocultar elementos en la UI |
| RNF-02 | Seguridad | Contraseñas hasheadas (hashers de Django) y validadores de fortaleza (longitud mínima 6, numéricos y similares) |
| RNF-03 | Seguridad | Protección CSRF en todos los formularios POST; logout vía POST |
| RNF-04 | Seguridad | Secretos fuera del repositorio: `DATABASE_URL` en `.env` (gitignore) |
| RNF-05 | Seguridad | Auditoría de accesos con IP, incluyendo proxies (`X-Forwarded-For`) |
| RNF-06 | Integridad | Ninguna operación de usuario debe poder autodestruirse (no borrado propio ni de superusers) |
| RNF-07 | Integridad | Bajas de producto **lógicas**: nunca borrar registros referenciados por ventas |
| RNF-08 | Disponibilidad | Idempotencia del seed de datos (`setup_inicial`) para poder reejecutarlo sin romper el entorno |
| RNF-09 | Rendimiento | Respuesta interactiva en CRUD y búsquedas; la búsqueda de productos no recarga la página (HTMX) |
| RNF-10 | Mantenibilidad | Suite de tests automatizados verde antes de cada entrega (**379 tests** hoy) |
| RNF-11 | Mantenibilidad | Convención de nombres y comentarios en español; estructura de apps por dominio |
| RNF-12 | Portabilidad | Corre en Windows con Python 3.10+; PostgreSQL principal con fallback automático a SQLite |
| RNF-13 | Localización | Español rioplatense (`es-ar`), huso horario Argentina, formato de fecha/hora local |
| RNF-14 | Usabilidad | Cada pantalla operativa accesible en ≤ 2 clics desde el menú según rol |
| RNF-15 | Compatibilidad | Navegadores modernos con soporte de CSS custom properties, `localStorage` y HTMX (Chrome/Edge/Firefox) |
| RNF-16 | Seguridad | En producción: `DEBUG=False`, `SECRET_KEY` y hosts desde el entorno, cookies `Secure`, CSRF con orígenes confiables y secretos de Mercado Pago/Resend fuera del repositorio |
| RNF-17 | Disponibilidad | Degradación controlada sin credenciales: el QR cae a modo de prueba y el correo a consola; ninguna pantalla devuelve 500 por falta de API keys |
| RNF-18 | Integridad | La demo es **idempotente**: correr `cargar_demo --limpiar` + `cargar_demo_clientes --limpiar` las veces que haga falta deja el mismo stock y los mismos totales |
| RNF-19 | Operación | El sistema publicado corre con gunicorn + WhiteNoise y se puede reconstruir desde el repositorio con `render.yaml` |

---

## 6. Historias de usuario y criterios de aceptación

### Sprint 1 (Entrega 24-09) — ✅ Completo

**HU-01 — Login del sistema**
Como usuario del sistema (dueño o cajero), quiero ingresar con usuario y
contraseña para que solo personal autorizado pueda operar el kiosco.
- CA: con credenciales válidas se ingresa; con inválidas se muestra error.
- *Estado: ✅ Hecho (`usuarios/tests.py`, 9 tests).*

**HU-02 — Separación de roles: Cajero**
Como dueño, quiero que el cajero solo pueda ver la pantalla de cobro, para que
no tenga acceso a costos, precios ni reportes del negocio.
- CA: un *Cajero* que accede a una URL de administración, catálogo o reportes
  recibe 403, y accede sin problemas a la pantalla de cobro.
- *Estado: ✅ Hecho (incluye test `test_no_muestra_costos_al_cajero`).*

**HU-03 — Separación de roles: Administrador**
Como dueño, quiero tener un usuario administrador con acceso total.
- CA: el grupo *Administrador* accede al panel, al catálogo, a los reportes y
  a la pantalla de cobro.
- *Estado: ✅ Hecho.*

### Sprint 2 (Entrega 01-10) — ✅ Completo

**HU-04 — Alta rápida de productos**
Como administrador, quiero cargar un producto nuevo ingresando nombre, código
de barras, precio de costo, precio de venta y stock, para tener el catálogo
actualizado.
- CA: si el código de barras ya existe, el sistema muestra un error y no
  permite el duplicado. También se pueden editar y dar de baja productos.
- *Estado: ✅ Hecho (`ProductoForm` con `clean_codigo_barras`; alta, edición
  y baja lógica reversible).*

**HU-05 — Lista de productos con búsqueda**
Como administrador, quiero una lista donde pueda buscar cualquier producto por
nombre o código para modificarle el precio o corregir el stock.
- CA: la búsqueda filtra en tiempo real (HTMX).
- *Estado: ✅ Hecho (HX-Request responde el partial de la tabla, sin recarga).*

**HU-06 — Alerta de stock bajo**
Como administrador, quiero que el sistema me marque en color los productos que
se están quedando sin stock, para saber qué tengo que salir a reponer.
- CA: productos con stock ≤ umbral se muestran marcados.
- *Estado: ✅ Hecho (`stock_minimo` configurable, default 5; badge en la
  tabla y en los reportes de stock).*

### Sprint 3 (Entrega 15-10) — ✅ Completo

**HU-07 — Carga rápida de productos al carrito**
Como cajero, quiero escanear o tipear un código de barras y que el producto se
agregue al carrito de inmediato.
- CA: si escaneo el mismo producto dos veces, se suma la cantidad en vez de
  crear una fila duplicada.
- *Estado: ✅ Hecho (`cobro_agregar` + `buscar_producto`: código exacto →
  nombre único → aviso de ambiguo; el carrito vive en `session["carrito"]`,
  sin `Venta` a medias). Además, la búsqueda en tiempo real arranca con
  3 caracteres (`cobro_buscar`) y sugiere productos para agregar con un clic.*

**HU-08 — Editar carrito antes de cobrar**
Como cajero, quiero poder borrar un producto del carrito o cambiar la cantidad
antes de confirmar la venta.
- CA: el total se recalcula al modificar el carrito.
- *Estado: ✅ Hecho (`cobro_cantidad` con sumar/restar/quitar y total
  recalculado en el parcial `_carrito.html`).*

**HU-09 — Cobro con efectivo o tarjeta**
Como cajero, quiero indicar si el cliente paga en efectivo o tarjeta, ingresar
el monto entregado y que el sistema calcule el vuelto exacto.
- CA: el stock se descuenta automáticamente al confirmar la venta.
- *Estado: ✅ Hecho (`confirmar_venta` con transacción + `select_for_update`,
  vuelto y botones de billetes/pago exacto, auditoría y comprobante;
  `metodo_pago` en `Venta`; 31 tests nuevos de cobro).*

### Sprint 4 (Entrega 05-11) — ✅ Completo

**HU-10 — Cierre de turno** — ✅ **Hecho.**
- CA: se registra el total en efectivo, en tarjeta, la cantidad de operaciones y
  qué usuario estaba a cargo.
- *Implementado con el modelo `Turno` (migración `0006`), los servicios
  `abrir_turno`/`totales_del_turno`/`cerrar_turno` (snapshot congelado en
  transacción) y la pantalla `/ventas/turno/cierre/`. Solo el responsable o el
  Administrador ven/cierran el turno; el cierre queda auditado. 17 tests.*

**HU-11 — Reporte de productos más vendidos** — ✅ **Hecho (adelantado).**
- CA: el reporte muestra el top 10 de productos por cantidad vendida en un
  período seleccionable.
- *Implementado en `/administracion/reportes/ventas/` junto con KPIs
  (ingresos, costo, ganancia, ticket promedio, margen), serie de 14 días y
  productos más rentables; más el reporte de stock en
  `/administracion/reportes/stock/`. 59 tests.*

**HU-12 — Clientes frecuentes (opcional)** — ✅ **Hecho.**
- CA: el cajero busca por CUIT/DNI y trae los datos automáticamente; si es
  nuevo, lo carga en una ventanita rápida.
- *Implementado en la app `clientes/`: modelo `Cliente` (DNI/CUIT único y
  normalizado, baja lógica), CRUD para el Administrador, búsqueda/asociación y
  alta rápida desde el cobro, `Venta.cliente` + `Venta.puntos_ganados`
  (1 punto cada $100, migración `0005`) y ficha con historial. 37 tests.*

### Consignas nuevas de la cátedra

**HU-13 — Catálogo online con pedido para retirar (take away)** — ✅ **Hecho.**
Como vecino, quiero ver el catálogo del kiosco con el stock y los precios
actuales, armar mi pedido y enviarlo por WhatsApp, para pasar a retirarlo sin
hacer cola.
- CA: la vista es pública (sin login); solo muestra productos activos y con
  stock; el mensaje del pedido y el link a WhatsApp usan el teléfono del local
  configurable.
- CA: cuando el cliente retira, se le **cobra** en el mostrador y el pedido
  queda con su venta y su cliente (nunca queda "entregado" sin cobrar).
- *Implementado con la app `pedidos/`: catálogo público en `/catalogo/`, carrito
  de pedido en sesión, `Pedido` + `ItemPedido` registrados en el sistema, link
  `wa.me` con el mensaje armado y panel interno de pedidos para el
  Administrador (marcar entregado/cancelado). El stock se muestra como
  **"Disponible" / "Agotado"**, nunca la cantidad exacta. 32 tests.*
- *Cierre del flujo: entregar un pedido **es cobrarlo**. El panel
  pide cliente (opcional), método de pago y monto; se crea la `Venta` con el
  **precio congelado** del pedido usando el mismo núcleo del POS (stock,
  puntos y fiado), y el pedido queda vinculado a la venta y al cliente
  (`Pedido.cliente` / `Pedido.venta`, migración `pedidos/0002`). 19 tests
  nuevos + 8 de la demo.*

**HU-14 — Cuenta corriente ("FIAR") para clientes frecuentes** — ✅ **Hecho.**
Como administrador, quiero que un cliente registrado pueda llevarse productos
y acumular deuda hasta un límite máximo que yo defino, para fidelizar a los
vecinos de confianza.
- CA: el cajero puede elegir "Cobrar a Cuenta Corriente" solo si la venta tiene
  un cliente asociado; el sistema **rechaza la venta si supera el límite**
  (validado en el servidor); el saldo y los pagos quedan registrados y
  visibles en la ficha del cliente.
- *Implementado: `Cliente.limite_credito` + `Cliente.saldo_deuda` y modelo
  `PagoCuentaCorriente` (migración `clientes/0002`); método de pago
  `cuenta_corriente` en `Venta` (migración `ventas/0007`); validación del
  límite y suma de la deuda dentro de la transacción de `confirmar_venta`;
  pantalla de pago en la ficha del cliente (solo Administrador); la deuda
  otorgada se informa aparte de la caja y de los ingresos y se congela en
  `Turno.deuda_otorgada`. 43 tests nuevos de cuenta corriente.*

### Extras de producto — ✅ Completo

**HU-15 — Cobro con QR de Mercado Pago** — ✅ **Hecho.**
Como cajero, quiero cobrar con un QR de Mercado Pago para que el cliente pague
con la app desde su celular, sin efectivo ni tarjeta.
- CA: al elegir **Mercado Pago (QR)** se genera el QR y la venta queda
  **pendiente** (stock reservado, sin contar en reportes ni en el turno) hasta
  que el pago se aprueba.
- CA: la caja se entera sola del pago (webhook y/o consulta periódica) y
  muestra el comprobante; recién ahí se suman los puntos de fidelidad.
- CA: si se cancela el cobro, el stock vuelve y los productos regresan al
  carrito; un cobro aprobado no se puede cancelar.
- *Implementado: `Venta.metodo_pago = mercado_pago` y `finalizada`
  (migración `ventas/0008`), `PagoMercadoPago`, flujo en `ventas/cobro_qr.py`,
  API en `ventas/mercadopago.py` (urllib, sin dependencias), vistas en
  `ventas/views_qr.py`, `Turno.total_mercado_pago` y modo de prueba con pago
  simulado. 16 tests.*

**HU-16 — Pantalla para el cliente en un celular** — ✅ **Hecho.**
Como dueño, quiero dejar un celular en el mostrador mirando al cliente que
muestre el QR de cada cobro, para que lo escanee cómodo.
- CA: el celular se actualiza solo (espera → QR → "¡Pago aprobado!") sin que
  nadie lo toque.
- *Implementado: `/ventas/display/` + `display_estado`, con la URL adaptada a
  la IP de la PC en la red local para que el celular pueda entrar.*

**HU-17 — Recuperación de contraseña** — ✅ **Hecho.**
Como usuario, quiero recuperar mi contraseña por correo para volver a entrar
sin depender de que un administrador me la cambie.
- CA: pido el enlace con mi correo, me llega un mail y elijo una contraseña
  nueva; el enlace vencido o usado muestra una pantalla amigable.
- *Implementado: vistas de `django.contrib.auth` con templates propios
  (`password_reset_form/done/confirm/complete`, `password_reset_email.html` y
  `.txt`, asunto propio), backend `ResendEmailBackend` y fallback a consola
  sin `RESEND_API_KEY`. 4 tests.*

**HU-18 — Publicación del sistema** — ✅ **Hecho.**
Como responsable del proyecto, quiero publicar el sistema en internet para que
el kiosco lo use desde cualquier lugar y para que funcione el OAuth de Mercado
Pago (que exige `https`).
- CA: el repositorio se publica en Render con un blueprint, base PostgreSQL,
  migraciones y usuarios iniciales automáticos; en el servidor `DEBUG=False` y
  `SECRET_KEY` propia.
- *Implementado: `render.yaml` (gunicorn), WhiteNoise, `STATIC_ROOT`,
  `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS` y proxy SSL desde el entorno;
  dependencias fijadas en `requirements.txt`.*

---

## 7. Flujo principal del producto

1. El usuario entra a `/` y es redirigido al login (o a `post_login` si ya
   tiene sesión).
2. Se autentica; el sistema detecta su rol:
   - **Administrador** → dashboard con métricas, acceso a gestión de usuarios,
     catálogo y reportes.
   - **Cajero** → pantalla de cobro.
   - **Sin rol** → aviso de que un administrador debe asignarle uno.
3. El administrador carga/edita/da de baja productos, consulta reportes de
   ventas y stock, gestiona usuarios y administra la ficha de los clientes
   frecuentes; cada acción sensible queda auditada.
4. El cajero opera la pantalla de cobro: escanea/tipea códigos, edita
   cantidades, opcionalmente asocia un cliente por DNI (o lo crea al vuelo) y
   cobra en efectivo, tarjeta o **Mercado Pago (QR)**; al confirmar se descuenta
   stock, se suman los puntos del cliente, la venta queda auditada y se muestra
   el comprobante. Con QR la venta queda **pendiente** hasta que el pago se
   aprueba (el stock ya está reservado); un celular en el mostrador puede
   mostrarle el QR al cliente y se actualiza solo. Si el cliente tiene cuenta
   corriente, puede cobrar **FIAR** (siempre dentro del límite); esa deuda se
   informa aparte, no entra a la caja del turno y el Administrador la cobra
   después desde la ficha del cliente.
5. Cualquier intento de acceder a una URL fuera del rol responde **403** con
   página de error amigable.
6. Si un usuario olvida su contraseña, pide un enlace desde el login, recibe un
   mail y elige una nueva; el sistema no depende de que un administrador se la
   cambie.

---

## 8. Criterios de aceptación globales y Definition of Done

**Definition of Done (aplica a cada historia):**

- [ ] Implementada en server-side, con control de rol correspondiente.
- [ ] Formularios con validación y mensajes al usuario (`django.messages`).
- [ ] Protección CSRF; métodos de escritura vía POST.
- [ ] Tests automatizados agregados y suite completa en verde
      (`python manage.py test`).
- [ ] UI responsive con los tokens/estilos del proyecto (neón + dark).
- [ ] Comentarios y nombres en español; documentación (README/backlog) actualizada.
- [ ] Sin regresiones en las funcionalidades ya entregadas.

**Criterios de aceptación del Sprint 3 (cumplidos):**

- [x] Escanear/tipear un código y ver el producto en el carrito sin usar el mouse.
- [x] Modificar cantidades o quitar ítems y ver el total recalculado.
- [x] Confirmar la venta con efectivo o tarjeta, mostrando el vuelto.
- [x] El stock se descuenta al confirmar y la venta queda registrada con su
      método de pago y cajero.
- [x] Los tests previos siguen en verde y se suman los nuevos (148 en ese momento).

**Criterios de aceptación del Sprint 4 (cumplidos):**

- [x] El administrador ve el reporte del top 10 de productos más vendidos por
      período (HU-11).
- [x] El administrador registra clientes con DNI/CUIT único y los da de baja
      sin perder su historial (HU-12).
- [x] El cajero busca un cliente por DNI en el cobro, lo asocia (o lo crea al
      vuelo) y la venta suma los puntos del cliente (HU-12).
- [x] El cajero cierra el turno y ve los totales por método, la cantidad de
      operaciones y quién estuvo a cargo (HU-10).
- [x] Los tests previos siguen en verde y se suman los nuevos (256 en total).

**Criterios de aceptación de las consignas de la cátedra (cumplidos):**

- [x] El vecino arma un pedido desde el catálogo público y lo envía por
      WhatsApp, y el pedido queda registrado y visible en el panel (HU-13).
- [x] El cajero cobra "FIAR" a un cliente con cuenta corriente y el sistema
      rechaza la venta si se pasa del límite definido por el administrador
      (HU-14).
- [x] El administrador cobra los pagos de la deuda desde la ficha del cliente
      y ve el saldo y el historial actualizados (HU-14).
- [x] Lo fiado no entra a la caja ni a los ingresos: se informa aparte como
      **deuda otorgada** (HU-14).
- [x] Los tests previos siguen en verde y se suman los nuevos (340 en total).

**Criterios de aceptación del cierre de HU-13 (cumplidos):**

- [x] Un pedido **no se puede marcar como entregado a mano**: para entregarlo
      hay que cobrarlo (RF-85, RF-90).
- [x] La entrega genera la `Venta` con el cliente, el método de pago y el
      total, y el pedido queda **vinculado** a ella (RF-85).
- [x] Se cobra el **precio congelado** del pedido, no el precio actual del
      catálogo (RF-86).
- [x] La entrega usa el **mismo núcleo de venta del POS**: stock, puntos y
      fiado con las mismas reglas, sin duplicar lógica (RF-87).
- [x] La entrega es **atómica**: si el cobro falla, el pedido sigue pendiente
      (RF-88).
- [x] El panel permite **asociar un cliente** (búsqueda sin depender de los
      acentos) o entregar como **consumidor final** (RF-89).
- [x] La entrega queda **auditada** (RF-91).
- [x] Los pedidos **pendientes no son clientes**: el cliente del kiosco recién
      existe cuando retira y paga (RF-92).
- [x] La demo es **reproducible** con un comando (`cargar_demo_clientes`) y
      todos los clientes cargados tienen compras reales (RF-93).
- [x] Los tests previos siguen en verde y se suman los nuevos (340 en total).

**Criterios de aceptación de los extras (cumplidos):**

- [x] El cajero cobra con **QR de Mercado Pago** y la venta queda pendiente
      hasta que el pago se aprueba; recién ahí suma puntos (HU-15).
- [x] Cancelar el cobro **devuelve el stock** y los productos al carrito; un
      cobro ya aprobado no se puede cancelar (HU-15).
- [x] El cierre de turno informa **"Total Mercado Pago (QR)"** aparte de
      efectivo y tarjeta (HU-15).
- [x] El negocio **conecta su cuenta** de Mercado Pago con el botón y la
      desconexión vuelve al modo anterior (HU-15).
- [x] La **pantalla del celular** del cliente se actualiza sola: espera → QR →
      "¡Pago aprobado!" (HU-16).
- [x] El usuario **recupera su contraseña por mail** y un enlace vencido
      muestra una pantalla amigable, no un 500 (HU-17).
- [x] El sistema se **publica en Render** con migraciones, estáticos y usuarios
      iniciales automáticos (HU-18).
- [x] La demo es **idempotente**: recargarla no pierde stock (RNF-18).
- [x] Los tests previos siguen en verde y se suman los nuevos (379 en total).

---

## 9. Roadmap

| Sprint | Entrega | Contenido | Estado |
|---|---|---|---|
| 1 | 24-09 | Login, roles, 403 server-side, post-login por rol | ✅ Completo |
| 2 | 01-10 | Catálogo: CRUD, código de barras, búsqueda HTMX, alerta de stock, gestión de usuarios | ✅ Completo |
| 3 | 15-10 | Carrito con lector de código de barras, edición de carrito, cobro efectivo/tarjeta con vuelto, método de pago, descuento de stock | ✅ Completo |
| 4 | 05-11 | **Reportes (HU-11) ✅** · **Clientes frecuentes (HU-12) ✅** · **Cierre de turno (HU-10) ✅** | ✅ Completo |
| - | — | **Consignas nuevas de la cátedra:** catálogo online + pedido por WhatsApp (HU-13) ✅ y cuenta corriente "FIAR" (HU-14) ✅ | ✅ 2/2 |
| - | — | **Cierre del flujo de HU-13:** entregar un pedido **es cobrarlo** (pedido ↔ venta ↔ cliente), precio congelado, núcleo de venta compartido con el POS y demo reproducible | ✅ Completo |
| - | — | **Extras:** cobro QR (HU-15) + display (HU-16) + marca Norvex, OAuth "Conectar con Mercado Pago" + publicación en Render, recuperación de contraseña con Resend, demo idempotente y fix `init_point` en cuentas de prueba | ✅ Completo |

---

## 10. Supuestos, riesgos y dependencias

| ID | Tipo | Descripción | Impacto | Estado / Mitigación |
|---|---|---|---|---|
| R-01 | ~~Riesgo~~ | Templates de catálogo faltantes (500 en `/ventas/productos/`) | Alto | ✅ **Resuelto:** 5 templates creados |
| R-02 | ~~Riesgo~~ | Rutas de catálogo sin chequeo de rol | Alto | ✅ **Resuelto:** `@rol_requerido("Administrador")` en las 4 vistas |
| R-03 | Riesgo | `toggle_usuario` cambia estado vía **GET** (sin POST/CSRF) | Medio | Abierto: convertir a POST con token |
| R-04 | ~~Riesgo~~ | `Venta` sin método de pago ni FK al cajero responsable | Alto | ✅ **Resuelto:** `metodo_pago`, `usuario`, `monto_entregado`, `vuelto` (migración `0004`) |
| R-05 | ~~Riesgo~~ | No hay lógica de venta: no descuenta stock ni calcula total | Alto | ✅ **Resuelto:** `ventas/services.py` con transacción, `select_for_update` y descuento de stock |
| R-06 | ~~Riesgo~~ | `SECRET_KEY` hardcodeada, `DEBUG=True` fijo y `ALLOWED_HOSTS` vacío | Alto si se despliega | ✅ **Resuelto:** `DEBUG`, `SECRET_KEY`, `ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS` desde el entorno; en producción cookies seguras y proxy SSL |
| R-07 | Riesgo | Paginación implementada pero sin usar en los templates | Bajo | Abierto: conectar `{% paginacion %}` |
| R-08 | Riesgo | Auditoría sin tests ni interfaz propia | Medio | Abierto: tests de señales + listado |
| R-09 | Riesgo | El dashboard no muestra KPIs de negocio (solo métricas de usuarios) | Bajo | Abierto: los KPIs viven en `/reportes/` |
| R-10 | ~~Riesgo~~ | Configuración de correo inválida (`MAILERS` en vez de `EMAIL_BACKEND`) | Bajo | ✅ **Resuelto:** `MAILERS` + `ResendEmailBackend`, templates de mail propios con el namespace correcto, fallback a consola sin API key y 4 tests del flujo |
| R-11 | Supuesto | Los usuarios de prueba (`admin`/`cajero1`, contraseña `kiosco2024`) son solo para desarrollo | — | No usar en producción; rotar credenciales |
| R-12 | Supuesto | El local dispone de PC con navegador moderno y conexión local al servidor | — | Fallback a SQLite para demo sin PostgreSQL |
| R-13 | ~~Riesgo~~ | Los pedidos del catálogo público (HU-13) llegan por WhatsApp y no quedan registrados en el sistema | Medio | ✅ **Resuelto:** cada pedido se guarda como `Pedido` + `ItemPedido` y el kiosquero lo ve en el panel de pedidos |
| R-14 | ~~Riesgo~~ | Lo fiado por cuenta corriente (HU-14) no es plata que entra a la caja | Medio | ✅ **Resuelto:** `METODOS_EN_CAJA = ("efectivo", "tarjeta")`; lo fiado se muestra aparte como **deuda otorgada** (en el turno y en los reportes) y no suma a los ingresos |
| R-15 | ~~Riesgo~~ | Un pedido de WhatsApp podía quedar **"entregado" sin cobrarse** (ni venta, ni stock descontado, ni cliente con compras) | Medio | ✅ **Resuelto:** entregar **es cobrar** (`pedidos.services.registrar_entrega`): el pedido queda con su `Venta` y su `Cliente`, y "entregado" ya no se marca a mano |
| R-16 | Riesgo | Un cobro QR pendiente que el cliente nunca paga deja **stock reservado** | Medio | Mitigado: el cajero puede cancelar (devuelve el stock y los ítems al carrito) y la preferencia vence a los 30 minutos. Abierto: liberar el stock automáticamente al vencer |
| R-17 | Riesgo | Dependencia de servicios externos (**Mercado Pago**, **Resend**) | Medio | Mitigado: sin credenciales el QR cae a modo de prueba y el correo a consola; si Mercado Pago falla, el cobro muestra el error y la caja sigue con efectivo/tarjeta. Abierto: reintentos y aviso al Administrador |
| R-18 | Riesgo | El plan gratis de Render **duerme** el sitio y la base vence a los 30 días | Medio para producción | Abierto: usar plan pago o apuntar `DATABASE_URL` a un PostgreSQL administrado (Supabase) |
| R-19 | Riesgo | Una sola cuenta de Mercado Pago por **instalación** (no hay multi-negocio) | Bajo | Abierto: `ConexionMercadoPago` está pensada para agregarle un FK al negocio si el sistema escala |
| R-20 | ~~Riesgo~~ | El webhook de Mercado Pago no puede llegar a `localhost` | Medio | ✅ **Mitigado:** la caja consulta el estado del pago cada pocos segundos; el webhook se usa cuando el sistema está publicado con `https` |
| R-21 | Riesgo | El QR ofrece **Mercado Pago** en pantallas donde no se cobra en el acto (entrega de pedidos) | Bajo | ✅ **Resuelto:** el formulario de entrega filtra por `METODOS_PAGO_VALIDOS` y solo ofrece efectivo, tarjeta y cuenta corriente |
| R-22 | Riesgo | La demo perdía **stock** en cada recarga (`cargar_demo --limpiar` borraba ventas ajenas sin reponer) | Alto para demos y pruebas | ✅ **Resuelto:** borrado selectivo de las ventas anónimas, reposición desde ventas e ítems de pedidos y verificación de idempotencia con test |
| D-01 | Dependencia | Consignas/entregas del TP con fechas fijas (Sprint 4: 05-11) | — | ✅ Cumplida: Sprint 4 completo |
| D-02 | ~~Dependencia~~ | HU-13 requería el teléfono del kiosco configurable | — | ✅ **Resuelto:** `KIOSCO_WHATSAPP`/`KIOSCO_NOMBRE` en `.env` (con `.env.example`), leídos por `pedidos/config.py` |

---

## 11. Criterios de éxito y métricas

| Métrica | Objetivo | Valor al 05-11-2026 |
|---|---|---|
| Tests automatizados en verde | 100% de la suite | **379/379 OK** (usuarios 13, ventas 141 —99 + 10 de `cargar_demo` + 16 de Mercado Pago + 16 de conexión OAuth—, clientes 83, pedidos 53, administración 89 —24 + 65 de reportes—, auditoría 0) |
| Historias Sprint 1 | 3/3 | 3/3 ✅ |
| Historias Sprint 2 | 3/3 | 3/3 ✅ (HU-04, HU-05, HU-06 cerradas) |
| Historias Sprint 3 | 3/3 al 15-10 | 3/3 ✅ (HU-07, HU-08, HU-09 cerradas) |
| Historias Sprint 4 | 3/3 al 05-11 | 3/3 ✅ (HU-10, HU-11 y HU-12 cerradas) |
| Consignas nuevas de la cátedra (HU-13/HU-14) | por definir | 2/2 ✅ (HU-13 y HU-14 cerradas) |
| Extras de producto (HU-15 a HU-18) | por definir | 4/4 ✅ (QR + display, OAuth/publicación, recuperación de contraseña) |
| Rutas críticas protegidas por rol | 100% | ✅ administración, catálogo, clientes, reportes, pedidos, turno ajeno y conectar/desconectar Mercado Pago → 403 para Cajero (el catálogo público es la excepción intencional: sin login) |
| Demo reproducible e idempotente | 2 recargas seguidas dejan el mismo estado | ✅ verificado (56 productos, 11 clientes, 681 ventas; 0 stock negativo; deuda = fiado) |
| Bloqueantes abiertos | 0 al entregar | **0 de severidad alta** (R-04, R-05, R-06, R-10, R-21 y R-22 resueltos) |

---

## 12. Historial de versiones

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0 | — | Versión inicial (alcance Sprint 1 + 2 en curso) |
| 2.0 | — | Cierre del Sprint 2 (CRUD + HTMX + alerta de stock), reportes del Sprint 4 entregados, 110 tests |
| 2.1 | — | Cierre del Sprint 3: RF-37 a RF-41 completadas, HU-07/08/09 ✅, R-04/R-05 resueltos, 148 tests |
| 2.2 | — | Fidelidad de clientes (HU-12) ✅: app `clientes/`, RF-45 a RF-51; consignas HU-13/HU-14 documentadas; 207 tests |
| 2.3 | — | Cierre del Sprint 4 (HU-10) ✅: modelo `Turno` con snapshot de totales, RF-54 a RF-58; Sprint 4 completo; 224 tests |
| 2.4 | — | Integración externa (HU-13) ✅: app `pedidos/` catálogo público, `Pedido`/`ItemPedido`, WhatsApp configurable y panel; RF-70 a RF-74; 256 tests |
| 2.5 | — | Cuenta corriente "FIAR" (HU-14) ✅: `limite_credito`/`saldo_deuda` + `PagoCuentaCorriente`, cobro fiado y deuda otorgada fuera de caja/ingresos; RF-75 a RF-84; 299 tests |
| 2.6 | — | Cierre del flujo de pedidos (HU-13): entregar **es cobrar**. `Pedido.cliente`/`Pedido.venta`, `registrar_entrega` con núcleo de venta del POS y precio congelado, demo reproducible con `cargar_demo_clientes`; RF-85 a RF-93; 340 tests |
| 2.7 | — | **QR Mercado Pago (HU-15)** + **display (HU-16)** + **OAuth "Conectar"** + **Resend** + **Render** (gunicorn/WhiteNoise). RF-94 a RF-115, demo idempotente y entrega sin `mercado_pago`; 379 tests |
| 2.8 | 05/11/2026 | Fix `ef1dd93`: `init_point` también con cuentas de prueba; cuentas sandbox documentadas en README; búsqueda de cliente sin acentos y demo idempotente ya cubiertos; 379 tests |
