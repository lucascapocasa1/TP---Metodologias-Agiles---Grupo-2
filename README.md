# Sistema Kiosco

Trabajo práctico de Metodologías Ágiles. Sistema web de gestión para un kiosco de barrio.

## Alcance de Sprint 1 — Seguridad y roles (Entrega 24-09)

> "Necesito poder entrar al sistema con mi usuario y contraseña, y que los
> empleados (los cajeros) solo puedan usar la pantalla de cobro y no entren
> a tocar la parte de administración o precios."

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
- Pantallas placeholder para cobro y administración (protegidas por login/roles).

---

## Alcance de Sprint 2 — Cargar y ordenar los productos (Entrega 01-10)

> "Poder cargar los productos nuevos uno tras otro rápido, poniéndoles el
> nombre, el código de barras, cuánto me costó, a cuánto lo vendo y cuántos
> tengo. Si el código ya existe, avísame."

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

### Modelos

- **Producto**: nombre, código de barras (único), precio costo, precio venta,
  stock, stock mínimo.
- **Categoría**: para agrupar productos (golosinas, bebidas, etc.).

---

## Alcance de Sprint 3 — La caja y las ventas (Entrega 15-10)

> "Cuando esté en la pantalla del cajero, quiero pasar el lector de código de
> barras o tipear el código, apretar Enter y que el producto se cargue al
> toque en el carrito sin tener que usar el mouse."

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

### Modelos

- **Venta**: fecha/hora, usuario cajero, total, método de pago (efectivo/tarjeta).
- **DetalleVenta**: venta, producto, cantidad, precio unitario al momento de la venta.

---

## Alcance de Sprint 4 — Cierres y saber qué se vende (Entrega 05-11)

> "Cuando termina el turno o el día, quiero apretar un botón y que me tire
> el total de plata que entró en efectivo, en tarjeta y cuántas ventas hice."

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

### Frontend

- **Bootstrap 5.3.3** vía CDN como framework de utilidades.
- **CSS custom** (`static/css/styles.css`) con design tokens via CSS
  custom properties para mantener consistencia visual y facilitar cambios
  futuros. La paleta, tipografía y espaciados se definen una vez en
  `:root` y se reutilizan en todas las páginas.
- **Tipografía DM Sans** (Google Fonts): familia redondeada y amigable
  que refleja la naturaleza de un kiosco de barrio — no corporativa ni
  genérica.
- **Paleta cálida**: amarillo dorado (`#F5A623`) como color primario
  (evoca la señalética de kioscos argentinos), navy profundo (`#1A1A2E`)
  para la barra de navegación, y superficies cálidas (`#FFFDF7`) en
  lugar del gris clínico de Bootstrap.
- **Componentes custom**: botones con feedback táctil (hover + sombra),
  alertas con borde lateral de color, cards con sombras sutiles, inputs
  con focus amarillo. Todo construido sobre las utilidades de Bootstrap
  pero con identidad propia.
- **Accesibilidad**: contraste WCAG AA, focus-visible para navegación
  por teclado, `prefers-reduced-motion` respetado.
- **Responsive**: el navbar se adapta a mobile ocultando el nombre de
  usuario y manteniendo los badges y el botón de salida.
- **HTMX** entra en el Sprint 3 para el carrito de cobro (agregar productos
  sin recargar la página).

---

## Cómo correr el proyecto

### Requisitos previos

- Python 3.10+
- PostgreSQL instalado y corriendo

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

# 5. Crear la base de datos en PostgreSQL
#    Abrí psql (o pgAdmin) y ejecutá:
#    CREATE DATABASE db_kiosco;

# 6. Configurar la conexión en el archivo .env (ver sección 3.1)

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
desde un archivo `.env` en la raíz del proyecto.

Copiá el archivo `.env.example` como `.env` y completá con tus datos:

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

Se incluyen tests que cubren:
- **`usuarios/tests.py`**: login correcto e incorrecto, acceso anónimo
  bloqueado, cajero bloqueado en administración, administrador con acceso
  total, y la redirección post-login según rol.
- **`ventas/tests.py`**: pantalla de cobro accesible solo con login,
  respuestas HTTP correctas.
