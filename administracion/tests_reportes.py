from datetime import date, datetime, timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from administracion import reportes
from ventas.models import Categoria, DetalleVenta, Producto, Venta


def _crear_venta(
    usuario, productos, fecha=None, finalizada=True, metodo_pago="efectivo"
):
    """
    Arma una venta con sus detalles. `productos` es una lista de tuplas
    (producto, cantidad). `metodo_pago` permite armar ventas fiadas (HU-14).
    """
    venta = Venta.objects.create(
        total=sum(
            (producto.precio * cantidad for producto, cantidad in productos),
            Decimal("0.00"),
        ),
        finalizada=finalizada,
        metodo_pago=metodo_pago,
    )
    for producto, cantidad in productos:
        DetalleVenta.objects.create(
            venta=venta,
            producto=producto,
            cantidad=cantidad,
            precio_unitario=producto.precio,
            costo_unitario=producto.costo,
        )

    if fecha is not None:
        # `fecha` es auto_now_add, así que se pisa después de crear.
        Venta.objects.filter(pk=venta.pk).update(fecha=fecha)
        venta.refresh_from_db()

    return venta


class BaseReportes(TestCase):
    """Usuarios y catálogo compartidos por los tests de reportes."""

    def setUp(self):
        self.grupo_admin = Group.objects.create(name="Administrador")
        self.grupo_cajero = Group.objects.create(name="Cajero")

        self.admin = User.objects.create_user(
            username="admin_test", password="claveSegura123"
        )
        self.admin.groups.add(self.grupo_admin)

        self.cajero = User.objects.create_user(
            username="cajero_test", password="claveSegura123"
        )
        self.cajero.groups.add(self.grupo_cajero)

        self.superuser = User.objects.create_superuser(
            username="super_test", password="claveSegura123"
        )

        self.categoria = Categoria.objects.create(nombre="Bebidas")

        # Vendido a 100, comprado a 60: 40% de margen.
        self.gaseosa = Producto.objects.create(
            nombre="Gaseosa 500ml",
            precio=Decimal("100.00"),
            costo=Decimal("60.00"),
            stock=10,
            categoria=self.categoria,
        )
        # Vendido a 50, comprado a 45: solo 11% de margen.
        self.agua = Producto.objects.create(
            nombre="Agua 500ml",
            precio=Decimal("50.00"),
            costo=Decimal("45.00"),
            stock=2,
            categoria=self.categoria,
        )
        self.agotado = Producto.objects.create(
            nombre="Galletas",
            precio=Decimal("120.00"),
            costo=Decimal("70.00"),
            stock=0,
            categoria=self.categoria,
        )
        self.sin_costo = Producto.objects.create(
            nombre="Chicle",
            precio=Decimal("80.00"),
            costo=Decimal("0.00"),
            stock=4,
            categoria=self.categoria,
        )


class ResolverRangoTests(TestCase):
    def test_sin_fechas_usa_ultimos_dias(self):
        desde, hasta, desde_dt, hasta_dt = reportes.resolver_rango()
        self.assertEqual(hasta, timezone.localdate())
        self.assertEqual(desde, timezone.localdate() - timedelta(days=13))
        self.assertLess(desde_dt, hasta_dt)

    def test_parsea_fechas_validas(self):
        desde, hasta, _, _ = reportes.resolver_rango("2026-01-01", "2026-01-31")
        self.assertEqual(desde, date(2026, 1, 1))
        self.assertEqual(hasta, date(2026, 1, 31))

    def test_invierte_rango_al_reves(self):
        desde, hasta, _, _ = reportes.resolver_rango("2026-01-31", "2026-01-01")
        self.assertEqual(desde, date(2026, 1, 1))
        self.assertEqual(hasta, date(2026, 1, 31))

    def test_fecha_invalida_cae_al_rango_por_defecto(self):
        desde, hasta, _, _ = reportes.resolver_rango("ayer", "no-es-fecha")
        self.assertEqual(hasta, timezone.localdate())

    def test_solo_desde_ignora_hasta(self):
        desde, hasta, _, _ = reportes.resolver_rango(desde="2026-03-10")
        self.assertEqual(desde, date(2026, 3, 10))
        self.assertEqual(hasta, timezone.localdate())

    def test_rango_incluye_todo_el_dia_final(self):
        _, _, _, hasta_dt = reportes.resolver_rango("2026-01-01", "2026-01-31")
        self.assertEqual(hasta_dt.hour, 23)
        self.assertEqual(hasta_dt.minute, 59)


