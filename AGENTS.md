# AGENTS.md

## Proyecto

Norvex (antes "Sistema Kiosco") — web app Django 6.1.1 para comercios, plataforma multiempresa (multitenant) con arquitectura single database + shared schema. Nacida para un kiosco (Sprint 4 completo + consignas de la cátedra: catálogo público con pedido por WhatsApp y cuenta corriente "FIAR"). Locale `es-ar`, timezone Argentina. **Base de datos: PostgreSQL** (`DATABASE_URL` en `.env`, p. ej. `postgresql://postgres:***@localhost:5432/db_kiosco`); SQLite queda solo como fallback si no hay `.env`.

## Configuración

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py setup_inicial   # crea Groups + usuarios de prueba
python manage.py runserver 8000  # el puerto de este proyecto es 8000
```

Requiere un servidor PostgreSQL accesible y un archivo `.env` con `DATABASE_URL`.

## Comandos

| Tarea | Comando |
|---|---|
| Correr todos los tests | `python manage.py test` |
| Tests de una app | `python manage.py test usuarios` |
| Un solo test class | `python manage.py test usuarios.tests.TestClassName` |
| Seed de la DB | `python manage.py setup_inicial` |
| Datos de demo (50+ productos y ventas desde 20/09/2026) | `python manage.py cargar_demo --limpiar` |
| Demo de clientes y pedidos de WhatsApp (va **después** de `cargar_demo`) | `python manage.py cargar_demo_clientes --limpiar` |
| Poblar 3 negocios completos (Kiosco De Barrio, Ferretería Martillito, Dietética Natural) | `python manage.py cargar_demo_todos --limpiar` |
| Migrar datos existentes al esquema multiempresa | `python manage.py migrar_a_multiempresa` |
| Migraciones | `python manage.py migrate` |

No hay linter, formatter ni typecheck configurados.

## Estructura

```
config/            # Settings y urls raíz del proyecto (DJANGO_SETTINGS_MODULE=config.settings)
usuarios/          # Auth: login, logout, registro, roles/grupos, decorador de autorización,
                   # templatetags (buscador, paginación), comando setup_inicial
                   # Modelo: Empleado (OneToOne con User, FK a Negocio, activo).
                   # Decorador: superadmin_requerido (solo is_superuser).
ventas/            # Catálogo (Categoria, Producto: CRUD completo con código de barras,
                   # búsqueda HTMX, ordenamiento por columna y alerta de stock),
                   # ventas (Venta, DetalleVenta), pantalla de cobro, cierre de turno
                   # y el comando de datos de demo cargar_demo.
                   # Todos los modelos tienen FK a Negocio (multiempresa).
                   # Modelo: ArqueoTurno (cierre de caja con conteo físico).
clientes/          # Cliente (fidelidad + cuenta corriente "FIAR", compartido entre negocios),
                   # PagoCuentaCorriente (tiene FK a Negocio),
                   # services.py (puntos, validar_fiado, buscar_clientes, cliente_bloqueado),
                   # demo_data.py y el comando cargar_demo_clientes
pedidos/           # Catálogo público sin login (HU-13), Pedido/ItemPedido/ReservaStock,
                   # services.py (carrito del pedido y registrar_entrega) y config.py (WhatsApp).
                   # Pedido tiene FK a Negocio. ReservaStock con expiración 48h.
administracion/    # Dashboard y CRUD de usuarios (listar/crear/editar/eliminar/roles/toggle).
                   # Panel superadmin (/superadmin/): crear/editar negocios,
                   # crear empleados, asignar negocio a usuario (solo is_superuser).
                   # Reportes de ventas y stock, exportación Excel de stock,
                   # productos sin movimiento.
auditoria/         # RegistroAuditoria + signals: audita cambios en usuarios y ventas
negocios/          # NUEVA APP: modelo Negocio (multiempresa), modelo Proveedor,
                   # modelo Documento (facturas), vista landing pública,
                   # comando migrar_a_multiempresa, comando cargar_demo_todos.
static/            # CSS/JS compartido (styles.css con el estilo visual neón)
templates/         # base.html + templates por app (también 403.html y 404.html)
                   # landing.html (página pública de comercios asociados)
                   # superadmin/ (templates de gestión de negocios y empleados)
                   # pedidos/documentos/ (templates de facturas)
                   # ventas/cierre_turno.html (formulario de arqueo de caja)
