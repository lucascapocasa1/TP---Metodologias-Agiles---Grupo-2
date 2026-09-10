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
config/            # settings y urls raíz del proyecto
usuarios/          # login, logout, grupos/roles, decorador de autorización
ventas/            # pantalla de cobro (placeholder protegido, Sprint 3 la completa)
administracion/    # panel del dueño (placeholder protegido, Sprint 4 lo completa)
templates/         # HTML compartido (base) + templates por app
static/css/        # estilos custom (design tokens, componentes kiosco)
.env.example       # plantilla del archivo de configuración (.env)
```

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