class ResumenVentasTests(BaseReportes):
    def setUp(self):
        super().setUp()
        self.hoy = timezone.localdate()
        _, _, self.desde_dt, self.hasta_dt = reportes.resolver_rango(
            f"{self.hoy - timedelta(days=30)}", f"{self.hoy}"
        )

    def test_sin_ventas_devuelve_ceros(self):
        resumen = reportes.resumen_ventas(self.desde_dt, self.hasta_dt)
        self.assertEqual(resumen["cantidad_ventas"], 0)
        self.assertEqual(resumen["ingresos"], Decimal("0.00"))
        self.assertEqual(resumen["ticket_promedio"], Decimal("0.00"))
        self.assertEqual(resumen["margen_porcentual"], Decimal("0.00"))

    def test_suma_ingresos_y_costos(self):
        # 2 gaseosas (200) + 1 agua (50) = 250 de venta
        # costo: 2x60 + 1x45 = 165 -> ganancia 85
        _crear_venta(self.admin, [(self.gaseosa, 2), (self.agua, 1)])

        resumen = reportes.resumen_ventas(self.desde_dt, self.hasta_dt)
        self.assertEqual(resumen["cantidad_ventas"], 1)
        self.assertEqual(resumen["ingresos"], Decimal("250.00"))
        self.assertEqual(resumen["costo"], Decimal("165.00"))
        self.assertEqual(resumen["ganancia"], Decimal("85.00"))

    def test_ticket_promedio_sobre_varias_ventas(self):
        _crear_venta(self.admin, [(self.gaseosa, 1)])  # 100
        _crear_venta(self.admin, [(self.gaseosa, 3)])  # 300

        resumen = reportes.resumen_ventas(self.desde_dt, self.hasta_dt)
        self.assertEqual(resumen["cantidad_ventas"], 2)
        self.assertEqual(resumen["ingresos"], Decimal("400.00"))
        self.assertEqual(resumen["ticket_promedio"], Decimal("200.00"))

    def test_cuenta_unidades_vendidas(self):
        _crear_venta(self.admin, [(self.gaseosa, 2), (self.agua, 1)])
        resumen = reportes.resumen_ventas(self.desde_dt, self.hasta_dt)
        self.assertEqual(resumen["unidades_vendidas"], 3)

    def test_excluye_ventas_fuera_del_rango(self):
        _crear_venta(
            self.admin,
            [(self.gaseosa, 1)],
            fecha=timezone.make_aware(datetime.combine(self.hoy - timedelta(days=60), datetime.min.time())),
        )
        resumen = reportes.resumen_ventas(self.desde_dt, self.hasta_dt)
        self.assertEqual(resumen["cantidad_ventas"], 0)

    def test_filtro_solo_finalizadas(self):
        _crear_venta(self.admin, [(self.gaseosa, 1)], finalizada=False)

        todas = reportes.resumen_ventas(self.desde_dt, self.hasta_dt)
        finalizadas = reportes.resumen_ventas(
            self.desde_dt, self.hasta_dt, solo_finalizadas=True
        )
        self.assertEqual(todas["cantidad_ventas"], 1)
        self.assertEqual(finalizadas["cantidad_ventas"], 0)

    def test_margen_usa_costo_congelado_no_el_actual(self):
        """Si el costo sube después, el margen histórico no se reescribe."""
        venta = _crear_venta(self.admin, [(self.gaseosa, 1)])
        self.gaseosa.costo = Decimal("95.00")
        self.gaseosa.save()

        resumen = reportes.resumen_ventas(self.desde_dt, self.hasta_dt)
        self.assertEqual(resumen["costo"], Decimal("60.00"))
        self.assertEqual(resumen["ganancia"], Decimal("40.00"))

        # Y el detalle sigue teniendo el costo viejo congelado.
        detalle = venta.detalles.first()
        self.assertEqual(detalle.costo_unitario, Decimal("60.00"))

    def test_venta_sin_detalles_no_revienta(self):
        Venta.objects.create(total=Decimal("999.00"), finalizada=True)
        resumen = reportes.resumen_ventas(self.desde_dt, self.hasta_dt)
        self.assertEqual(resumen["ingresos"], Decimal("999.00"))
        self.assertEqual(resumen["costo"], Decimal("0.00"))
        self.assertEqual(resumen["ganancia"], Decimal("999.00"))


