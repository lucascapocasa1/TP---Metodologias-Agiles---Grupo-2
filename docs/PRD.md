# PRD — Documento de Requerimientos de Producto

## Sistema Kiosco

| Campo | Valor |
|---|---|
| Documento | PRD v2.6 |
| Fecha | 21/10/2026 |
| Versión del código documentado | `main` (21-10-2026) + HU-13 con el flujo de entrega cerrado, Sprint 4 completo |
| Proyecto | Sistema Kiosco — TP Metodologías Ágiles (UNAB) |
| Estado del producto | **Sprint 1 ✅ · Sprint 2 ✅ · Sprint 3 ✅ · Sprint 4 ✅ (reportes + clientes + cierre de turno) · HU-13 ✅ (catálogo público + WhatsApp **y entrega cobrada**) · HU-14 ✅ (cuenta corriente "FIAR") · 340 tests en verde** |
| Documento relacionado | [ARD — Arquitectura y requerimientos técnicos](ARD.md) |

> Historial: v1.0 (24-09) documentaba el alcance de Sprints 1 y 2 en curso.
> v2.0 refleja el cierre del Sprint 2 (catálogo con CRUD + HTMX), la entrega
> adelantada de los reportes del Sprint 4 y dejaba como único bloque pendiente
> la caja/cobro del Sprint 3.
> v2.1 cierra el Sprint 3 (HU-07/08/09): carrito de cobro con escáner,
> edición de cantidades y cobro efectivo/tarjeta con vuelto y descuento de
> stock, adelantado al 05-10 respecto de la entrega del 15-10.
> v2.2 cierra la fidelidad de clientes (HU-12, entregada el 17-10: app
> `clientes/`, CRUD, DNI único y puntos 1 cada $100 asociados a la venta) y
> suma las dos consignas nuevas de la cátedra (catálogo online con pedido por
> WhatsApp y cuenta corriente), todavía **pendientes**.
> v2.3 cierra el Sprint 4 integrando el cierre de turno (HU-10, 19-10: modelo
> `Turno` con snapshot de totales, pantalla de apertura/cierre y control de
> responsable); suite en 224 tests.
> v2.4 implementa la integración externa (HU-13, 19-10: app `pedidos/` con
> catálogo público sin login, pedido registrado, link a WhatsApp y panel
> interno); suite en 256 tests.
> v2.5 cierra las consignas de la cátedra con la cuenta corriente (HU-14,
> 19-10: saldo de deuda por cliente con límite, cobro fiado desde el POS,
> registro de pagos solo para el Administrador y la deuda otorgada mostrada
> aparte de la caja y de los ingresos); suite en 299 tests.
> v2.6 cierra el círculo del pedido por WhatsApp: **entregar es cobrar**. El
> pedido entregado genera la `Venta` con su cliente y queda vinculado a ella
> (precio congelado, stock, puntos y fiado con las mismas reglas del POS);
> además la demo de clientes queda reproducible y coherente con
> `manage.py cargar_demo_clientes`; suite en 340 tests.

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
| O7 | Reconocer al cliente frecuente | Cliente identificado por DNI con historial y puntos acumulados | ✅ Alcanzado (HU-12, 17-10) |

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
| **Fidelidad de clientes** | Modelo `Cliente` (DNI/CUIT único y normalizado, baja lógica), CRUD para el Administrador, búsqueda y alta rápida desde el cobro, asociación de la venta al cliente y puntos (1 cada $100) con historial | 4 (adelantado 17-10) |
| **Pedidos online** | Catálogo público sin login (solo "Disponible"/"Agotado"), carrito de pedido, registro del `Pedido` y envío por WhatsApp; panel interno para ver y cambiar el estado | consigna (adelantada 19-10) |
| **Cuenta corriente** | Cliente con límite de crédito, cobro fiado desde el POS, saldo de deuda con historial de pagos y deuda otorgada informada aparte de la caja y de los ingresos | consigna (adelantada 19-10) |
| **Datos de demo** | Comando `cargar_demo`: 56 productos en 8 categorías y ventas desde el 20/09/2026 con semilla fija, para demos y pruebas | 4 |
| **Experiencia de usuario** | Identidad "toldo de barrio" con estilo neón cian fijo, modo oscuro, responsive, accesibilidad, formato de dinero unificado (`montos`) | transversal |

