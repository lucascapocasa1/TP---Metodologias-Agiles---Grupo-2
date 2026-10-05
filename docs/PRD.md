# PRD — Documento de Requerimientos de Producto

## Sistema Kiosco

| Campo | Valor |
|---|---|
| Documento | PRD v2.1 |
| Fecha | 05/10/2026 |
| Versión del código documentado | `main` @ `60e490b` (03-10-2026) + cambios de Sprint 3 sin commitear |
| Proyecto | Sistema Kiosco — TP Metodologías Ágiles (UNAB) |
| Estado del producto | **Sprint 1 ✅ · Sprint 2 ✅ · Sprint 3 ✅ · Reportes (S4) ✅ · 148 tests en verde** |
| Documento relacionado | [ARD — Arquitectura y requerimientos técnicos](ARD.md) |

> Historial: v1.0 (24-09) documentaba el alcance de Sprints 1 y 2 en curso.
> v2.0 refleja el cierre del Sprint 2 (catálogo con CRUD + HTMX), la entrega
> adelantada de los reportes del Sprint 4 y dejaba como único bloque pendiente
> la caja/cobro del Sprint 3.
> v2.1 cierra el Sprint 3 (HU-07/08/09): carrito de cobro con escáner,
> edición de cantidades y cobro efectivo/tarjeta con vuelto y descuento de
> stock, adelantado al 05-10 respecto de la entrega del 15-10.

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

### 1.4 Glosario

| Término | Significado |
|---|---|
| Kiosco | Comercio minorista de barrio; usuario final del sistema |
| Rol | Grupo de Django (`Administrador`, `Cajero`) que define qué ve y puede hacer un usuario |
| Categoría | Agrupación de productos (ej. Golosinas, Bebidas) |
| Baja lógica | Desactivar un producto (`activo=False`) sin borrar el registro para no romper ventas históricas |
| Stock bajo | `stock ≤ stock_minimo` (umbral configurable por producto, default 5) |
| Venta / Detalle | Cabecera de una operación de cobro y sus líneas de producto |
| Auditoría | Registro inmutable de acciones relevantes (usuario, acción, fecha, IP) |
| Sprint | Iteración con entrega demostrable (4 sprints en el TP) |

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
| **Experiencia de usuario** | Identidad "toldo de barrio" con estilo neón cian fijo, modo oscuro, responsive, accesibilidad | transversal |

### 2.2 Fuera del alcance actual (pendiente)

- **Sprint 4 — Cierres (entrega 05-11):** modelo `Turno` y cierre de turno
  (HU-10), modelo `Cliente` con búsqueda por CUIT/DNI (HU-12). El reporte de
  top 10 (HU-11) ya está entregado.
- **Por definir:** Mercado Pago, recuperación de contraseña, logo propio,
  KPIs de negocio en el dashboard principal, comercio configurable
  (nombre/colores del local parametrizables).

### 2.3 Restricciones

- Entregas fijas: Sprint 1 (24-09) ✅ · Sprint 2 (01-10) ✅ · Sprint 3 (15-10,
  cerrado el 05-10) ✅ · Sprint 4 (05-11).
- Aplicación **web** (navegador), sin app nativa; se usa en PC del kiosco y
  eventualmente en celular/tablet.
- Trabajo en equipo con merge a `main`; los artefactos deben poder integrarse
  sin romper los tests existentes (148 en verde).
- Idioma y formato argentinos: español rioplatense, moneda ARS, horario
  `America/Argentina/Buenos_Aires`.
- El servidor de desarrollo corre en el puerto **8001** (el 8000 está ocupado
  por el backend VPN de otro proyecto y no debe tocarse).

---

## 3. Usuarios / personas

| Persona | Rol en el sistema | Qué necesita | Qué **no** debe ver |
|---|---|---|---|
| **Dueño / Administrador** | Grupo `Administrador` (o superuser) | Gestionar usuarios, cargar y consultar productos, ver reportes, stock, costos y auditoría | — (acceso total) |
| **Cajero** | Grupo `Cajero` | Entrar al sistema y usar la pantalla de cobro | Costos, precios de compra, catálogo, reportes, administración de usuarios (recibe 403) |
| **Usuario sin rol** | Autenticado sin grupo | Ver un aviso de que aún no tiene permisos | Cualquier pantalla operativa |
| **Público (no autenticado)** | — | Iniciar sesión o registrarse | Todo el resto (redirigido al login) |

---

## 4. Requerimientos funcionales

Prioridad: **M** = Must (imprescindible), **S** = Should, **C** = Could.
Estado verificado contra el código el 05-10-2026.

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

### 4.6 Auditoría

| ID | Requerimiento | Prioridad | Estado |
|---|---|---|---|
| RF-42 | Registro automático de login y logout con usuario, acción, fecha e IP | M | ✅ Hecho |
| RF-43 | Registro de acciones de administración (crear/editar/eliminar/asignar rol/toggle de usuarios) | S | ✅ Hecho |
| RF-44 | Registros de solo lectura (no editables ni eliminables desde la interfaz) | M | ✅ Hecho (Django admin en solo lectura) |
| RF-45 | Interfaz propia para consultar la auditoría | C | ⏳ Pendiente (hasta ahora solo vía Django admin) |

