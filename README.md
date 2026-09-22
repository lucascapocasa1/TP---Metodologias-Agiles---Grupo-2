# Sistema Kiosco

Trabajo práctico de Metodologías Ágiles. Sistema web de gestión para un kiosco de barrio.

**Estado al 22-09-2026:** Sprint 1 completo · Sprint 2 en progreso · Frontend rediseñado con
3 estilos visuales conmutables · 35 tests en verde.

---

## Estado actual del trabajo

### Seguridad y roles (Sprint 1) — completo

- Login/logout con Django Authentication, roles vía Django Groups
  (`Administrador`, `Cajero`) y restricción server-side con `@rol_requerido` (403).
- Redirección post-login por rol (`post_login`) y aviso `sin_rol` para usuarios sin grupo.
- Registro público de cuentas en `/usuarios/registro/`: nace **sin rol** y cae en
  `sin_rol` hasta que un administrador le asigne uno.
- Auditoría automática de login/logout con IP (`auditoria/`).

### Productos y catálogo (Sprint 2) — en progreso

- Modelos **Categoria**, **Producto**, **Venta** y **DetalleVenta** creados y migrados
  (`ventas/migrations/0001_initial.py`), registrados en el admin de Django
  (Venta con inline de detalles).
- Vistas y URLs de **lista de productos con búsqueda** (GET por nombre/descripción) y
  **alta de productos** con categoría nueva.
- **Pendiente bloqueante:** faltan los templates `ventas/lista_productos.html` y
  `ventas/agregar_producto.html` — por eso `/ventas/productos/` y
  `/ventas/productos/agregar/` devuelven **500 (TemplateDoesNotExist)**. Las views,
  urls y modelos sí están; hay que crear esos dos templates.
- **Pendiente vs HU-04/05/06:** código de barras, precio de costo y precio de venta
  separados, stock mínimo, marca de stock ≤ 5, y búsqueda en tiempo real con HTMX
  (hoy la búsqueda recarga la página).

### Gestión de usuarios — completo

- CRUD de usuarios para el administrador: listar (búsqueda por nombre/usuario, filtro
  por rol, paginación), crear, editar, eliminar, activar/desactivar y asignar roles,
  con protecciones (no puede desactivar/eliminar superusuarios ni su propia cuenta).
- 22 tests de `administracion` cubren todo el flujo.

### Pantalla de cobro (Sprint 3) — pendiente

- Sigue siendo placeholder, ahora con un mock de escáner de código de barras
  reservado para el Sprint 3. Los modelos `Venta`/`DetalleVenta` ya existen como base.

### Frontend — rediseño completo