- **`administracion/tests.py`**: dashboard accesible solo para
  administradores, cajero bloqueado, Superuser con acceso total.

## Estructura del proyecto

```
kiosco_sprint1/
│
├── manage.py                         # Punto de entrada de Django. Arranca el
│                                     # servidor de desarrollo, corre migraciones,
│                                     # tests y management commands.
│
├── requirements.txt                  # Dependencias del proyecto: Django, psycopg2
│                                     # (driver de PostgreSQL) y django-environ
│                                     # (lectura de variables de entorno).
│
├── .env                              # Variables de entorno (DATABASE_URL para
│                                     # PostgreSQL). No se sube al repo (.gitignore).
│
├── .env.example                      # Plantilla del .env para que cada integrante
│                                     # del grupo copie y complete con sus datos.
│
├── .gitignore                        # Archivos que Git ignora: __pycache__,
│                                     # venv/, db.sqlite3, .env, .agents/
│
├── db.sqlite3                        # Base de datos SQLite local (fallback si no
│                                     # hay DATABASE_URL configurado).
│
│
├── config/                           # Paquete de configuración del proyecto Django.
│   ├── __init__.py
│   ├── settings.py                   # Configuración principal: base de datos
│   │                                 # (PostgreSQL via .env con fallback a SQLite),
│   │                                 # apps instaladas, middleware, autenticación
│   │                                 # (LOGIN_URL, LOGIN_REDIRECT_URL), idioma
│   │                                 # (es-ar), zona horaria, archivos estáticos.
│   ├── urls.py                       # URLs raíz: incluye las URLs de cada app
│   │                                 # (usuarios, ventas, administracion), el admin
│   │                                 # de Django y el handler404 para páginas no
│   │                                 # encontradas.
│   ├── wsgi.py                       # Punto de entrada WSGI para producción
│   │                                 # (gunicorn, uwsgi, etc.).
│   └── asgi.py                       # Punto de entrada ASGI (si se usa en el futuro
│                                     # con canales/websockets).
│
│
├── usuarios/                         # App de autenticación y control de acceso.
│   │                                 # Es la app más completa del Sprint 1.
│   ├── apps.py                       # Configuración de la app (UsuariosConfig).
│   ├── models.py                     # Vacío — no modela nada propio, usa
│   │                                 # django.contrib.auth.models.User y Group.
│   ├── views.py                      # LoginKioscoView (login con formulario
│   │                                 # Bootstrap), post_login (redirige según rol:
│   │                                 # admin→dashboard, cajero→cobro), sin_rol
│   │                                 # (aviso si el usuario no tiene grupo).
│   ├── urls.py                       # 4 rutas: login/, logout/, post-login/,
│   │                                 # sin-rol/ (app_name = "usuarios").
│   ├── forms.py                      # LoginKioscoForm: extiende AuthenticationForm
│   │                                 # con clases CSS del kiosco (kiosco-input,
│   │                                 # autofocus, placeholders).
│   ├── decorators.py                 # Rol_requerido (decorador para vistas de
│   │                                 # función), RolRequeridoMixin (para CBVs),
│   │                                 # es_administrador() y es_cajero() (helpers).
│   │                                 # Siempre chequea grupo + superuser bypass.
│   ├── admin.py                      # Vacío — no registra modelos propios.
│   ├── tests.py                      # 9 tests: login éxito/fallo, 403 cajero→admin,
│   │                                 # 200 admin→admin, admin→cobro, redirecciones
│   │                                 # post-login por rol.
│   ├── migrations/                   # Migraciones de Django (vacío, no hay modelos).
│   ├── templatetags/                 # Tags de template reutilizables.
│   │   ├── __init__.py
│   │   ├── pagination_tags.py        # {% paginacion %} y {% param %}: componentes
│   │   │                             # de paginación y preservación de query params.
│   │   └── (tags.py)                 # Tag para preservar parámetros GET al paginar.
│   └── management/                   # Comandos personalizados de Django.
│       ├── __init__.py
│       └── commands/
│           ├── __init__.py
│           └── setup_inicial.py      # "python manage.py setup_inicial": crea los
│                                     # grupos Administrador y Cajero, y los usuarios
│                                     # de prueba admin/kiosco2024 y cajero1/kiosco2024.
│                                     # Idempotente: no duplica si ya existen.
│
│
├── ventas/                           # App de pantalla de cobro (POS).
│   ├── apps.py                       # Configuración de la app (VentasConfig).
│   ├── models.py                     # Vacío — se completa en Sprint 3 con Venta,
│   │                                 # DetalleVenta.
│   ├── views.py                      # pantalla_cobro: vista protegida por
│   │                                 # @login_required. Renderiza un placeholder
│   │                                 # que Sprint 3 convertirá en el carrito real.
│   ├── urls.py                       # 1 ruta: cobro/ (app_name = "ventas").
│   ├── admin.py                      # Vacío.
│   ├── tests.py                      # 4 tests: login requerido, cajero accede,
│   │                                 # admin accede, template correcto.
│   └── migrations/                   # Vacío.
│
│
├── administracion/                   # App del panel de administración (dueño).
│   ├── apps.py                       # Configuración de la app (AdministracionConfig).
│   ├── models.py                     # Vacío — se completa en Sprint 2 con Producto,
│   │                                 # Categoría.
│   ├── views.py                      # dashboard: vista protegida por
│   │                                 # @rol_requerido("Administrador"). Renderiza
│   │                                 # placeholder que Sprint 2-4 completará.
│   ├── urls.py                       # 1 ruta: dashboard/ (app_name = "administracion").
│   ├── admin.py                      # Vacío.
│   ├── tests.py                      # 6 tests: login requerido, admin accede,
│   │                                 # cajero recibe 403, superuser accede, template
│   │                                 # correcto, usuario sin grupo recibe 403.
│   └── migrations/                   # Vacío.
│
│
├── auditoria/                        # App de logs de auditoría.
│   ├── apps.py                       # AuditoriaConfig: carga signals.py en ready()
│   │                                 # para que se registren login/logout auto.
│   ├── models.py                     # RegistroAuditoria: campos usuario (FK),
│   │                                 # accion (str), detalle (text), fecha
│   │                                 # (auto_now_add), ip (GenericIPAddress).
│   ├── signals.py                    # Escucha user_logged_in y user_logged_out
│   │                                 # de Django. Al recibir la señal, crea un
│   │                                 # RegistroAuditoria automáticamente.
│   ├── utils.py                      # Funciones utilitarias: registrar_login(),
│   │                                 # registrar_logout(), registrar_accion()
│   │                                 # (para logear acciones custom), _obtener_ip()
│   │                                 # (extrae IP real del request, respeta proxy).
│   ├── admin.py                      # RegistroAuditoriaAdmin: solo lectura en el
│   │                                 # admin de Django (list_display, filtros,
│   │                                 # búsqueda). No permite agregar/editar/borrar.
│   ├── views.py                      # Vacío.
│   ├── tests.py                      # Vacío.
│   └── migrations/
│       └── 0001_initial.py           # Crea la tabla auditoria_registroauditoria.
│
│
├── templates/                        # Templates HTML (Django Template Language).
│   ├── base.html                     # Layout base: carga Bootstrap 5.3.3 + Bootstrap
│   │                                 # Icons (CDN), CSS custom, favicon SVG. Navbar
│   │                                 # condicional (solo si está autenticado): marca,
│   │                                 # nombre de usuario, badge de rol, toggle de
│   │                                 # modo oscuro, botón salir. Script en <head>
│   │                                 # para modo oscuro sin flash. Script al final
│   │                                 # para el toggle del tema.
│   ├── 403.html                      # Página de "Acceso denegado" (extend base).
│   │                                 # Ícono bi-lock, mensaje, botón volver.
│   ├── 404.html                      # Página de "Página no encontrada" (extend base).
│   │                                 # Ícono bi-question-circle, mensaje, botón volver.
│   ├── usuarios/
│   │   ├── login.html                # Formulario de login: card centrada con ícono
│   │   │                             # de marca (bi-shop), campos usuario/contraseña
│   │   │                             # con clases kiosco-input, alerta de error si
│   │   │                             # form.errors, botón "Ingresar".
│   │   └── sin_rol.html              # Aviso para usuarios sin grupo asignado.
│   │                                 # Ícono bi-explanation-triangle, instrucciones,
│   │                                 # botón volver al login.
│   ├── ventas/
│   │   └── pantalla_cobro.html       # Placeholder de cobro: ícono bi-receipt,
│   │                                 # título, alerta informativa del Sprint 1,
│   │                                 # link a administración (solo visible para admin).
│   └── administracion/
│       └── dashboard.html            # Placeholder de admin: ícono bi-gear,
│                                     # título, alerta informativa, link a cobro.
│
│
├── static/                           # Archivos estáticos (CSS, imágenes).
│   ├── css/
│   │   └── styles.css                # Estilos custom (~700 líneas). Design tokens
│   │                                 # en :root (colores, radios, sombras, transición).
│   │                                 # Componentes: kiosco-navbar, kiosco-card,
│   │                                 # btn-kiosco, kiosco-input, kiosco-alert,
│   │                                 # login-wrapper, error-page, warning-page,
│   │                                 # placeholder-page. Dark mode via [data-theme="dark"]
│   │                                 # (colores Catppuccin-inspired). Paginación y
│   │                                 # search box. Responsive (mobile ≤576px).
│   │                                 # Accesibilidad: prefers-reduced-motion.
│   └── img/
│       └── favicon.svg               # Favicon: "K" amarilla (#F5A623) sobre fondo
│                                     # navy (#1A1A2E), bordes redondeados.
│
│
├── venv/                             # Entorno virtual Python (no se sube al repo).
│                                     # Contiene Django 6.1.1, psycopg2-binary,
│                                     # django-environ y todas las dependencias.
│
└── .agents/                          # Configuración de agentes IA (no relevante
    └── skills/                       # para el proyecto en sí).
        └── frontend-design/
```