### 4.7 Experiencia de usuario y presentación

| ID | Requerimiento | Prioridad | Estado |
|---|---|---|---|
| RF-46 | Identidad visual propia ("toldo de barrio"), coherente en todas las pantallas | S | ✅ Hecho |
| RF-47 | Estilo visual consistente persistido por navegador | C | ✅ Hecho (neón cian fijo en `data-tema`; se eliminaron Cartelera y Ticket) |
| RF-48 | Modo oscuro persistente, sin destello al cargar, respetando `prefers-color-scheme` | C | ✅ Hecho |
| RF-49 | Diseño responsive (PC, celular) | S | ✅ Hecho |
| RF-50 | Accesibilidad: contraste AA, navegación por teclado (`focus-visible`), `prefers-reduced-motion`, `aria-label` en controles de tema | S | ✅ Hecho |
| RF-51 | Páginas de error amigables 403 y 404 | S | ✅ Hecho |

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
| RNF-10 | Mantenibilidad | Suite de tests automatizados verde antes de cada entrega (**148 tests** hoy) |
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

### Sprint 4 (Entrega 05-11) — 🟡 Parcial

**HU-10 — Cierre de turno** — ⏳ Pendiente.
*CA: se registra el total en efectivo, en tarjeta, la cantidad de operaciones y
qué usuario estaba a cargo. Requiere modelo `Turno` y FK de `Venta` a usuario.*

**HU-11 — Reporte de productos más vendidos** — ✅ **Hecho (adelantado).**
- CA: el reporte muestra el top 10 de productos por cantidad vendida en un
  período seleccionable.
- *Implementado en `/administracion/reportes/ventas/` junto con KPIs
  (ingresos, costo, ganancia, ticket promedio, margen), serie de 14 días y
  productos más rentables; más el reporte de stock en
  `/administracion/reportes/stock/`. 57 tests.*

**HU-12 — Clientes frecuentes (opcional)** — ⏳ Pendiente.
*CA: el cajero busca por CUIT y trae los datos automáticamente; si es nuevo, lo
carga en una ventanita rápida. Requiere modelo `Cliente`.*

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
   ventas y stock y gestiona usuarios; cada acción sensible queda auditada.
4. El cajero opera la pantalla de cobro: escanea/tipea códigos, edita
   cantidades, cobra en efectivo o tarjeta con vuelto y confirma la venta
   (descuenta stock, queda auditada y muestra el comprobante).
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
- [x] Los tests previos siguen en verde y se suman los nuevos (148 en total).

---

## 9. Roadmap

| Sprint | Entrega | Contenido | Estado |
|---|---|---|---|
| 1 | 24-09 | Login, roles, 403 server-side, post-login por rol | ✅ Completo |
| 2 | 01-10 | Catálogo: CRUD, código de barras, búsqueda HTMX, alerta de stock, gestión de usuarios | ✅ Completo |
| 3 | 15-10 | Carrito con lector de código de barras, edición de carrito, cobro efectivo/tarjeta con vuelto, método de pago, descuento de stock | ✅ Completo (cerrado 05-10) |
| 4 | 05-11 | **Reportes (HU-11): ✅ entregado** · Cierre de turno (HU-10), clientes frecuentes (HU-12) | 🟡 Parcial |

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
| D-01 | Dependencia | Consignas/entregas del TP con fechas fijas (Sprint 3: 15-10) | — | ✅ Cumplida: Sprint 3 cerrado 10 días antes |

---

## 11. Criterios de éxito y métricas

| Métrica | Objetivo | Valor al 05-10-2026 |
|---|---|---|
| Tests automatizados en verde | 100% de la suite | **148/148 OK** (usuarios 9, ventas 60, administración 22, reportes 57) |
| Historias Sprint 1 | 3/3 | 3/3 ✅ |
| Historias Sprint 2 | 3/3 | 3/3 ✅ (HU-04, HU-05, HU-06 cerradas) |
| Historias Sprint 3 | 3/3 al 15-10 | 3/3 ✅ (HU-07, HU-08, HU-09 cerradas el 05-10) |
| Historias Sprint 4 | 3/3 al 05-11 | 1/3 ✅ (HU-11 entregado) |
| Rutas críticas protegidas por rol | 100% | ✅ administración, catálogo y reportes → 403 para Cajero |
| Bloqueantes abiertos | 0 al entregar | **0 de severidad alta** (R-04 y R-05 resueltos) |

---

## 12. Historial de versiones

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0 | 24/09/2026 | Versión inicial (alcance Sprint 1 + 2 en curso) |
| 2.0 | 05/10/2026 | Cierre del Sprint 2 (CRUD + HTMX + alerta de stock), reportes del Sprint 4 entregados, 110 tests, riesgos resueltos/abiertos actualizados |
| 2.1 | 05/10/2026 | Cierre del Sprint 3: RF-37 a RF-41 completadas, HU-07/08/09 ✅, R-04/R-05 resueltos, 148 tests |
