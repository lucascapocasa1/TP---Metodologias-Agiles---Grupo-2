# Norvex

<img src="static/img/norvex-logo.svg" alt="Logo de Norvex" width="260">

Trabajo práctico de Metodologías Ágiles. **Norvex** (antes "Sistema Kiosco")
es una plataforma web de gestión y cobro para comercios. Nació para un kiosco
de barrio, pero la caja, el stock, los clientes y el cobro con QR no dependen
del rubro: sirve para cualquier negocio que venda productos con precio y stock.

**Estado al 21-10-2026:** Sprint 1 completo · Sprint 2 completo (catálogo de
productos + gestión de usuarios) · Sprint 3 completo (caja y cobro) ·
**Sprint 4 completo** (reportes de ventas y stock + fidelidad de clientes +
cierre de turno) · **consignas de la cátedra completas** (HU-13: catálogo
público + pedido por WhatsApp **con el cobro de la entrega cerrado**; HU-14:
cuenta corriente "FIAR") · estilo neón cian único · **cobro con QR de
Mercado Pago** (HU-15) y pantalla para el celular del cliente (HU-16) ·
marca **Norvex** · botón **"Conectar con Mercado Pago"** para que la plata
le llegue al negocio · listo para publicar en Render · **372 tests** en verde.

---

## Documentación

| Documento | Contenido |
|---|---|
| [docs/PRD.md](docs/PRD.md) | Documento de Requerimientos de Producto (v2.6): alcance, personas, requerimientos funcionales (RF-01…RF-93) y no funcionales, historias de usuario con criterios de aceptación, riesgos y métricas. |
| [docs/ARD.md](docs/ARD.md) | Arquitectura y Requerimientos Técnicos (v2.6): stack, diagramas (flujo y modelo de datos), endpoints, autorización, auditoría, 18 mini-ADRs y calidad. |

Ambos documentos describen el estado del producto al **Sprint 4 completo +
consignas de la cátedra (HU-13 y HU-14)** (versión 21-10-2026) y son el
entregable de documentación del trabajo práctico.

---

## Estado del proyecto

| Sprint | Contenido | Estado |
|---|---|---|
| 1 | Login, roles y 403 server-side (HU-01…03) | ✅ Completo |
| 2 | Catálogo de productos + gestión de usuarios (HU-04…06) | ✅ Completo |
| 3 | Caja: carrito, edición del carrito y cobro con vuelto (HU-07…09) | ✅ Completo (cerrado 05-10) |
| 4 | Reportes de ventas y stock (HU-11), fidelidad de clientes (HU-12) y cierre de turno (HU-10) | ✅ Completo (19-10) |
| — | Consignas de la cátedra: integración externa (catálogo público + pedido por WhatsApp) y cuenta corriente ("FIAR") | ✅ Completo (19-10): HU-13 y HU-14 |
| — | Cierre del flujo de HU-13: **entregar un pedido es cobrarlo** (la venta del mostrador queda vinculada al pedido de WhatsApp) | ✅ Completo (21-10) |
| — | Cobro con QR de Mercado Pago (HU-15), pantalla para el celular del cliente (HU-16) y marca Norvex | ✅ Completo (23-10) |
| — | Botón "Conectar con Mercado Pago" (la plata le llega al negocio) y sistema listo para publicar | ✅ Completo (23-10) |