### Flujo de autenticación (cómo funciona login → pantalla)

1. El usuario visita `http://127.0.0.1:8000/` → redirige a `usuarios:post_login`.
2. Si no está autenticado, Django lo manda a `usuarios:login` (configurado en `LOGIN_URL`).
3. El formulario (`LoginKioscoForm`) valida credenciales contra `auth.User`.
4. Al loguearse, `post_login` chequea el grupo:
   - `es_administrador(user)` → redirige a `administracion:dashboard`.
   - `es_cajero(user)` → redirige a `ventas:pantalla_cobro`.
   - Sin grupo → redirige a `usuarios:sin_rol`.
5. Si el usuario escribe una URL protegida a mano, el decorador `rol_requerido`
   lanza `PermissionDenied` (403) que se renderiza con `templates/403.html`.

### Flujo de auditoría

- Las señales `user_logged_in` y `user_logged_out` (Django) están conectadas en
  `auditoria/signals.py`. Cada login/logout crea un `RegistroAuditoria` con
  usuario, acción, fecha e IP automáticamente. Las acciones custom se logean
  con `registrar_accion()` desde cualquier vista.

### Modo oscuro

- Un script inline en `<head>` de `base.html` lee `localStorage` y aplica
  `data-theme="dark"` en `<html>` antes del render (sin flash).
- El botón toggle en el navbar cambia el atributo y guarda en `localStorage`.
- Los estilos dark están en `styles.css` bajo selectores `[data-theme="dark"]`.

## Backlog

| Item | Sprint |
|------|--------|
| Módulo de stock y precios (Producto, CRUD, precio de costo oculto para Cajero) | Sprint 2 |
| Alerta de stock bajo con marcas de color | Sprint 2 |
| Carrito de cobro rápido con lector de código de barras (HTMX) | Sprint 3 |
| Calculadora de vuelto con botones de billetes comunes y "pago exacto" | Sprint 3 |
| Descuento automático de stock al confirmar venta | Sprint 3 |
| Cierre de turno: totales por efectivo/tarjeta, cantidad de operaciones, usuario responsable | Sprint 4 |
| Reporte de productos más vendidos | Sprint 4 |
| Alta/búsqueda de clientes por CUIT/DNI para facturación opcional | Sprint 4 |