class DeudaOtorgadaTests(BaseReportes):
    """HU-14: lo fiado a cuenta corriente no cuenta como ingreso."""

    def setUp(self):
        super().setUp()
        self.hoy = timezone.localdate()
        _, _, self.desde_dt, self.hasta_dt = reportes.resolver_rango(
            f"{self.hoy - timedelta(days=30)}", f"{self.hoy}"
        )

    def test_ingresos_excluyen_lo_fiado(self):
        _crear_venta(self.admin, [(self.gaseosa, 2)])  # $200 cobrado
        _crear_venta(
            self.admin,
            [(self.gaseosa, 3)],
            metodo_pago="cuenta_corriente",  # $300 fiado
        )
        resumen = reportes.resumen_ventas(self.desde_dt, self.hasta_dt)
        self.assertEqual(resumen["ingresos"], Decimal("200.00"))
        self.assertEqual(resumen["cantidad_ventas"], 1)

    def test_deuda_otorgada_suma_solo_lo_fiado(self):
        _crear_venta(self.admin, [(self.gaseosa, 2)])
        _crear_venta(
            self.admin, [(self.gaseosa, 3)], metodo_pago="cuenta_corriente"
        )
        fiado = reportes.deuda_otorgada(self.desde_dt, self.hasta_dt)
        self.assertEqual(fiado, Decimal("300.00"))

    def test_deuda_otorgada_sin_ventas_fiadas_es_cero(self):
        _crear_venta(self.admin, [(self.gaseosa, 1)])
        fiado = reportes.deuda_otorgada(self.desde_dt, self.hasta_dt)
        self.assertEqual(fiado, Decimal("0.00"))

    def test_ventas_por_dia_excluye_lo_fiado(self):
        _crear_venta(self.admin, [(self.gaseosa, 1)])  # $100
        _crear_venta(
            self.admin, [(self.gaseosa, 5)], metodo_pago="cuenta_corriente"
        )
        serie = reportes.ventas_por_dia(self.desde_dt, self.hasta_dt)
        self.assertEqual(serie[-1]["ingresos"], Decimal("100.00"))

    def test_top_productos_excluye_lo_fiado(self):
        _crear_venta(self.admin, [(self.gaseosa, 1)])
        _crear_venta(
            self.admin, [(self.gaseosa, 9)], metodo_pago="cuenta_corriente"
        )
        top = reportes.top_productos(self.desde_dt, self.hasta_dt)
        gaseosa = next(f for f in top if f["producto__id"] == self.gaseosa.pk)
        self.assertEqual(gaseosa["unidades"], 1)

    def test_ventas_del_rango_puede_incluir_fiado(self):
        _crear_venta(
            self.admin, [(self.gaseosa, 1)], metodo_pago="cuenta_corriente"
        )
        cobradas = reportes.ventas_del_rango(
            self.desde_dt, self.hasta_dt, incluir_fiado=False
        )
        todas = reportes.ventas_del_rango(
            self.desde_dt, self.hasta_dt, incluir_fiado=True
        )
        self.assertEqual(cobradas.count(), 0)
        self.assertEqual(todas.count(), 1)