### 2.2 Estado de lo planificado y fuera del alcance actual

- **Sprint 4 — Cierres (entrega 05-11):** ✅ **Completo.** HU-10 (cierre de
  turno), HU-11 (top 10 y reportes) y HU-12 (clientes frecuentes) entregadas;
  el cierre de turno se integró el 19-10.
- **Consignas nuevas de la cátedra** (sin sprint/fecha asignados; ambas ✅
  **completas el 19-10**):
  - **Integración externa (HU-13):** ✅ **Completo (19-10).** Catálogo online
    público con armado de pedido para retiro ("take away"), pedido registrado
    en el sistema y envío por WhatsApp al local.
  - **Cuenta corriente ("FIAR", HU-14):** ✅ **Completo (19-10).** Saldo de
    deuda por cliente frecuente con límite máximo definido por el
    administrador, cobro a cuenta corriente en la pantalla del POS, registro
    de pagos (solo Administrador) y deuda otorgada excluida de la caja y de
    los ingresos.
- **Por definir:** Mercado Pago, recuperación de contraseña, logo propio,
  comercio configurable (nombre/colores del local parametrizables).

### 2.3 Restricciones

- Entregas fijas: Sprint 1 (24-09) ✅ · Sprint 2 (01-10) ✅ · Sprint 3 (15-10,
  cerrado el 05-10) ✅ · Sprint 4 (05-11, cerrado el 19-10) ✅.
- Aplicación **web** (navegador), sin app nativa; se usa en PC del kiosco y
  eventualmente en celular/tablet.
- Trabajo en equipo con merge a `main`; los artefactos deben poder integrarse
  sin romper los tests existentes (340 en verde).
- Idioma y formato argentinos: español rioplatense, moneda ARS, horario
  `America/Argentina/Buenos_Aires`.
- El servidor de desarrollo corre en el puerto **8001** (conservar ese puerto
  en todas las máquinas del equipo).

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
Estado verificado contra el código el 19-10-2026 (`main` @ `b043f1f`).

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
| RF-41 | Método de pago (efectivo/tarjeta) y cajero responsable en `Venta` | M | HU-09/10 | ✅ Hecho (`metodo_pago`, `usuario`, `monto_entregado`, `vuelto`) |
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
| RF-55 | Abrir el turno (uno activo por persona) y ver los totales en vivo: efectivo, tarjeta y cantidad de operaciones | M | HU-10 | ✅ Hecho (`abrir_turno`, `totales_del_turno`) |
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
| RNF-10 | Mantenibilidad | Suite de tests automatizados verde antes de cada entrega (**340 tests** hoy) |
| RNF-11 | Mantenibilidad | Convención de nombres y comentarios en español; estructura de apps por dominio |
| RNF-12 | Portabilidad | Corre en Windows con Python 3.10+; PostgreSQL principal con fallback automático a SQLite |
| RNF-13 | Localización | Español rioplatense (`es-ar`), huso horario Argentina, formato de fecha/hora local |
| RNF-14 | Usabilidad | Cada pantalla operativa accesible en ≤ 2 clics desde el menú según rol |
| RNF-15 | Compatibilidad | Navegadores modernos con soporte de CSS custom properties, `localStorage` y HTMX (Chrome/Edge/Firefox) |

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

### Sprint 3 (Entrega 15-10) — ✅ Completo (cerrado el 05-10)

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

### Sprint 4 (Entrega 05-11) — ✅ Completo (cerrado el 19-10)

**HU-10 — Cierre de turno** — ✅ **Hecho (19-10-2026).**
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

**HU-12 — Clientes frecuentes (opcional)** — ✅ **Hecho (17-10-2026).**
- CA: el cajero busca por CUIT/DNI y trae los datos automáticamente; si es
  nuevo, lo carga en una ventanita rápida.
