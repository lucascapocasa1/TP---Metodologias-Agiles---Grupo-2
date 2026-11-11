# Norvex

<img src="static/img/norvex-logo.svg" alt="Logo de Norvex" width="260">

Trabajo práctico de Metodologías Ágiles. **Norvex** (antes "Sistema Kiosco") es una plataforma web de gestión y cobro para comercios: caja, stock, clientes, pedidos de WhatsApp, cuenta corriente "FIAR" y cobro con QR de Mercado Pago. Ahora es una plataforma **multiempresa (multitenant)**: varios comercios pueden usar la misma instalación, cada uno con sus propios productos, clientes, ventas y tienda online, sin que los datos se mezclen.

**Estado:** Sprint 1-4 completos · Consignas de la cátedra completas (HU-13 y HU-14) · Extras: cobro QR (HU-15/16), botón "Conectar con Mercado Pago", recuperación de contraseña con Resend, publicación en Render, arquitectura multiempresa, catálogo público por negocio, panel de superadmin, exportación de stock a Excel, arqueo de caja con conteo físico, productos sin movimiento, módulos separados de **Facturas** y **Proveedores** (con deuda por proveedor y pago FIFO), layout de gestión con sidebar compartido y **dashboard analítico con selector de período** · **472 tests** en verde.

Publicado en: `https://norvex.onrender.com/`

---

## Documentación

| Documento | Contenido |
|---|---|
| [docs/PRD.md](docs/PRD.md) | Requerimientos de producto (RF-01…RF-115), historias de usuario y criterios de aceptación. |
| [docs/ARD.md](docs/ARD.md) | Arquitectura técnica, modelo de datos, endpoints, autorización y ADRs. |
| [docs/MANUAL_USUARIO.md](docs/MANUAL_USUARIO.md) | Guía rápida de uso: cómo vender, cerrar turno, gestionar facturas y proveedores. |
| [AGENTS.md](AGENTS.md) | Instrucciones para el agente de IA: estructura, modelos, arquitectura multiempresa, URLs, usuarios de prueba y convenciones. |

---

## Estado del proyecto

| Sprint / Etapa | Entrega | Contenido | Estado |
|---|---|---|---|
| 1 | 24-09 | Login, roles y 403 server-side (HU-01…03) | ✅ Completo |
| 2 | 01-10 | Catálogo de productos + gestión de usuarios (HU-04…06) | ✅ Completo |
| 3 | 15-10 | Caja: carrito, edición y cobro con vuelto (HU-07…09) | ✅ Completo |
| 4 | 05-11 | Reportes de ventas y stock, fidelidad de clientes y cierre de turno (HU-10…12) | ✅ Completo |
| Consignas | — | Catálogo público + pedido por WhatsApp con cobro de la entrega (HU-13) y cuenta corriente "FIAR" (HU-14) | ✅ Completo |
| Extras | — | Cobro con QR y pantalla para el cliente (HU-15/16), botón "Conectar con Mercado Pago", recuperación de contraseña con Resend, publicación en Render | ✅ Completo |
| Multiempresa | — | Modelo Negocio, Empleado, aislamiento de datos, tienda pública `/t/<slug>/`, panel superadmin | ✅ Completo |
| Exportación Excel | — | Exportar stock a Excel desde el reporte de stock | ✅ Completo |
| Arqueo de caja | — | Conteo físico al cerrar turno, diferencias sobrante/faltante | ✅ Completo |
| Productos sin movimiento | — | KPI en dashboard, listado con descuento manual y baja de producto | ✅ Completo |
| Facturas | — | Servicios y gastos (luz, gas, seguridad e higiene, otro), PDF adjunto y alerta a 7 días | ✅ Completo |
| Proveedores | — | Facturas de mercadería, deuda por proveedor, filtros y pago FIFO | ✅ Completo |
| Interfaz de gestión | — | Sidebar compartido, navbar sticky y dashboard con KPIs clickeables | ✅ Completo |
| Dashboard analítico | — | Período 7/30/90/personalizado, ventas con variación, clientes FIAR, pedidos pendientes, rotación, medios de pago y vencimientos | ✅ Completo |

