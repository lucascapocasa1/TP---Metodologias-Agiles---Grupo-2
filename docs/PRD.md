# PRD — Documento de Requerimientos de Producto

## Sistema Kiosco

| Campo | Valor |
|---|---|
| Documento | PRD v1.0 |
| Fecha | 24/09/2026 |
| Proyecto | Sistema Kiosco — TP Metodologías Ágiles (UNAB) |
| Sprint vigente | **Sprint 2** — "Cargar y ordenar los productos" (entrega 01-10) |
| Estado del producto | Sprint 1 completo · Sprint 2 en progreso · 35 tests en verde |
| Documento relacionado | [ARD — Arquitectura y requerimientos técnicos](ARD.md) |

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

| # | Objetivo | Medible |
|---|---|---|
| O1 | Acceso restringido por roles (dueño vs. cajero) | 100% de las rutas protegidas verificadas server-side (403), con tests |
| O2 | Carga y consulta rápida de productos | Alta y búsqueda de productos sin salir de la interfaz web |
| O3 | Trazabilidad de acciones sensibles | Login/logout y operaciones sobre usuarios registrados con usuario, fecha e IP |
| O4 | Interfaz clara y personalizable para el local | 3 estilos visuales + modo oscuro, contraste AA |
| O5 | Base sólida para caja y reportes | Modelos de venta normalizados y testeados antes del Sprint 3 |

### 1.4 Glosario

| Término | Significado |
|---|---|
| Kiosco | Comercio minorista de barrio; usuario final del sistema |
| Rol | Grupo de Django (`Administrador`, `Cajero`) que define qué ve y puede hacer un usuario |
| Categoría | Agrupación de productos (ej. Golosinas, Bebidas) |
| Venta / Detalle | Cabecera de una operación de cobro y sus líneas de producto |
| Auditoría | Registro inmutable de acciones relevantes (usuario, acción, fecha, IP) |
| Sprint | Iteración de 2 semanas con entrega demostrable (4 sprints en el TP) |

---

## 2. Alcance

### 2.1 Dentro del alcance (Sprint 1 + Sprint 2)

| Bloque | Contenido |
|---|---|
| **Autenticación y roles** | Login/logout, registro público de cuentas, redirección por rol, denegación 403 server-side |
| **Gestión de usuarios** | Dashboard con métricas; listar con búsqueda y filtros; crear, editar, eliminar, activar/desactivar, asignar/quitar roles |
| **Catálogo de productos** | Modelos Categoría/Producto, alta de productos, lista con búsqueda |
| **Pantalla de cobro** | Acceso protegido (placeholder funcional con mock de escáner, base del Sprint 3) |
| **Auditoría** | Registro automático de login/logout con IP; registro de acciones CRUD de usuarios |
| **Experiencia de usuario** | Identidad visual "toldo de barrio", 3 estilos conmutables, modo oscuro, responsive, accesibilidad |

### 2.2 Fuera del alcance de este documento (Sprints 3 y 4)