- *Implementado en la app `clientes/`: modelo `Cliente` (DNI/CUIT único y
  normalizado, baja lógica), CRUD para el Administrador, búsqueda/asociación y
  alta rápida desde el cobro, `Venta.cliente` + `Venta.puntos_ganados`
  (1 punto cada $100, migración `0005`) y ficha con historial. 37 tests.*

### Consignas nuevas de la cátedra

**HU-13 — Catálogo online con pedido para retirar (take away)** — ✅ **Hecho (19-10-2026), flujo cerrado (21-10-2026).**
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
- *Cierre del flujo (21-10-2026): entregar un pedido **es cobrarlo**. El panel
  pide cliente (opcional), método de pago y monto; se crea la `Venta` con el
  **precio congelado** del pedido usando el mismo núcleo del POS (stock,
  puntos y fiado), y el pedido queda vinculado a la venta y al cliente
  (`Pedido.cliente` / `Pedido.venta`, migración `pedidos/0002`). 19 tests
  nuevos + 8 de la demo.*

**HU-14 — Cuenta corriente ("FIAR") para clientes frecuentes** — ✅ **Hecho (19-10-2026).**
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
   cobra en efectivo o tarjeta con vuelto; al confirmar se descuenta stock, se
   suman los puntos del cliente, la venta queda auditada y se muestra el
   comprobante. Si el cliente tiene cuenta corriente, puede cobrar **FIAR**
   (siempre dentro del límite); esa deuda se informa aparte, no entra a la caja
   del turno y el Administrador la cobra después desde la ficha del cliente.
5. Cualquier intento de acceder a una URL fuera del rol responde **403** con
   página de error amigable.

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

**Criterios de aceptación del Sprint 3 (cumplidos el 05-10):**

- [x] Escanear/tipear un código y ver el producto en el carrito sin usar el mouse.
- [x] Modificar cantidades o quitar ítems y ver el total recalculado.
- [x] Confirmar la venta con efectivo o tarjeta, mostrando el vuelto.
- [x] El stock se descuenta al confirmar y la venta queda registrada con su
      método de pago y cajero.
- [x] Los tests previos siguen en verde y se suman los nuevos (148 en ese momento).

**Criterios de aceptación del Sprint 4 (cumplidos el 19-10-2026):**

- [x] El administrador ve el reporte del top 10 de productos más vendidos por
      período (HU-11).
- [x] El administrador registra clientes con DNI/CUIT único y los da de baja
      sin perder su historial (HU-12).
- [x] El cajero busca un cliente por DNI en el cobro, lo asocia (o lo crea al
      vuelo) y la venta suma los puntos del cliente (HU-12).
- [x] El cajero cierra el turno y ve los totales por método, la cantidad de
      operaciones y quién estuvo a cargo (HU-10).
- [x] Los tests previos siguen en verde y se suman los nuevos (256 en total).

**Criterios de aceptación de las consignas de la cátedra (cumplidos el 19-10-2026):**

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

**Criterios de aceptación del cierre de HU-13 (cumplidos el 21-10-2026):**

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

---

## 9. Roadmap

| Sprint | Entrega | Contenido | Estado |
|---|---|---|---|
| 1 | 24-09 | Login, roles, 403 server-side, post-login por rol | ✅ Completo |
| 2 | 01-10 | Catálogo: CRUD, código de barras, búsqueda HTMX, alerta de stock, gestión de usuarios | ✅ Completo |
| 3 | 15-10 | Carrito con lector de código de barras, edición de carrito, cobro efectivo/tarjeta con vuelto, método de pago, descuento de stock | ✅ Completo (cerrado 05-10) |
| 4 | 05-11 | **Reportes (HU-11) ✅** · **Clientes frecuentes (HU-12) ✅ (17-10)** · **Cierre de turno (HU-10) ✅ (19-10)** | ✅ Completo |
| - | sin fecha | **Consignas nuevas de la cátedra:** catálogo online + pedido por WhatsApp (HU-13) ✅ (19-10) y cuenta corriente "FIAR" (HU-14) ✅ (19-10) | ✅ 2/2 |
| - | 21-10 | **Cierre del flujo de HU-13:** entregar un pedido **es cobrarlo** (pedido ↔ venta ↔ cliente), precio congelado, núcleo de venta compartido con el POS y demo reproducible | ✅ Completo |

