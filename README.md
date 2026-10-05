# Sistema Kiosco

Trabajo práctico de Metodologías Ágiles. Sistema web de gestión para un kiosco de barrio.

**Estado al 05-10-2026:** Sprint 1 completo · Sprint 2 completo (catálogo de
productos) · Sprint 3 completo (caja y cobro) · reportes de ventas y stock ·
estilo neón cian único · 148 tests en verde.

---

## Documentación

| Documento | Contenido |
|---|---|
| [docs/PRD.md](docs/PRD.md) | Documento de Requerimientos de Producto (v2.1): alcance, personas, requerimientos funcionales (RF-01…RF-51) y no funcionales, historias de usuario con criterios de aceptación, riesgos y métricas. |
| [docs/ARD.md](docs/ARD.md) | Arquitectura y Requerimientos Técnicos (v2.1): stack, diagramas (flujo y modelo de datos), endpoints, autorización, auditoría, 12 mini-ADRs y calidad. |

Ambos documentos describen el estado del producto al **Sprint 3 cerrado +
reportes entregados** (fecha de versión 05-10-2026, código `60e490b` + cambios
de Sprint 3 sin commitear) y son el entregable de documentación del trabajo
práctico.

---

## Estado actual del trabajo

### Seguridad y roles (Sprint 1) — completo

- Login/logout con Django Authentication, roles vía Django Groups
  (`Administrador`, `Cajero`) y restricción server-side con `@rol_requerido` (403).
- Redirección post-login por rol (`post_login`) y aviso `sin_rol` para usuarios sin grupo.
- Registro público de cuentas en `/usuarios/registro/`: nace **sin rol** y cae en
  `sin_rol` hasta que un administrador le asigne uno.
- Auditoría automática de login/logout con IP (`auditoria/`).

### Productos y catálogo (Sprint 2) — completo

- Modelos **Categoria**, **Producto**, **Venta** y **DetalleVenta** creados y migrados
  (`0001_initial.py`, `0002_...costo...` con `Producto.costo` y
  `0003_...` con `codigo_barras` y `stock_minimo`), registrados en el admin de
  Django (Venta con inline de detalles).
- **HU-04 — alta rápida:** `ventas/forms.py::ProductoForm` con nombre, código de
  barras, descripción, costo, precio de venta, stock, stock mínimo y categoría
  (con "categoría nueva"). El código de barras **no se permite duplicado**
  (`clean_codigo_barras`).
- **CRUD completo:** alta, edición (`productos/<id>/editar/`) y **baja lógica**
  (`productos/<id>/eliminar/` → `activo=False`, se puede reactivar desde editar).
- **HU-05 — búsqueda en tiempo real con HTMX:** el input dispara
  `hx-get /ventas/productos/` cada 300 ms y la vista responde solo con el
  partial `ventas/_productos_tabla.html` (sin recargar la página).
- **HU-06 — alerta de stock:** `Producto.stock_bajo` (stock ≤ `stock_minimo`,
  configurable por producto) y badge `.badge-stock-bajo` en la tabla.
- **Seguridad:** las 4 vistas del catálogo usan `@rol_requerido("Administrador")`
  → el cajero recibe 403 (no ve costos ni precios).

### Reportes (Sprint 4) — completo

- `/administracion/reportes/ventas/`: resumen (cantidad, ingresos, costo,
  ganancia, ticket promedio, margen %), serie de 14 días, top 10 de productos,
  más rentables.
- `/administracion/reportes/stock/`: inventario valorado a costo y a venta,
  stock bajo (≤5), sin stock, por categoría y productos con margen bajo.
- Protegidos con `@rol_requerido("Administrador")` → el cajero recibe 403.
- 57 tests en `administracion/tests_reportes.py`.

### Gestión de usuarios — completo

- CRUD de usuarios para el administrador: listar (búsqueda por nombre/usuario, filtro
  por rol, paginación), crear, editar, eliminar, activar/desactivar y asignar roles,
  con protecciones (no puede desactivar/eliminar superusuarios ni su propia cuenta).
- 22 tests de `administracion` cubren todo el flujo.

### Pantalla de cobro (Sprint 3) — completo

- **HU-07 — carrito con lector:** input escáner con mock; al escanear o tipear
  un código y apretar Enter, `ventas/services.py::buscar_producto` lo resuelve
  (código exacto → nombre único → aviso si es ambiguo) y `cobro_agregar` lo
  suma al carrito (`session["carrito"]`); repetir el mismo producto suma
  cantidad en vez de duplicar la fila. **Búsqueda en tiempo real:** desde
  3 letras/carácteres, `cobro_buscar` sugiere productos en `_cobro_resultados.html`
  y un clic los agrega.