- Identidad visual "toldo de barrio" y **3 estilos conmutables**: **Cartelera**
  (por defecto), **Ticket** y **Neón**, más modo oscuro. Detalle en
  [Decisiones técnicas → Frontend](#frontend) y
  [Selector de estilos visuales](#selector-de-estilos-visuales).

### Tests

- **35 tests OK** (`python manage.py test`): `usuarios` 9, `ventas` 4,
  `administracion` 22.

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

**HU-02 — Separación de roles: Cajero**
Como dueño, quiero que el cajero solo pueda ver la pantalla de cobro, para
que no tenga acceso a costos, precios ni reportes del negocio.
- Criterio de aceptación: un usuario del grupo *Cajero* que intenta acceder
  a una URL de administración recibe "Acceso denegado" (403), y accede sin
  problemas a la pantalla de cobro.

**HU-03 — Separación de roles: Administrador**
Como dueño, quiero tener un usuario administrador con acceso total, para
manejar yo mismo la parte sensible del negocio (desde el local o de forma
remota).
- Criterio de aceptación: un usuario del grupo *Administrador* accede tanto
  al panel de administración como a la pantalla de cobro.

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

**Estado:** en progreso (ver [Estado actual](#estado-actual-del-trabajo)).

### Historias de usuario

**HU-04 — Alta rápida de productos**
Como administrador, quiero cargar un producto nuevo ingresando nombre,
código de barras, precio de costo, precio de venta y stock, para tener el
catálogo actualizado.
- Criterio de aceptación: si el código de barras ya existe, el sistema
  muestra un error y no permite el duplicado.

**HU-05 — Lista de productos con búsqueda**
Como administrador, quiero una lista donde pueda buscar cualquier producto
por nombre o código para modificarle el precio o corregir el stock.
- Criterio de aceptación: la búsqueda filtra en tiempo real (HTMX).

**HU-06 — Alerta de stock bajo**
Como administrador, quiero que el sistema me marque en color los productos
que se están quedando sin stock, para saber qué tengo que salir a reponer.
- Criterio de aceptación: productos con stock ≤ 5 se muestran marcados.

### Modelos (implementados)

- **Categoria**: nombre, descripción.
- **Producto**: nombre, descripción, precio (único por ahora), stock,
  categoría (FK), activo. *Todavía sin código de barras, precio de costo /
  venta separados ni stock mínimo (pendientes de las HU).*
- **Venta**: fecha/hora, total, finalizada. Base para el Sprint 3.
- **DetalleVenta**: venta, producto, cantidad, precio unitario, `subtotal()`.
  Base para el Sprint 3.

---

## Alcance de Sprint 3 — La caja y las ventas (Entrega 15-10)

> "Cuando esté en la pantalla del cajero, quiero pasar el lector de código de
> barras o tipear el código, apretar Enter y que el producto se cargue al
> toque en el carrito sin tener que usar el mouse."

**Estado:** pendiente. Los modelos `Venta` y `DetalleVenta` ya existen como
base; la pantalla de cobro tiene el lugar reservado para el lector.

### Historias de usuario

**HU-07 — Carga rápida de productos al carrito**
Como cajero, quiero escanear o tipear un código de barras y que el producto
se agregue al carrito de inmediato.
- Criterio de aceptación: si escaneo el mismo producto dos veces, se suma
  la cantidad (2) en vez de crear una fila duplicada.

**HU-08 — Editar carrito antes de cobrar**
Como cajero, quiero poder borrar un producto del carrito o cambiar la
cantidad antes de confirmar la venta.
- Criterio de aceptación: el total se recalcula al modificar el carrito.

**HU-09 — Cobro con efectivo o tarjeta**
Como cajero, quiero indicar si el cliente paga en efectivo o tarjeta,
ingresar el monto entregado y que el sistema calcule el vuelto exacto.
- Criterio de aceptación: el stock se descuenta automáticamente al
  confirmar la venta.

### Modelos (ya creados como base)

- **Venta**: fecha/hora, total, finalizada. *Falta método de pago
  (efectivo/tarjeta) y usuario cajero.*
- **DetalleVenta**: venta, producto, cantidad, precio unitario al momento
  de la venta.

---

## Alcance de Sprint 4 — Cierres y saber qué se vende (Entrega 05-11)

> "Cuando termina el turno o el día, quiero apretar un botón y que me tire
> el total de plata que entró en efectivo, en tarjeta y cuántas ventas hice."

**Estado:** pendiente.

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

### Frontend

<a id="frontend"></a>

- **Bootstrap 5.3.3 + Bootstrap Icons** vía CDN como framework de utilidades.
- **CSS custom** (`static/css/styles.css`, ~2.900 líneas) con design tokens vía
  CSS custom properties (`:root` + variantes). La paleta, tipografía, radios y
  sombras se definen una vez y se reutilizan en todas las páginas.
- **Identidad "toldo de barrio"**: rotulación de kiosco argentino — contorno
  de tinta + sombra dura, etiquetas de precio adhesivas, código de barras como
  gráfico temático, códigos de error grandes (403/404) y filete de toldo en el
  navbar. Tipografía display **Alfa Slab One** + interfaz **Archivo**.
- **3 estilos visuales conmutables** (ver sección siguiente): **Cartelera**
  (por defecto), **Ticket** (estética de comprobante impreso) y **Neón**
  (cartelería nocturna). Cada estilo define su propia paleta, tipografía y
  radios.
- **Modo oscuro** persistente (`data-theme="dark"`), con los tres estilos
  también disponibles en su variante oscura.
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
- **HTMX** sigue quedando para el Sprint 3 (carrito de cobro); la búsqueda de
  productos hoy es un GET con recarga.

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
python manage.py runserver
```

Abrí `http://127.0.0.1:8000/` en el navegador.

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

**35 tests** actualmente:

- **`usuarios/tests.py` (9)**: login correcto e incorrecto, acceso anónimo
  bloqueado, cajero bloqueado en administración, administrador con acceso
  total, y la redirección post-login según rol.
- **`ventas/tests.py` (4)**: pantalla de cobro accesible solo con login,
  cajero y admin acceden, template correcto.
- **`administracion/tests.py` (22)**: dashboard (login, admin, 403 cajero,
  403 sin grupo, estadísticas) y CRUD de usuarios (listar con búsqueda y
  filtro por rol, crear, editar, eliminar con protección de superusuarios,
  activar/desactivar, asignar/quitar roles).

## Estructura del proyecto

```
kiosco_sprint1/
│
├── manage.py                         # Punto de entrada de Django.
├── requirements.txt                  # Django 6.1.1, psycopg2-binary,
│                                     # django-environ.
├── README.md                         # Este archivo.
├── AGENTS.md                         # Instrucciones para agentes IA.
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
│   ├── models.py                     # Categoria, Producto, Venta,
│   │                                 # DetalleVenta (migración 0001).
│   ├── views.py                      # pantalla_cobro (placeholder con mock
│   │                                 # de escáner), lista_productos (búsqueda
│   │                                 # GET), agregar_producto (alta con
│   │                                 # categoría nueva).
│   ├── urls.py                       # 3 rutas: cobro/, productos/,
│   │                                 # productos/agregar/.
│   ├── admin.py                      # Venta (inline DetalleVenta), Producto,
│   │                                 # Categoria.
│   ├── tests.py                      # 4 tests.
│   └── migrations/0001_initial.py    # Tablas de catálogo y ventas.
│   ⚠ Faltan: templates/ventas/lista_productos.html y
│     templates/ventas/agregar_producto.html (las dos URLs dan 500).
│
├── administracion/                   # Panel del dueño.
│   ├── views.py                      # dashboard (stats de usuarios) + CRUD:
│   │                                 # listar, crear, editar, eliminar,
│   │                                 # asignar_roles, toggle_usuario.
│   ├── urls.py                       # 7 rutas bajo /administracion/.
│   ├── forms.py                      # UsuarioForm (alta/edición con
│   │                                 # contraseña opcional al editar) y
│   │                                 # AsignarRolForm (checkboxes de grupos).
│   ├── tests.py                      # 22 tests.
│   └── templates → ../templates/administracion/ (7 templates).
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
│   │                                 # de estilo, botón oscuro, salir),
│   │                                 # bloque de messages, scripts de tema y
│   │                                 # de estilo sin flash.
│   ├── 403.html / 404.html           # error-page con código grande.
│   ├── usuarios/
│   │   ├── login.html                # login-split: toldo a la izquierda +
│   │   │                             # panel de ingreso a la derecha, botón
│   │   │                             # de estilo flotante.
│   │   ├── registro.html             # auth-card de alta de cuenta.
│   │   ├── sin_rol.html              # warning-page sin grupo asignado.
│   │   └── tags/                     # Partiales de paginación y buscador.
│   ├── ventas/
│   │   └── pantalla_cobro.html       # Placeholder con mock de escáner.
│   └── administracion/               # Panel del equipo:
│       ├── dashboard.html            # stats de usuarios + accesos rápidos.
│       ├── listar_usuarios.html      # tabla con búsqueda/filtros.
│       ├── crear_usuario.html / editar_usuario.html
│       ├── eliminar_usuario.html     # confirmación con advertencia.
│       └── asignar_roles.html        # checkboxes de grupos.
│
├── static/
│   ├── css/styles.css                # ~2.900 líneas: tokens del toldo, 3
│   │                                 # estilos (cartelera/ticket/neon) con
│   │                                 # dark variant, componentes base,
│   │                                 # bloques auth/admin del equipo con
│   │                                 # aliases de tokens, responsive,
│   │                                 # reduced-motion.
│   └── img/favicon.svg               # Tira amarilla + "K" sobre tinta
│                                     # (#17130E / #FFC400).
│
├── venv/                             # Entorno virtual (no se sube).
└── .agents/skills/frontend-design/   # Skill de diseño usada para el
                                      # rediseño.
```

### Flujo de autenticación (cómo funciona login → pantalla)

1. El usuario visita `http://127.0.0.1:8000/` → redirige a `usuarios:post_login`.
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
- Los estilos dark están en `styles.css` bajo selectores `[data-theme="dark"]`,
  tanto para los componentes base como para los 3 estilos.

### Selector de estilos visuales

- Tres estilos, ciclados con el botón de paleta (navbar y login):
  **Cartelera → Ticket → Neón → Cartelera…**
- **Cartelera** (por defecto): Alfa Slab One + Archivo, negros `#0D0D0F`/
  `#121214`, rojo `#E23D28`, focos amarillos, radios 6px.
- **Ticket**: IBM Plex Mono en todo, papel `#F7F7F4` con tinta `#101010`,
  navbar casi negra, radios 0px, perforación gris.
- **Neón**: Righteous + Space Grotesk, noche `#120B1F`, rosa `#FF2E9A` con
  glow y cian `#00E5FF`, radios 10px.
- Persistencia en `localStorage['kiosco-estilo']` + atributo `data-tema` en
  `<html>` (script en `<head>` para aplicarlo sin flash). Un valor inválido o
  viejo en el storage se sanea a `cartelera`.
- Cada estilo tiene su variante oscura (`data-theme="dark"` combinado con
  `data-tema`).

## Backlog

| Item | Sprint | Estado |
|------|--------|--------|
| Login + roles + 403 server-side + post-login por rol | 1 | Hecho |
| Auditoría de login/logout con IP | transversal | Hecho |
| Registro de cuentas públicas (sin rol) | transversal | Hecho |
| CRUD de usuarios + búsqueda + filtro por roles + paginación | 2 | Hecho |
| Modelos Categoria, Producto, Venta, DetalleVenta + admin Django | 2 | Hecho |
| Views/urls de lista y alta de productos | 2 | Parcial (faltan 2 templates → 500) |
| Código de barras + precio costo/venta + stock mínimo (HU-04) | 2 | Pendiente |
| Búsqueda de productos en tiempo real con HTMX (HU-05) | 2 | Pendiente |
| Alerta de stock ≤ 5 con marca de color (HU-06) | 2 | Pendiente |
| Carrito de cobro con lector de código de barras (HU-07/08) | 3 | Pendiente |
| Cobro efectivo/tarjeta con vuelto (HU-09) | 3 | Pendiente |
| Descuento automático de stock al confirmar venta | 3 | Pendiente |
| Cierre de turno: totales por método, operaciones, responsable (HU-10) | 4 | Pendiente |
| Reporte top 10 de productos más vendidos (HU-11) | 4 | Pendiente |
| Alta/búsqueda de clientes por CUIT/DNI (HU-12, opcional) | 4 | Pendiente |
| Rediseño frontend: identidad toldo + 3 estilos + modo oscuro | transversal | Hecho |
