# AGENTS.md

## Proyecto

Norvex (antes "Sistema Kiosco") — web app Django 6.1.1 para comercios, nacida para un kiosco (Sprint 4 completo + consignas de la cátedra: catálogo público con pedido por WhatsApp y cuenta corriente "FIAR"). Locale `es-ar`, timezone Argentina. **Base de datos: PostgreSQL** (`DATABASE_URL` en `.env`, p. ej. `postgresql://postgres:***@localhost:5432/db_kiosco`); SQLite queda solo como fallback si no hay `.env`.

## Configuración

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py setup_inicial   # crea Groups + usuarios de prueba
python manage.py runserver 8001  # el 8001 es el puerto de este proyecto
```

Requiere un servidor PostgreSQL accesible y un archivo `.env` con `DATABASE_URL`.
Siempre verificar con `Get-NetTCPConnection -LocalPort 8001 -State Listen` antes de levantar; el puerto 8000 no debe usarse.

## Comandos

| Tarea | Comando |
|---|---|
| Correr todos los tests | `python manage.py test` |
| Tests de una app | `python manage.py test usuarios` |
| Un solo test class | `python manage.py test usuarios.tests.TestClassName` |
| Seed de la DB | `python manage.py setup_inicial` |
| Datos de demo (50+ productos y ventas desde 20/09/2026) | `python manage.py cargar_demo --limpiar` |
| Demo de clientes y pedidos de WhatsApp (va **después** de `cargar_demo`) | `python manage.py cargar_demo_clientes --limpiar` |
| Migraciones | `python manage.py migrate` |

No hay linter, formatter ni typecheck configurados.

## Estructura

```
config/            # Settings y urls raíz del proyecto (DJANGO_SETTINGS_MODULE=config.settings)
usuarios/          # Auth: login, logout, registro, roles/grupos, decorador de autorización,
                   # templatetags (buscador, paginación), comando setup_inicial
ventas/            # Catálogo (Categoria, Producto: CRUD completo con código de barras,
                   # búsqueda HTMX, ordenamiento por columna y alerta de stock),
                   # ventas (Venta, DetalleVenta), pantalla de cobro, cierre de turno
                   # y el comando de datos de demo cargar_demo
clientes/          # Cliente (fidelidad + cuenta corriente "FIAR"), PagoCuentaCorriente,
                   # services.py (puntos, validar_fiado, buscar_clientes, cliente_bloqueado),
                   # demo_data.py y el comando cargar_demo_clientes
pedidos/           # Catálogo público sin login (HU-13), Pedido/ItemPedido,
                   # services.py (carrito del pedido y registrar_entrega) y config.py (WhatsApp)
administracion/    # Dashboard y CRUD de usuarios (listar/crear/editar/eliminar/roles/toggle)
auditoria/         # RegistroAuditoria + signals: audita cambios en usuarios y ventas
static/            # CSS/JS compartido (styles.css con el estilo visual neón)
templates/         # base.html + templates por app (también 403.html y 404.html)
```

Modelos: `ventas` → `Categoria`, `Producto` (`codigo_barras` unique, `costo`, `stock_minimo`, property `stock_bajo`), `Venta`, `DetalleVenta`, `Turno`; `clientes` → `Cliente` (`limite_credito`, `saldo_deuda`), `PagoCuentaCorriente`; `pedidos` → `Pedido` (`cliente`, `venta`), `ItemPedido`; `auditoria` → `RegistroAuditoria`; `usuarios` y `administracion` no tienen modelos (usan `auth.User`).

## Convenciones clave

- **Roles vía Django Groups** (`"Administrador"`, `"Cajero"`), no permisos individuales.
- **Autorización**: decorador `@rol_requerido("Rol")` (function views) o `RolRequeridoMixin` (CBVs) en `usuarios/decorators.py`. Superusers bypassean el chequeo. Sin rol → 403.
- **Flujo de auth**: `LoginKioscoView` → `post_login` redirige por rol (admin → dashboard, cajero → cobro, sin rol → `sin_rol`). `LOGIN_URL = 'usuarios:login'`.
- **URLs**: cada app define `app_name` y patrones con nombre. Raíz `/` → `usuarios:post_login`.
- **Templates**: extienden `base.html` (Bootstrap 5 CDN). Blocks: `titulo`, `contenido`.
- **HTMX**: CDN al final de `base.html`. Las vistas revisan `request.headers.get("HX-Request")` y devuelven solo el partial (ej. `ventas:lista_productos` → `ventas/_productos_tabla.html`).
- **Frontend**: un solo estilo visual, **neón cian**, fijo — `data-tema="neon"` se fuerza en el `<head>` de `base.html` + `data-theme` (claro/oscuro) en `<html>`; tema oscuro en `localStorage['kiosco-tema']`. No existe selector de estilos (el botón `#estiloToggle` y las paletas cartelera/ticket fueron eliminados); botón `#darkToggle` sí. Vocabulario de animaciones "toldo" al final de `static/css/styles.css`; respetar `prefers-reduced-motion`.
- **Usuarios de prueba** (los crea `setup_inicial`): `admin`/`kiosco2024` (Administrador), `cajero1`/`kiosco2024` (Cajero).
- **Entregar un pedido es cobrarlo**: no existe "marcar entregado" sin venta. El flujo de entrega vive en `pedidos/services.py::registrar_entrega` (llama a `ventas/services.py::registrar_venta_desde_items`, el **núcleo de venta compartido** con el POS, y cobra el **precio congelado** del pedido). No reimplementar reglas de stock/puntos/fiado en `pedidos`: se reusan las de `clientes/services.py`.
- **Búsqueda de cliente**: siempre con `clientes/services.py::buscar_clientes` (la usan el POS y el panel de pedidos; ignora acentos). Para tocar datos de un cliente en una venta, usar `clientes/services.py::cliente_bloqueado` (`select_for_update`).
- **Dinero en la UI**: siempre con el filtro `|montos` (`{% load formatos %}`, en `usuarios/templatetags/formatos.py`) → `$30.500`, con centavos solo si los hay. Nunca `floatformat` para importes.
- **Estilo de código**: nombres de apps y comentarios en español. Seguir las convenciones existentes al agregar apps o archivos nuevos.

## Cobro con QR de Mercado Pago (HU-15/16)

- Método `mercado_pago` en `Venta.METODO_PAGO`. La venta se crea con `services._crear_venta(..., finalizada=False)`: stock reservado, puntos al aprobar.
- Lógica en `ventas/cobro_qr.py`, API en `ventas/mercadopago.py` (urllib, sin dependencias), vistas en `ventas/views_qr.py`. Modelo `PagoMercadoPago`, migración `ventas/0008`.
- Sin `MP_ACCESS_TOKEN` en `.env` → modo de prueba (pago simulado en `/ventas/pagar/<token>/`). Con `TEST-...` usa sandbox.
- Display para el celular del cliente en `/ventas/display/` (misma red: `runserver 0.0.0.0:8001`).