```

## Modelo de datos multiempresa

`negocios` → `Negocio` (nombre, slug unique, logo, whatsapp, email, direccion, horarios, color_primario, activo).

`usuarios` → `Empleado` (OneToOne con User, FK a Negocio, activo). Un usuario trabaja en un solo negocio.

`ventas` → `Categoria`, `Producto` (FK a Negocio), `Venta` (FK a Negocio), `DetalleVenta`, `Turno` (FK a Negocio), `PagoMercadoPago`, `ConexionMercadoPago` (FK a Negocio), `ArqueoTurno` (FK a Turno, conteo físico de caja).

`clientes` → `Cliente` (compartido, sin FK a Negocio; un mismo cliente puede comprar en varios negocios), `PagoCuentaCorriente` (FK a Negocio).

`pedidos` → `Pedido` (FK a Negocio), `ItemPedido`, `ReservaStock` (expiración 48h).

## Arquitectura multiempresa (multitenant)

- **Single database + shared schema**: una sola base de datos, todos los datos de todos los negocios en las mismas tablas, aislados por `negocio_id`.
- **Middleware `NegocioMiddleware`**: resuelve `request.negocio` para cada request:
  - `/t/<slug>/` (tienda pública): busca `Negocio` por slug de la URL.
  - Rutas privadas (`/ventas/`, `/clientes/`, `/pedidos/`, `/administracion/`): usa `request.user.empleado.negocio`.
  - `/superadmin/`: sin negocio único (superadmin ve todo).
- **Aislamiento de datos desde el backend**: todas las consultas de modelos con FK a Negocio filtran por `negocio=request.negocio`. Nunca confiar en `negocio_id` enviado por el frontend.
- **Cliente compartido**: `Cliente` no tiene FK a Negocio; un mismo cliente puede comprar en varios negocios. Cada negocio ve solo sus propias `Venta` y `Pedido`.
- **Superadmin**: usuario con `is_superuser=True`. Puede crear negocios, empleados, y acceder a `/superadmin/`.

## URLs

- `/` → Landing pública con recuadros de negocios activos (cada uno lleva a su tienda `/t/<slug>/`).
- `/t/<slug>/` → Tienda pública de un negocio (sin login).
- `/catalogo/` → Catálogo público general (HU-13, mantiene compatibilidad).
- `/app/` → Gestión privada (login requerido, filtrado por negocio del usuario).
- `/superadmin/` → Panel de superadmin (solo `is_superuser=True`).
- `/negocios/documentos/facturas/` → Facturas de servicios y gastos del negocio (luz, gas, seguridad e higiene, otro).
- `/negocios/documentos/proveedores/` → Facturas de mercadería y deuda por proveedor (filtro y pago FIFO).
- `/negocios/documentos/` → Listado histórico sin separar (no se enlaza desde el menú lateral).
- Raíz `/` ya no redirige a login: muestra la landing pública.

## Comandos adicionales

| Tarea | Comando |
|---|---|
| Migrar datos existentes a multiempresa | `python manage.py migrar_a_multiempresa` |
| Poblar 3 negocios con datos de demo | `python manage.py cargar_demo_todos --limpiar` |

## Nuevas funcionalidades (multiempresa)

### Exportación de stock a Excel
Desde `/administracion/reportes/stock/`, el Administrador puede descargar un archivo Excel con todos los productos activos de su negocio (incluye stock=0, excluye inactivos). Columnas: producto, categoría, código de barras, stock actual, stock mínimo, precio, costo, valor a costo, valor a venta, margen unitario, margen %. Archivo: `stock_<slug>_<DD-MM-AAAA>.xlsx`.

### Arqueo de caja (cierre de turno con conteo físico)
Desde `/ventas/cierre_turno/`, al cerrar el turno el cajero o Administrador ingresa los montos físicos contados (efectivo, tarjeta, Mercado Pago). El sistema compara con los totales del sistema y calcula diferencias (sobrante/faltante). Guarda un registro `ArqueoTurno` vinculado al turno.

### Productos sin movimiento
Desde `/administracion/reportes/productos-sin-movimiento/`, lista productos del negocio sin ventas ni pedidos entregados en los últimos X días (default 30). Muestra el **costo** de cada producto (para saber qué precio poner; "—" si no tiene costo cargado) y desde ahí se puede editar el precio directamente (descuento 5%, 10%, 15% o valor manual) o dar de baja el producto. Hay un KPI en el dashboard.

### Reporte de ventas: productos más rentables
`/administracion/reportes/ventas/` muestra el ranking de `productos_mas_rentables` con un toggle **Unidad / Total** arriba a la derecha (`?modo=unidad|total`). En "Unidad" ordena y muestra ganancia, costo y unidades **por unidad vendida** (promedio del período); en "Total" usa los montos acumulados. Cada fila trae ambos juegos de números calculados en la misma consulta.

### Dashboard analítico (selector de período)
`/administracion/dashboard/` arma casi toda su analítica en `administracion/reportes.py`: `resolver_periodo_dashboard` normaliza el período (`7`, `30`, `90` o `personalizado` con `desde`/`hasta`) y `analitica_dashboard` devuelve el bloque completo que consume el template. Un período válido gana sobre las fechas sueltas del querystring. Métricas: ventas del período con variación contra el período anterior y serie diaria/semanal (`serie_dashboard`, con `unidades` por barra para el tooltip), clientes FIAR del negocio (`clientes_fiar`), pedidos pendientes con más de 48 h (`pedidos_pendientes`), rotación top 5 + sin ventas (`rotacion_productos`), ingresos por medio de pago sin fiado (`ingresos_por_metodo_pago`) y vencimientos a 7 días (`proximos_vencimientos`). Los KPIs de "Clientes FIAR" y "Total Usuarios" linkean a `/clientes/?cuenta=corriente` y a "Gestionar usuarios". Tests en `administracion/tests_dashboard_analitica.py` y `administracion/tests_reportes.py`.

### Facturas / Documentos del negocio (rediseñado)
Desde `/negocios/documentos/facturas/` y `/negocios/documentos/proveedores/` (dos ítems separados del menú lateral), el Administrador del negocio puede crear, editar y gestionar documentos. **Facturas** agrupa servicios y gastos (luz, gas, seguridad e higiene, otro) sin deuda de proveedores; **Proveedores** agrupa solo las facturas de mercadería (`categoria="proveedor"`) con resumen de deuda por proveedor y pago FIFO.

Regla única en `negocios/services.py`: el estado se deriva del saldo (`pendiente`/`pagada`; `anulada` es la única decisión manual), "vencida" se mide sobre el saldo, `monto_pagado` es caché actualizado en la misma transacción, y `0 ≤ monto_pagado ≤ monto` es invariable. `DIAS_ALERTA_VENCIMIENTO = 7` unifica el alerta del listado y el dashboard.

Listado: vista por defecto "Por pagar" ordenado por urgencia (vencidas más vieja primero → por vencer más próxima primero → resto), con 6 pestañas (contador siempre visible) y banda de totales (deuda total, vencido, vence esta semana, pagado). Se mantiene compatibilidad con `?estado=`.

Pagos: modelo `PagoDocumento` (documento, negocio, fecha, monto, método, comprobante, usuario, nota, `grupo_pago`). Cada pago registra su historial. `registrar_pago` crea el `PagoDocumento` y actualiza el caché. `aplicar_pago_proveedor` hace FIFO por `fecha_vencimiento` agrupando los pagos bajo un mismo `grupo_pago` (previsualizable antes de confirmar); `deshacer_pago` revierte una operación completa.

Proveedores: CRUD (`crear/editar/detalle`), ficha con cuenta corriente, saldo y vencido, historial de pagos con botón "Deshacer operación" por grupo, y acción "Convertir en proveedor" para los nombres escritos a mano (de a uno, con confirmación; sin migración automática). Acciones de documento: registrar pago, editar, anular (con motivo) y reactivar.

Cada documento tiene monto, monto pagado, fecha de emisión, fecha de vencimiento, estado (pendiente/pagada/anulada), motivo de anulación y un adjunto opcional (PDF, JPG o PNG, máximo 5 MB) que se sube desde `/negocios/documentos/<id>/subir-adjunto/` y se puede ver desde el listado y el detalle del proveedor. Hay KPIs "Deuda a proveedores" y "Deuda a servicios" en el dashboard que enlazan a cada módulo. Alerta automática para facturas que vencen en 7 días. Se puede marcar como pagada con pago parcial o total.

## Templates

- Extienden `base.html` (Bootstrap 5 CDN). Blocks: `titulo`, `contenido`, `body_class`, `menu_lateral`.
- Endpoints de gestión (administración, clientes, pedidos, documentos, ventas) extienden `base_admin.html`: mismo layout + menú lateral fijo (`templates/includes/sidebar_admin.html`). El ítem activo se marca con `{% menu_activo 'url_name' %}` y las secciones solo-Administrador con `{% usuario_admin user %}` (tags en `usuarios/templatetags/roles.py`). El navbar superior es `position: sticky` y publica su alto en `--navbar-alto`.
- HTMX: CDN al final de `base.html`. Las vistas revisan `request.headers.get("HX-Request")` y devuelven solo el partial (ej. `ventas:lista_productos` → `ventas/_productos_tabla.html`).
- Frontend: un solo estilo visual, **neón cian**, fijo — `data-tema="neon"` se fuerza en el `<head>` de `base.html` + `data-theme` (claro/oscuro) en `<html>`; tema oscuro en `localStorage['kiosco-tema']`. No existe selector de estilos (el botón `#estiloToggle` y las paletas cartelera/ticket fueron eliminados); botón `#darkToggle` sí. Vocabulario de animaciones "toldo" al final de `static/css/styles.css`; respetar `prefers-reduced-motion`.