---

## Funcionalidades principales

- **Sprint 1 — Seguridad y roles:** login/logout, roles por Django Groups (`Administrador` / `Cajero`), redirección post-login por rol, registro público sin rol, auditoría de login/logout con IP.
- **Sprint 2 — Catálogo:** CRUD completo de productos con código de barras único, costo (solo admin), stock mínimo y alerta de stock bajo, búsqueda HTMX y ordenamiento por columna.
- **Sprint 3 — Caja:** carrito en sesión, carga por código de barras, edición de cantidades, cobro en efectivo/tarjeta con vuelto y descuento automático de stock.
- **Sprint 4 - Cierres y reportes:** cierre de turno, reportes de ventas y stock (KPIs, serie diaria, top 10, rentabilidad con vista por unidad o por total del período), fidelidad de clientes (1 punto cada $100) con asociación en el cobro.
- **HU-13 — Catálogo público + WhatsApp:** vitrina sin login que no expone el stock exacto, carrito del pedido y envío por WhatsApp. Entregar un pedido es cobrarlo: se cobra el precio congelado usando el mismo núcleo de venta del POS.
- **HU-14 — Cuenta corriente "FIAR":** límite y saldo por cliente, cobro fiado validado en la transacción, registro de pagos (solo admin) y "deuda otorgada" separada de la caja y de los ingresos.
- **HU-15/16 — Cobro con QR de Mercado Pago:** venta pendiente hasta aprobar el pago, stock reservado, puntos al aprobar, pantalla para el celular del cliente y webhook. Sin token: modo de prueba con pago simulado.
- **Conectar con Mercado Pago (OAuth):** el admin conecta la cuenta del negocio y la plata le llega directo a esa cuenta.
- **Recuperación de contraseña:** "¿Olvidaste tu contraseña?" por correo con Resend. Sin `RESEND_API_KEY` el correo se imprime en consola.
- **Arquitectura multiempresa:** modelo `Negocio`, `Empleado` (un empleado = un solo negocio), aislamiento de datos por `negocio_id` desde el backend, tienda pública por `/t/<slug>/`, panel de superadmin para crear negocios y empleados.
- **Tienda pública por negocio:** catálogo sin login por negocio, carrito de pedido, confirmación con retiro en local o envío a domicilio (+$1000), reserva de stock con expiración de 48 horas.
- **Exportación de stock a Excel:** desde el reporte de stock, descarga de Excel con todos los productos del negocio (nombre, categoría, stock, precio, costo, margen).
- **Arqueo de caja:** cierre de turno con conteo físico de efectivo, tarjeta y Mercado Pago; cálculo de diferencia sobrante/faltante.
- **Productos sin movimiento:** KPI en dashboard con productos sin ventas en los últimos 30 días, listado con costo y edición de precio (descuento rápido o manual) y baja de producto.
- **Facturas (servicios y gastos):** módulo propio para luz, gas, seguridad e higiene y otros gastos, con monto, fecha de vencimiento, estado (pendiente/pagada/anulada), pago parcial y archivo PDF adjunto opcional. Alerta automática a 7 días del vencimiento y KPI "Deuda a servicios" en el dashboard.
- **Proveedores:** módulo separado con las facturas de mercadería (`categoria="proveedor"`), resumen de deuda pendiente por proveedor, tarjetas de deuda, filtro por proveedor, listado paginado de a 10 y pago FIFO (el pago se aplica primero a la factura más antigua). KPI "Deuda a proveedores" en el dashboard.
- **Interfaz de gestión:** las pantallas privadas comparten `base_admin.html` con sidebar fijo (`includes/sidebar_admin.html`), ítem activo por endpoint y navbar sticky que publica su alto en `--navbar-alto`; el dashboard muestra KPIs clickeables con animación de conteo.

---

## Tecnologías

