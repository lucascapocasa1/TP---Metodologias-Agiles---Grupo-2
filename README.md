# Sistema Kiosco — Sprint 1

Trabajo práctico de Metodologías Ágiles. Sistema web de gestión para un kiosco.

## 1. Alcance de este Sprint

De toda la conversación con el Product Owner y los stakeholders, este primer
sprint **solo** resuelve el pedido explícito para esta entrega:

> "Necesito poder entrar al sistema con mi usuario y contraseña, y que los
> empleados (los cajeros) solo puedan usar la pantalla de cobro y no entren
> a tocar la parte de administración o precios."

Todo lo demás que se charló en la reunión (velocidad de carga por código de
barras, botones de vuelto rápido, alta de clientes por CUIT, cierre de
turno con arqueo de caja) queda deliberadamente **fuera de este sprint** y
pasa al backlog de sprints siguientes — son funcionalidades sobre pantallas
que en este sprint son solo una cáscara protegida por login y roles.

### Historias de usuario cubiertas

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

Ambas historias se probaron con tests automáticos (`usuarios/tests.py`,
Django Test Framework) y manualmente contra el servidor de desarrollo.

## 2. Decisiones técnicas

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
- **HTMX** entra en el sprint del carrito de cobro (agregar productos
  sin recargar la página).

## 3. Cómo correr el proyecto

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

### 3.1. Archivo .env

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

## 4. Correr los tests

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

## 5. Estructura del proyecto

```
config/            # settings y urls raíz del proyecto
usuarios/          # login, logout, grupos/roles, decorador de autorización
ventas/            # pantalla de cobro (placeholder protegido, Sprint 2 la completa)
administracion/    # panel del dueño (placeholder protegido, sprints siguientes lo completan)
templates/         # HTML compartido (base) + templates por app
static/css/        # estilos custom (design tokens, componentes kiosco)
.env.example       # plantilla del archivo de configuración (.env)
```

## 6. Backlog para próximos sprints (según la reunión con el cliente)

- Carrito de cobro rápido con lector de código de barras (HTMX).
- Calculadora de vuelto con botones de billetes comunes y "pago exacto".
- Módulo de stock y precios (con precio de costo oculto para el rol Cajero).
- Alta/búsqueda rápida de clientes por CUIT para facturación opcional.
- Cierre de turno: totales por efectivo/tarjeta, cantidad de operaciones y
  registro del usuario responsable del turno.
