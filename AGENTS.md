# AGENTS.md

## Proyecto

Sistema Kiosco — web app Django 6.1.1 para un kiosco (Sprint 2: login, roles, CRUD de usuarios, catálogo de productos y pantalla de cobro). Locale `es-ar`, timezone Argentina. **Base de datos: PostgreSQL** (`DATABASE_URL` en `.env`, p. ej. `postgresql://postgres:***@localhost:5432/db_kiosco`); SQLite queda solo como fallback si no hay `.env`.

## Configuración

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py setup_inicial   # crea Groups + usuarios de prueba
python manage.py runserver
```

Requiere un servidor PostgreSQL accesible y un archivo `.env` con `DATABASE_URL`.

## Comandos

| Tarea | Comando |
|---|---|
| Correr todos los tests | `python manage.py test` |
| Tests de una app | `python manage.py test usuarios` |
| Un solo test class | `python manage.py test usuarios.tests.TestClassName` |
| Seed de la DB | `python manage.py setup_inicial` |
| Migraciones | `python manage.py migrate` |

No hay linter, formatter ni typecheck configurados.

## Estructura

```
config/            # Settings y urls raíz del proyecto (DJANGO_SETTINGS_MODULE=config.settings)
usuarios/          # Auth: login, logout, roles/grupos, decorador de autorización,
                   # recuperación de clave por email, templatetags, comando setup_inicial
ventas/            # Catálogo (Categoria, Producto), ventas (Venta, DetalleVenta) y pantalla de cobro
administracion/    # Dashboard y CRUD de usuarios (listar/crear/editar/eliminar/roles/toggle)
auditoria/         # RegistroAuditoria + signals: audita cambios en usuarios y ventas
static/            # CSS/JS compartido (styles.css con los 3 estilos visuales)
templates/         # base.html + templates por app (también 403.html y 404.html)
```

Modelos: `ventas` → `Categoria`, `Producto`, `Venta`, `DetalleVenta`; `auditoria` → `RegistroAuditoria`; `usuarios` y `administracion` no tienen modelos (usan `auth.User`).

**CRUD de productos** (solo Administrador, vía `@rol_requerido("Administrador")`): `ventas:lista_productos` (listado + búsqueda por nombre/descripción/categoría), `ventas:agregar_producto`, `ventas:editar_producto`, `ventas:eliminar_producto` (con pantalla de confirmación) y `ventas:toggle_producto` (activar/desactivar sin borrar). Las vistas leen `request.POST` directo y devuelven `errores` en el contexto para re-renderizar el form; la categoría se puede elegir existente o crear una nueva escribiendo en `nueva_categoria` (gana si viene completa). El dashboard (`administracion:dashboard`) muestra una sección "Productos y Stock" con tarjetas de productos activos / sin stock y accesos rápidos.

**Gap conocido**: `ventas:toggle_producto` (y `administracion:toggle_usuario`) mutan estado en GET, sin token CSRF. `auditoria` no tiene URLs ni UI. No hay paginación en los listados.

## Convenciones clave

- **Roles vía Django Groups** (`"Administrador"`, `"Cajero"`), no permisos individuales.
- **Autorización**: decorador `@rol_requerido("Rol")` (function views) o `RolRequeridoMixin` (CBVs) en `usuarios/decorators.py`. Superusers bypassean el chequeo. Sin rol → 403.
- **Flujo de auth**: `LoginKioscoView` → `post_login` redirige por rol (admin → dashboard, cajero → cobro, sin rol → `sin_rol`). `LOGIN_URL = 'usuarios:login'`.
- **Recuperación de acceso por email**: 4 rutas con las vistas de Django y templates propios en español — `usuarios:recuperar_clave` (pide email), `usuarios:recuperacion_enviada`, `usuarios:resetear_clave` (`<uidb64>/<token>/`) y `usuarios:recuperacion_completada`. Anti-enumeración: un email desconocido redirige igual a la pantalla de éxito y no envía nada. **En dev el email se imprime en consola** (`EMAIL_BACKEND` = console backend): el link se copia de ahí.
- **Alta de usuarios**: no hay auto-registro. Las cuentas las crea el Administrador desde `administracion:crear_usuario` (que es donde también se carga el email, necesario para la recuperación por email).
- **Email**: `EMAIL_BACKEND` + `DEFAULT_FROM_EMAIL` en `config/settings.py` (antes había un `MAILERS` que no es un setting de Django y no hacía nada). Para producción hay que cambiar a `smtp.EmailBackend` con `EMAIL_HOST`/`EMAIL_PORT`/`EMAIL_HOST_USER`/`EMAIL_HOST_PASSWORD` en `.env`.
- **URLs**: cada app define `app_name` y patrones con nombre. Raíz `/` → `usuarios:post_login`.
- **Templates**: extienden `base.html` (Bootstrap 5 CDN). Blocks: `titulo`, `contenido`.
- **Frontend**: 3 estilos conmutables — `data-tema` (`cartelera` | `ticket` | `neon`) + `data-theme` (claro/oscuro) en `<html>`; preferencia en `localStorage` (`kiosco-estilo`, `kiosco-tema`); default saneado a `cartelera`. Botones `#estiloToggle` y `#darkToggle`. Vocabulario de animaciones "toldo" al final de `static/css/styles.css`; respetar `prefers-reduced-motion`.
- **Usuarios de prueba** (los crea `setup_inicial`): `admin`/`kiosco2024` (Administrador), `cajero1`/`kiosco2024` (Cajero).
- **Estilo de código**: nombres de apps y comentarios en español. Seguir las convenciones existentes al agregar apps o archivos nuevos.