class VentasPorDiaTests(BaseReportes):
    def setUp(self):
        super().setUp()
        self.hoy = timezone.localdate()
        _, _, self.desde_dt, self.hasta_dt = reportes.resolver_rango(
            f"{self.hoy - timedelta(days=6)}", f"{self.hoy}"
        )

    def test_sin_ventas_devuelve_la_serie_en_ceros(self):
        """
        Aunque no haya ventas, la serie cubre el rango pedido: el gráfico
        necesita los días para dibujar el eje.
        """
        serie = reportes.ventas_por_dia(self.desde_dt, self.hasta_dt)
        self.assertEqual(len(serie), 7)
        for fila in serie:
            self.assertEqual(fila["ventas"], 0)
            self.assertEqual(fila["ingresos"], Decimal("0.00"))

    def test_agrupa_por_dia(self):
        """Dos ventas del mismo día se suman en una sola fila."""
        _crear_venta(self.admin, [(self.gaseosa, 1)])  # 100
        _crear_venta(self.admin, [(self.gaseosa, 2)])  # 200

        serie = reportes.ventas_por_dia(self.desde_dt, self.hasta_dt)

        con_ventas = [fila for fila in serie if fila["ventas"] > 0]
        self.assertEqual(len(con_ventas), 1)
        self.assertEqual(con_ventas[0]["ventas"], 2)
        self.assertEqual(con_ventas[0]["ingresos"], Decimal("300.00"))

    def test_rellena_dias_sin_ventas(self):
        """Un día sin ventas va con ceros, no desaparece de la serie."""
        _crear_venta(self.admin, [(self.gaseosa, 1)])

        serie = reportes.ventas_por_dia(self.desde_dt, self.hasta_dt)
        self.assertEqual(len(serie), 7)
        self.assertEqual(sum(fila["ventas"] for fila in serie), 1)

        con_ventas = [fila for fila in serie if fila["ventas"] > 0]
        self.assertEqual(len(con_ventas), 1)

        for fila in serie:
            if fila["ventas"] == 0:
                self.assertEqual(fila["ingresos"], Decimal("0.00"))
                self.assertEqual(fila["ganancia"], Decimal("0.00"))

    def test_serie_cubre_el_rango_pedido(self):
        """
        Si solo se vendió el primer día del rango, los días siguientes igual
        aparecen en cero. Antes la serie se cortaba en la última venta y
        el gráfico mentía sobre los días sin datos.
        """
        inicio = self.hoy - timedelta(days=6)
        _crear_venta(
            self.admin,
            [(self.gaseosa, 1)],
            fecha=timezone.make_aware(datetime.combine(inicio, datetime.min.time())),
        )

        serie = reportes.ventas_por_dia(self.desde_dt, self.hasta_dt)
        self.assertEqual(len(serie), 7)
        self.assertEqual(serie[0]["ventas"], 1)
        self.assertEqual(serie[-1]["dia"], self.hoy)
        self.assertEqual(serie[-1]["ventas"], 0)

    def test_serie_en_orden_cronologico(self):
        _crear_venta(self.admin, [(self.gaseosa, 1)])
        serie = reportes.ventas_por_dia(self.desde_dt, self.hasta_dt)
        fechas = [fila["dia"] for fila in serie]
        self.assertEqual(fechas, sorted(fechas))

    def test_incluye_ganancia_por_dia(self):
        _crear_venta(self.admin, [(self.gaseosa, 1)])
        serie = reportes.ventas_por_dia(self.desde_dt, self.hasta_dt)
        dia_con_venta = [f for f in serie if f["ventas"] > 0][0]
        self.assertEqual(dia_con_venta["costo"], Decimal("60.00"))
        self.assertEqual(dia_con_venta["ganancia"], Decimal("40.00"))

    def test_incluye_unidades_por_dia(self):
        """El tooltip del gráfico necesita cuántas unidades se vendieron."""
        _crear_venta(self.admin, [(self.gaseosa, 2), (self.agua, 3)])
        serie = reportes.ventas_por_dia(self.desde_dt, self.hasta_dt)

        dia_con_venta = [f for f in serie if f["ventas"] > 0][0]
        self.assertEqual(dia_con_venta["unidades"], 5)
        # Los días sin ventas también traen el campo, en cero.
        self.assertTrue(all("unidades" in fila for fila in serie))
        self.assertEqual(sum(fila["unidades"] for fila in serie), 5)