### Backend
- **Python 3.10+** con **Django 6.1.1** (Django puede servir por WSGI/ASGI: `config/wsgi.py` / `config/asgi.py`).
- **PostgreSQL** como base principal mediante `psycopg2-binary` (lectura de `DATABASE_URL` con `django-environ`; sin `DATABASE_URL` cae a SQLite para desarrollo).
- Arquitectura por apps propias: `usuarios`, `ventas`, `clientes`, `pedidos`, `administracion`, `auditoria`, `negocios`. Lógica de negocio en `services.py` de cada app.
- Autenticación con **Django Authentication** + roles por **Django Groups** y decorador `rol_requerido`.
- Auditoría con **Django signals** (`user_logged_in` / `user_logged_out`).
- Configuración por variables de entorno con `.env` (ver **Configuración**); locale `es-ar`, zona horaria `America/Argentina/Buenos_Aires`.
- **Resend API** para correos (recuperación de contraseña, ver `usuarios/email_backend.py`); sin API key usa backend de consola.
- **Mercado Pago Checkout Pro + OAuth**: cliente con `urllib` de la librería estándar (sin dependencias extra), webhook y consulta de pagos cada 3 s.
- **Openpyxl** para exportación de stock a Excel.
- Producción: **WhiteNoise** para estáticos y **gunicorn** como servidor WSGI, publicado en **Render** con PostgreSQL.

### Frontend
- Plantillas **Django Template Language (DTL)** en `templates/` con layout base `base.html`, Bootstrap 5 + Bootstrap Icons por CDN.
- **HTMX** por CDN para actualizaciones parciales sin recargar (búsqueda de productos, carrito, buscadores de cliente y catálogo público).
- **CSS puro** en `static/css/styles.css` con tokens via CSS custom properties; no usa bundler ni build step. Cobro QR con `static/css/cobro_qr.css`.
- **JavaScript vanilla** para polling (caja QR y pantalla del cliente), tema claro/oscuro en `localStorage['kiosco-tema']` y `prefers-reduced-motion`.
- Estilo único **neón cian** (`data-tema="neon"` forzado en `<head>`), identidad "toldo de barrio", tipografías Righteous + Space Grotesk desde Google Fonts.
- Responsive básico (navbar, login y tablas); errores 403/404 con templates propios.

---

## Decisiones técnicas

- **Base de datos:** PostgreSQL con `DATABASE_URL` en `.env` (fallback a SQLite si no se define).
- **Roles:** Django Groups + decorador `@rol_requerido` / `RolRequeridoMixin`. Sin rol → 403.
- **Carrito en sesión:** la `Venta` solo se crea al confirmar, en una transacción con `select_for_update`.
- **Núcleo de venta compartido:** el POS y la entrega de pedidos usan `ventas/services.py::registrar_venta_desde_items`.
- **Frontend:** Bootstrap 5 + HTMX, estilo único neón cian (`data-tema="neon"`) con modo claro/oscuro en `localStorage`.

---

## Cómo correr el proyecto

### Requisitos

- Python 3.10+
- PostgreSQL corriendo (opcional: sin `DATABASE_URL` usa SQLite)

### Instalación

```powershell
cd "C:\Users\Capocasa\Desktop\UNAB\2026 SEGUNDO CUATRI\METODOLOGIAS AGILES\TP\kiosco_sprint1"
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # y completar DATABASE_URL
python manage.py migrate
python manage.py setup_inicial
python manage.py runserver 8000
```

Abrir `http://127.0.0.1:8000/`.

### Datos de demo

```powershell
python manage.py cargar_demo --limpiar
python manage.py cargar_demo_clientes --limpiar
```

- `cargar_demo`: ~57 productos en 7 categorías y ventas desde el 20/09/2026 (semilla fija, determinístico).
- `cargar_demo_clientes`: clientes con compras reales, puntos, deuda FIAR y pedidos de WhatsApp. Va **después** de `cargar_demo`.
- `cargar_demo_todos --limpiar`: pobla los 3 negocios (Kiosco De Barrio, Ferretería Martillito, Dietética Natural) con productos, usuarios, ventas, pedidos, turnos y clientes.