## Usuarios de prueba

| Usuario | Contraseña | Rol | Negocio |
|---|---|---|---|
| `admin` | `kiosco2024` | Superadmin | todos |
| `admin_barrio` | `kiosco2024` | Administrador | Kiosco De Barrio |
| `cajero_barrio_1` | `kiosco2024` | Cajero | Kiosco De Barrio |
| `cajero_barrio_2` | `kiosco2024` | Cajero | Kiosco De Barrio |
| `admin_martillito` | `kiosco2024` | Administrador | Ferretería Martillito |
| `cajero_martillito_1` | `kiosco2024` | Cajero | Ferretería Martillito |
| `cajero_martillito_2` | `kiosco2024` | Cajero | Ferretería Martillito |
| `admin_natural` | `kiosco2024` | Administrador | Dietética Natural |
| `cajero_natural_1` | `kiosco2024` | Cajero | Dietética Natural |
| `cajero_natural_2` | `kiosco2024` | Cajero | Dietética Natural |

Los crea `setup_inicial` + `cargar_demo_todos --limpiar`.

## Flujo de ventas

**Entregar un pedido es cobrarlo**: no existe "marcar entregado" sin venta. El flujo de entrega vive en `pedidos/services.py::registrar_entrega` (llama a `ventas/services.py::registrar_venta_desde_items`, el **núcleo de venta compartido** con el POS, y cobra el **precio congelado** del pedido). No reimplementar reglas de stock/puntos/fiado en `pedidos`: se reusan las de `clientes/services.py`.