---

## 10. Supuestos, riesgos y dependencias

| ID | Tipo | Descripción | Impacto | Estado / Mitigación |
|---|---|---|---|---|
| R-01 | ~~Riesgo~~ | Templates de catálogo faltantes (500 en `/ventas/productos/`) | Alto | ✅ **Resuelto (03-10):** 5 templates creados |
| R-02 | ~~Riesgo~~ | Rutas de catálogo sin chequeo de rol | Alto | ✅ **Resuelto:** `@rol_requerido("Administrador")` en las 4 vistas |
| R-03 | Riesgo | `toggle_usuario` cambia estado vía **GET** (sin POST/CSRF) | Medio | Abierto: convertir a POST con token |
| R-04 | ~~Riesgo~~ | `Venta` sin método de pago ni FK al cajero responsable | Alto | ✅ **Resuelto (05-10):** `metodo_pago`, `usuario`, `monto_entregado`, `vuelto` (migración `0004`) |
| R-05 | ~~Riesgo~~ | No hay lógica de venta: no descuenta stock ni calcula total | Alto | ✅ **Resuelto (05-10):** `ventas/services.py` con transacción, `select_for_update` y descuento de stock |
| R-06 | Riesgo | `SECRET_KEY` hardcodeada, `DEBUG=True` fijo y `ALLOWED_HOSTS` vacío | Alto si se despliega | Abierto: mover a `.env` antes de producción |
| R-07 | Riesgo | Paginación implementada pero sin usar en los templates | Bajo | Abierto: conectar `{% paginacion %}` |
| R-08 | Riesgo | Auditoría sin tests ni interfaz propia | Medio | Abierto: tests de señales + listado |
| R-09 | Riesgo | El dashboard no muestra KPIs de negocio (solo métricas de usuarios) | Bajo | Abierto: los KPIs viven en `/reportes/` |
| R-10 | Riesgo | Configuración de correo inválida (`MAILERS` en vez de `EMAIL_BACKEND`) | Bajo | Abierto: bloquea "olvidé mi contraseña" |
| R-11 | Supuesto | Los usuarios de prueba (`admin`/`cajero1`, contraseña `kiosco2024`) son solo para desarrollo | — | No usar en producción; rotar credenciales |
| R-12 | Supuesto | El local dispone de PC con navegador moderno y conexión local al servidor | — | Fallback a SQLite para demo sin PostgreSQL |
| R-13 | ~~Riesgo~~ | Los pedidos del catálogo público (HU-13) llegan por WhatsApp y no quedan registrados en el sistema | Medio | ✅ **Resuelto (19-10):** cada pedido se guarda como `Pedido` + `ItemPedido` y el kiosquero lo ve en el panel de pedidos |
| R-14 | ~~Riesgo~~ | Lo fiado por cuenta corriente (HU-14) no es plata que entra a la caja | Medio | ✅ **Resuelto (19-10):** `METODOS_EN_CAJA = ("efectivo", "tarjeta")`; lo fiado se muestra aparte como **deuda otorgada** (en el turno y en los reportes) y no suma a los ingresos |
| R-15 | ~~Riesgo~~ | Un pedido de WhatsApp podía quedar **"entregado" sin cobrarse** (ni venta, ni stock descontado, ni cliente con compras) | Medio | ✅ **Resuelto (21-10):** entregar **es cobrar** (`pedidos.services.registrar_entrega`): el pedido queda con su `Venta` y su `Cliente`, y "entregado" ya no se marca a mano |
| D-01 | Dependencia | Consignas/entregas del TP con fechas fijas (Sprint 4: 05-11) | — | ✅ Cumplida: Sprint 4 cerrado el 19-10 |
| D-02 | ~~Dependencia~~ | HU-13 requería el teléfono del kiosco configurable | — | ✅ **Resuelto (19-10):** `KIOSCO_WHATSAPP`/`KIOSCO_NOMBRE` en `.env` (con `.env.example`), leídos por `pedidos/config.py` |

---

