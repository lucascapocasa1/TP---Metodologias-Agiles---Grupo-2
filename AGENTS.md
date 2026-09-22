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
usuarios/          # Auth: login, logout, registro, roles/grupos, decorador de autorización,
                   # templatetags (buscador, paginación), comando setup_inicial
ventas/            # Catálogo (Categoria, Producto), ventas (Venta, DetalleVenta) y pantalla de cobro
administracion/    # Dashboard y CRUD de usuarios (listar/crear/editar/eliminar/roles/toggle)
auditoria/         # RegistroAuditoria + signals: audita cambios en usuarios y ventas
static/            # CSS/JS compartido (styles.css con los 3 estilos visuales)
templates/         # base.html + templates por app (también 403.html y 404.html)
```

Modelos: `ventas` → `Categoria`, `Producto`, `Venta`, `DetalleVenta`; `auditoria` → `RegistroAuditoria`; `usuarios` y `administracion` no tienen modelos (usan `auth.User`).

**Gap conocido**: existen las views/urls de `ventas:lista_productos` y `ventas:agregar_producto` pero faltan sus templates (`templates/ventas/lista_productos.html` y `agregar_producto.html`): esas rutas devuelven 500 (`TemplateDoesNotExist`).

## Convenciones clave

- **Roles vía Django Groups** (`"Administrador"`, `"Cajero"`), no permisos individuales.
- **Autorización**: decorador `@rol_requerido("Rol")` (function views) o `RolRequeridoMixin` (CBVs) en `usuarios/decorators.py`. Superusers bypassean el chequeo. Sin rol → 403.
- **Flujo de auth**: `LoginKioscoView` → `post_login` redirige por rol (admin → dashboard, cajero → cobro, sin rol → `sin_rol`). `LOGIN_URL = 'usuarios:login'`.
- **URLs**: cada app define `app_name` y patrones con nombre. Raíz `/` → `usuarios:post_login`.
- **Templates**: extienden `base.html` (Bootstrap 5 CDN). Blocks: `titulo`, `contenido`.
- **Frontend**: 3 estilos conmutables — `data-tema` (`cartelera` | `ticket` | `neon`) + `data-theme` (claro/oscuro) en `<html>`; preferencia en `localStorage` (`kiosco-estilo`, `kiosco-tema`); default saneado a `cartelera`. Botones `#estiloToggle` y `#darkToggle`. Vocabulario de animaciones "toldo" al final de `static/css/styles.css`; respetar `prefers-reduced-motion`.
- **Usuarios de prueba** (los crea `setup_inicial`): `admin`/`kiosco2024` (Administrador), `cajero1`/`kiosco2024` (Cajero).
- **Estilo de código**: nombres de apps y comentarios en español. Seguir las convenciones existentes al agregar apps o archivos nuevos.