**Búsqueda de cliente**: siempre con `clientes/services.py::buscar_clientes` (la usan el POS y el panel de pedidos; ignora acentos). Para tocar datos de un cliente en una venta, usar `clientes/services.py::cliente_bloqueado` (`select_for_update`).

**Dinero en la UI**: siempre con el filtro `|montos` (`{% load formatos %}`, en `usuarios/templatetags/formatos.py`) → `$30.500`, con centavos solo si los hay. Nunca `floatformat` para importes.

**Estilo de código**: nombres de apps y comentarios en español. Seguir las convenciones existentes al agregar apps o archivos nuevos.

## Cobro con QR de Mercado Pago (HU-15/16)

- Método `mercado_pago` en `Venta.METODO_PAGO`. La venta se crea con `services._crear_venta(..., finalizada=False)`: stock reservado, puntos al aprobar.
- Lógica en `ventas/cobro_qr.py`, API en `ventas/mercadopago.py` (urllib, sin dependencias), vistas en `ventas/views_qr.py`. Modelo `PagoMercadoPago`, migración `ventas/0008`.
- Sin `MP_ACCESS_TOKEN` en `.env` → modo de prueba (pago simulado en `/ventas/pagar/<token>/`). Con `TEST-...` usa sandbox.
- Display para el celular del cliente en `/ventas/display/` (misma red: `runserver 0.0.0.0:8000`).
- Botón "Conectar con Mercado Pago" (OAuth) en `/ventas/mercadopago/` (solo Administrador): `ConexionMercadoPago` (una por instalación, migración `ventas/0009`), vistas en `ventas/views_conexion.py`. Token a usar: cuenta conectada → `MP_ACCESS_TOKEN` → modo de prueba. Necesita `MP_CLIENT_ID`/`MP_CLIENT_SECRET` y el sistema online con https.
- Publicación: `render.yaml` (Render). En el servidor `DEBUG=false` y `SECRET_KEY` propia; WhiteNoise y gunicorn están en `requirements.txt`.