- **HU-08 — edición:** botones de sumar/restar/quitar por ítem
  (`cobro_cantidad`, HTMX) que reemplazan el partial `_carrito.html` y
  recalculan el total en cada request.
- **HU-09 — cobro:** método de pago efectivo/tarjeta, monto entregado con
  preview de vuelto, botones de billetes (100/200/500/1000/2000) y "pago
  exacto"; `confirmar_venta` crea la `Venta` en una transacción con
  `select_for_update`, congela precios, descuenta stock con `F()`, guarda
  `metodo_pago`, `usuario`, `monto_entregado` y `vuelto`, audita la operación
  y muestra el comprobante (`/ventas/cobro/?venta=<id>`).
- Migración `0004_...` sobre `Venta`. 38 tests nuevos en `ventas/tests.py`
  (60 en total para la app).

### Frontend — rediseño completo

- Identidad visual "toldo de barrio" con **un solo estilo: Neón cian** (fijo),
  más modo oscuro. Las paletas Cartelera y Ticket se eliminaron; detalle en
  [Decisiones técnicas → Frontend](#frontend) y
  [Estilo visual](#estilo-visual).

### Tests

- **148 tests OK** (`python manage.py test`): `usuarios` 9, `ventas` 60,
  `administracion` 22 + 57 de reportes.

---

## Alcance de Sprint 1 — Seguridad y roles (Entrega 24-09)

> "Necesito poder entrar al sistema con mi usuario y contraseña, y que los
> empleados (los cajeros) solo puedan usar la pantalla de cobro y no entren
> a tocar la parte de administración o precios."

**Estado:** completo.

### Historias de usuario

**HU-01 — Login del sistema**
Como usuario del sistema (dueño o cajero), quiero ingresar con usuario y
contraseña para que solo personal autorizado pueda operar el kiosco.
- Criterio de aceptación: con credenciales válidas se ingresa al sistema;
  con credenciales inválidas se muestra un error y no se ingresa.
- *Estado: ✅ Hecho.*

**HU-02 — Separación de roles: Cajero**
Como dueño, quiero que el cajero solo pueda ver la pantalla de cobro, para
que no tenga acceso a costos, precios ni reportes del negocio.
- Criterio de aceptación: un usuario del grupo *Cajero* que intenta acceder
  a una URL de administración recibe "Acceso denegado" (403), y accede sin
  problemas a la pantalla de cobro.
- *Estado: ✅ Hecho.*

**HU-03 — Separación de roles: Administrador**
Como dueño, quiero tener un usuario administrador con acceso total, para
manejar yo mismo la parte sensible del negocio (desde el local o de forma
remota).
- Criterio de aceptación: un usuario del grupo *Administrador* accede tanto
  al panel de administración como a la pantalla de cobro.
- *Estado: ✅ Hecho.*

### Qué se implementó

- Login con usuario y contraseña (Django Authentication).
- Roles basados en Django Groups: "Administrador" y "Cajero".
- Restricción server-side por decorador (`usuarios/decorators.py`): el cajero
  que escribe la URL a mano recibe 403, no solo se le oculta el botón.
- Redirección post-login por rol: cajero va directo a cobro, admin al dashboard.
- Pantallas protegidas por login/roles para cobro y administración.

---

## Alcance de Sprint 2 — Cargar y ordenar los productos (Entrega 01-10)

> "Poder cargar los productos nuevos uno tras otro rápido, poniéndoles el
> nombre, el código de barras, cuánto me costó, a cuánto lo vendo y cuántos
> tengo. Si el código ya existe, avísame."

**Estado:** completo (HU-04, HU-05 y HU-06 implementadas y testeadas).

### Historias de usuario

**HU-04 — Alta rápida de productos**
Como administrador, quiero cargar un producto nuevo ingresando nombre,
código de barras, precio de costo, precio de venta y stock, para tener el
catálogo actualizado.
- Criterio de aceptación: si el código de barras ya existe, el sistema
  muestra un error y no permite el duplicado.
- *Estado: ✅ Hecho.*

**HU-05 — Lista de productos con búsqueda**
Como administrador, quiero una lista donde pueda buscar cualquier producto
por nombre o código para modificarle el precio o corregir el stock.
- Criterio de aceptación: la búsqueda filtra en tiempo real (HTMX).
- *Estado: ✅ Hecho.*

**HU-06 — Alerta de stock bajo**
Como administrador, quiero que el sistema me marque en color los productos
que se están quedando sin stock, para saber qué tengo que salir a reponer.
- Criterio de aceptación: productos con stock ≤ 5 se muestran marcados.
- *Estado: ✅ Hecho.*

### Modelos (implementados)

- **Categoria**: nombre, descripción.
- **Producto**: nombre, descripción, precio de venta, **costo** (solo lo ve el
  administrador), stock, stock mínimo, código de barras (único), categoría
  (FK), activo.
- **Venta**: fecha/hora, total, finalizada.
- **DetalleVenta**: venta, producto, cantidad, precio unitario,
  **costo_unitario**, `subtotal()`, `costo_total()`, `ganancia()`.

---

## Alcance de Sprint 3 — La caja y las ventas (Entrega 15-10)

> "Cuando esté en la pantalla del cajero, quiero pasar el lector de código de
> barras o tipear el código, apretar Enter y que el producto se cargue al
> toque en el carrito sin tener que usar el mouse."

**Estado:** completo (HU-07, HU-08 y HU-09 implementadas y testeadas; cerrado
el 05-10, diez días antes de la entrega del 15-10).

### Historias de usuario

**HU-07 — Carga rápida de productos al carrito**
Como cajero, quiero escanear o tipear un código de barras y que el producto
se agregue al carrito de inmediato.
- Criterio de aceptación: si escaneo el mismo producto dos veces, se suma
  la cantidad (2) en vez de crear una fila duplicada.
- *Estado: ✅ Hecho.*

**HU-08 — Editar carrito antes de cobrar**
Como cajero, quiero poder borrar un producto del carrito o cambiar la
cantidad antes de confirmar la venta.
- Criterio de aceptación: el total se recalcula al modificar el carrito.
- *Estado: ✅ Hecho.*

**HU-09 — Cobro con efectivo o tarjeta**
Como cajero, quiero indicar si el cliente paga en efectivo o tarjeta,
ingresar el monto entregado y que el sistema calcule el vuelto exacto.
- Criterio de aceptación: el stock se descuenta automáticamente al
  confirmar la venta.
- *Estado: ✅ Hecho.*

### Cómo está implementado

- **Carrito en la sesión** (`request.session["carrito"]`), no en la base de
  datos: no quedan ventas "a medias" que ensucien los reportes (ADN-11 del ARD).
- **`ventas/services.py`**: `buscar_producto`, `agregar_al_carrito`,
  `modificar_cantidad`, `total_del_carrito` y `confirmar_venta`
  (transacción + `select_for_update` + descuento de stock).
- **Endpoints HTMX**: `/ventas/cobro/agregar/`, `/ventas/cobro/cantidad/` y
  `/ventas/cobro/confirmar/` responden el partial `_carrito.html`;
  `/ventas/cobro/buscar/` responde las sugerencias del escáner
  (`_cobro_resultados.html`) desde 3 caracteres.
- **`Venta` ampliada** (migración `0004`): `metodo_pago` (efectivo/tarjeta),
  `usuario` (cajero responsable, `SET_NULL`), `monto_entregado` y `vuelto`.
- **Auditoría**: cada venta confirmada se registra con
  `registrar_accion()`, y el comprobante es visible solo para quien la cobró
  o para un administrador (403 si no).

---

## Alcance de Sprint 4 — Cierres y saber qué se vende (Entrega 05-11)

> "Cuando termina el turno o el día, quiero apretar un botón y que me tire
> el total de plata que entró en efectivo, en tarjeta y cuántas ventas hice."

**Estado:** en progreso — **HU-11 (reporte top 10) hecha** con
`administracion/reportes.py`; faltan HU-10 (cierre de turno) y HU-12
(clientes).

### Historias de usuario

**HU-10 — Cierre de turno**
Como cajero, quiero cerrar mi turno y que el sistema me muestre el total
en efectivo, en tarjeta y la cantidad de operaciones realizadas, para poder
contar la plata de la caja.
- Criterio de aceptación: se registra qué usuario estaba a cargo del turno.

**HU-11 — Reporte de productos más vendidos**
Como administrador, quiero ver un reporte de los productos más vendidos,
para no quedarme sin mercadería de lo que más sale.
- Criterio de aceptación: el reporte muestra el top 10 de productos por
  cantidad vendida en un período seleccionable.
- *Estado: ✅ Hecho.*

**HU-12 — Clientes frecuentes (opcional)**
Como administrador, quiero poder registrar clientes con nombre y CUIT/DNI,
para que el cajero pueda asociar una venta a un cliente cuando lo solicite
(sin interrumpir el flujo del consumidor final).
- Criterio de aceptación: el cajero busca por CUIT y trae los datos
  automáticamente; si es nuevo, lo carga en una ventanita rápida.

---

## Decisiones técnicas

### Backend

- **Base de datos**: PostgreSQL como base de datos principal del proyecto.
  Se utiliza `django-environ` para leer la variable `DATABASE_URL` desde un
  archivo `.env` (no subido al repo por seguridad). Si no se define la
  variable, el sistema cae automáticamente a SQLite para desarrollo local
  sin configuración extra.

- **Roles con Django Groups**, no con permisos sueltos: el pedido de este
  sprint es binario ("cajero solo ve cobro"), no hay todavía acciones finas
  para diferenciar (ej. "puede ver stock pero no editar precio"). Eso se
  resuelve más adelante con `django.contrib.auth.models.Permission` sobre
  cada modelo, cuando exista el modelo de Producto.

- **Restricción por decorador (`usuarios/decorators.py`)**: `rol_requerido`
  para vistas de función y `RolRequeridoMixin` para vistas basadas en clase
  (se va a necesitar en el sprint de stock con `ListView`/`CreateView`).
  El cajero no solo "no ve el botón": si escribe la URL a mano, el servidor
  le devuelve 403. Es un requisito de seguridad real, no solo de UI.

- **Redirección post-login por rol** (`usuarios/views.py::post_login`): cada
  usuario cae directo en su pantalla (cajero → cobro, admin → dashboard),
  para no exponer un menú con opciones que no le corresponden.

- **Auditoría con señales**: `user_logged_in` / `user_logged_out` crean un
  `RegistroAuditoria` (usuario, acción, fecha, IP) sin tocar las vistas de
  login.

- **Carrito en la sesión, venta al confirmar** (Sprint 3): el carrito es una
  lista en `request.session["carrito"]`; la `Venta` recién se crea en
  `services.confirmar_venta()` dentro de una transacción (con
  `select_for_update` y descuento de stock con `F()`), de modo que nunca
  queda una venta parcial que contaminaría los reportes.

### Frontend

<a id="frontend"></a>

- **Bootstrap 5.3.3 + Bootstrap Icons** vía CDN como framework de utilidades.
- **CSS custom** (`static/css/styles.css`, ~3.200 líneas) con design tokens vía
  CSS custom properties (`:root` + variantes). La paleta, tipografía, radios y
  sombras se definen una vez y se reutilizan en todas las páginas.
- **Identidad "toldo de barrio"**: rotulación de kiosco argentino — contorno
  de tinta + sombra dura, etiquetas de precio adhesivas, código de barras como
  gráfico temático, códigos de error grandes (403/404) y filete de toldo en el
  navbar. Tipografía display **Righteous** + interfaz **Space Grotesk**.
- **Un solo estilo visual: Neón cian** (ver sección siguiente): paleta cian
  `#00C8E0` sobre azul profundo `#081822`, con glow y grilla de piso. Las
  paletas Cartelera y Ticket fueron eliminadas del CSS y el botón de selector
  de estilo se retiró del navbar y del login.
- **Modo oscuro** persistente (`data-theme="dark"`) en el estilo neón.
- **Componentes custom**: `kiosco-navbar`, badges de rol, `btn-kiosco`,
  `kiosco-input`, `kiosco-alert`, `placeholder-page`, `error-page`,
  `warning-page`, mock de escáner en cobro, `sello` y banner `viene`.
- **CSS heredado del equipo**: al hacer el merge con `main` se integraron los
  bloques *Auth pages* (login/registro) y *Admin Panel* (dashboard y gestión
  de usuarios) con un shim de aliases (`--surface`, `--radius-*`,
  `--kiosco-yellow`, …) para que usen los tokens del rediseño.
- **Accesibilidad**: contraste AA, `focus-visible` para teclado,
  `prefers-reduced-motion` respetado, `aria-label` en los botones de tema.
- **Responsive**: en mobile el navbar oculta el nombre de usuario y mantiene
  badges y salida; el login pasa a panel único bajo 900px.
- **HTMX** (CDN en `base.html`) se usa en la búsqueda del catálogo de
  productos y en las acciones del carrito del cobro; el token CSRF se envía
  globalmente con `hx-headers`.

---

## Cómo correr el proyecto

### Requisitos previos

- Python 3.10+
- PostgreSQL instalado y corriendo (**opcional**: sin `DATABASE_URL` el
  proyecto usa SQLite automáticamente)

### Instalación

Abrí una terminal en VSCode (menú Terminal > New Terminal) y ejecutá los
siguientes comandos **uno por uno**:

```powershell
# 1. Entrar a la carpeta del proyecto
cd "C:\Users\TU_USUARIO\Desktop\UNAB\2026 SEGUNDO CUATRI\METODOLOGIAS AGILES\TP\kiosco_sprint1"

# 2. Crear el entorno virtual (una sola vez)
python -m venv venv

# 3. Activar el entorno virtual
.\venv\Scripts\Activate.ps1

# 4. Instalar las dependencias (una sola vez)
pip install -r requirements.txt

# 5. Crear la base de datos en PostgreSQL (solo si vas a usar PostgreSQL)
#    Abrí psql (o pgAdmin) y ejecutá:
#    CREATE DATABASE db_kiosco;

# 6. Configurar la conexión en el archivo .env (ver sección siguiente)

# 7. Crear las tablas de la base de datos (una sola vez)
python manage.py migrate

# 8. Crear los grupos y usuarios de prueba (una sola vez)
python manage.py setup_inicial

# 9. Levantar el servidor de desarrollo
python manage.py runserver 8001
```

Abrí `http://127.0.0.1:8001/` en el navegador.

> **Nota:** los pasos 2, 4, 5, 6, 7 y 8 solo se hacen la **primera vez**.
> Después de eso, solo necesitás activar el entorno (paso 3) y levantar
> el servidor (paso 9).

### Archivo .env

El proyecto usa `django-environ` para leer la configuración de base de datos
desde un archivo `.env` en la raíz del proyecto (no hay `.env.example` en el
repo: crealo a mano).

```
DATABASE_URL=postgresql://postgres:1234@localhost:5432/db_kiosco
```

Formato: `postgresql://USUARIO:CONTRASEÑA@HOST:PUERTO/NOMBRE_DB`

> **Importante:** el archivo `.env` está en `.gitignore` y **nunca** se sube
> al repositorio (contiene contraseñas). Si no se define `DATABASE_URL`, el
> sistema usa SQLite automáticamente como fallback.

### Usuarios de prueba (creados por `setup_inicial`)

| Usuario   | Contraseña   | Rol            |
|-----------|--------------|----------------|
| `admin`   | `kiosco2024` | Administrador  |
| `cajero1` | `kiosco2024` | Cajero         |

## Correr los tests

Con el entorno virtual activado:

```powershell
python manage.py test
```

**148 tests** actualmente:

- **`usuarios/tests.py` (9)**: login correcto e incorrecto, acceso anónimo
  bloqueado, cajero bloqueado en administración, administrador con acceso
  total, y la redirección post-login según rol.
- **`ventas/tests.py` (60)**: pantalla de cobro (login, cajero, admin,
  template) + catálogo (acceso 403 para el cajero en las 4 vistas, alta con
  costo y código, código duplicado rechazado, precio 0 rechazado, categoría
  nueva, edición, baja lógica, búsqueda por nombre/código, respuesta HTMX con
  partial y alerta de stock bajo) + **Sprint 3** (carrito: agregar por
  código, duplicado suma cantidad, sumar/restar/quitar y total; cobro:
  efectivo con vuelto, pago exacto, tarjeta, stock insuficiente, auditoría de
  la venta; comprobante: formato de pesos y 403 para ventas ajenas; búsqueda
  en tiempo real del escáner desde 3 caracteres).
- **`administracion/tests.py` (22)**: dashboard (login, admin, 403 cajero,
  403 sin grupo, estadísticas) y CRUD de usuarios (listar con búsqueda y
  filtro por rol, crear, editar, eliminar con protección de superusuarios,
  activar/desactivar, asignar/quitar roles).
- **`administracion/tests_reportes.py` (57)**: resumen de ventas, serie
  diaria, top 10, productos rentables, stock valorado, stock por categoría,
  margen bajo, propiedades de `Producto`/`DetalleVenta` y las vistas de
  reportes (incluye 403 para el cajero).

## Estructura del proyecto

```
kiosco_sprint1/
│
├── manage.py                         # Punto de entrada de Django.
├── requirements.txt                  # Django 6.1.1, psycopg2-binary,
│                                     # django-environ.
├── README.md                         # Este archivo.
├── AGENTS.md                         # Instrucciones para agentes IA.
├── docs/
│   ├── PRD.md                        # Requerimientos de producto (v2.1).
│   └── ARD.md                        # Arquitectura y requerimientos técnicos.
├── .env                              # DATABASE_URL (no se sube al repo).
├── .gitignore                        # __pycache__, venv/, db.sqlite3, .env…
│
├── config/                           # Configuración del proyecto Django.
│   ├── settings.py                   # BD (PostgreSQL via .env con fallback a
│   │                                 # SQLite), apps, LOGIN_URL, es-ar,
│   │                                 # America/Argentina/Buenos_Aires.
│   ├── urls.py                       # Raíz: admin/, / → post_login, includes
│   │                                 # de usuarios/ventas/administracion,
│   │                                 # handler404.
│   ├── wsgi.py / asgi.py             # Puntos de entrada WSGI/ASGI.
│
├── usuarios/                         # Autenticación y control de acceso.
│   ├── views.py                      # LoginKioscoView, registro_usuario
│   │                                 # (cuenta sin rol), post_login (según
│   │                                 # rol), sin_rol.
│   ├── urls.py                       # 5 rutas: login/, logout/, post-login/,
│   │                                 # sin-rol/, registro/.
│   ├── forms.py                      # LoginKioscoForm y RegistroUsuarioForm
│   │                                 # (widgets kiosco-input).
│   ├── decorators.py                 # @rol_requerido, RolRequeridoMixin,
│   │                                 # es_administrador(), es_cajero().
│   ├── tests.py                      # 9 tests.
│   ├── templatetags/
│   │   └── pagination_tags.py        # {% paginacion %} (inclusion tag) y
│   │                                 # {% param %} (preserva query params).
│   └── management/commands/
│       └── setup_inicial.py          # Crea grupos + usuarios de prueba.
│                                     # Idempotente.
│
├── ventas/                           # Productos y pantalla de cobro (POS).
│   ├── models.py                     # Categoria, Producto, Venta (método de
│   │                                 # pago, cajero, vuelto), DetalleVenta.
│   ├── services.py                   # Carrito en sesión + confirmar_venta
│   │                                 # (transacción, stock, precios HU-09).
│   ├── views.py                      # pantalla_cobro + cobro_agregar /
│   │                                 # cobro_cantidad / cobro_confirmar (HTMX),
│   │                                 # lista_productos y CRUD de productos
│   │                                 # (@rol_requerido Administrador).
│   ├── forms.py                      # ProductoForm (HU-04): código de barras
│   │                                 # sin duplicados, costo, precio, stock,
│   │                                 # stock_minimo y categoría.
│   ├── urls.py                       # 10 rutas: 5 de cobro/ y 5 de productos/.
│   ├── admin.py                      # Venta (inline DetalleVenta), Producto,
│   │                                 # Categoria.
│   ├── tests.py                      # 60 tests.
│   └── migrations/                   # 0001 catálogo/ventas, 0002 costo,
│                                     # 0003 código de barras + stock mínimo,
│                                     # 0004 campos de cobro de la Venta.
│
├── administracion/                   # Panel del dueño.
│   ├── views.py                      # dashboard (stats de usuarios), CRUD:
│   │                                 # listar, crear, editar, eliminar,
│   │                                 # asignar_roles, toggle_usuario, y las
│   │                                 # vistas de reportes (solo admin).
│   ├── reportes.py                   # Resúmenes de ventas y stock: ingresos,
│   │                                 # ganancia, ticket promedio, top 10,
│   │                                 # stock valorado, por categoría, margen.
│   ├── urls.py                       # 9 rutas bajo /administracion/
│   │                                 # (7 de usuarios + 2 de reportes).
│   ├── forms.py                      # UsuarioForm (alta/edición con
│   │                                 # contraseña opcional al editar) y
│   │                                 # AsignarRolForm (checkboxes de grupos).
│   ├── tests.py                      # 22 tests.
│   ├── tests_reportes.py             # 57 tests.
│   └── templates → ../templates/administracion/ (8 templates).
│
├── auditoria/                        # Logs de auditoría.
│   ├── models.py                     # RegistroAuditoria: usuario, acción,
│   │                                 # detalle, fecha, IP.
│   ├── signals.py                    # user_logged_in/out → crea registro.
│   ├── utils.py                      # registrar_login/logout/accion(),
│   │                                 # _obtener_ip().
│   ├── admin.py                      # Solo lectura en el admin de Django.
│   └── migrations/0001_initial.py
│
├── templates/                        # Django Template Language.
│   ├── base.html                     # Layout: Google Fonts + Bootstrap CDN,
│   │                                 # navbar (marca, usuario, badges, botón
│   │                                 # oscuro, salir), bloque de messages,
│   │                                 # scripts de tema y de estilo neón.
│   ├── 403.html / 404.html           # error-page con código grande.
│   ├── usuarios/
│   │   ├── login.html                # login-split: toldo a la izquierda +
│   │   │                             # panel de ingreso a la derecha.
│   │   ├── registro.html             # auth-card de alta de cuenta.
│   │   ├── sin_rol.html              # warning-page sin grupo asignado.
│   │   └── tags/                     # Partiales de paginación y buscador.
│   ├── ventas/
│   │   ├── pantalla_cobro.html       # POS: escáner, carrito, pago (HU-07…09).
│   │   ├── _carrito.html             # Partial HTMX del carrito y form de pago.
│   │   ├── _cobro_resultados.html    # Sugerencias del escáner (≥3 caracteres).
│   │   ├── lista_productos.html      # Catálogo con búsqueda HTMX.
│   │   ├── _productos_tabla.html     # Partial que devuelve HTMX.
│   │   ├── agregar_producto.html     # Alta (HU-04).
│   │   ├── editar_producto.html      # Edición de precios y stock.
│   │   └── eliminar_producto.html    # Confirmación de baja lógica.
│   └── administracion/               # Panel del equipo:
│       ├── dashboard.html            # stats de usuarios + accesos rápidos.
│       ├── listar_usuarios.html      # tabla con búsqueda/filtros.
│       ├── crear_usuario.html / editar_usuario.html
│       ├── eliminar_usuario.html     # confirmación con advertencia.
│       ├── asignar_roles.html        # checkboxes de grupos.
│       ├── reportes_ventas.html       # resumen, serie diaria, top 10.
│       └── reportes_stock.html        # inventario valorado y alertas.
│
├── static/
│   ├── css/styles.css                # ~3.200 líneas: tokens del toldo, estilo
│   │                                 # neón (único) con dark variant,
│   │                                 # componentes base, bloques auth/admin
│   │                                 # del equipo con aliases de tokens,
│   │                                 # responsive, reduced-motion.
│   └── img/favicon.svg               # Tira amarilla + "K" sobre tinta
│                                     # (#17130E / #FFC400).
│
├── venv/                             # Entorno virtual (no se sube).
└── .agents/skills/frontend-design/   # Skill de diseño usada para el
                                      # rediseño.
```

### Flujo de autenticación (cómo funciona login → pantalla)

1. El usuario visita `http://127.0.0.1:8001/` → redirige a `usuarios:post_login`.
2. Si no está autenticado, Django lo manda a `usuarios:login` (configurado en `LOGIN_URL`).
3. El formulario (`LoginKioscoForm`) valida credenciales contra `auth.User`.
4. **Registro:** cualquiera puede crear cuenta en `/usuarios/registro/`; el usuario
   nace sin grupo y, hasta que un administrador le asigne rol, cae en `sin_rol`.
5. Al loguearse, `post_login` chequea el grupo:
   - `es_administrador(user)` → redirige a `administracion:dashboard`.
    - `es_cajero(user)` → redirige a `ventas:pantalla_cobro`.
   - Sin grupo → redirige a `usuarios:sin_rol`.
6. Si el usuario escribe una URL protegida a mano, el decorador `rol_requerido`
   lanza `PermissionDenied` (403) que se renderiza con `templates/403.html`.

### Flujo de auditoría

- Las señales `user_logged_in` y `user_logged_out` (Django) están conectadas en
  `auditoria/signals.py`. Cada login/logout crea un `RegistroAuditoria` con
  usuario, acción, fecha e IP automáticamente. Las acciones custom se logean
  con `registrar_accion()` desde cualquier vista.

### Modo oscuro

- Un script inline en `<head>` de `base.html` lee `localStorage['kiosco-tema']`
  y aplica `data-theme="dark"` en `<html>` antes del render (sin flash). Si no
  hay nada guardado, respeta `prefers-color-scheme`.
- El botón de luna/sol en el navbar cambia el atributo y guarda en `localStorage`.
- Los estilos dark están en `styles.css` bajo selectores `[data-theme="dark"]`.

### Estilo visual

- **Un solo estilo: Neón cian.** Righteous + Space Grotesk, noche `#081822`,
  cian `#00C8E0` como luz principal con glow contenido y un azul `#5FE6F5` de
  apoyo, radios 10px.
- `data-tema="neon"` se fuerza en el script inline del `<head>` de `base.html`
  (sin flash); `localStorage['kiosco-estilo']` se limpia si existía.
- Se eliminaron las paletas **Cartelera** y **Ticket** (CSS y selector) y el
  botón `#estiloToggle` del navbar y del login. Solo queda `#darkToggle`
  (claro/oscuro).

## Backlog

Estado real al **05-10-2026** (unificado: tabla original + backlog nuevo).

### Hecho

| Item | Sprint | Evidencia |
|------|--------|-----------|
| Login + roles + 403 server-side + post-login por rol | 1 | `usuarios/decorators.py`, tests de `usuarios` |
| Auditoría de login/logout con IP | transversal | `auditoria/signals.py` |
| Registro de cuentas públicas (sin rol) | transversal | `usuarios:registro` |
| CRUD de usuarios + búsqueda + filtro por roles + paginación | 2 | `administracion/views.py`, 22 tests |
| Modelos Categoria, Producto, Venta, DetalleVenta + admin Django | 2 | `ventas/models.py` (+ migración 0002 con `costo`) |
| Campo de costo en Producto (lo ve solo el admin) | 2 | `Producto.costo`, `DetalleVenta.costo_unitario` |
| Cajero no accede a costos de mercadería | transversal | `@rol_requerido("Administrador")` + test `test_no_muestra_costos_al_cajero` (403) |
| Reporte top 10 de productos más vendidos (HU-11) | 4 | `administracion/reportes.py::top_productos` |
| Consulta de ventas, stock, costos y reportes para el administrador | 4 | `/administracion/reportes/ventas/` y `/reportes/stock/` |
| KPIs de negocio: ingresos, ganancia, margen, ticket promedio, stock valorizado | 4 | `reportes.py` (`resumen_ventas`, `resumen_stock`, `ventas_por_dia`) |
| Rediseño frontend: identidad toldo + modo oscuro | transversal | `static/css/styles.css` |
| Estilo neón cian único (se eliminaron cartelera/ticket) | transversal | `data-tema="neon"` forzado en `base.html` |
| Views/urls + templates de lista y alta de productos | 2 | `ventas/views.py`, 5 templates en `templates/ventas/` (ya no dan 500) |
| Código de barras en Producto + alta sin duplicados (HU-04) | 2 | `Producto.codigo_barras` (unique) + `ProductoForm.clean_codigo_barras` |
| Altas, bajas y modificaciones de productos (CRUD) | 2 | `agregar/`, `<id>/editar/`, `<id>/eliminar/` (baja lógica, reversible) |
| Búsqueda de productos en tiempo real con HTMX (HU-05) | 2 | `hx-get` en el buscador + partial `_productos_tabla.html` |
| Alerta de stock bajo configurable (HU-06) | 2 | `Producto.stock_minimo` (default 5) + `stock_bajo` + `.badge-stock-bajo` |
| Catálogo protegido para el administrador (el cajero: 403) | 2 | `@rol_requerido("Administrador")` en las 4 vistas de `ventas` |
| Carrito de cobro con lector de código de barras (HU-07/08) | 3 | `ventas/services.py` + `cobro_agregar`/`cobro_cantidad` con partial `_carrito.html` |
| Búsqueda en tiempo real en el cobro (desde 3 letras) | 3 | `cobro_buscar` + `hx-get` con debounce 300 ms y partial `_cobro_resultados.html` |
| Cobro efectivo/tarjeta con vuelto (HU-09) | 3 | `cobro_confirmar` + preview de vuelto, billetes y "pago exacto" |
| Botón "pago exacto" en el cobro | 3 | `.btn-exacto` rellena el monto con el total |
| Vuelto rápido con billetes/montos predeterminados | 3 | Botones de billetes (100/200/500/1000/2000) |
| Método de pago en `Venta` (efectivo/tarjeta) | 3 | `Venta.metodo_pago` (migración `0004`) |
| Descuento automático de stock al confirmar venta | 3 | `transaction.atomic` + `F("stock")` en `confirmar_venta` |
| Cajero responsable en cada venta | 3 | `Venta.usuario` (`SET_NULL`) + auditoría de la venta |

### Parcial

| Item | Sprint | Qué falta |
|------|--------|-----------|
| KPIs en el dashboard principal | 2 | El dashboard sigue mostrando solo métricas de usuarios (los de negocio están en `/reportes/`) |
| Logo propio del kiosco | por definir | Solo `favicon.svg`; el navbar usa icono de Bootstrap + texto |
| Comercio configurable (nombre y colores del local) | por definir | Identidad fija en neón; se parametrizaría vía settings/templates |

### Pendiente

| Item | Sprint | Notas |
|------|--------|-------|
| Cierre de turno: totales por método, operaciones, responsable (HU-10) | 4 | Requiere modelo `Turno` (el FK de `Venta` a usuario y método de pago ya existen) |
| Alta/búsqueda de clientes por CUIT/DNI (HU-12) | 4 | Requiere modelo `Cliente` y FK opcional en `Venta` |
| Cobro con Mercado Pago (MP) | por definir | Sin dependencia ni integración en `requirements.txt` |
| Recuperar contraseña ("¿Olvidaste tu contraseña?") | por definir | Sin `password_reset` ni `EMAIL_*` en settings |

### Pasos a seguir

1. **~~Sprint 2 (cerrar)~~ — HECHO:** catálogo con alta/edición/baja, código de
   barras, búsqueda HTMX y alerta de stock.
2. **~~Sprint 3 (la caja)~~ — HECHO:** carrito con HTMX/JS, campo `metodo_pago`
   y `usuario` en `Venta`, vuelto + pago exacto + billetes, descuento de
   stock y comprobante (148 tests en verde).
3. **Sprint 4 (cierres):** modelo `Turno`, cierre con totales por método y
   operaciones, y modelo `Cliente` con búsqueda por CUIT/DNI.
4. **Extras (por definir):** Mercado Pago, recuperar contraseña, logo,
   KPIs de negocio en el dashboard, comercio configurable.
