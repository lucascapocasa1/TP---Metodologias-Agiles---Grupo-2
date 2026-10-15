from datetime import datetime, time, timedelta

from django.contrib.auth.models import Group, User
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import RegistroAuditoria
from .utils import registrar_accion


class BaseAuditoria(TestCase):
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

        self.sin_rol = User.objects.create_user(
            username="sin_rol", password="claveSegura123"
        )

        self.superuser = User.objects.create_superuser(
            username="super_test", password="claveSegura123"
        )

    def login_admin(self):
        """Entrar como admin y dejar el historial limpio para el test.

        La señal `user_logged_in` crea su propio registro, que ensuciaría
        los conteos y los estados vacíos.
        """
        self.client.login(username="admin_test", password="claveSegura123")
        RegistroAuditoria.objects.all().delete()

    def registrar(self, accion, detalle="", usuario=None):
        """Crea un registro por el camino real y lo devuelve."""
        registrar_accion(usuario or self.admin, accion, detalle)
        return RegistroAuditoria.objects.latest("pk")


class HistorialAccesoTests(BaseAuditoria):
    def test_acceso_requiere_login(self):
        respuesta = self.client.get(reverse("auditoria:historial"))
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn("login", respuesta.url)

    def test_cajero_recibe_403(self):
        self.client.login(username="cajero_test", password="claveSegura123")
        respuesta = self.client.get(reverse("auditoria:historial"))
        self.assertEqual(respuesta.status_code, 403)

    def test_usuario_sin_grupo_recibe_403(self):
        self.client.login(username="sin_rol", password="claveSegura123")
        respuesta = self.client.get(reverse("auditoria:historial"))
        self.assertEqual(respuesta.status_code, 403)

    def test_administrador_puede_acceder(self):
        self.client.login(username="admin_test", password="claveSegura123")
        respuesta = self.client.get(reverse("auditoria:historial"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertTemplateUsed(respuesta, "auditoria/historial.html")

    def test_superuser_puede_acceder(self):
        self.client.login(username="super_test", password="claveSegura123")
        respuesta = self.client.get(reverse("auditoria:historial"))
        self.assertEqual(respuesta.status_code, 200)


class HistorialListadoTests(BaseAuditoria):
    def test_muestra_detalle_de_ventas_y_de_cambios(self):
        self.login_admin()
        self.registrar("Venta confirmada", "Venta N° 7 por $1.500,00 (Efectivo)")
        self.registrar("Usuario editado", "Se editó el usuario 'cajero_test'")

        respuesta = self.client.get(reverse("auditoria:historial"))

        self.assertContains(respuesta, "Venta N° 7 por $1.500,00 (Efectivo)")
        self.assertContains(respuesta, "Se editó el usuario &#x27;cajero_test&#x27;")

    def test_ordena_del_mas_reciente_al_mas_viejo(self):
        self.login_admin()
        viejo = self.registrar("Inicio de sesión")
        nuevo = self.registrar("Cierre de sesión")
        RegistroAuditoria.objects.filter(pk=viejo.pk).update(
            fecha=timezone.now() - timedelta(days=1)
        )

        respuesta = self.client.get(reverse("auditoria:historial"))

        acciones = [r.accion for r in respuesta.context["registros"]]
        self.assertEqual(acciones, [nuevo.accion, viejo.accion])

    def test_registro_sin_usuario_se_muestra_como_sistema(self):
        self.login_admin()
        RegistroAuditoria.objects.create(accion="Algo automático", detalle="Sin autor")

        respuesta = self.client.get(reverse("auditoria:historial"))

        self.assertContains(respuesta, "Algo automático")
        self.assertContains(respuesta, "Sistema")

    def test_contadores_por_tipo_de_evento(self):
        self.login_admin()
        self.registrar("Venta confirmada", "Venta N° 1 por $900,00 (Efectivo)")
        self.registrar("Venta confirmada", "Venta N° 2 por $100,00 (Tarjeta)")
        self.registrar("Usuario creado", "Se creó el usuario 'pepe'")
        self.registrar("Inicio de sesión")

        respuesta = self.client.get(reverse("auditoria:historial"))

        self.assertEqual(respuesta.context["totales"]["total"], 4)
        self.assertEqual(respuesta.context["totales"]["ventas"], 2)
        self.assertEqual(respuesta.context["totales"]["usuarios"], 1)
        self.assertEqual(respuesta.context["totales"]["sesiones"], 1)

    def test_sin_registros_muestra_estado_vacio(self):
        self.login_admin()
        respuesta = self.client.get(reverse("auditoria:historial"))
        self.assertContains(respuesta, "No hay registros para mostrar")


class HistorialFiltrosTests(BaseAuditoria):
    def test_tipo_ventas_lista_solo_ventas(self):
        self.login_admin()
        self.registrar("Venta confirmada", "Venta N° 3 por $500,00 (Efectivo)")
        self.registrar("Usuario eliminado", "Se eliminó el usuario 'viejo'")

        respuesta = self.client.get(reverse("auditoria:historial"), {"tipo": "ventas"})

        acciones = [r.accion for r in respuesta.context["registros"]]
        self.assertEqual(acciones, ["Venta confirmada"])
        self.assertNotContains(respuesta, "Se eliminó el usuario")
        self.assertEqual(respuesta.context["tipo"], "ventas")

    def test_tipo_invalido_se_ignora(self):
        self.login_admin()
        self.registrar("Inicio de sesión")

        respuesta = self.client.get(reverse("auditoria:historial"), {"tipo": "raro"})

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context["tipo"], "")

    def test_busca_por_detalle_y_por_usuario(self):
        self.login_admin()
        self.registrar("Venta confirmada", "Venta N° 9 por $700,00 (Tarjeta)")
        self.registrar("Roles actualizados", "Roles de 'cajero_test' a Cajero")

        respuesta = self.client.get(reverse("auditoria:historial"), {"q": "tarjeta"})

        acciones = [r.accion for r in respuesta.context["registros"]]
        self.assertEqual(acciones, ["Venta confirmada"])

        respuesta = self.client.get(reverse("auditoria:historial"), {"q": "cajero_test"})
        acciones = [r.accion for r in respuesta.context["registros"]]
        self.assertEqual(acciones, ["Roles actualizados"])

    def test_filtro_por_rango_de_fechas(self):
        self.login_admin()
        reciente = self.registrar("Venta confirmada", "Venta de hoy")
        antiguo = self.registrar("Venta confirmada", "Venta vieja")
        RegistroAuditoria.objects.filter(pk=antiguo.pk).update(
            fecha=timezone.make_aware(
                datetime.combine(
                    timezone.localdate() - timedelta(days=10), time(12, 0)
                )
            )
        )

        hoy = timezone.localdate()
        respuesta = self.client.get(
            reverse("auditoria:historial"),
            {"desde": hoy.isoformat(), "hasta": hoy.isoformat()},
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context["desde"], hoy)
        self.assertEqual(
            [r.pk for r in respuesta.context["registros"]], [reciente.pk]
        )

    def test_rango_invertido_se_intercambia(self):
        self.login_admin()
        self.registrar("Venta confirmada", "Venta N° 4")

        hoy = timezone.localdate()
        fecha_vieja = hoy - timedelta(days=30)
        respuesta = self.client.get(
            reverse("auditoria:historial"),
            {"desde": hoy.isoformat(), "hasta": fecha_vieja.isoformat()},
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context["desde"], fecha_vieja)
        self.assertEqual(respuesta.context["hasta"], hoy)
        self.assertEqual(len(respuesta.context["registros"]), 1)


class HistorialPaginacionTests(BaseAuditoria):
    def test_pagina_dos_muestra_el_resto(self):
        self.login_admin()
        for i in range(25):
            self.registrar("Inicio de sesión", f"Acceso {i}")

        respuesta = self.client.get(reverse("auditoria:historial"), {"page": "2"})

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context["page_obj"].number, 2)
        self.assertEqual(len(respuesta.context["registros"]), 5)

    def test_pagina_invalida_no_revienta(self):
        self.login_admin()
        for i in range(3):
            self.registrar("Inicio de sesión", f"Acceso {i}")

        respuesta = self.client.get(reverse("auditoria:historial"), {"page": "999"})

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context["page_obj"].number, 1)

    def test_paginar_preserva_el_filtro_de_tipo(self):
        self.login_admin()
        for i in range(21):
            self.registrar("Venta confirmada", f"Venta {i}")
        self.registrar("Inicio de sesión")

        respuesta = self.client.get(
            reverse("auditoria:historial"), {"tipo": "ventas", "page": "1"}
        )

        self.assertContains(respuesta, "tipo=ventas&amp;page=2")