Carrito con lector de código de barras, cobro efectivo/tarjeta con vuelto,
descuento de stock, cierre de turno, reportes de ventas y clientes frecuentes.
Se detallan como roadmap en la sección 9 y sus HU en el
[README](../README.md#alcance-de-sprint-3--la-caja-y-las-ventas-entrega-15-10).

### 2.3 Restricciones

- Entregas fijas: Sprint 1 (24-09), Sprint 2 (01-10), Sprint 3 (15-10),
  Sprint 4 (05-11).
- Aplicación **web** (navegador), sin app nativa; se usa en PC del kiosco y
  eventualmente en celular/tablet.
- Trabajo en equipo con merge a `main`; los artefactos deben poder integrarse
  sin romper los tests existentes.
- Idioma y formato argentinos: español rioplatense, moneda ARS, horario
  `America/Argentina/Buenos_Aires`.

---

## 3. Usuarios / personas

| Persona | Rol en el sistema | Qué necesita | Qué **no** debe ver |
|---|---|---|---|
| **Dueño / Administrador** | Grupo `Administrador` (o superuser) | Gestionar usuarios, cargar y consultar productos, ver reportes y auditoría | — (acceso total) |
| **Cajero** | Grupo `Cajero` | Entrar al sistema y usar la pantalla de cobro | Costos, precios de compra, reportes, administración de usuarios |
| **Usuario sin rol** | Autenticado sin grupo | Ver un aviso de que aún no tiene permisos | Cualquier pantalla operativa |
| **Público (no autenticado)** | — | Iniciar sesión o registrarse | Todo el resto (redirigido al login) |

---

## 4. Requerimientos funcionales

Prioridad: **M** = Must (imprescindible), **S** = Should, **C** = Could.
Estado: **Hecho** / **Parcial** / **Pendiente** (verificado contra el código el 24-09-2026).

### 4.1 Autenticación y control de acceso

| ID | Requerimiento | Prioridad | HU | Estado |
|---|---|---|---|---|
| RF-01 | Login con usuario y contraseña; error claro con credenciales inválidas | M | HU-01 | Hecho |
| RF-02 | Logout seguro (solo POST) que destruye la sesión | M | HU-01 | Hecho |
| RF-03 | Registro público de cuentas; el usuario nace **sin rol** | S | — | Hecho |
| RF-04 | Redirección post-login según rol: admin → dashboard, cajero → cobro, sin rol → aviso `sin_rol` | M | — | Hecho |
| RF-05 | Restricción **server-side** por rol: las URLs de administración devuelven 403 a un Cajero (no basta ocultar botones) | M | HU-02 | Hecho |
| RF-06 | El Administrador accede tanto al panel de administración como a la pantalla de cobro | M | HU-03 | Hecho |
| RF-07 | Todo acceso a pantallas operativas exige login (anónimos → redirect al login) | M | HU-01/02 | Hecho |

### 4.2 Gestión de usuarios (solo Administrador)

| ID | Requerimiento | Prioridad | Estado |
|---|---|---|---|
| RF-08 | Listar usuarios con búsqueda por nombre/usuario/email | M | Hecho |
| RF-09 | Filtrar la lista por estado (activo/inactivo) y por rol | S | Hecho |
| RF-10 | Crear usuario con contraseña y rol asignado | M | Hecho |
| RF-11 | Editar datos del usuario, con contraseña opcional | M | Hecho |
| RF-12 | Activar/desactivar usuarios sin borrar la cuenta | S | Hecho |
| RF-13 | Eliminar usuario con paso de confirmación | S | Hecho |
| RF-14 | Asignar/quitar roles (grupos) desde la interfaz | M | Hecho |
| RF-15 | Protecciones: no se puede eliminar ni desactivar la cuenta propia ni un superusuario | M | Hecho |
| RF-16 | Dashboard con métricas de usuarios (total, activos, inactivos, por rol, sin rol) | S | Hecho |
| RF-17 | Paginación de listados largos | C | Parcial (tag `{% paginacion %}` existe; aún no se usa en los templates) |

### 4.3 Catálogo de productos

| ID | Requerimiento | Prioridad | HU | Estado |
|---|---|---|---|---|
| RF-18 | Modelos de Categoría y Producto con precio, stock y estado activo | M | HU-04 | Hecho |
| RF-19 | Alta de producto desde la interfaz, con creación inline de categoría nueva | M | HU-04 | Parcial (view y URL existen; **faltan los templates** → la ruta devuelve 500) |
| RF-20 | Lista de productos con búsqueda por nombre o descripción | M | HU-05 | Parcial (idem: falta el template) |
| RF-21 | Código de barras con validación de duplicado (error si ya existe) | M | HU-04 | Pendiente |
| RF-22 | Precio de costo y precio de venta separados | M | HU-04 | Pendiente |
| RF-23 | Stock mínimo por producto | S | HU-04 | Pendiente |
| RF-24 | Búsqueda en tiempo real sin recarga (HTMX) | S | HU-05 | Pendiente (hoy es GET con recarga) |
| RF-25 | Marca de color en productos con stock ≤ 5 | S | HU-06 | Pendiente |
| RF-26 | Edición y baja de productos desde la interfaz (hoy solo vía Django admin) | M | HU-05 | Pendiente |

### 4.4 Pantalla de cobro (base para Sprint 3)

| ID | Requerimiento | Prioridad | HU | Estado |
|---|---|---|---|---|
| RF-27 | Pantalla de cobro accesible solo con login (Cajero y Administrador) | M | HU-07 | Hecho (placeholder) |
| RF-28 | Modelos `Venta` y `DetalleVenta` como base del carrito (fecha, total, cantidad, precio unitario, `subtotal()`) | M | HU-07/08 | Hecho (sin lógica de negocio todavía) |
| RF-29 | Lugar reservado en la UI para el lector de código de barras (mock visible) | S | HU-07 | Hecho (mock) |
| RF-30 | Carga de productos al carrito, edición de cantidades, cobro con vuelto y descuento de stock | M | HU-07/08/09 | Pendiente (Sprint 3) |

### 4.5 Auditoría

| ID | Requerimiento | Prioridad | Estado |
|---|---|---|---|
| RF-31 | Registro automático de login y logout con usuario, acción, fecha e IP | M | Hecho |
| RF-32 | Registro de acciones de administración (crear/editar/eliminar/asignar rol/toggle de usuarios) | S | Hecho |
| RF-33 | Registros de solo lectura (no editables ni eliminables desde la interfaz) | M | Hecho (admin de Django en solo lectura) |
| RF-34 | Interfaz propia para consultar la auditoría | C | Pendiente (hasta ahora solo vía Django admin) |

### 4.6 Experiencia de usuario y presentación

| ID | Requerimiento | Prioridad | Estado |
|---|---|---|---|
| RF-35 | Identidad visual propia ("toldo de barrio"), coherente en todas las pantallas | S | Hecho |
| RF-36 | 3 estilos conmutables (Cartelera, Ticket, Neón) persistidos por navegador | C | Hecho |
| RF-37 | Modo oscuro persistente, sin destello al cargar, respetando `prefers-color-scheme` | C | Hecho |
| RF-38 | Diseño responsive (PC, celular) | S | Hecho |
| RF-39 | Accesibilidad: contraste AA, navegación por teclado (`focus-visible`), `prefers-reduced-motion`, `aria-label` en controles de tema | S | Hecho |
| RF-40 | Páginas de error amigables 403 y 404 | S | Hecho |

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
| RNF-07 | Disponibilidad | Idempotencia del seed de datos (`setup_inicial`) para poder reejecutarlo sin romper el entorno |
| RNF-08 | Rendimiento | Respuesta interactiva en operaciones CRUD y búsquedas sobre tablas de escala de kiosco (cientos de productos, decenas de usuarios) |
| RNF-09 | Mantenibilidad | Suite de tests automatizados verde antes de cada entrega (**35 tests** hoy) |
| RNF-10 | Mantenibilidad | Convención de nombres y comentarios en español; estructura de apps por dominio |
| RNF-11 | Portabilidad | Corre en Windows con Python 3.10+; PostgreSQL principal con fallback automático a SQLite |
| RNF-12 | Localización | Español rioplatense (`es-ar`), huso horario Argentina, formato de fecha/hora local |
| RNF-13 | Usabilidad | Cada pantalla operativa accesible en ≤ 2 clics desde el menú según rol |
| RNF-14 | Compatibilidad | Navegadores modernos con soporte de CSS custom properties y `localStorage` (Chrome/Edge/Firefox) |

---

## 6. Historias de usuario y criterios de aceptación

### Sprint 1 (Entrega 24-09) — **Completo**

**HU-01 — Login del sistema**
Como usuario del sistema (dueño o cajero), quiero ingresar con usuario y
contraseña para que solo personal autorizado pueda operar el kiosco.
- CA: con credenciales válidas se ingresa al sistema; con inválidas se muestra
  error y no se ingresa.
- *Estado: Hecho (`usuarios/tests.py`, 9 tests).*

**HU-02 — Separación de roles: Cajero**
Como dueño, quiero que el cajero solo pueda ver la pantalla de cobro, para que
no tenga acceso a costos, precios ni reportes del negocio.
- CA: un usuario del grupo *Cajero* que accede a una URL de administración
  recibe "Acceso denegado" (403), y accede sin problemas a la pantalla de cobro.
- *Estado: Hecho. **Excepción:** las rutas de productos de `/ventas/` hoy solo
  exigen login (ver riesgo R-03).*

**HU-03 — Separación de roles: Administrador**
Como dueño, quiero tener un usuario administrador con acceso total, para
manejar yo mismo la parte sensible del negocio.
- CA: el grupo *Administrador* accede al panel de administración y a la
  pantalla de cobro.
- *Estado: Hecho.*

### Sprint 2 (Entrega 01-10) — **En progreso**

**HU-04 — Alta rápida de productos**
Como administrador, quiero cargar un producto nuevo ingresando nombre, código
de barras, precio de costo, precio de venta y stock, para tener el catálogo
actualizado.
- CA: si el código de barras ya existe, el sistema muestra un error y no
  permite el duplicado.
- *Estado: Parcial. Hay alta de producto con categoría, pero **faltan** código
  de barras, precios de costo/venta separados, stock mínimo y el control de
  duplicado; y **faltan los templates** (RF-19/RF-21/RF-22).*

**HU-05 — Lista de productos con búsqueda**
Como administrador, quiero una lista donde pueda buscar cualquier producto por
nombre o código para modificarle el precio o corregir el stock.
- CA: la búsqueda filtra en tiempo real (HTMX).
- *Estado: Parcial. La búsqueda por nombre/descripción existe en la view pero
  falta el template y la búsqueda en tiempo real (RF-20/RF-24/RF-26).*

**HU-06 — Alerta de stock bajo**
Como administrador, quiero que el sistema me marque en color los productos que
se están quedando sin stock, para saber qué tengo que salir a reponer.
- CA: productos con stock ≤ 5 se muestran marcados.
- *Estado: Pendiente (RF-25).*

### Sprints 3 y 4 — fuera de este alcance

Ver [README → Alcance de Sprint 3](../README.md#alcance-de-sprint-3--la-caja-y-las-ventas-entrega-15-10)
(HU-07 a HU-09) y [Alcance de Sprint 4](../README.md#alcance-de-sprint-4--cierres-y-saber-qué-se-vende-entrega-05-11)
(HU-10 a HU-12).

---

## 7. Flujo principal del producto

1. El usuario entra a `/` y es redirigido al login (o a `post_login` si ya
   tiene sesión).
2. Se autentica; el sistema detecta su rol:
   - **Administrador** → dashboard con métricas y acceso a gestión de usuarios
     y catálogo.
   - **Cajero** → pantalla de cobro.
   - **Sin rol** → aviso de que un administrador debe asignarle uno.
3. El administrador carga/consulta productos y gestiona usuarios; cada acción
   sensible queda auditada.
4. El cajero opera la pantalla de cobro (hoy placeholder; Sprint 3: carrito,
   escaneo y cobro).
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
- [ ] UI responsive con los tokens/estilos del proyecto (3 estilos + dark).
- [ ] Comentarios y nombres en español; documentación (README/backlog) actualizada.
- [ ] Sin regresiones en las funcionalidades ya entregadas.

**Criterios de aceptación del Sprint 2:**

- Cargar un producto nuevo desde la interfaz sin usar el Django admin.
- Buscar un producto por nombre y ver solo los coincidentes.
- Un Cajero sigue sin poder entrar a `/administracion/` (403).
- Los 35 tests actuales siguen en verde y se suman los nuevos.

---

## 9. Roadmap (fuera de alcance actual)

| Sprint | Entrega | Contenido | HU |
|---|---|---|---|
| 3 | 15-10 | Carrito con lector de código de barras, edición de carrito, cobro efectivo/tarjeta con vuelto, descuento de stock | HU-07, HU-08, HU-09 |
| 4 | 05-11 | Cierre de turno con totales por método, reporte top 10 de productos, clientes frecuentes (opcional) | HU-10, HU-11, HU-12 |

---

## 10. Supuestos, riesgos y dependencias

| ID | Tipo | Descripción | Impacto | Mitigación |
|---|---|---|---|---|
| R-01 | Riesgo | Faltan `templates/ventas/lista_productos.html` y `agregar_producto.html`: `/ventas/productos/` y `/ventas/productos/agregar/` devuelven 500 | Alto — bloquea HU-04/05 | Crear los dos templates antes del 01-10 |
| R-02 | Riesgo | `toggle_usuario` cambia estado por **GET** (sin POST/CSRF) | Medio — seguridad | Convertir a POST con token en el Sprint 2 |
| R-03 | Riesgo | Las rutas de `/ventas/` solo exigen login, no rol: un Cajero podría dar de alta productos | Alto — contradice HU-02 | Aplicar `@rol_requerido("Administrador")` a catálogo |
| R-04 | Riesgo | `Venta` no registra método de pago ni cajero responsable | Medio — bloquea HU-09/10 | Agregar campos en Sprint 3 |
| R-05 | Riesgo | La búsqueda no está en tiempo real y la paginación no se usa en templates | Bajo | Implementar con HTMX + tag `{% paginacion %}` |
| R-06 | Riesgo | `SECRET_KEY` hardcodeada, `DEBUG=True` fijo y `ALLOWED_HOSTS` vacío | Alto si se despliega | Mover a `.env` antes de cualquier puesta en producción |
| R-07 | Supuesto | Los usuarios de prueba (`admin`/`cajero1`, contraseña `kiosco2024`) son solo para desarrollo | — | No usar en producción; rotar credenciales |
| R-08 | Supuesto | El local dispone de PC con navegador moderno y conexión local al servidor | — | Fallback a SQLite para demo sin PostgreSQL |
| D-01 | Dependencia | Consignas/entregas del TP con fechas fijas por sprint | — | Priorizar bloqueantes de cada sprint primero |

---

## 11. Criterios de éxito y métricas

| Métrica | Objetivo | Valor al 24-09-2026 |
|---|---|---|
| Tests automatizados en verde | 100% de la suite | 35/35 OK |
| Historias del Sprint 1 cerradas | 3/3 | 3/3 |
| Historias del Sprint 2 cerradas | 3/3 al 01-10 | 0/3 (2 parciales, 1 pendiente) |
| Rutas críticas protegidas por rol | 100% | Administración protegida; `/ventas/` con rol pendiente (R-03) |
| Bloqueantes del Sprint 2 | 0 al entregar | 2 abiertos (R-01, R-03) |

---

## 12. Historial de versiones

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0 | 24/09/2026 | Versión inicial del PRD (alcance Sprint 1 + 2) |