El detalle de cada sprint está en los apartados **Alcance de Sprint 1-4**;
el avance item por item, en [Backlog](#backlog). Las dos consignas nuevas de
la cátedra (catálogo online + pedido por WhatsApp y cuenta corriente) están
en [Integración externa y cuenta corriente](#integración-externa-y-cuenta-corriente-pedido-de-la-cátedra).

---

## Qué cambió en esta versión (Conectar con Mercado Pago — 23-10-2026)

### El problema

Para cobrar con QR, el sistema necesita saber **a qué cuenta de Mercado Pago
mandar la plata**. Pedirle al dueño de un negocio que entre al panel de
desarrolladores y copie un token es complicado, y con el alias solo no
alcanza: Mercado Pago no deja que un sistema vea los pagos de una cuenta
sabiendo solo el alias.

### La solución: botón "Conectar con Mercado Pago" (OAuth)

Es lo que usan Tiendanube, PedidosYa y otras plataformas:

1. El administrador entra a **Panel → Mercado Pago** y toca **Conectar con
   Mercado Pago**.
2. Se abre Mercado Pago: inicia sesión con la cuenta del negocio y toca
   **Autorizar**.
3. Mercado Pago lo devuelve a Norvex con un código de un solo uso, que el
   sistema canjea por las credenciales de esa cuenta y las guarda.
4. Desde ese momento, **cada cobro con QR se hace a nombre de esa cuenta**: la
   plata le llega directo al negocio. Si se desconecta, vuelve al modo de prueba.

**¿A qué cuenta va la plata?** A la cuenta conectada; si no hay, a la del
`MP_ACCESS_TOKEN` del `.env` (desarrollo); si tampoco hay, no se cobra:
**modo de prueba** con pago simulado.

**No se mezclan negocios:** cada negocio tiene **su propia instalación** de
Norvex (su servidor y su base), con **una** cuenta conectada. Si en el futuro
el sistema pasa a multi-negocio, `ConexionMercadoPago` está pensada para
agregarle un FK al negocio sin rehacerla.

**Seguridad:**
- Solo el **Administrador** puede conectar o desconectar (el cajero: 403).
- La vuelta de Mercado Pago se valida con un `state` al azar guardado en la
  sesión: otra página no puede forzar la conexión de una cuenta ajena.
- Las credenciales no se muestran en ninguna pantalla ni en el admin de Django.
- El token dura ~6 meses: si le faltan menos de 7 días, se renueva solo con el
  `refresh_token`.
- Conectar y desconectar queda en la **auditoría**.

**Requisito:** Mercado Pago solo vuelve a direcciones `https://`, así que el
botón funciona con el **sistema publicado** (ver "Publicar el sistema") o con
un **túnel** desde la PC. En `127.0.0.1` el panel lo avisa y la caja sigue en
modo de prueba. Además, publicado con `https`, cada cobro le pasa a Mercado
Pago la dirección del **webhook**, y el pago se confirma al instante.

### Archivos

| Archivo | Cambio | Por qué |
|---|---|---|
| `ventas/models.py` | Nuevo modelo `ConexionMercadoPago` (token, refresh token, vencimiento, cuenta, prueba/real, quién la conectó) | Guardar la cuenta del negocio. Una por instalación. |
| `ventas/migrations/0009_conexion_mercadopago.py` | Nueva migración | |
| `ventas/mercadopago.py` | Elige el token (cuenta conectada → `.env` → prueba); OAuth: `url_autorizacion`, `conectar_cuenta`, `renovar_conexion`, `desconectar_cuenta` | Toda la charla con Mercado Pago en un solo lugar. |
| `ventas/views_conexion.py` | Nuevo: panel, conectar, callback y desconectar (`@rol_requerido("Administrador")`) | |
| `ventas/cobro_qr.py` | Manda la URL del webhook a Mercado Pago cuando el sistema está online con `https` | Confirmación instantánea del pago. |
| `templates/ventas/mercadopago_config.html` | Nueva pantalla **Panel → Mercado Pago** | |
| `templates/administracion/dashboard.html` | Tarjeta "Mercado Pago" en el panel | |
| `config/settings.py` | `MP_CLIENT_ID`, `MP_CLIENT_SECRET`, `MP_OAUTH_PRUEBA`, `MP_REDIRECT_URI`; `DEBUG` y `SECRET_KEY` desde el `.env`; `STATIC_ROOT`, WhiteNoise y https detrás del proxy | Poder publicar el sistema sin cambiar nada para el que corre en local. |
| `requirements.txt` | `whitenoise` (sirve los estáticos publicado) y `gunicorn` (servidor web) | Solo se usan en el servidor; en local todo sigue igual. |
| `render.yaml` | Nuevo: publica el sitio y la base en Render con un clic | |
| `ventas/tests_conexion_mp.py` | 16 tests nuevos | Ver "Correr los tests". |

---

## Versión anterior: Mercado Pago y Norvex — 23-10-2026

### Historias de usuario nuevas

**HU-15 — Cobro con QR de Mercado Pago**
Como cajero, quiero cobrar con un QR de Mercado Pago para que el cliente pague
con la app desde su celular, sin efectivo ni tarjeta.
- Criterio de aceptación: la caja se entera sola cuando el pago se aprueba y
  muestra el comprobante. Hasta entonces la venta no cuenta en reportes ni en
  el turno. Si cancelo el cobro, el stock vuelve y los productos regresan al
  carrito.

**HU-16 — Pantalla para el cliente en un celular**
Como dueño, quiero dejar un celular en el mostrador mirando al cliente que
muestre el QR de cada cobro, para que lo escanee cómodo.
- Criterio de aceptación: el celular se actualiza solo (espera → QR →
  "¡Pago aprobado!") sin que nadie lo toque.

### Cómo funciona el cobro con QR

1. En el carrito aparece un método más: **Mercado Pago (QR)**. Al elegirlo, el
   botón pasa a "Generar QR de Mercado Pago".
2. Se crea la `Venta` con el **mismo núcleo** que el resto de los cobros
   (`services._crear_venta`), pero con `finalizada=False`: el stock queda
   reservado y la venta todavía no cuenta en reportes ni en el turno. Los
   puntos de fidelidad se suman recién al aprobarse el pago.
3. El servidor pide a la API de Mercado Pago (Checkout Pro) un link de pago con
   los productos de la venta; ese link es el que se dibuja como QR.
4. La caja pregunta cada 3 segundos si ya se pagó; el servidor consulta a
   Mercado Pago si hay un pago aprobado con la referencia `norvex-venta-<id>`.
   También hay un **webhook** para cuando el sistema esté en un servidor
   público: el aviso no se cree a ciegas, se vuelve a pedir el pago a la API.
5. Aprobado el pago, la venta pasa a finalizada y la caja abre el comprobante.
   En el cierre de turno aparece **"Total Mercado Pago (QR)"** aparte de
   efectivo y tarjeta.

**Modo de prueba:** sin `MP_ACCESS_TOKEN` en el `.env`, el QR abre una página
de **pago simulado** del propio sistema. Así se muestra todo el circuito sin
cuenta de Mercado Pago ni plata real. Con un token `TEST-...` se usa el
entorno de pruebas (sandbox) de Mercado Pago.

### Archivos

| Archivo | Cambio | Por qué |
|---|---|---|
| `ventas/models.py` | `Venta.METODO_PAGO` suma `mercado_pago`; `Turno.total_mercado_pago`; nuevo modelo `PagoMercadoPago` (link de pago, estado, ID de pago, si es simulado) | Registrar el cobro QR y su estado sin tocar cómo funcionan los demás métodos. |
| `ventas/migrations/0008_mercadopago_qr.py` | Nueva migración | `total_mercado_pago` tiene `db_default=0`, así el código anterior puede seguir abriendo turnos en una base compartida. |
| `ventas/services.py` | `_crear_venta(..., finalizada=True)`: con `False` deja la venta pendiente y no suma puntos todavía. El turno suma Mercado Pago | El QR usa **las mismas** reglas de stock, cliente y precio que el POS. |
| `ventas/mercadopago.py` | Nuevo: llamadas a la API (crear preferencia, buscar pago aprobado, obtener pago) con `urllib` | Sin dependencias nuevas en `requirements.txt`. |
| `ventas/cobro_qr.py` | Nuevo: iniciar, aprobar y cancelar el cobro QR | Lógica del QR separada del resto del cobro. |
| `ventas/views.py` | `cobro_confirmar` deriva a QR si el método es Mercado Pago; el contexto de la caja suma el cobro en curso | Único cambio sobre las vistas existentes. |
| `ventas/views_qr.py` | Nuevo: estado del pago, cancelar, display del celular, pago simulado y webhook | Vistas del QR en un archivo propio. |
| `ventas/urls.py` | Rutas `cobro/qr/<id>/estado/`, `cobro/qr/<id>/cancelar/`, `display/`, `display/estado/`, `pagar/<token>/`, `mercadopago/webhook/` | |
| `templates/ventas/_carrito.html` | Ícono de QR y texto "Generar QR" para el método nuevo | |
| `templates/ventas/pantalla_cobro.html` | Ventana con el QR que espera el pago + tarjeta "Mostrar el QR en un celular" | |
| `templates/ventas/cierre_turno.html` | Tarjeta "Total Mercado Pago (QR)" | |
| `templates/ventas/display.html`, `pago_simulado.html`, `_cabeza_celular.html` | Nuevas: pantalla del celular y pago de prueba | |
| `static/css/cobro_qr.css` | Estilos del QR con los tokens neón | Aparte de `styles.css` para no generar conflictos. |
| `config/settings.py` | Variables `MP_*`; `ALLOWED_HOSTS` acepta la IP de la PC (celular); conexión a la base persistente y sesiones en caché | Con Supabase cada consulta tarda ~180 ms: reusar la conexión ahorra ~1 s por pantalla. |
| `ventas/tests_mercadopago.py` | 16 tests nuevos | Ver "Correr los tests". |

### Marca Norvex

- **Nombre:** Norvex en el navbar, el login, las pestañas y el panel.
- **Logo:** una "N" cuya pata derecha es una flecha hacia arriba (crecimiento
  del negocio), en cian neón sobre noche. Archivos: `static/img/norvex-logo.svg`
  (con el nombre, para presentaciones), `static/img/favicon.svg` y
  `templates/includes/norvex_marca.svg` (la "N" que se usa en la app y toma el
  color del texto).
- El catálogo público sigue mostrando el **nombre del negocio**
  (`KIOSCO_NOMBRE`), porque es lo que tiene que ver el cliente del local.

---

## Versión anterior: cierre de HU-13 — 21-10-2026

Todo el detalle conceptual está en el [PRD](docs/PRD.md) (RF-85…RF-92) y en el
[ARD](docs/ARD.md) (ADN-18). Acá está el inventario, archivo por archivo, de
**qué se tocó y por qué**:

### Modelo de datos

| Archivo | Cambio | Por qué |
|---|---|---|
| `pedidos/models.py` | `Pedido.cliente` (FK `clientes.Cliente`, `SET_NULL`, `related_name="pedidos"`) y `Pedido.venta` (FK `ventas.Venta`, `SET_NULL`, `related_name="pedidos"`) + properties `fue_cobrado` y `esta_pendiente` | El pedido de WhatsApp tiene que quedar **ligado** al cobro del mostrador: sin esto, un pedido "entregado" no tenía venta ni cliente. |
| `pedidos/migrations/0002_pedido_cliente_pedido_venta.py` | Nueva migración (depende de `clientes 0002` y `ventas 0007`) | La referencia va **de `pedidos` hacia `ventas.Venta`** (y no al revés) para que las migraciones no se ciclen: `ventas` no sabe nada de `pedidos`. |

### Núcleo de venta compartido (`ventas/`)

| Archivo | Cambio | Por qué |
|---|---|---|
| `ventas/services.py` | Se extrajo `_precio_de_item` y `_crear_venta` (núcleo **sin transacción propia**) | El POS y la entrega de un pedido tienen que aplicar **las mismas** reglas de stock, puntos y fiado. |
| `ventas/services.py` | Nuevo `registrar_venta_desde_items(items, metodo_pago, cliente, usuario, monto_entregado)` | Abre la transacción y bloquea al cliente (`select_for_update`). Es el punto de entrada del POS **y** de la entrega. |
| `ventas/services.py` | `confirmar_venta` conserva su firma y sus mensajes (es un wrapper del núcleo) | No se rompe nada de lo que ya estaba: el POS sigue igual, pero ahora comparte el código. |
| `ventas/services.py` | `_precio_de_item` acepta un **precio opcional por ítem** | La entrega cobra el **precio congelado** del pedido (lo que el cliente vio), no el precio actual del catálogo. |

### Flujo de entrega (`pedidos/`)

| Archivo | Cambio | Por qué |
|---|---|---|
| `pedidos/services.py` | Nuevo `items_del_pedido_para_cobro(pedido)` | Convierte los ítems del pedido en items listos para cobrar, con el precio congelado. |
| `pedidos/services.py` | Nuevo `registrar_entrega(pedido, cliente, metodo_pago, usuario, monto_entregado=None)` | **Entregar es cobrar**: bloquea el pedido, valida que siga pendiente, llama al núcleo de venta del POS y deja el pedido `entregado` con su venta y su cliente. Todo en **una sola transacción**. |
| `pedidos/views.py` | Nuevo `entregar_pedido` (POST) | La vista del cobro: busca el cliente, cobra y **audita** la entrega. |
| `pedidos/views.py` | Nuevo `buscar_cliente_pedido` (GET, HTMX) | Buscador de cliente del panel, con la búsqueda compartida del POS. |
| `pedidos/views.py` | `cambiar_estado_pedido` **rechaza** el estado `entregado` | No existe "marcar entregado" sin cobrar: el estado se deriva del cobro, no se escribe a mano. |
| `pedidos/urls.py` | Rutas `pedidos:entregar` y `pedidos:buscar_cliente` | Los dos endpoints nuevos. |
| `pedidos/services.py` | Comentario actualizado en `agregar_al_pedido` | Decía "el descuento real ocurre en el cobro del POS": ahora ocurre en la entrega. |

### Búsqueda de cliente compartida (`clientes/`)

| Archivo | Cambio | Por qué |
|---|---|---|
| `clientes/services.py` | Nuevo `buscar_clientes(consulta)` | **Una sola** búsqueda para el POS y el panel de pedidos (DNI, nombre o apellido; mínimo 2 caracteres, máximo 8 resultados). |
| `clientes/services.py` | Nuevo `_sin_acentos(texto)` + segundo repaso sin acentos | Postgres compara los acentos: en el mostrador nadie escribe tildes, así que "perez" tiene que encontrar a "Pérez". Bug real, affects las dos pantallas. |
| `clientes/services.py` | Nuevo `cliente_bloqueado(cliente)` | `select_for_update` sobre la fila del cliente para que dos cobros simultáneos no se pisen los puntos ni la deuda. |
| `clientes/views.py` | `buscar_cliente` refactorizado | Usa el helper compartido en vez de su propia consulta. |

### Vista y estilos

| Archivo | Cambio | Por qué |
|---|---|---|
| `templates/pedidos/detalle_pedido.html` | Reescrito: card **"Entregar y cobrar"** con buscador de cliente, métodos de pago, monto entregado y **vuelto en vivo**; muestra la venta cuando ya se cobró | El kiosquero cobra lo que el cliente pidió, en la misma pantalla donde ve el pedido. |
| `templates/pedidos/_resultados_cliente.html` | Nuevo partial HTMX | Resultados del buscador de cliente del panel. |
| `static/css/styles.css` | Nuevas clases `.pedido-entrega-card`, `.pedido-entrega-form`, `.pedido-nota`, `.pedido-cobro-resumen` | Estilos de la nueva card, en el mismo lenguaje visual neón. |

### Demo reproducible

| Archivo | Cambio | Por qué |
|---|---|---|
| `clientes/demo_data.py` | Nuevo módulo con los datos de la demo (clientes, perfiles de pago y pedidos) | La demo es **dato declarativo**, no un script ad-hoc. |
| `clientes/management/commands/cargar_demo_clientes.py` | Nuevo comando `cargar_demo_clientes [--limpiar]` | Crea clientes **con compras reales** y los pedidos de WhatsApp; los entregados se cobran **con el flujo real** (`registrar_entrega`). `--limpiar` borra, repone el stock y recarga. |

### Tests

| Archivo | Cambio |
|---|---|
| `pedidos/tests.py` | Nueva clase `EntregaPedidoTests` (19 casos) + `test_buscar_clientes_del_panel_ignora_los_acentos`; `test_cambiar_estado_a_entregado` pasó a `test_cambiar_estado_a_entregado_exige_cobrar` |
| `clientes/tests.py` | 3 casos de búsqueda sin acentos + nueva clase `DemoClientesTests` (8 casos: todo cliente cargado tiene compras, la deuda es lo fiado menos lo pagado, los puntos suman las ventas, los pedidos pendientes no son clientes, los entregados cobran de verdad, no queda stock negativo, `--limpiar` devuelve el stock y recarga la misma demo) |

**Balance:** la suite pasó de **309 → 340 tests**, todos en verde.

---

## Alcance de Sprint 1 — Seguridad y roles (Entrega 24-09)

> "Necesito poder entrar al sistema con mi usuario y contraseña, y que los
> empleados (los cajeros) solo puedan usar la pantalla de cobro y no entren
> a tocar la parte de administración o precios."

**Estado:** completo.

### Historias de usuario

**HU-01 — Login del sistema**
Como usuario del sistema (dueño o cajero), quiero ingresar con usuario y
contraseña para que solo personal autorizado pueda operar el kiosco.
- Criterio de aceptación: con credenciales válidas se ingresa al sistema;
  con credenciales inválidas se muestra un error y no se ingresa.
- *Estado: ✅ Hecho.*

**HU-02 — Separación de roles: Cajero**
Como dueño, quiero que el cajero solo pueda ver la pantalla de cobro, para
que no tenga acceso a costos, precios ni reportes del negocio.
- Criterio de aceptación: un usuario del grupo *Cajero* que intenta acceder
  a una URL de administración recibe "Acceso denegado" (403), y accede sin
  problemas a la pantalla de cobro.
- *Estado: ✅ Hecho.*

**HU-03 — Separación de roles: Administrador**
Como dueño, quiero tener un usuario administrador con acceso total, para
manejar yo mismo la parte sensible del negocio (desde el local o de forma
remota).
- Criterio de aceptación: un usuario del grupo *Administrador* accede tanto
  al panel de administración como a la pantalla de cobro.
- *Estado: ✅ Hecho.*

### Qué se implementó

- Login con usuario y contraseña (Django Authentication).
- Roles basados en Django Groups: "Administrador" y "Cajero".
- Restricción server-side por decorador (`usuarios/decorators.py`): el cajero
  que escribe la URL a mano recibe 403, no solo se le oculta el botón.
- Redirección post-login por rol: cajero va directo a cobro, admin al dashboard.
- Pantallas protegidas por login/roles para cobro y administración.
- Registro público de cuentas (`/usuarios/registro/`): nace **sin rol** y cae
  en `sin_rol` hasta que un administrador le asigne uno.
- Auditoría automática de login/logout con IP (`auditoria/signals.py`).

---

## Alcance de Sprint 2 — Cargar y ordenar los productos (Entrega 01-10)

> "Poder cargar los productos nuevos uno tras otro rápido, poniéndoles el
> nombre, el código de barras, cuánto me costó, a cuánto lo vendo y cuántos
> tengo. Si el código ya existe, avísame."

**Estado:** completo (HU-04, HU-05 y HU-06 implementadas y testeadas).

### Historias de usuario

**HU-04 — Alta rápida de productos**
Como administrador, quiero cargar un producto nuevo ingresando nombre,
código de barras, precio de costo, precio de venta y stock, para tener el
catálogo actualizado.
- Criterio de aceptación: si el código de barras ya existe, el sistema
  muestra un error y no permite el duplicado.
- *Estado: ✅ Hecho.*

**HU-05 — Lista de productos con búsqueda**
Como administrador, quiero una lista donde pueda buscar cualquier producto
por nombre o código para modificarle el precio o corregir el stock.
- Criterio de aceptación: la búsqueda filtra en tiempo real (HTMX).
- *Estado: ✅ Hecho.*

**HU-06 — Alerta de stock bajo**
Como administrador, quiero que el sistema me marque en color los productos
que se están quedando sin stock, para saber qué tengo que salir a reponer.
- Criterio de aceptación: productos con stock ≤ 5 se muestran marcados.
- *Estado: ✅ Hecho.*

### Modelos (implementados)

- **Categoria**: nombre, descripción.
- **Producto**: nombre, descripción, precio de venta, **costo** (solo lo ve el
  administrador), stock, stock mínimo, código de barras (único), categoría
  (FK), activo.
- **Venta**: fecha/hora, total, finalizada, método de pago, cajero, monto
  entregado, vuelto, **cliente** (opcional) y **puntos ganados**.
- **DetalleVenta**: venta, producto, cantidad, precio unitario,
  **costo_unitario**, `subtotal()`, `costo_total()`, `ganancia()`.
- **Cliente** (app `clientes`, Sprint 4): nombre, apellido, DNI/CUIT (único,
  normalizado), teléfono, email, fecha de registro, **puntos**, **límite de
  crédito** (`limite_credito`, 0 = sin cuenta corriente), **saldo de deuda**
  (`saldo_deuda`) y activo.
- **PagoCuentaCorriente** (HU-14): cliente, monto, fecha, usuario que lo cobró y
  observación; es el historial de pagos de la deuda.
- **Turno** (Sprint 4, cierre de caja): usuario a cargo, fecha de apertura,
  fecha de cierre (vacía mientras está abierto), **total_efectivo**,
  **total_tarjeta**, **deuda_otorgada** (lo fiado, que no entra a la caja) y
  **cantidad_operaciones** (estos se congelan al cerrar).

---

## Alcance de Sprint 3 — La caja y las ventas (Entrega 15-10)

> "Cuando esté en la pantalla del cajero, quiero pasar el lector de código de
> barras o tipear el código, apretar Enter y que el producto se cargue al
> toque en el carrito sin tener que usar el mouse."

**Estado:** completo (HU-07, HU-08 y HU-09 implementadas y testeadas; cerrado
el 05-10, diez días antes de la entrega del 15-10).

### Historias de usuario

**HU-07 — Carga rápida de productos al carrito**
Como cajero, quiero escanear o tipear un código de barras y que el producto
se agregue al carrito de inmediato.
- Criterio de aceptación: si escaneo el mismo producto dos veces, se suma
  la cantidad (2) en vez de crear una fila duplicada.
- *Estado: ✅ Hecho.*

**HU-08 — Editar carrito antes de cobrar**
Como cajero, quiero poder borrar un producto del carrito o cambiar la
cantidad antes de confirmar la venta.
- Criterio de aceptación: el total se recalcula al modificar el carrito.
- *Estado: ✅ Hecho.*

**HU-09 — Cobro con efectivo o tarjeta**
Como cajero, quiero indicar si el cliente paga en efectivo o tarjeta,
ingresar el monto entregado y que el sistema calcule el vuelto exacto.
- Criterio de aceptación: el stock se descuenta automáticamente al
  confirmar la venta.
- *Estado: ✅ Hecho.*

### Cómo está implementado

- **Carrito en la sesión** (`request.session["carrito"]`), no en la base de
  datos: no quedan ventas "a medias" que ensucien los reportes (ADN-11 del ARD).
- **`ventas/services.py`**: `buscar_producto`, `agregar_al_carrito`,
  `modificar_cantidad`, `total_del_carrito` y `confirmar_venta`
  (transacción + `select_for_update` + descuento de stock).
- **Endpoints HTMX**: `/ventas/cobro/agregar/`, `/ventas/cobro/cantidad/` y
  `/ventas/cobro/confirmar/` responden el partial `_carrito.html`;
  `/ventas/cobro/buscar/` responde las sugerencias del escáner
  (`_cobro_resultados.html`) desde 3 caracteres.
- **`Venta` ampliada** (migración `0004`): `metodo_pago` (efectivo/tarjeta),
  `usuario` (cajero responsable, `SET_NULL`), `monto_entregado` y `vuelto`.
- **Auditoría**: cada venta confirmada se registra con
  `registrar_accion()`, y el comprobante es visible solo para quien la cobró
  o para un administrador (403 si no).

---

## Alcance de Sprint 4 — Cierres y saber qué se vende (Entrega 05-11)

> "Cuando termina el turno o el día, quiero apretar un botón y que me tire
> el total de plata que entró en efectivo, en tarjeta y cuántas ventas hice."

**Estado:** ✅ **Completo (19-10).** Los **reportes de ventas y stock se
entregaron adelantado** (05-10) con `administracion/reportes.py`, la
**fidelidad de clientes** (HU-12) se sumó el 17-10 con la app `clientes/` y el
**cierre de turno** (HU-10) se integró el 19-10 desde la rama `Cierre_caja`.

### Historias de usuario

**HU-10 — Cierre de turno**
Como cajero, quiero cerrar mi turno y que el sistema me muestre el total
en efectivo, en tarjeta y la cantidad de operaciones realizadas, para poder
contar la plata de la caja.
- Criterio de aceptación: se registra qué usuario estaba a cargo del turno.
- *Estado: ✅ Hecho (19-10).*

**HU-11 — Reporte de productos más vendidos**
Como administrador, quiero ver un reporte de los productos más vendidos,
para no quedarme sin mercadería de lo que más sale.
- Criterio de aceptación: el reporte muestra el top 10 de productos por
  cantidad vendida en un período seleccionable.
- *Estado: ✅ Hecho.*

**HU-12 — Clientes frecuentes (opcional)**
Como administrador, quiero poder registrar clientes con nombre y CUIT/DNI,
para que el cajero pueda asociar una venta a un cliente cuando lo solicite
(sin interrumpir el flujo del consumidor final).
- Criterio de aceptación: el cajero busca por CUIT y trae los datos
  automáticamente; si es nuevo, lo carga en una ventanita rápida.
- *Estado: ✅ Hecho (17-10).*

### Cómo está implementado el módulo de clientes (HU-12)

- **App propia `clientes/`** con el modelo `Cliente` (DNI/CUIT único y
  normalizado: se aceptan puntos y guiones al cargarlo, se guardan sin ellos),
  teléfono, email, fecha de registro, puntos y baja lógica (`activo`).
- **Fidelidad de puntos**: 1 punto cada $100 de compra
  (`clientes/services.py::PUNTOS_POR_PESO`). `Venta.puntos_ganados` guarda lo
  que sumó cada venta, así que el historial no se recalcula si después cambia
  la regla ni si se da de baja el cliente.
- **CRUD solo para el administrador**
  (`/clientes/`, `/clientes/crear/`, `editar/`, `eliminar/` y la ficha
  `detalle/`): el cajero recibe 403, igual que en el catálogo.
- **Asociación en el cobro** (`@login_required`): el cajero busca el cliente
  por DNI y lo asocia al carrito, que vive en la sesión; la venta se ata al
  cliente recién al confirmar (`Venta.cliente`, `SET_NULL`). Si el cliente es
  nuevo, el alta rápida lo crea y lo asocia sin salir de la pantalla de cobro.
- **Venta sin cliente**: el flujo del consumidor final no cambia; asociar un
  cliente es siempre opcional.
- **Auditoría**: el alta/edición/baja y la venta con cliente quedan registradas
  con `registrar_accion()`.

### Cómo está implementado el cierre de turno (HU-10)

- **Modelo `Turno`** (`ventas/models.py`, migración `0006`): guarda el
  `usuario` a cargo (FK `SET_NULL`), la `fecha_apertura`, la `fecha_cierre`
  (vacía mientras el turno sigue abierto) y el **snapshot** del cierre
  (`total_efectivo`, `total_tarjeta`, `deuda_otorgada`, `cantidad_operaciones`).
- **Servicios** (`ventas/services.py`): `abrir_turno()` no permite dos turnos
  activos de la misma persona; `turno_abierto()` busca el turno sin cerrar;
  `totales_del_turno()` calcula en vivo mientras está abierto y devuelve el
  snapshot congelado una vez cerrado; `cerrar_turno()` guarda los totales
  dentro de una transacción con `select_for_update` para que el histórico no
  cambie si después se registran más ventas.
- **Qué cuenta**: solo ventas `finalizada=True` del usuario del turno, dentro
  de su franja (desde la apertura hasta el cierre o hasta ahora). Se separan
  **efectivo** y **tarjeta** (los métodos en `METODOS_EN_CAJA`); lo fiado a
  **cuenta corriente** no entra a la caja: se muestra aparte como **"Deuda
  otorgada (FIAR)"** y se congela en `Turno.deuda_otorgada` (HU-14).
- **Pantalla** `/ventas/turno/cierre/` (`ventas/cierre_turno.html`): abrir
  turno, ver los totales en vivo, cerrarlo y consultar el resumen del turno
  (el recién cerrado con `?turno=<id>` o cualquier histórico). Accesible desde
  el atajo "Cierre de turno" en la pantalla de cobro y desde el dashboard.
- **Control de responsable**: cualquiera puede abrir su propio turno; ver o
  cerrar el turno de otro devuelve 403 salvo para el Administrador.
- **Auditoría**: el cierre queda registrado con `registrar_accion()`
  ("Cierre de turno", con los totales formateados y la cantidad de
  operaciones). 20 tests.

---

## Integración externa y cuenta corriente (pedido de la cátedra)

Son las dos consignas nuevas de la cátedra. **Ambas están implementadas**
(19-10): la **integración externa (HU-13)** y la **cuenta corriente (HU-14)**.

### 1) Integración externa: catálogo online + pedido para retiro ("take away") — ✅ Hecho

**Lo que se pedía:** una vista pública (sin login) donde los vecinos vean el
stock y los precios actuales del kiosco, armen un pedido y lo envíen por
WhatsApp al local, para que el cajero solo tenga que cobrarlo cuando el cliente
llegue a retirarlo.

**Cómo quedó implementado:**

- **App `pedidos/`** con los modelos `Pedido` y `ItemPedido` (migración
  `0001_initial`). El pedido **no es una `Venta`**: no descuenta stock ni entra
  a la caja por sí solo; se cobra en el POS cuando el cliente retira.
- **Catálogo público en `/catalogo/`** (`pedidos:catalogo`), sin
  `@login_required`, con filtro por categoría. La disponibilidad se muestra
  como **"Disponible" / "Agotado"** (`Producto.stock > 0`), **nunca la
  cantidad exacta** de stock.
- **Carrito del pedido en sesión** (`session["pedido"]`, separado del carrito
  del POS): agregar, quitar y confirmar con el nombre de quien pide.
- **Mensaje y link a WhatsApp** armados en el servidor (`pedidos/config.py`):
  el teléfono del local sale de `KIOSCO_WHATSAPP` (y el nombre, de
  `KIOSCO_NOMBRE`) en el `.env`; si no está configurado, la pantalla avisa en
  vez de abrir un chat a un número de prueba.
- **Panel interno de pedidos** (`/catalogo/panel/`, solo Administrador):
  listar, filtrar por estado y ver el detalle.
- **32 tests** nuevos (catálogo sin login, que no exponga el stock exacto,
  armado y confirmación del pedido, texto/URL de WhatsApp y permisos del panel).

#### Cierre del flujo (21-10-2026): entregar un pedido **es cobrarlo**

- **El pedido quedó vinculado al cobro**: `Pedido.cliente` y `Pedido.venta`
  (migración `pedidos/0002`, ambos `SET_NULL`). La referencia va de `pedidos`
  hacia `ventas.Venta`, así que `ventas` no depende de `pedidos` y las
  migraciones no se ciclan.
- **No hay "Marcar como entregado"**: el estado `entregado` **no se puede
  marcar a mano** (`pedidos:cambiar_estado` lo rechaza y deriva a "Entregar y
  cobrar"). Entregar sin cobrar dejaría pedidos sin venta y sin stock
  descontado.
- **Pantalla "Entregar y cobrar"** (`/catalogo/panel/<id>/`): busca el cliente
  (DNI, nombre o apellido, **sin depender de los acentos**: "perez" encuentra a
  "Pérez"), elige el método de pago (efectivo, tarjeta o cuenta corriente) y
  calcula el vuelto en vivo. **El cliente es opcional**: sin cliente, la venta
  es de consumidor final (sin puntos ni deuda).
- **Se cobra el precio congelado del pedido** (lo que el cliente vio al
  armarlo), no el precio actual del catálogo.
- **Un solo núcleo de venta** (`ventas/services.py::registrar_venta_desde_items`):
  el POS y la entrega usan el mismo servicio, así que el stock, los puntos y el
  fiado se aplican con las mismas reglas y no están duplicados. Todo en **una
  sola transacción** con el pedido bloqueado (`select_for_update`): o se cobra y
  se entrega, o el pedido sigue pendiente.
- **La entrega queda auditada** (`registrar_accion()`): quién entregó, qué se
  cobró, con qué cliente y cuántos puntos.
- **19 tests nuevos** de la entrega + **9 tests** de la demo de clientes.

> El detalle de las decisiones de diseño está en **ADN-18** del
> [ARD](docs/ARD.md).

### 2) Módulo de Ventas / POS: cuenta corriente ("FIAR") para clientes frecuentes — ✅ Hecho

**Lo que se pedía:** que los clientes registrados puedan acumular un saldo de
deuda con un **límite máximo definido por el administrador**, y que al cobrar
el cajero pueda elegir **"Cobrar a Cuenta Corriente"**.

**Cómo quedó implementado:**

- **Límite y saldo en el cliente** (`clientes/models.py`, migración `0002`):
  `Cliente.limite_credito` (0 = sin cuenta corriente) y `Cliente.saldo_deuda`
  (deuda vigente). El Administrador define el límite desde el alta y la edición
  de clientes; se rechazan valores negativos.
- **Historial de pagos** con el modelo `PagoCuentaCorriente` (monto, fecha,
  usuario que cobró y observación): sobrevive a la baja lógica del cliente.
- **Cobro fiado desde el POS**: nuevo método de pago `cuenta_corriente` en
  `Venta.METODO_PAGO` (migración `ventas/0007`). La opción "Cobrar a Cuenta
  Corriente" aparece **solo si el carrito tiene un cliente con cuenta
  corriente**; sin cliente no hay a quién fiar.
- **Validación del límite server-side**: al confirmar el cobro,
  `clientes/services.py::validar_fiado` corre **dentro de la misma transacción**
  de `confirmar_venta` (con `select_for_update`); si la deuda nueva supera el
  límite, la venta se rechaza con un mensaje que dice cuánto debe, el límite y
  cuánto le queda, y el carrito **no se vacía**. Si pasa, `sumar_deuda()` sube
  el saldo con `F()` en la misma transacción.
- **Pago de la deuda** (`/clientes/<id>/pagos/registrar/`): **solo el
  Administrador** registra pagos (el cajero recibe 403). Un pago ≤ 0 o mayor a
  la deuda se rechaza. La ficha del cliente muestra el estado de la cuenta
  corriente (límite, deuda, crédito disponible, aviso de "al límite") y el
  historial de pagos; el listado de clientes muestra la deuda o "al día · límite".
- **Lo fiado no entra a la caja ni a los ingresos**: `METODOS_EN_CAJA =
  ("efectivo", "tarjeta")` define qué suma a la caja; lo fiado se informa
  aparte como **"Deuda otorgada (FIAR)"** en el cierre de turno (`Turno.deuda_otorgada`)
  y en los reportes (`reportes.deuda_otorgada()`), con un aviso de que no es
  plata que esté en la caja. Los KPIs de ingresos, la serie por día, el top de
  productos y los más rentables la **excluyen**.
- **43 tests nuevos** de cuenta corriente (límite, fiado, pagos y reportes).

> El detalle de las decisiones de diseño está en **ADN-14** y **ADN-17** del
> [ARD](docs/ARD.md).

---

## Decisiones técnicas

### Backend

- **Base de datos**: PostgreSQL como base de datos principal del proyecto.
  Se utiliza `django-environ` para leer la variable `DATABASE_URL` desde un
  archivo `.env` (no subido al repo por seguridad). Si no se define la
  variable, el sistema cae automáticamente a SQLite para desarrollo local
  sin configuración extra.

- **Roles con Django Groups**, no con permisos sueltos: el acceso es binario
  ("cajero solo ve el cobro" / "administrador ve todo"), no hay acciones
  finas que diferenciar (ej. "puede ver stock pero no editar precio"). El
  modelo `Producto` ya existe (Sprint 2) y la decisión se mantuvo; si algún
  día hace falta permiso fino, se pasa a
  `django.contrib.auth.models.Permission` por modelo.

- **Restricción por decorador (`usuarios/decorators.py`)**: `rol_requerido`
  en todas las vistas (hoy todas son funciones); `RolRequeridoMixin` está
  definido y disponible por si se adoptan CBVs, aunque ninguna vista lo usa
  todavía. El cajero no solo "no ve el botón": si escribe la URL a mano, el
  servidor le devuelve 403. Es un requisito de seguridad real, no solo de UI.

- **Redirección post-login por rol** (`usuarios/views.py::post_login`): cada
  usuario cae directo en su pantalla (cajero → cobro, admin → dashboard),
  para no exponer un menú con opciones que no le corresponden.

- **Auditoría con señales**: `user_logged_in` / `user_logged_out` crean un
  `RegistroAuditoria` (usuario, acción, fecha, IP) sin tocar las vistas de
  login.

- **Carrito en la sesión, venta al confirmar** (Sprint 3): el carrito es una
  lista en `request.session["carrito"]`; la `Venta` recién se crea en
  `services.confirmar_venta()` dentro de una transacción (con
  `select_for_update` y descuento de stock con `F()`), de modo que nunca
  queda una venta parcial que contaminaría los reportes.

- **El catálogo público registra un `Pedido`, no una `Venta`** (HU-13): la
  vista pública es la única sin rol; el pedido vive en `session["pedido"]`
  (separado del carrito del POS) y recién se persiste al confirmar. Como no es
  una venta, no descuenta stock ni entra a la caja: el cobro real pasa en el
  POS cuando el cliente retira. El link a WhatsApp se arma en el servidor
  (`pedidos/config.py`) y lo abre el navegador (`wa.me`), sin API ni
  credenciales.

- **Cuenta corriente con el saldo guardado y validación transaccional**
  (HU-14): el límite se define **por cliente** (`Cliente.limite_credito`) y la
  deuda se **guarda** en `Cliente.saldo_deuda` (con `PagoCuentaCorriente` como
  historial). La validación del límite y la suma de la deuda corren **dentro de
  la transacción** de `confirmar_venta` con `select_for_update`, así que dos
  cobros simultáneos no pueden pasarse del límite por una condición de carrera.
  Lo fiado **no** entra a la caja ni a los ingresos: `METODOS_EN_CAJA` centraliza
  qué suma, y la deuda se informa aparte como "Deuda otorgada (FIAR)".

### Frontend

<a id="frontend"></a>

- **Bootstrap 5.3.3 + Bootstrap Icons 1.11.3** vía CDN como framework de utilidades.
- **CSS custom** (`static/css/styles.css`, ~3.400 líneas) con design tokens vía
  CSS custom properties (`:root` + variantes). La paleta, tipografía, radios y
  sombras se definen una vez y se reutilizan en todas las páginas.
- **Identidad "toldo de barrio"**: rotulación de kiosco argentino — contorno
  de tinta + sombra dura, etiquetas de precio adhesivas, código de barras como
  gráfico temático, códigos de error grandes (403/404) y filete de toldo en el
  navbar. Tipografía display **Righteous** + interfaz **Space Grotesk**.
- **Un solo estilo visual: Neón cian** (ver sección siguiente): paleta cian
  `#00C8E0` sobre azul profundo `#081822`, con glow y grilla de piso. Las
  paletas Cartelera y Ticket fueron eliminadas del CSS y el botón de selector
  de estilo se retiró del navbar y del login.
- **Modo oscuro** persistente (`data-theme="dark"`) en el estilo neón.
- **Componentes custom**: `kiosco-navbar`, badges de rol, `btn-kiosco`,
  `kiosco-input`, `kiosco-alert`, `placeholder-page`, `error-page`,
  `warning-page`, mock de escáner en cobro, `sello` y banner `viene`.
- **CSS heredado del equipo**: al hacer el merge con `main` se integraron los
  bloques *Auth pages* (login/registro) y *Admin Panel* (dashboard y gestión
  de usuarios) con un shim de aliases (`--surface`, `--radius-*`,
  `--kiosco-yellow`, …) para que usen los tokens del rediseño.
- **Accesibilidad**: contraste AA, `focus-visible` para teclado,
  `prefers-reduced-motion` respetado, `aria-label` en los botones de tema.
- **Responsive**: bajo 576px el navbar oculta el nombre de usuario y mantiene
  badges y salida; bajo 860px el login pasa a panel único.
- **HTMX** (CDN en `base.html`) se usa en la búsqueda del catálogo de
  productos, en las acciones del carrito y en la búsqueda en tiempo real del
  escáner del cobro (desde 3 caracteres); el token CSRF se envía
  globalmente con `hx-headers`.

---

## Cómo correr el proyecto

### Requisitos previos

- Python 3.10+
- PostgreSQL instalado y corriendo (**opcional**: sin `DATABASE_URL` el
  proyecto usa SQLite automáticamente)

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

# 5. Crear la base de datos en PostgreSQL (solo si vas a usar PostgreSQL)
#    Abrí psql (o pgAdmin) y ejecutá:
#    CREATE DATABASE db_kiosco;

# 6. Configurar la conexión en el archivo .env (ver sección siguiente)

# 7. Crear las tablas de la base de datos (una sola vez)
python manage.py migrate

# 8. Crear los grupos y usuarios de prueba (una sola vez)
python manage.py setup_inicial

# 9. (Opcional) Cargar datos de demo: 50+ productos y ventas desde el 20/09/2026
#    --limpiar borra el historial de ventas desde esa fecha y lo regenera
python manage.py cargar_demo --limpiar

# 9b. (Opcional) Cargar la demo de clientes y pedidos de WhatsApp:
#     clientes con compras reales y pedidos del catálogo público (los que
#     retiró, cobrados con el flujo real). Va DESPUÉS de cargar_demo.
#     --limpiar borra la demo anterior, repone el stock y la vuelve a cargar
python manage.py cargar_demo_clientes --limpiar

# 10. Levantar el servidor de desarrollo
python manage.py runserver 8001
```

Abrí `http://127.0.0.1:8001/` en el navegador.

> El proyecto se abre con `runserver`, no con la extensión "Go Live / Live
> Server" de VS Code (esa solo muestra archivos sueltos).

### Probar el cobro con QR y el celular (HU-15/16)

1. Levantá el servidor escuchando en la red local:
   `python manage.py runserver 0.0.0.0:8001` (si Windows pregunta, permití el
   acceso en redes privadas).
2. Entrá con `cajero1`, cargá productos, elegí **Mercado Pago (QR)** y tocá
   **Generar QR de Mercado Pago**.
3. Con un celular en el mismo Wi‑Fi, escaneá el QR chico de "Mostrar el QR en
   un celular" e iniciá sesión con el mismo usuario: ese celular muestra el QR
   de cada cobro.
4. Para simular que el cliente paga: escaneá el QR grande con otro celular o
   tocá "simular el pago del cliente" en la caja, y después **Pagar**. La caja
   abre el comprobante y el celular muestra "¡Pago aprobado!".

> **Nota:** los pasos 2, 4, 5, 6, 7 y 8 solo se hacen la **primera vez**.
> Después de eso, solo necesitás activar el entorno (paso 3) y levantar
> el servidor (paso 10).

### Publicar el sistema (Render)

> Netlify **no** sirve: solo publica páginas estáticas y no corre Django.
> Render (o Railway, PythonAnywhere) sí, y tiene plan gratis.

1. Creá una cuenta en https://render.com (podés entrar con GitHub).
2. **New → Blueprint** y elegí este repositorio. Render lee `render.yaml` y
   crea el sitio y una base PostgreSQL. En cada publicación instala, junta los
   estáticos, corre las migraciones y `setup_inicial`.
3. Cuando termine, el sitio queda en `https://norvex-XXXX.onrender.com`.
   Entrá con `admin` / `kiosco2024` y **cambiá las contraseñas**.

Notas: el plan gratis "duerme" el sitio si no se usa (la primera visita tarda
~1 minuto) y la base gratis de Render vence a los 30 días. Para algo más
estable se puede apuntar `DATABASE_URL` a Supabase.

### Conectar con Mercado Pago (una sola vez, quien publica el sistema)

1. En https://www.mercadopago.com.ar/developers/panel/app creá una aplicación
   (producto **Checkout Pro**).
2. En la aplicación, **URL de redireccionamiento**: la que muestra **Panel →
   Mercado Pago** en el sistema publicado
   (`https://<tu-dominio>/ventas/mercadopago/callback/`).
3. Copiá el **Client ID** y el **Client Secret** de la aplicación a las
   variables `MP_CLIENT_ID` y `MP_CLIENT_SECRET` (en Render: servicio →
   *Environment*). `MP_OAUTH_PRUEBA=true` conecta cuentas de **prueba**
   (plata ficticia); `false`, cuentas reales.
4. Listo: cada negocio entra a **Panel → Mercado Pago** y toca **Conectar**.

**Para probar con plata ficticia (sandbox):** en la aplicación, sección
*Cuentas de prueba*, creá un **vendedor** y un **comprador**. El vendedor es el
que se conecta con el botón; con el comprador (y las tarjetas de prueba de
Mercado Pago) se paga el QR desde el celular. El pago aparece en la caja y en
la cuenta del vendedor de prueba.

**Desde la PC, sin publicar (túnel):** con
`cloudflared tunnel --url http://localhost:8001` se obtiene una dirección
`https://….trycloudflare.com` temporal. Cargala en el `.env`:

```
CSRF_TRUSTED_ORIGINS=https://….trycloudflare.com
MP_REDIRECT_URI=https://….trycloudflare.com/ventas/mercadopago/callback/
```

registrá esa misma `MP_REDIRECT_URI` en la aplicación de Mercado Pago y entrá
al sistema por la dirección del túnel. La dirección cambia cada vez que se
abre el túnel.

### Archivo .env

El proyecto usa `django-environ` para leer la configuración desde un archivo
`.env` en la raíz del proyecto. Hay una plantilla versionada, `.env.example`:
copiala a `.env` y completá los datos.

```
DATABASE_URL=postgresql://postgres:1234@localhost:5432/db_kiosco
KIOSCO_NOMBRE=Kiosco de Barrio
KIOSCO_WHATSAPP=5491155554444
```

Formato: `postgresql://USUARIO:CONTRASEÑA@HOST:PUERTO/NOMBRE_DB`

Variables opcionales de Mercado Pago (HU-15):

```
MP_ACCESS_TOKEN=TEST-...      # Access Token de prueba de tu app de Mercado Pago
MP_NOTIFICATION_URL=          # URL pública al webhook (opcional)
```

Sin `MP_ACCESS_TOKEN` el cobro con QR funciona en **modo de prueba** (pago
simulado). El token se saca de https://www.mercadopago.com.ar/developers/panel/app
(Credenciales de prueba → Access Token).

`KIOSCO_WHATSAPP` es el WhatsApp del local para los pedidos del catálogo público
(HU-13): formato internacional y solo dígitos, sin `+` ni espacios. Si queda en
el valor de ejemplo, la pantalla de pedido avisa que falta configurarlo en vez
de abrir un chat a un número de prueba.

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
python manage.py test --keepdb
```

> **Nota:** usamos `--keepdb` para reutilizar la base de test entre corridas
> (es más rápido y evita el `DROP DATABASE` colgado por conexiones huérfanas de
> corridas anteriores). Si necesitás recrearla desde cero, corré
> `python manage.py test` sin el flag.

**340 tests** actualmente:

- **`usuarios/tests.py` (9)**: login correcto e incorrecto, acceso anónimo
  bloqueado, cajero bloqueado en administración, administrador con acceso
  total, y la redirección post-login según rol.
- **`ventas/tests.py` (108)**: pantalla de cobro (login, cajero, admin,
  template) + catálogo (acceso 403 para el cajero en las 4 vistas, alta con
  costo y código, código duplicado rechazado, precio 0 rechazado, categoría
  nueva, edición, baja lógica, búsqueda por nombre/código, respuesta HTMX con
  partial y alerta de stock bajo) + ordenamiento de columnas (asc/desc por
  nombre, precio, stock y código, con defaults seguros ante parámetros
  basura) + **Sprint 3** (carrito: agregar por
  código, duplicado suma cantidad, sumar/restar/quitar y total; cobro:
  efectivo con vuelto, pago exacto, tarjeta, stock insuficiente, auditoría de
  la venta; comprobante: formato de pesos y 403 para ventas ajenas; búsqueda
  en tiempo real del escáner desde 3 caracteres) + **Sprint 4** (cierre de
  turno: apertura registra al responsable, no se abren dos turnos a la vez,
  totales en vivo antes de cerrar, el cierre congela el snapshot, las ventas
  de otro cajero/no finalizadas/anteriores a la apertura quedan afuera, el
  resumen formatea los montos, 403 para el turno ajeno y auditoría del
  cierre) + **HU-14** (lo fiado no entra a la caja, la pantalla muestra la
  deuda otorgada y el cierre la congela en `Turno.deuda_otorgada`).
- **`ventas/tests_cargar_demo.py` (9)**: el seed de datos de demo (catálogo
  completo con códigos únicos, ventas desde el 20/09/2026 sin fechas en el
  futuro, precios y costos congelados en el detalle, vuelto solo en efectivo,
  no duplica sin `--limpiar`, regenera idéntico con `--limpiar`, no pisa
  productos cargados a mano y el caso de totales no múltiplos de 100).
- **`clientes/tests.py` (82)**: acceso (cajero no entra al CRUD, sí busca y
  asocia en el cobro), alta/edición con DNI único y normalizado (puntos,
  guiones y letras), baja lógica que conserva ventas y puntos, asociación al
  carrito en la sesión, suma de puntos (1 cada $100) y su previsualización,
  comprobante con cliente y puntos, alta rápida desde el cobro, listado con
  estadísticas y ficha con historial + **HU-14** (propiedades de la cuenta
  corriente, fiado dentro/fuera del límite, sin cliente y sin cuenta corriente,
  el carrito no se vacía al rechazar, registro de pagos que baja el saldo,
  rechazo de monto ≤ 0 o mayor a la deuda, 403 del cajero, ficha con cuenta
  corriente e historial de pagos y validación del límite en el formulario) +
  **búsqueda sin acentos** ("perez" encuentra a "Pérez") + **demo de clientes**
  (todo cliente cargado tiene compras, la deuda es lo fiado menos lo pagado, los
  puntos suman las ventas, los pedidos pendientes no son clientes, los
  entregados cobran de verdad, no queda stock negativo y `--limpiar` devuelve el
  stock y recarga la misma demo).
- **`administracion/tests.py` (24)**: dashboard (login, admin, 403 cajero,
  403 sin grupo, estadísticas, KPI de stock bajo contando productos activos y
  linkeando al reporte) y CRUD de usuarios (listar con búsqueda y
  filtro por rol, crear, editar, eliminar con protección de superusuarios,
  activar/desactivar, asignar/quitar roles).
- **`administracion/tests_reportes.py` (65)**: resumen de ventas, serie
  diaria, top 10, productos rentables, stock valorado, stock por categoría,
  margen bajo, propiedades de `Producto`/`DetalleVenta` y las vistas de
  reportes (incluye 403 para el cajero, badge `status-bajo` rojo y el ancla
  `#stock-bajo`) + **HU-14** (los ingresos, la serie, el top y la rentabilidad
  excluyen lo fiado; `deuda_otorgada()` lo suma aparte y el listado de ventas
  puede incluirlas).
- **`pedidos/tests.py` (52)**: catálogo público (visible sin login, que **no**
  exponga el stock exacto, marca de agotados y solo productos activos), armado
  del pedido (agregar, duplicados, cantidad inválida, producto agotado, quitar,
  baja lógica del producto), confirmación (crea `Pedido` + ítems con el precio
  congelado, valida nombre e ítems, vaciar) y WhatsApp (texto y URL con el
  número configurado, normalización del teléfono, el placeholder no cuenta como
  configurado), más el panel interno (403 del cajero, listado/filtro/detalle del
  admin, cambio de estado auditado y POST obligatorio) + **cierre del flujo**
  ("entregado" exige cobrar, la entrega crea la `Venta` con el precio congelado
  y vincula cliente y venta, no se puede cobrar dos veces, la búsqueda de
  cliente ignora los acentos y la entrega queda auditada).

## Estructura del proyecto

```
kiosco_sprint1/
│
├── manage.py                         # Punto de entrada de Django.
├── requirements.txt                  # Django 6.1.1, psycopg2-binary,
│                                     # django-environ.
├── README.md                         # Este archivo.
├── AGENTS.md                         # Instrucciones para agentes IA.
├── docs/
│   ├── PRD.md                        # Requerimientos de producto (v2.6).
│   └── ARD.md                        # Arquitectura y requerimientos técnicos (v2.6).
├── .env                              # DATABASE_URL + WhatsApp del local (no se sube al repo).
├── .env.example                      # Plantilla de .env (sí se versiona).
├── .gitignore                        # __pycache__, venv/, db.sqlite3, .env…
│
├── config/                           # Configuración del proyecto Django.
│   ├── settings.py                   # BD (PostgreSQL via .env con fallback a
│   │                                 # SQLite), apps, LOGIN_URL, es-ar,
│   │                                 # America/Argentina/Buenos_Aires.
│   ├── urls.py                       # Raíz: admin/, / → post_login, includes
│   │                                 # de catalogo/pedidos, usuarios/clientes/
│   │                                 # ventas/administracion, handler404.
│   ├── wsgi.py / asgi.py             # Puntos de entrada WSGI/ASGI.
│
├── usuarios/                         # Autenticación y control de acceso.
│   ├── views.py                      # LoginKioscoView, registro_usuario
│   │                                 # (cuenta sin rol), post_login (según
│   │                                 # rol), sin_rol.
│   ├── urls.py                       # 5 rutas: login/, logout/, post-login/,
│   │                                 # sin-rol/, registro/.
│   ├── forms.py                      # LoginKioscoForm y RegistroUsuarioForm
│   │                                 # (widgets kiosco-input).
│   ├── decorators.py                 # @rol_requerido, RolRequeridoMixin,
│   │                                 # es_administrador(), es_cajero().
│   ├── tests.py                      # 9 tests.
│   ├── templatetags/
│   │   └── pagination_tags.py        # {% paginacion %} (inclusion tag) y
│   │                                 # {% param %} (preserva query params).
│   └── management/commands/
│       └── setup_inicial.py          # Crea grupos + usuarios de prueba.
│                                     # Idempotente.
│
├── ventas/                           # Productos y pantalla de cobro (POS).
│   ├── models.py                     # Categoria, Producto, Venta (método de
│   │                                 # pago —incl. cuenta corriente—, cajero,
│   │                                 # vuelto, cliente y puntos),
│   │                                 # DetalleVenta y Turno (cierre de caja
│   │                                 # con deuda otorgada).
│   ├── services.py                   # Carrito en sesión + confirmar_venta
│   │                                 # (transacción, stock, precios HU-09,
│   │                                 # validación del fiado) +
│   │                                 # registrar_venta_desde_items (núcleo
│   │                                 # de venta compartido con la entrega de
│   │                                 # pedidos) y apertura/cierre del turno
│   │                                 # (HU-10).
│   ├── views.py                      # pantalla_cobro + cobro_agregar /
│   │                                 # cobro_cantidad / cobro_confirmar (HTMX),
│   │                                 # cierre_turno, lista_productos (búsqueda +
│   │                                 # orden por columna asc/desc) y CRUD de
│   │                                 # productos (@rol_requerido Administrador).
│   ├── forms.py                      # ProductoForm (HU-04): código de barras
│   │                                 # sin duplicados, costo, precio, stock,
│   │                                 # stock_minimo y categoría.
│   ├── urls.py                       # 10 rutas: 6 de cobro/ y turno/ + 4 de
│   │                                 # productos/.
│   ├── admin.py                      # Venta (inline DetalleVenta), Producto,
│   │                                 # Categoria.
│   ├── management/commands/
│   │   └── cargar_demo.py            # 56 productos + ventas desde el 20/09/2026
│   │                                 # (semilla fija; --limpiar regenera).
│   ├── tests.py                      # 108 tests.
│   ├── tests_cargar_demo.py          # 9 tests del seed de datos.
│   └── migrations/                   # 0001 catálogo/ventas, 0002 costo,
│                                     # 0003 código de barras + stock mínimo,
│                                     # 0004 campos de cobro de la Venta,
│                                     # 0005 cliente + puntos de fidelidad,
│                                     # 0006 Turno (cierre de turno),
│                                     # 0007 deuda otorgada + método
│                                     # cuenta_corriente (HU-14).
│
├── clientes/                         # Fidelidad (HU-12) y cuenta corriente
│                                     # (HU-14), Sprint 4 + consigna.
│   ├── models.py                     # Cliente: nombre, apellido, DNI/CUIT
│   │                                 # (único), teléfono, email, fecha de
│   │                                 # registro, puntos, limite_credito,
│   │                                 # saldo_deuda y activo; PagoCuentaCorriente
│   │                                 # (historial de pagos).
│   ├── services.py                   # Regla de puntos (1 cada $100), cliente
│   │                                 # asociado en la sesión, validar_fiado,
│   │                                 # sumar_deuda, registrar_pago,
│   │                                 # cliente_bloqueado y buscar_clientes
│   │                                 # (búsqueda compartida con el panel de
│   │                                 # pedidos, sin depender de los acentos).
│   ├── views.py                      # CRUD de clientes (403 para el cajero) +
│   │                                 # buscar/asociar/quitar y alta rápida
│   │                                 # desde el cobro + registrar_pago
│   │                                 # (solo Administrador).
│   ├── forms.py                      # ClienteForm (DNI normalizado y único,
│   │                                 # limite_credito) y PagoCuentaCorrienteForm.
│   ├── urls.py                       # 10 rutas: CRUD, cobro y pagos.
│   ├── admin.py                      # Cliente y PagoCuentaCorriente.
│   ├── demo_data.py                  # Datos de la demo de clientes y pedidos
│   │                                 # (perfiles de pago: debe, al límite,
│   │                                 # al día, al día con cuenta corriente).
│   ├── management/commands/
│   │   └── cargar_demo_clientes.py   # Demo de clientes con compras reales +
│   │                                 # pedidos de WhatsApp (los entregados se
│   │                                 # cobran con el flujo real; --limpiar
│   │                                 # borra, repone el stock y recarga).
│   ├── tests.py                      # 82 tests.
│   └── migrations/                   # 0001 Cliente, 0002 límite/saldo +
│                                     # PagoCuentaCorriente (HU-14).
│
├── pedidos/                          # Integración externa (HU-13, consigna).
│   ├── models.py                     # Pedido (estado, total congelado) e
│   │                                 # ItemPedido (nombre y precio congelados);
│   │                                 # cliente y venta (al cobrar la entrega).
│   ├── services.py                   # Carrito del pedido en sesión
│   │                                 # (session["pedido"]), crear_pedido, el
│   │                                 # texto armado para WhatsApp y
│   │                                 # registrar_entrega (cobrar la entrega
│   │                                 # en una sola transacción).
│   ├── config.py                     # KIOSCO_NOMBRE / KIOSCO_WHATSAPP desde
│   │                                 # el .env + armado del link wa.me.
│   ├── views.py                      # Catálogo público sin login (HTMX) +
│   │                                 # panel de pedidos (solo Administrador):
│   │                                 # entregar_pedido (cobra) y
│   │                                 # buscar_cliente_pedido (HTMX).
│   ├── urls.py                       # 9 rutas: 4 públicas (/catalogo/…) y 5
│   │                                 # del panel (/catalogo/panel/…).
│   ├── admin.py                      # Pedido (inline ItemPedido).
│   ├── tests.py                      # 52 tests.
│   └── migrations/                   # 0001 Pedido/ItemPedido (HU-13),
│                                     # 0002 cliente + venta (cierre de HU-13).
│
├── administracion/                   # Panel del dueño.
│   ├── views.py                      # dashboard (stats de usuarios + KPI de
│   │                                 # stock bajo con link al reporte), CRUD:
│   │                                 # listar, crear, editar, eliminar,
│   │                                 # asignar_roles, toggle_usuario, y las
│   │                                 # vistas de reportes (solo admin).
│   ├── reportes.py                   # Resúmenes de ventas y stock: ingresos,
│   │                                 # ganancia, ticket promedio, top 10,
│   │                                 # stock valorado, por categoría, margen.
│   ├── urls.py                       # 9 rutas bajo /administracion/
│   │                                 # (7 de usuarios + 2 de reportes).
│   ├── forms.py                      # UsuarioForm (alta/edición con
│   │                                 # contraseña opcional al editar) y
│   │                                 # AsignarRolForm (checkboxes de grupos).
│   ├── tests.py                      # 24 tests.
│   ├── tests_reportes.py             # 65 tests.
│   └── templates → ../templates/administracion/ (8 templates).
│
├── auditoria/                        # Logs de auditoría.
│   ├── models.py                     # RegistroAuditoria: usuario, acción,
│   │                                 # detalle, fecha, IP.
│   ├── signals.py                    # user_logged_in/out → crea registro.
│   ├── utils.py                      # registrar_login/logout/accion(),
│   │                                 # _obtener_ip().
│   ├── admin.py                      # Solo lectura en el admin de Django.
│   └── migrations/0001_initial.py
│
├── templates/                        # Django Template Language.
│   ├── base.html                     # Layout: Google Fonts + Bootstrap CDN,
│   │                                 # navbar (marca, usuario, badges, botón
│   │                                 # oscuro, salir), bloque de messages,
│   │                                 # scripts de tema y de estilo neón.
│   ├── 403.html / 404.html           # error-page con código grande.
│   ├── usuarios/
│   │   ├── login.html                # login-split: toldo a la izquierda +
│   │   │                             # panel de ingreso a la derecha.
│   │   ├── registro.html             # auth-card de alta de cuenta.
│   │   ├── sin_rol.html              # warning-page sin grupo asignado.
│   │   └── tags/                     # Partiales de paginación y buscador.
│   ├── ventas/
│   │   ├── pantalla_cobro.html       # POS: escáner, carrito, pago (HU-07…09).
│   │   ├── _carrito.html             # Partial HTMX del carrito y form de pago
│   │   │                             # (incluye la opción "FIAR" y la barra de
│   │   │                             # cuenta corriente, HU-14).
│   │   ├── _cobro_resultados.html    # Sugerencias del escáner (≥3 caracteres).
│   │   ├── lista_productos.html      # Catálogo con búsqueda HTMX.
│   │   ├── _productos_tabla.html     # Partial que devuelve HTMX.
│   │   ├── agregar_producto.html     # Alta (HU-04).
│   │   ├── editar_producto.html      # Edición de precios y stock.
│   │   ├── cierre_turno.html         # Apertura, totales, deuda otorgada y
│   │   │                             # resumen del turno (HU-10/HU-14).
│   │   └── eliminar_producto.html    # Confirmación de baja lógica.
│   ├── clientes/                     # Fidelidad (HU-12) y cuenta corriente
│   │   │                             # (HU-14):
│   │   ├── listar_clientes.html      # tabla con búsqueda y estadísticas.
│   │   ├── _clientes_tabla.html      # Partial que devuelve HTMX (muestra la
│   │   │                             # deuda o el límite de cada cliente).
│   │   ├── crear_cliente.html / editar_cliente.html  # incluyen el límite.
│   │   ├── eliminar_cliente.html     # Confirmación de baja lógica.
│   │   ├── detalle_cliente.html      # ficha: puntos, historial, cuenta
│   │   │                             # corriente e historial de pagos.
│   │   └── _resultados_cobro.html    # búsqueda + alta rápida en el cobro.
│   ├── pedidos/                      # Integración externa (HU-13):
│   │   ├── catalogo.html             # vitrina pública sin login.
│   │   ├── _carrito_pedido.html      # Partial HTMX del pedido en curso.
│   │   ├── pedido_confirmado.html    # paso a WhatsApp con el pedido armado.
│   │   ├── lista_pedidos.html        # panel de pedidos (solo Administrador).
│   │   ├── _pedidos_tabla.html       # Partial que devuelve HTMX.
│   │   ├── detalle_pedido.html       # detalle + card "Entregar y cobrar"
│   │   │                             # (buscador de cliente, método de pago,
│   │   │                             # monto y vuelto en vivo).
│   │   └── _resultados_cliente.html  # Partial HTMX de la búsqueda de cliente.
│   └── administracion/               # Panel del equipo:
│       ├── dashboard.html            # stats de usuarios + accesos rápidos.
│       ├── listar_usuarios.html      # tabla con búsqueda/filtros.
│       ├── crear_usuario.html / editar_usuario.html
│       ├── eliminar_usuario.html     # confirmación con advertencia.
│       ├── asignar_roles.html        # checkboxes de grupos.
│       ├── reportes_ventas.html       # resumen, serie diaria, top 10.
│       └── reportes_stock.html        # inventario valorado y alertas.
│
├── static/
│   ├── css/styles.css                # ~3.600 líneas: tokens del toldo, estilo
│   │                                 # neón (único) con dark variant,
│   │                                 # componentes base, bloques auth/admin
│   │                                 # del equipo con aliases de tokens,
│   │                                 # responsive, reduced-motion.
│   └── img/favicon.svg               # Tira amarilla + "K" sobre tinta
│                                     # (#17130E / #FFC400).
│
├── venv/                             # Entorno virtual (no se sube).
└── .agents/skills/frontend-design/   # Skill de diseño usada para el
                                      # rediseño.
```

### Flujo de autenticación (cómo funciona login → pantalla)

1. El usuario visita `http://127.0.0.1:8001/` → redirige a `usuarios:post_login`.
2. Si no está autenticado, Django lo manda a `usuarios:login` (configurado en `LOGIN_URL`).
3. El formulario (`LoginKioscoForm`) valida credenciales contra `auth.User`.
4. **Registro:** cualquiera puede crear cuenta en `/usuarios/registro/`; el usuario
   nace sin grupo y, hasta que un administrador le asigne rol, cae en `sin_rol`.
5. Al loguearse, `post_login` chequea el grupo:
   - `es_administrador(user)` → redirige a `administracion:dashboard`.
    - `es_cajero(user)` → redirige a `ventas:pantalla_cobro`.
   - Sin grupo → redirige a `usuarios:sin_rol`.
6. Si el usuario escribe una URL protegida a mano, el decorador `rol_requerido`
   lanza `PermissionDenied` (403) que se renderiza con `templates/403.html`.

### Flujo de auditoría

- Las señales `user_logged_in` y `user_logged_out` (Django) están conectadas en
  `auditoria/signals.py`. Cada login/logout crea un `RegistroAuditoria` con
  usuario, acción, fecha e IP automáticamente. Las acciones custom se logean
  con `registrar_accion()` desde cualquier vista.

### Modo oscuro

- Un script inline en `<head>` de `base.html` lee `localStorage['kiosco-tema']`
  y aplica `data-theme="dark"` en `<html>` antes del render (sin flash). Si no
  hay nada guardado, respeta `prefers-color-scheme`.
- El botón de luna/sol en el navbar cambia el atributo y guarda en `localStorage`.
- Los estilos dark están en `styles.css` bajo selectores `[data-theme="dark"]`.

### Estilo visual

- **Un solo estilo: Neón cian.** Righteous + Space Grotesk, noche `#081822`,
  cian `#00C8E0` como luz principal con glow contenido y un azul `#5FE6F5` de
  apoyo, radios 10px.
- `data-tema="neon"` se fuerza en el script inline del `<head>` de `base.html`
  (sin flash); `localStorage['kiosco-estilo']` se limpia si existía.
- Se eliminaron las paletas **Cartelera** y **Ticket** (CSS y selector) y el
  botón `#estiloToggle` del navbar y del login. Solo queda `#darkToggle`
  (claro/oscuro).

## Backlog

Estado real al **21-10-2026** (unificado: tabla original + backlog nuevo).

### Hecho

| Item | Sprint | Evidencia |
|------|--------|-----------|
| Login + roles + 403 server-side + post-login por rol | 1 | `usuarios/decorators.py`, tests de `usuarios` |
| Registro de cuentas públicas (sin rol) | 1 | `usuarios:registro` |
| Auditoría de login/logout con IP | 1 | `auditoria/signals.py` |
| Rediseño frontend: identidad toldo + modo oscuro | 1 | `static/css/styles.css` |
| Modelos Categoria, Producto, Venta, DetalleVenta + admin Django | 2 | `ventas/models.py` (+ migración `0002` con `costo`) |
| Campo de costo en Producto (lo ve solo el admin) | 2 | `Producto.costo`, `DetalleVenta.costo_unitario` |
| Cajero no accede a costos de mercadería | 2 | `@rol_requerido("Administrador")` + `administracion/tests_reportes.py::test_no_muestra_costos_al_cajero` (403) |
| Views/urls + templates de lista y alta de productos | 2 | `ventas/views.py`, 5 templates en `templates/ventas/` (ya no dan 500) |
| Código de barras en Producto + alta sin duplicados (HU-04) | 2 | `Producto.codigo_barras` (unique) + `ProductoForm.clean_codigo_barras` |
| Altas, bajas y modificaciones de productos (CRUD) | 2 | `agregar/`, `<id>/editar/`, `<id>/eliminar/` (baja lógica, reversible) |
| Búsqueda de productos en tiempo real con HTMX (HU-05) | 2 | `hx-get` en el buscador + partial `_productos_tabla.html` |
| Alerta de stock bajo configurable (HU-06) | 2 | `Producto.stock_minimo` (default 5) + `stock_bajo` + `.badge-stock-bajo` |
| Catálogo protegido para el administrador (el cajero: 403) | 2 | `@rol_requerido("Administrador")` en las 4 vistas de `ventas` |
| CRUD de usuarios + búsqueda + filtro por roles + paginación | 2 | `administracion/views.py`, 24 tests |
| Estilo neón cian único (se eliminaron cartelera/ticket) | 2 | `data-tema="neon"` forzado en `base.html` |
| Carrito de cobro con lector de código de barras (HU-07/08) | 3 | `ventas/services.py` + `cobro_agregar`/`cobro_cantidad` con partial `_carrito.html` |
| Búsqueda en tiempo real en el cobro (desde 3 letras) | 3 | `cobro_buscar` + `hx-get` con debounce 300 ms y partial `_cobro_resultados.html` |
| Cobro efectivo/tarjeta con vuelto (HU-09) | 3 | `cobro_confirmar` + preview de vuelto, billetes y "pago exacto" |
| Botón "pago exacto" en el cobro | 3 | `.btn-exacto` rellena el monto con el total |
| Vuelto rápido con billetes/montos predeterminados | 3 | Botones de billetes (100/200/500/1000/2000) |
| Método de pago en `Venta` (efectivo/tarjeta) | 3 | `Venta.metodo_pago` (migración `0004`) |
| Descuento automático de stock al confirmar venta | 3 | `transaction.atomic` + `F("stock")` en `confirmar_venta` |
| Cajero responsable en cada venta | 3 | `Venta.usuario` (`SET_NULL`) + auditoría de la venta |
| Reporte top 10 de productos más vendidos (HU-11) | 4 | `administracion/reportes.py::top_productos` |
| Consulta de ventas, stock, costos y reportes para el administrador | 4 | `/administracion/reportes/ventas/` y `/reportes/stock/` |
| KPIs de negocio: ingresos, ganancia, margen, ticket promedio, stock valorizado | 4 | `reportes.py` (`resumen_ventas`, `resumen_stock`, `ventas_por_dia`) |
| KPI de stock bajo clickeable en el dashboard | 4 | `.stat-alert` + ancla `#stock-bajo` → `/administracion/reportes/stock/` |
| Ordenamiento del catálogo por columna (asc/desc) | 4 | `CAMPOS_ORDEN` + params `orden`/`direccion` en `lista_productos` |
| Datos de demo reproducibles (56 productos + ventas desde 20/09/2026) | 4 | `cargar_demo` (semilla fija `20260920`, flags `--limpiar`/`--ventas-por-dia`) |
| Formato de dinero unificado en la UI (`montos`) | 4 | `usuarios/templatetags/formatos.py` |
| Fidelidad de clientes: modelo, CRUD, DNI único y baja lógica (HU-12) | 4 | app `clientes/`, 82 tests |
| Puntos de fidelidad (1 cada $100) + historial por venta | 4 | `clientes/services.py`, `Venta.cliente`/`puntos_ganados` (migración `0005`) |
| Asociación de cliente en el cobro (buscar por DNI + alta rápida) | 4 | `clientes:buscar`/`asociar`/`quitar`/`alta_rapida` + carrito en sesión |
| Cierre de turno: totales por método, operaciones, responsable (HU-10) | 4 | `Turno` + `abrir/cerrar_turno` (migración `0006`) + `/ventas/turno/cierre/`, 20 tests |
| Catálogo público sin login con pedido para retirar (HU-13) | Consigna | app `pedidos/`: `/catalogo/`, `Pedido`/`ItemPedido` (migración `0001`), 52 tests |
| Pedido enviado por WhatsApp con teléfono configurable | Consigna | `pedidos/config.py` (`KIOSCO_WHATSAPP`/`KIOSCO_NOMBRE`) + link `wa.me` con el pedido armado |
| Las compras del catálogo quedan registradas en el sistema | Consigna | `Pedido`/`ItemPedido` + panel `/catalogo/panel/` (cancelar, auditado) |
| **Entregar un pedido es cobrarlo** (cierre de HU-13) | Consigna | `Pedido.cliente`/`Pedido.venta` (migración `pedidos/0002`) + `pedidos:entregar` + `registrar_entrega` (precio congelado, una sola transacción, núcleo de venta del POS) |
| Búsqueda de cliente compartida entre el POS y el panel, **sin acentos** | Consigna | `clientes/services.py::buscar_clientes` (el POS y el panel de pedidos usan la misma) |
| Demo de clientes con compras reales y pedidos de WhatsApp | Consigna | `manage.py cargar_demo_clientes` (`clientes/demo_data.py`; los entregados se cobran con el flujo real) |
| Cuenta corriente ("FIAR"): límite y saldo por cliente (HU-14) | Consigna | `Cliente.limite_credito`/`saldo_deuda` + `PagoCuentaCorriente` (migración `clientes/0002`) |
| Cobro fiado desde el POS con validación del límite (HU-14) | Consigna | `Venta.metodo_pago=cuenta_corriente` (migración `ventas/0007`) + `validar_fiado`/`sumar_deuda` transaccional |
| Pago de la deuda e historial, solo para el Administrador (HU-14) | Consigna | `clientes:registrar_pago` (`@rol_requerido("Administrador")`) + ficha con historial |
| Lo fiado fuera de la caja y de los ingresos, como "deuda otorgada" (HU-14) | Consigna | `METODOS_EN_CAJA` + `Turno.deuda_otorgada` + `reportes.deuda_otorgada()` |
| Cobro con QR de Mercado Pago, con modo de prueba (HU-15) | Extra | `ventas/mercadopago.py` + `cobro_qr.py` + `PagoMercadoPago` (migración `ventas/0008`), 16 tests |
| Pantalla para el celular del cliente (HU-16) | Extra | `/ventas/display/` (se actualiza sola cada 2 s) |
| Botón "Conectar con Mercado Pago": la plata le llega al negocio | Extra | `ConexionMercadoPago` (migración `ventas/0009`) + `views_conexion.py`, 16 tests |
| Sistema listo para publicar (Render) | Extra | `render.yaml`, WhiteNoise, gunicorn, `DEBUG`/`SECRET_KEY` desde el entorno |
| Total de Mercado Pago en el cierre de turno | Extra | `Turno.total_mercado_pago` |
| Marca y logo propios: Norvex | Extra | `static/img/norvex-logo.svg`, `favicon.svg`, `templates/includes/norvex_marca.svg` |
| Velocidad con Supabase (conexión persistente y sesiones en caché) | Extra | `CONN_MAX_AGE`, `SESSION_ENGINE = cached_db` |

### Pendiente

| Item | Sprint | Notas |
|------|--------|-------|
| Comercio configurable (nombre y colores del local) | por definir | Identidad fija en neón; se parametrizaría vía settings/templates |
| Publicar el sistema y crear la aplicación de Norvex en Mercado Pago | por definir | Todo el código está listo: falta hacer los pasos de "Publicar el sistema" y "Conectar con Mercado Pago" |
| Multi-negocio (varios comercios en una sola instalación) | futuro | Hoy es una instalación por negocio; requeriría un modelo `Negocio` en todas las apps |
| Recuperar contraseña ("¿Olvidaste tu contraseña?") | por definir | Sin `password_reset` ni `EMAIL_*` en settings |