class SenalesYUtilsTests(BaseAuditoria):
    """El registro lo escriben las señales de sesión y `registrar_accion`."""

    def test_el_login_y_el_logout_quedan_registrados(self):
        self.client.login(username="admin_test", password="claveSegura123")
        self.assertTrue(
            RegistroAuditoria.objects.filter(
                accion="Inicio de sesión", usuario=self.admin
            ).exists()
        )

        self.client.logout()
        self.assertTrue(
            RegistroAuditoria.objects.filter(
                accion="Cierre de sesión", usuario=self.admin
            ).exists()
        )

    def test_registrar_accion_guarda_detalle_e_ip(self):
        request = RequestFactory().get("/")
        request.META["REMOTE_ADDR"] = "127.0.0.1"

        registrar_accion(self.admin, "Usuario creado", "Se creó 'pepe'", request)

        registro = RegistroAuditoria.objects.latest("pk")
        self.assertEqual(registro.usuario, self.admin)
        self.assertEqual(registro.detalle, "Se creó 'pepe'")
        self.assertEqual(registro.ip, "127.0.0.1")


class BotonEnLosReportesTests(BaseAuditoria):
    """El botón a la auditoría vive en la cabecera de ambos reportes."""

    def setUp(self):
        super().setUp()
        self.login_admin()

    def test_reporte_de_ventas_tiene_el_boton(self):
        respuesta = self.client.get(reverse("administracion:reportes_ventas"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, f'href="{reverse("auditoria:historial")}"')

    def test_reporte_de_stock_tiene_el_boton(self):
        respuesta = self.client.get(reverse("administracion:reportes_stock"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, f'href="{reverse("auditoria:historial")}"')

    def test_las_fichas_del_historial_filtran_por_tipo(self):
        respuesta = self.client.get(reverse("auditoria:historial"))
        self.assertContains(respuesta, "tipo=ventas")
        self.assertContains(respuesta, "tipo=usuarios")
        self.assertContains(respuesta, "tipo=sesiones")
