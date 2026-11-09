# Norvex

<img src="static/img/norvex-logo.svg" alt="Logo de Norvex" width="260">

Trabajo práctico de Metodologías Ágiles. **Norvex** (antes "Sistema Kiosco") es una plataforma web de gestión y cobro para comercios: caja, stock, clientes, pedidos de WhatsApp, cuenta corriente "FIAR" y cobro con QR de Mercado Pago. Ahora es una plataforma **multiempresa (multitenant)**: varios comercios pueden usar la misma instalación, cada uno con sus propios productos, clientes, ventas y tienda online, sin que los datos se mezclen.

**Estado:** Sprint 1-4 completos · Consignas de la cátedra completas (HU-13 y HU-14) · Extras: cobro QR (HU-15/16), botón "Conectar con Mercado Pago", recuperación de contraseña con Resend, publicación en Render, arquitectura multiempresa, catálogo público por negocio, panel de superadmin, exportación de stock a Excel, arqueo de caja con conteo físico, productos sin movimiento y módulo de facturas/documentos · **410 tests** en verde.

Publicado en: `https://norvex.onrender.com/`

---

## Documentación

| Documento | Contenido |
|---|---|
| [docs/PRD.md](docs/PRD.md) | Requerimientos de producto (RF-01…RF-115), historias de usuario y criterios de aceptación. |
| [docs/ARD.md](docs/ARD.md) | Arquitectura técnica, modelo de datos, endpoints, autorización y ADRs. |
| [AGENTS.md](AGENTS.md) | Instrucciones para el agente de IA: estructura, modelos, arquitectura multiempresa, URLs, usuarios de prueba y convenciones. |
| [cambios-antes-de-entrega-final.md](cambios-antes-de-entrega-final.md) | Contrato de diseño de la evolución multiempresa. |
| [plan-implementacion-etapas.md](plan-implementacion-etapas.md) | Plan de implementación por etapas de las nuevas funcionalidades. |

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
| Facturas / Documentos | — | Facturas por negocio, PDF adjunto, alerta 7 días, KPI deudas a proveedores | ✅ Completo |

---

## Funcionalidades principales

- **Sprint 1 — Seguridad y roles:** login/logout, roles por Django Groups (`Administrador` / `Cajero`), redirección post-login por rol, registro público sin rol, auditoría de login/logout con IP.
- **Sprint 2 — Catálogo:** CRUD completo de productos con código de barras único, costo (solo admin), stock mínimo y alerta de stock bajo, búsqueda HTMX y ordenamiento por columna.
- **Sprint 3 — Caja:** carrito en sesión, carga por código de barras, edición de cantidades, cobro en efectivo/tarjeta con vuelto y descuento automático de stock.
- **Sprint 4 — Cierres y reportes:** cierre de turno, reportes de ventas y stock (KPIs, serie diaria, top 10, rentabilidad), fidelidad de clientes (1 punto cada $100) con asociación en el cobro.
- **HU-13 — Catálogo público + WhatsApp:** vitrina sin login que no expone el stock exacto, carrito del pedido y envío por WhatsApp. Entregar un pedido es cobrarlo: se cobra el precio congelado usando el mismo núcleo de venta del POS.
- **HU-14 — Cuenta corriente "FIAR":** límite y saldo por cliente, cobro fiado validado en la transacción, registro de pagos (solo admin) y "deuda otorgada" separada de la caja y de los ingresos.
- **HU-15/16 — Cobro con QR de Mercado Pago:** venta pendiente hasta aprobar el pago, stock reservado, puntos al aprobar, pantalla para el celular del cliente y webhook. Sin token: modo de prueba con pago simulado.
- **Conectar con Mercado Pago (OAuth):** el admin conecta la cuenta del negocio y la plata le llega directo a esa cuenta.
- **Recuperación de contraseña:** "¿Olvidaste tu contraseña?" por correo con Resend. Sin `RESEND_API_KEY` el correo se imprime en consola.
- **Arquitectura multiempresa:** modelo `Negocio`, `Empleado` (un empleado = un solo negocio), aislamiento de datos por `negocio_id` desde el backend, tienda pública por `/t/<slug>/`, panel de superadmin para crear negocios y empleados.
- **Tienda pública por negocio:** catálogo sin login por negocio, carrito de pedido, confirmación con retiro en local o envío a domicilio (+$1000), reserva de stock con expiración de 48 horas.
- **Exportación de stock a Excel:** desde el reporte de stock, descarga de Excel con todos los productos del negocio (nombre, categoría, stock, precio, costo, margen).
- **Arqueo de caja:** cierre de turno con conteo físico de efectivo, tarjeta y Mercado Pago; cálculo de diferencia sobrante/faltante.
- **Productos sin movimiento:** KPI en dashboard con productos sin ventas en los últimos 30 días, listado con edición de precio (descuento rápido o manual) y baja de producto.
- **Facturas / Documentos del negocio:** creación, edición y gestión de facturas (luz, gas, seguridad e higiene, proveedores, otro) con monto, fecha de vencimiento, estado (pendiente/pagada/anulada) y archivo PDF adjunto opcional. KPI de "Deudas a proveedores", alerta automática a 7 días del vencimiento, pago parcial soportado.

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
| `admin_martillito` | `kiosco2024` | Administrador | Ferretería Martillito |
| `cajero_martillito_1` | `kiosco2024` | Cajero | Ferretería Martillito |
| `admin_natural` | `kiosco2024` | Administrador | Dietética Natural |
| `cajero_natural_1` | `kiosco2024` | Cajero | Dietética Natural |

### Correr los tests

```powershell
python manage.py test --keepdb
```

410 tests en verde.

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
├── administracion/      # Dashboard, usuarios y reportes
├── auditoria/           # Logs de auditoría
├── templates/
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
- Facturas/documentos del negocio con PDF adjunto, expiración 7 días y KPI de deudas a proveedores

### Pendiente

| Item | Notas |
|---|---|
| Fechas de vencimiento por lote (FIFO) | Para controlar stock por lote de compra y evitar vender productos vencidos. |
| Multi-sucursal por negocio | Un comercio con varios locales, cada uno con su propio stock y caja. |
| Facturación electrónica (AFIP/ARCA) | Generar factura electrónica con CAE y código QR. |
| Notificaciones automáticas | Email o WhatsApp al cliente cuando el pedido está listo. |
| Dashboard comparativo entre negocios | Para el superadmin, comparar ventas entre comercios. |