class TopProductosTests(BaseReportes):
    def setUp(self):
        super().setUp()
        self.hoy = timezone.localdate()
        _, _, self.desde_dt, self.hasta_dt = reportes.resolver_rango(
            f"{self.hoy - timedelta(days=30)}", f"{self.hoy}"
        )

    def test_ordena_por_unidades_vendidas(self):
        _crear_venta(self.admin, [(self.agua, 1)])
        _crear_venta(self.admin, [(self.gaseosa, 5)])

        top = reportes.top_productos(self.desde_dt, self.hasta_dt)
        self.assertEqual(len(top), 2)
        self.assertEqual(top[0]["producto__nombre"], "Gaseosa 500ml")
        self.assertEqual(top[0]["unidades"], 5)

    def test_respeta_el_limite(self):
        _crear_venta(self.admin, [(self.gaseosa, 1), (self.agua, 1), (self.agotado, 1)])
        top = reportes.top_productos(self.desde_dt, self.hasta_dt, limite=2)
        self.assertEqual(len(top), 2)

    def test_ganancia_mas_alta_puede_no_ser_mas_vendido(self):
        """
        El agua se vende más unidades pero deja menos plata: 7 x $5 = $35
        contra 6 gaseosas x $40 = $240. Por eso los dos rankings no
        pueden ser el mismo listado.
        """
        _crear_venta(self.admin, [(self.agua, 7)])
        _crear_venta(self.admin, [(self.gaseosa, 6)])

        top = reportes.top_productos(self.desde_dt, self.hasta_dt)
        rentables = reportes.productos_mas_rentables(self.desde_dt, self.hasta_dt)

        self.assertEqual(top[0]["producto__nombre"], "Agua 500ml")
        self.assertEqual(rentables[0]["producto__nombre"], "Gaseosa 500ml")

    def test_rentables_trae_montos_por_unidad(self):
        _crear_venta(self.admin, [(self.gaseosa, 4)])  # 4 x $100, costo $60

        fila = reportes.productos_mas_rentables(
            self.desde_dt, self.hasta_dt
        )[0]

        self.assertEqual(fila["ganancia"], Decimal("160.00"))
        self.assertEqual(fila["ganancia_unitaria"], Decimal("40.00"))
        self.assertEqual(fila["costo_unitario"], Decimal("60.00"))
        self.assertEqual(fila["ingresos_unitarios"], Decimal("100.00"))

    def test_orden_por_unidad_cambia_el_ranking(self):
        """
        El agua deja $100 en total (20 x $5) y la gaseosa $40 (1 x $40).
        Por total gana el agua; por unidad gana la gaseosa.
        """
        _crear_venta(self.admin, [(self.agua, 20)])
        _crear_venta(self.admin, [(self.gaseosa, 1)])

        por_total = reportes.productos_mas_rentables(
            self.desde_dt, self.hasta_dt
        )
        por_unidad = reportes.productos_mas_rentables(
            self.desde_dt, self.hasta_dt, por_unidad=True
        )

        self.assertEqual(por_total[0]["producto__nombre"], "Agua 500ml")
        self.assertEqual(por_unidad[0]["producto__nombre"], "Gaseosa 500ml")


class ResumenStockTests(BaseReportes):
    def test_cuenta_productos_y_unidades(self):
        stock = reportes.resumen_stock()
        self.assertEqual(stock["cantidad_productos"], 4)
        self.assertEqual(stock["unidades"], 16)  # 10 + 2 + 0 + 4

    def test_valoriza_a_costo_y_a_venta(self):
        stock = reportes.resumen_stock()
        # a costo: 10x60 + 2x45 + 0x70 + 4x0 = 690
        self.assertEqual(stock["valor_costo"], Decimal("690.00"))
        # a venta: 10x100 + 2x50 + 0x120 + 4x80 = 1420
        self.assertEqual(stock["valor_venta"], Decimal("1420.00"))
        self.assertEqual(stock["ganancia_potencial"], Decimal("730.00"))

    def test_excluye_inactivos(self):
        self.gaseosa.activo = False
        self.gaseosa.save()

        stock = reportes.resumen_stock(solo_activos=True)
        self.assertEqual(stock["cantidad_productos"], 3)

    def test_detecta_stock_bajo(self):
        stock = reportes.resumen_stock()
        # El agua (2), el chicle (4) y las galletas (0) están en o por
        # debajo de 5. La gaseosa (10) no entra.
        self.assertEqual(stock["cantidad_stock_bajo"], 3)
        nombres = {p.nombre for p in stock["stock_bajo"]}
        self.assertEqual(nombres, {"Agua 500ml", "Chicle", "Galletas"})

    def test_cuenta_sin_stock(self):
        stock = reportes.resumen_stock()
        self.assertEqual(stock["sin_stock"], 1)

    def test_cuenta_productos_sin_costo(self):
        stock = reportes.resumen_stock()
        self.assertEqual(stock["sin_costo"], 1)

    def test_stock_bajo_ordenado_de_menor_a_mayor(self):
        stock = reportes.resumen_stock()
        cantidades = [p.stock for p in stock["stock_bajo"]]
        self.assertEqual(cantidades, sorted(cantidades))


