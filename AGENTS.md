# AGENTS.md

## Project

Sistema Kiosco — Django 6.1.1 web app for a kiosk (Sprint 1: login + role-based access). Spanish (es-ar) locale, Argentina timezone. SQLite for dev; PostgreSQL planned later.

## Setup

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py setup_inicial   # seeds Groups + test users
python manage.py runserver
```

## Commands

| Task | Command |
|---|---|
| Run all tests | `python manage.py test` |
| Run app tests | `python manage.py test usuarios` |
| Run single test class | `python manage.py test usuarios.tests.TestClassName` |
| Seed DB | `python manage.py setup_inicial` |
| Migrate | `python manage.py migrate` |

No linter, formatter, or typecheck tools are configured.

## Structure

```
config/            # Django project settings, root urls (DJANGO_SETTINGS_MODULE=config.settings)
usuarios/          # Auth: login, logout, groups/roles, authorization decorator
ventas/            # Checkout screen (placeholder, Sprint 2)
administracion/    # Admin dashboard (placeholder, future sprints)
templates/         # Shared base.html + per-app templates
```

All three app `models.py` are currently empty — no DB models yet.

## Key conventions

- **Roles via Django Groups** (`"Administrador"`, `"Cajero"`), not individual permissions.
- **Authorization**: `@rol_requerido("Rol")` decorator (function views) or `RolRequeridoMixin` (CBVs) in `usuarios/decorators.py`. Superusers bypass checks. Unauthorized → 403.
- **Auth flow**: `LoginKioscoView` → `post_login` redirects per role (admin → dashboard, cashier → checkout, no-role → `sin_rol`). `LOGIN_URL = 'usuarios:login'`.
- **URLs**: each app defines `app_name` and named patterns. Root `/` → `usuarios:post_login`.
- **Templates**: extend `base.html` (Bootstrap 5 CDN). Blocks: `titulo`, `contenido`.
- **Test users** (created by `setup_inicial`): `admin`/`kiosco2024` (Administrador), `cajero1`/`kiosco2024` (Cajero).
- **Code style**: app names and code comments are in Spanish. Follow existing conventions when adding new apps or files.