## 11. Criterios de éxito y métricas

| Métrica | Objetivo | Valor al 21-10-2026 |
|---|---|---|
| Tests automatizados en verde | 100% de la suite | **340/340 OK** (usuarios 9, ventas 108 —incluye 9 de `cargar_demo`—, clientes 82 —73 + 9 de la demo—, pedidos 52, administración 89 —24 + 65 de reportes—, auditoría 0) |
| Historias Sprint 1 | 3/3 | 3/3 ✅ |
| Historias Sprint 2 | 3/3 | 3/3 ✅ (HU-04, HU-05, HU-06 cerradas) |
| Historias Sprint 3 | 3/3 al 15-10 | 3/3 ✅ (HU-07, HU-08, HU-09 cerradas el 05-10) |
| Historias Sprint 4 | 3/3 al 05-11 | 3/3 ✅ (HU-10, HU-11 y HU-12 cerradas) |
| Consignas nuevas de la cátedra (HU-13/HU-14) | por definir | 2/2 ✅ (HU-13 y HU-14 cerradas el 19-10) |
| Rutas críticas protegidas por rol | 100% | ✅ administración, catálogo, clientes, reportes, pedidos y turno ajeno → 403 para Cajero (el catálogo público es la excepción intencional: sin login) |
| Bloqueantes abiertos | 0 al entregar | **0 de severidad alta** (R-04, R-05 y el bug del seed resueltos) |

---

## 12. Historial de versiones

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0 | 24/09/2026 | Versión inicial (alcance Sprint 1 + 2 en curso) |
| 2.0 | 05/10/2026 | Cierre del Sprint 2 (CRUD + HTMX + alerta de stock), reportes del Sprint 4 entregados, 110 tests, riesgos resueltos/abiertos actualizados |
| 2.1 | 05/10/2026 | Cierre del Sprint 3: RF-37 a RF-41 completadas, HU-07/08/09 ✅, R-04/R-05 resueltos, 148 tests |
| 2.2 | 19/10/2026 | Fidelidad de clientes (HU-12) ✅: app `clientes/`, RF-45 a RF-51, riesgos R-13/R-14 y dependencia D-02; consignas nuevas de la cátedra (HU-13 catálogo público + WhatsApp, HU-14 cuenta corriente) documentadas como pendientes; 207 tests |
| 2.3 | 19/10/2026 | Cierre del Sprint 4 (HU-10) ✅: modelo `Turno` con snapshot de totales, RF-54 a RF-58, pantalla de apertura/cierre y control de responsable; reenumerados los RF de auditoría (RF-59…) y UX (RF-63…); Sprint 4 marcado completo; 224 tests |
| 2.4 | 19/10/2026 | Integración externa (HU-13) ✅: app `pedidos/` con catálogo público sin login, `Pedido`/`ItemPedido` registrados, link a WhatsApp configurable y panel interno de pedidos; RF-70 a RF-74; riesgos R-13/D-02 resueltos; 256 tests |
| 2.5 | 19/10/2026 | Cuenta corriente "FIAR" (HU-14) ✅: `Cliente.limite_credito`/`saldo_deuda` + `PagoCuentaCorriente`, cobro fiado desde el POS con validación de límite, pagos solo para el Administrador, deuda otorgada fuera de la caja y de los ingresos (`Turno.deuda_otorgada`); RF-75 a RF-84; riesgo R-14 resuelto; consignas de la cátedra 2/2; 299 tests |
| 2.6 | 21/10/2026 | Cierre del flujo de pedidos (HU-13): entregar un pedido **es cobrarlo**. `Pedido.cliente` + `Pedido.venta` (migración `pedidos/0002`), servicio `registrar_entrega` con el núcleo de venta del POS (stock, puntos y fiado) y el **precio congelado** del pedido, pantalla "Entregar y cobrar" con búsqueda de cliente (sin depender de los acentos), "entregado" ya no se marca a mano y la entrega queda auditada. RF-85 a RF-93. Demo reproducible con `manage.py cargar_demo_clientes` (clientes con compras reales + pedidos de WhatsApp, los entregados cobrados con el flujo real); 340 tests |