class StockPorCategoriaTests(BaseReportes):
    def test_agrupa_por_categoria(self):
        otras = Categoria.objects.create(nombre="Snacks")
        Producto.objects.create(
            nombre="Papa",
            precio=Decimal("200.00"),
            costo=Decimal("100.00"),
            stock=5,
            categoria=otras,
        )

        filas = reportes.stock_por_categoria()
        self.assertEqual(len(filas), 2)
        # Snacks vale 500 a costo, Bebidas 690.
        self.assertEqual(filas[0]["categoria__nombre"], "Bebidas")


class ProductosBajoMargenTests(BaseReportes):
    def test_detecta_margen_bajo(self):
        # El agua tiene 11% de margen; la gaseosa 40%.
        bajos = reportes.productos_bajo_margen(umbral=Decimal("20.00"))
        nombres = [p.nombre for p in bajos]
        self.assertEqual(nombres, ["Agua 500ml"])

    def test_ignora_productos_sin_costo(self):
        """Sin costo cargado el margen es 0, pero no es un producto malo."""
        bajos = reportes.productos_bajo_margen(umbral=Decimal("20.00"))
        self.assertNotIn("Chicle", [p.nombre for p in bajos])

    def test_ordena_del_margen_mas_bajo(self):
        bajos = reportes.productos_bajo_margen(umbral=Decimal("99.00"))
        porcentajes = [p.margen_porcentual for p in bajos]
        self.assertEqual(porcentajes, sorted(porcentajes))


class PropiedadesProductoTests(BaseReportes):
    def test_margen_unitario(self):
        self.assertEqual(self.gaseosa.margen_unitario, Decimal("40.00"))

    def test_margen_porcentual_sobre_costo(self):
        # (100 - 60) / 60 * 100 = 66.666...
        self.assertAlmostEqual(
            float(self.gaseosa.margen_porcentual), 66.6667, places=3
        )

    def test_margen_porcentual_cero_sin_costo(self):
        self.assertEqual(self.sin_costo.margen_porcentual, Decimal("0.00"))

    def test_valor_del_stock(self):
        self.assertEqual(self.gaseosa.valor_stock_costo, Decimal("600.00"))
        self.assertEqual(self.gaseosa.valor_stock_venta, Decimal("1000.00"))


class PropiedadesDetalleVentaTests(BaseReportes):
    def test_costo_y_ganancia(self):
        venta = _crear_venta(self.admin, [(self.gaseosa, 3)])
        detalle = venta.detalles.first()

        self.assertEqual(detalle.subtotal(), Decimal("300.00"))
        self.assertEqual(detalle.costo_total(), Decimal("180.00"))
        self.assertEqual(detalle.ganancia(), Decimal("120.00"))