### Usuarios de prueba

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

### Correr los tests

```powershell
python manage.py test --keepdb
```

464 tests en verde.

---

## Cobro con QR de Mercado Pago

Flujo: el cajero elige **Mercado Pago (QR)** → se genera un link de pago (Checkout Pro) que se dibuja como QR → la caja consulta cada 3 segundos si ya se aprobó → al aprobarse, la venta se finaliza y aparece en el cierre de turno como **Total Mercado Pago (QR)**.

Prioridad del token: **cuenta conectada (OAuth) → `MP_ACCESS_TOKEN` del `.env` → modo de prueba** (pago simulado).

### Cuentas de prueba (sandbox, para facultad)

Para probar el flujo completo en modo sandbox:

| Cuenta | ID | Usuario | Contraseña | Cód. verificación |
|---|---|---|---|---|
| **Comprador** | 3809513038 | `TESTUSER5602888735222767984` | `QX5FnVgdxg` | 513038 |
| **Vendedor** | 3809513042 | `TESTUSER4734636893281846594` | `x7CWpT5XWB` | 513042 |

- El **vendedor** se conecta con el botón **Panel → Mercado Pago → Conectar**.
- El **comprador** escanea el QR y paga con la app de Mercado Pago usando esas credenciales. Con cuentas de prueba también se usa `init_point` (funciona igual que en real).

### Conectar con Mercado Pago (quien publica el sistema)

1. Crear una app (Checkout Pro) en https://www.mercadopago.com.ar/developers/panel/app
2. Cargar `MP_CLIENT_ID` y `MP_CLIENT_SECRET` en el entorno (Render: servicio → Environment).
3. Registrar la URL de vuelta (`https://<dominio>/ventas/mercadopago/callback/`) en la aplicación.
4. Entrar a **Panel → Mercado Pago** y tocar **Conectar**.

### Publicar en Render

Netlify no sirve (solo estático). En Render: **New → Blueprint** y elegir este repo. `render.yaml` crea el sitio y la base PostgreSQL; en cada deploy instala, junta estáticos, migra y corre `setup_inicial`.
Para cargar la demo en la base de Render sin tocar la URL, entrar al servicio → pestaña **Shell** y correr:

```powershell
python manage.py migrate
python manage.py setup_inicial
python manage.py cargar_demo --limpiar
python manage.py cargar_demo_clientes --limpiar
```

---

## Configuración (`.env`)