class ReportesVentasViewTests(BaseReportes):
    def test_acceso_requiere_login(self):
        respuesta = self.client.get(reverse("administracion:reportes_ventas"))
        self.assertEqual(respuesta.status_code, 302)

    def test_cajero_recibe_403(self):
        self.client.login(username="cajero_test", password="claveSegura123")
        respuesta = self.client.get(reverse("administracion:reportes_ventas"))
        self.assertEqual(respuesta.status_code, 403)

    def test_usuario_sin_grupo_recibe_403(self):
        User.objects.create_user(username="sin_rol", password="claveSegura123")
        self.client.login(username="sin_rol", password="claveSegura123")
        respuesta = self.client.get(reverse("administracion:reportes_ventas"))
        self.assertEqual(respuesta.status_code, 403)

    def test_administrador_puede_acceder(self):
        self.client.login(username="admin_test", password="claveSegura123")
        respuesta = self.client.get(reverse("administracion:reportes_ventas"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertTemplateUsed(respuesta, "administracion/reportes_ventas.html")

    def test_superuser_puede_acceder(self):
        self.client.login(username="super_test", password="claveSegura123")
        respuesta = self.client.get(reverse("administracion:reportes_ventas"))
        self.assertEqual(respuesta.status_code, 200)

    def test_pasa_kpis_al_template(self):
        _crear_venta(self.admin, [(self.gaseosa, 2), (self.agua, 1)])
        self.client.login(username="admin_test", password="claveSegura123")

        respuesta = self.client.get(reverse("administracion:reportes_ventas"))
        resumen = respuesta.context["resumen"]
        self.assertEqual(resumen["cantidad_ventas"], 1)
        self.assertEqual(resumen["ingresos"], Decimal("250.00"))

    def test_filtro_por_rango_de_fechas(self):
        hoy = timezone.localdate()
        _crear_venta(
            self.admin,
            [(self.gaseosa, 1)],
            fecha=timezone.make_aware(datetime.combine(hoy - timedelta(days=10), datetime.min.time())),
        )

        self.client.login(username="admin_test", password="claveSegura123")
        # Rango que no cubre la venta.
        respuesta = self.client.get(
            reverse("administracion:reportes_ventas"),
            {"desde": f"{hoy}", "hasta": f"{hoy}"},
        )
        self.assertEqual(respuesta.context["resumen"]["cantidad_ventas"], 0)

        # Rango que sí la cubre.
        respuesta = self.client.get(
            reverse("administracion:reportes_ventas"),
            {"desde": f"{hoy - timedelta(days=20)}", "hasta": f"{hoy}"},
        )
        self.assertEqual(respuesta.context["resumen"]["cantidad_ventas"], 1)

    def test_solo_finalizadas_desde_el_query(self):
        _crear_venta(self.admin, [(self.gaseosa, 1)], finalizada=False)
        self.client.login(username="admin_test", password="claveSegura123")

        respuesta = self.client.get(
            reverse("administracion:reportes_ventas"), {"finalizadas": "1"}
        )
        self.assertEqual(respuesta.context["resumen"]["cantidad_ventas"], 0)
        self.assertTrue(respuesta.context["solo_finalizadas"])

    def test_toggle_unidad_cambia_los_montos_de_rentables(self):
        _crear_venta(self.admin, [(self.gaseosa, 2)])
        self.client.login(username="admin_test", password="claveSegura123")

        total = self.client.get(reverse("administracion:reportes_ventas"))
        unidad = self.client.get(
            reverse("administracion:reportes_ventas"), {"modo": "unidad"}
        )

        self.assertEqual(total.context["modo_rentables"], "total")
        self.assertEqual(unidad.context["modo_rentables"], "unidad")
        fila = unidad.context["rentables"][0]
        self.assertEqual(fila["ganancia_unitaria"], Decimal("40.00"))
        self.assertEqual(fila["costo_unitario"], Decimal("60.00"))
        self.assertContains(unidad, "Ganancia c/u")
        self.assertContains(total, "Ganancia</th>")

    def test_calcula_techo_de_las_barras(self):
        _crear_venta(self.admin, [(self.gaseosa, 5)])
        self.client.login(username="admin_test", password="claveSegura123")

        respuesta = self.client.get(reverse("administracion:reportes_ventas"))
        self.assertEqual(respuesta.context["max_ingresos"], Decimal("500.00"))
        self.assertEqual(respuesta.context["max_ganancia"], Decimal("200.00"))

    def test_vista_vacia_no_revienta(self):
        """
        Sin ventas la vista igual tiene que renderizar: la serie viene en
        ceros (para dibujar el eje) y las barras quedan en 0 de alto.
        """
        self.client.login(username="admin_test", password="claveSegura123")
        respuesta = self.client.get(reverse("administracion:reportes_ventas"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context["resumen"]["cantidad_ventas"], 0)
        self.assertEqual(list(respuesta.context["ventas"]), [])
        # La serie no está vacía: trae los días del rango, todos en cero.
        self.assertEqual(len(respuesta.context["serie"]), 14)
        self.assertEqual(
            sum(fila["ventas"] for fila in respuesta.context["serie"]), 0
        )
        self.assertEqual(respuesta.context["max_ingresos"], 0)
        self.assertEqual(respuesta.context["max_ganancia"], 0)

    def test_no_muestra_costos_al_cajero(self):
        """El cajero no llega a la vista: 403 antes de renderizar nada."""
        _crear_venta(self.admin, [(self.gaseosa, 1)])
        self.client.login(username="cajero_test", password="claveSegura123")

        respuesta = self.client.get(reverse("administracion:reportes_ventas"))
        self.assertEqual(respuesta.status_code, 403)
        self.assertNotIn("resumen", respuesta.context)


class ReportesStockViewTests(BaseReportes):
    def test_acceso_requiere_login(self):
        respuesta = self.client.get(reverse("administracion:reportes_stock"))
        self.assertEqual(respuesta.status_code, 302)

    def test_cajero_recibe_403(self):
        self.client.login(username="cajero_test", password="claveSegura123")
        respuesta = self.client.get(reverse("administracion:reportes_stock"))
        self.assertEqual(respuesta.status_code, 403)

    def test_administrador_puede_acceder(self):
        self.client.login(username="admin_test", password="claveSegura123")
        respuesta = self.client.get(reverse("administracion:reportes_stock"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertTemplateUsed(respuesta, "administracion/reportes_stock.html")

    def test_pasa_resumen_de_stock(self):
        self.client.login(username="admin_test", password="claveSegura123")
        respuesta = self.client.get(reverse("administracion:reportes_stock"))

        stock = respuesta.context["stock"]
        self.assertEqual(stock["cantidad_productos"], 4)
        self.assertEqual(stock["valor_costo"], Decimal("690.00"))

    def test_filtro_de_activos(self):
        self.gaseosa.activo = False
        self.gaseosa.save()
        self.client.login(username="admin_test", password="claveSegura123")

        respuesta = self.client.get(
            reverse("administracion:reportes_stock"), {"activos": "0"}
        )
        self.assertEqual(respuesta.context["stock"]["cantidad_productos"], 4)

    def test_lista_bajo_margen(self):
        self.client.login(username="admin_test", password="claveSegura123")
        respuesta = self.client.get(reverse("administracion:reportes_stock"))
        nombres = [p.nombre for p in respuesta.context["bajo_margen"]]
        self.assertIn("Agua 500ml", nombres)

    def test_vista_vacia_no_revienta(self):
        Producto.objects.all().delete()
        self.client.login(username="admin_test", password="claveSegura123")

        respuesta = self.client.get(reverse("administracion:reportes_stock"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context["stock"]["cantidad_productos"], 0)
        self.assertEqual(list(respuesta.context["por_categoria"]), [])

    def test_badge_de_stock_bajo_es_rojo_no_verde(self):
        """El badge de la tabla de stock bajo es `status-bajo` (rojo):
        un producto con pocas unidades es una alerta, no un "todo OK"."""
        self.client.login(username="admin_test", password="claveSegura123")
        respuesta = self.client.get(reverse("administracion:reportes_stock"))

        self.assertContains(respuesta, "status-bajo")
        # El producto con stock 2 ("Agua 500ml") sale con ese badge...
        agua_fila = next(
            (p for p in respuesta.context["stock"]["stock_bajo"] if p.stock == 2),
            None,
        )
        self.assertIsNotNone(agua_fila)
        # ...y nunca con status-active (verde): acá hay 2 productos con
        # stock entre 1 y 5 (Agua con 2 y Chicle con 4).
        self.assertContains(respuesta, 'status-badge status-bajo', count=2)

    def test_ancla_stock_bajo_existe_para_el_link_del_dashboard(self):
        """El KPI del dashboard linkea a /reportes/stock/#stock-bajo."""
        self.client.login(username="admin_test", password="claveSegura123")
        respuesta = self.client.get(reverse("administracion:reportes_stock"))
        self.assertContains(respuesta, 'id="stock-bajo"')