Copiar `.env.example` a `.env` y completar:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/db_kiosco
KIOSCO_NOMBRE=Kiosco de Barrio
KIOSCO_WHATSAPP=5491155554444
```

Opcionales:

```env
MP_ACCESS_TOKEN=          # vacío = modo de prueba (pago simulado)
MP_CLIENT_ID=
MP_CLIENT_SECRET=
MP_OAUTH_PRUEBA=true
MP_NOTIFICATION_URL=
RESEND_API_KEY=           # vacío = el correo se imprime en consola
```

`.env` no se sube al repositorio (está en `.gitignore`).

---

## Estructura del proyecto

```
kiosco_sprint1/
├── manage.py
├── requirements.txt
├── render.yaml
├── .env.example
├── config/              # Settings y URLs raíz
├── usuarios/            # Auth, roles, setup_inicial
├── ventas/              # Catálogo, POS, turnos, QR de Mercado Pago, cargar_demo
├── clientes/            # Fidelidad, FIAR, cargar_demo_clientes
├── pedidos/             # Catálogo público y pedidos de WhatsApp
├── administracion/      # Dashboard (analítica por período), usuarios y reportes
├── auditoria/           # Logs de auditoría
├── negocios/            # Multiempresa: Negocio, Proveedor, Documento (facturas), landing
├── templates/
│   ├── base.html        # Layout general + navbar sticky + HTMX
│   ├── base_admin.html  # Layout de gestión con sidebar compartido
│   └── includes/sidebar_admin.html
└── static/
```

---

## Backlog

### Hecho

- Login, roles, 403 y post-login por rol · Auditoría con IP · Registro público sin rol
- Catálogo con código de barras, costo, stock mínimo y búsqueda HTMX
- Carrito y cobro con vuelto, descuento de stock y cajero responsable
- Reportes de ventas/stock, fidelidad con puntos y cierre de turno
- Catálogo público + WhatsApp con **entregar = cobrar** (HU-13)
- Cuenta corriente "FIAR" con límite, fiado y pagos (HU-14)
- Cobro QR de Mercado Pago + pantalla del cliente (HU-15/16)
- Botón "Conectar con Mercado Pago" (OAuth) y publicación en Render
- Recuperación de contraseña por correo con Resend
- Arquitectura multiempresa: modelo `Negocio`, `Empleado`, aislamiento de datos por `negocio_id`, tienda pública `/t/<slug>/`, panel superadmin
- Exportación de stock a Excel desde el reporte de stock
- Arqueo de caja con conteo físico y cálculo de sobrante/faltante
- Productos sin movimiento con KPI, descuento manual y baja de producto
- Facturas de servicios y gastos con PDF adjunto, alerta a 7 días y KPI "Deuda a servicios"
- Proveedores como módulo separado: deuda por proveedor, filtros, paginación de 10 y pago FIFO
- Layout de gestión unificado (`base_admin.html` + sidebar compartido) y navbar sticky
- Dashboard con KPIs clickeables y deuda separada por proveedores / servicios
- Dashboard analítico con selector de período (7/30/90 días o rango personalizado):
  - **Ventas del período** con variación % contra el período anterior y gráfico de barras (diario hasta 31 días, semanal para rangos más largos).
  - **Clientes FIAR**: cantidad, deuda total, clientes al límite y top 5 por saldo (solo clientes con ventas en el negocio).
  - **Pedidos sin entregar**: conteo, monto potencial y aviso de pedidos con más de 48 h.
  - **Rotación de stock**: top 5 más vendidos y top 5 sin ventas en el período.
  - **Ingresos por medio de pago**: barras de efectivo / tarjeta / Mercado Pago y el fiado aparte (no es plata de caja).
  - **Próximos vencimientos**: documentos pendientes en los próximos 7 días con monto y link al módulo.
- Demo de los 3 negocios con stock realista y productos sin movimiento

### Pendiente

| Item | Notas |
|---|---|
| Fechas de vencimiento por lote (FIFO) | Para controlar stock por lote de compra y evitar vender productos vencidos. |
| Multi-sucursal por negocio | Un comercio con varios locales, cada uno con su propio stock y caja. |
| Facturación electrónica (AFIP/ARCA) | Generar factura electrónica con CAE y código QR. |
| Notificaciones automáticas | Email o WhatsApp al cliente cuando el pedido está listo. |
| Dashboard comparativo entre negocios | Para el superadmin, comparar ventas entre comercios. |

---

## Dónde quedamos (para retomar mañana)

**Última sesión — 10/11/2026**

- Se amplió el **dashboard** (`/administracion/dashboard/`) con seis mejoras de analítica, todas en la misma pantalla:
  - **Selector de período compartido**: últimos 7 / 30 / 90 días o rango personalizado (por defecto 30). Las fechas solo se muestran cuando se elige "Personalizado" y el período elegido manda sobre las fechas ocultas del formulario.
  - **Ventas del período**: total, ganancia, ticket promedio, unidades y variación % contra el período anterior, con gráfico de barras (diario hasta 31 días; agrupado por semana ISO en rangos más largos).
  - **Clientes FIAR**: cantidad, deuda total, al límite y top 5 por saldo. Como `Cliente` es compartido, solo se cuentan los que tienen ventas en el negocio actual.
  - **Pedidos sin entregar**: conteo, monto potencial y aviso de los que llevan más de 48 h (la reserva de stock vence a las 48 h).
  - **Rotación de stock**: top 5 más vendidos del período y top 5 sin ventas en el mismo rango.
  - **Ingresos por medio de pago**: barras CSS de efectivo / tarjeta / Mercado Pago; el fiado se informa aparte porque no es plata que entró a la caja.
  - **Próximos vencimientos**: ventana fija de 7 días, con monto pendiente y link al módulo de Facturas o Proveedores según la categoría.
- La lógica vive en `administracion/reportes.py` (`resolver_periodo_dashboard`, `analitica_dashboard` y las funciones por métrica) y se testea en `administracion/tests_dashboard_analitica.py`.
- Se mantiene la separación previa de documentos en dos ítems del menú lateral: **Facturas** (`/negocios/documentos/facturas/`, servicios y gastos) y **Proveedores** (`/negocios/documentos/proveedores/`, mercadería, deuda por proveedor y pago FIFO).
- `python manage.py test --keepdb` → **472 tests OK**. Verificado con Playwright: selector de período, tarjetas, gráfico (tooltip propio con unidades del día), paneles, links, tema oscuro, vista móvil y consola sin errores.

**Para retomar:**

```powershell
.\venv\Scripts\Activate.ps1
python manage.py runserver 8000
python manage.py test --keepdb
```

Entrar con `admin_barrio` / `kiosco2024` y revisar `/administracion/dashboard/` con los períodos 7, 30, 90 y personalizado.

---

## Ideas para seguir agregando

### KPIs y tarjetas para el dashboard

Prioridad sugerida: **Alta** = operación diaria; **Media** = relación con el cliente; **Baja** = analítica.

| # | Idea | Qué mostraría | Prioridad |
|---|---|---|---|
| 1 | ~~**Ventas del período**~~ | ✅ Hecho: monto, variación vs. período anterior y gráfico con selector de fechas. | Alta |
| 2 | **Stock crítico (0 unidades)** | Cantidad de productos con `stock = 0`, en rojo, con link directo al reporte de stock. | Alta |
| 3 | **Stock actual vs mínimo** | Total de productos con stock > 0 y cuántos están en o por debajo del mínimo (hoy ya existe "Stock bajo", se puede ampliar el detalle). | Alta |
| 4 | ~~**Clientes FIAR**~~ | ✅ Hecho: cantidad, deuda total, al límite y top 5 por saldo. | Media |
| 5 | ~~**Pedidos públicos pendientes**~~ | ✅ Hecho: conteo, monto potencial y aviso de pedidos con más de 48 h. | Media |
| 6 | **Rentabilidad bruta estimada** | Si todos los productos tienen costo y precio: inversión a costo, ganancia potencial si se vende todo y margen % promedio. | Media |
| 7 | ~~**Rotación de stock**~~ | ✅ Hecho: top 5 más vendidos y top 5 sin ventas en el período. | Baja |
| 8 | **Estado de turnos** | Turnos abiertos sin cerrar y diferencia de caja del último arqueo (sobrante/faltante). | Baja |
| 9 | ~~**Ingresos por método de pago**~~ | ✅ Hecho: efectivo / tarjeta / Mercado Pago con total, cantidad y porcentaje; el fiado va aparte. | Baja |
| 10 | ~~**Próximos vencimientos**~~ | ✅ Hecho: documentos pendientes en los próximos 7 días con monto y link al módulo. | Media |

### Otras mejoras posibles

- **Dashboard por rol:** que el Cajero vea solo su caja y sus ventas del día, no los KPIs de deuda.
- **Dashboard comparativo para superadmin:** ranking de negocios por ventas, deuda y stock.
- **Exportar el dashboard:** botón para descargar los KPIs del mes a Excel/PDF.
- **Alertas configurables:** definir desde la UI los días de anticipación de vencimientos y el umbral de stock bajo por negocio.
- **Historial de deuda por proveedor:** gráfico de evolución de la deuda y de los pagos FIFO.
- **Recordatorio de pago:** marcar facturas próximas a vencer y enviar aviso por email.
- **Tests de la parte visual:** ampliar Playwright a los flujos de alta/edición de facturas y proveedores.
