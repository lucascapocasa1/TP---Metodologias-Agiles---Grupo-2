"""
Tests del botón "Conectar con Mercado Pago" (OAuth).

Mercado Pago no se llama de verdad: `mercadopago._llamar` se reemplaza con
mock para simular sus respuestas.
"""
from datetime import timedelta
from unittest import mock
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth.models import Group, User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from auditoria.models import RegistroAuditoria

from . import mercadopago
from .models import ConexionMercadoPago, PagoMercadoPago
from .tests import BaseCobro

CREDENCIALES = {"MP_CLIENT_ID": "123", "MP_CLIENT_SECRET": "secreto", "MP_ACCESS_TOKEN": ""}

RESPUESTA_TOKEN = {
    "access_token": "TEST-token-del-negocio",
    "refresh_token": "TG-refresh",
    "expires_in": 15552000,
    "user_id": 999,
    "live_mode": False,
}


def respuesta_mp(metodo, ruta, datos=None, token=None):
    """Imita a Mercado Pago: canje de token y datos de la cuenta."""
    if ruta == "/oauth/token":
        return RESPUESTA_TOKEN
    if ruta == "/users/me":
        return {"first_name": "Kiosco", "last_name": "Don Pepe"}
    raise AssertionError(f"Llamada inesperada a {ruta}")


class BaseConexion(TestCase):
    def setUp(self):
        Group.objects.create(name="Administrador")
        Group.objects.create(name="Cajero")
        self.admin = User.objects.create_user(username="dueno", password="claveSegura123")
        self.admin.groups.add(Group.objects.get(name="Administrador"))
        self.cajero = User.objects.create_user(username="caja", password="claveSegura123")
        self.cajero.groups.add(Group.objects.get(name="Cajero"))
        self.client.login(username="dueno", password="claveSegura123")

    def conectar(self):
        """Toca el botón y simula la vuelta de Mercado Pago con el código."""
        respuesta = self.client.post(reverse("ventas:mercadopago_conectar"))
        state = parse_qs(urlsplit(respuesta.url).query)["state"][0]
        with mock.patch("ventas.mercadopago._llamar", side_effect=respuesta_mp) as llamar:
            self.client.get(reverse("ventas:mercadopago_callback"), {"code": "TG-codigo", "state": state})
        return llamar


@override_settings(**CREDENCIALES)
class ConectarCuentaTests(BaseConexion):
    def test_solo_el_administrador_ve_el_panel(self):
        self.assertEqual(self.client.get(reverse("ventas:mercadopago_config")).status_code, 200)
        self.client.logout()
        self.client.login(username="caja", password="claveSegura123")
        self.assertEqual(self.client.get(reverse("ventas:mercadopago_config")).status_code, 403)
        self.assertEqual(self.client.post(reverse("ventas:mercadopago_conectar")).status_code, 403)

    def test_el_boton_lleva_a_mercado_pago(self):
        respuesta = self.client.post(reverse("ventas:mercadopago_conectar"))
        self.assertEqual(respuesta.status_code, 302)
        destino = urlsplit(respuesta.url)
        parametros = parse_qs(destino.query)
        self.assertEqual(destino.netloc, "auth.mercadopago.com")
        self.assertEqual(parametros["client_id"], ["123"])
        self.assertTrue(parametros["redirect_uri"][0].endswith("/ventas/mercadopago/callback/"))
        self.assertTrue(parametros["state"][0])

    def test_conectar_guarda_la_cuenta_del_negocio(self):
        llamar = self.conectar()
        conexion = ConexionMercadoPago.actual()
        self.assertEqual(conexion.access_token, "TEST-token-del-negocio")
        self.assertEqual(conexion.mp_user_id, "999")
        self.assertEqual(conexion.nombre_cuenta, "Kiosco Don Pepe")
        self.assertFalse(conexion.produccion)
        self.assertEqual(conexion.conectada_por, self.admin)
        self.assertGreater(conexion.expira, timezone.now() + timedelta(days=100))
        # Se canjeó el código con las credenciales de la plataforma.
        datos = llamar.call_args_list[0].args[2]
        self.assertEqual(datos["code"], "TG-codigo")
        self.assertEqual(datos["client_secret"], "secreto")
        self.assertTrue(RegistroAuditoria.objects.filter(accion="Mercado Pago conectado").exists())

    def test_el_panel_no_muestra_el_token(self):
        self.conectar()
        respuesta = self.client.get(reverse("ventas:mercadopago_config"))
        self.assertContains(respuesta, "Kiosco Don Pepe")
        self.assertNotContains(respuesta, "TEST-token-del-negocio")
        self.assertNotContains(respuesta, "TG-refresh")

    def test_rechaza_una_vuelta_con_state_falso(self):
        self.client.post(reverse("ventas:mercadopago_conectar"))
        with mock.patch("ventas.mercadopago._llamar", side_effect=respuesta_mp) as llamar:
            self.client.get(reverse("ventas:mercadopago_callback"), {"code": "TG-x", "state": "falso"})
        llamar.assert_not_called()
        self.assertIsNone(ConexionMercadoPago.actual())

    def test_si_el_dueno_cancela_no_se_conecta(self):
        self.client.post(reverse("ventas:mercadopago_conectar"))
        self.client.get(reverse("ventas:mercadopago_callback"), {"error": "access_denied"})
        self.assertIsNone(ConexionMercadoPago.actual())

    def test_conectar_otra_cuenta_reemplaza_la_anterior(self):
        self.conectar()
        self.conectar()
        self.assertEqual(ConexionMercadoPago.objects.count(), 1)

    def test_desconectar(self):
        self.conectar()
        self.client.post(reverse("ventas:mercadopago_desconectar"))
        self.assertIsNone(ConexionMercadoPago.actual())
        self.assertFalse(mercadopago.esta_configurado())


@override_settings(MP_CLIENT_ID="", MP_CLIENT_SECRET="", MP_ACCESS_TOKEN="")
class SinAplicacionTests(BaseConexion):
    def test_sin_aplicacion_el_boton_no_se_muestra(self):
        respuesta = self.client.get(reverse("ventas:mercadopago_config"))
        self.assertNotContains(respuesta, "Conectar con Mercado Pago</button>")
        self.assertContains(respuesta, "modo de prueba")
        respuesta = self.client.post(reverse("ventas:mercadopago_conectar"))
        self.assertRedirects(respuesta, reverse("ventas:mercadopago_config"))


@override_settings(**CREDENCIALES)
class TokenAUsarTests(TestCase):
    def crear_conexion(self, **campos):
        datos = {
            "access_token": "TEST-conectado",
            "refresh_token": "TG-refresh",
            "expira": timezone.now() + timedelta(days=150),
            "mp_user_id": "1",
        }
        datos.update(campos)
        return ConexionMercadoPago.objects.create(**datos)

    def test_sin_nada_es_modo_de_prueba(self):
        self.assertFalse(mercadopago.esta_configurado())

    @override_settings(MP_ACCESS_TOKEN="TEST-del-env")
    def test_la_cuenta_conectada_gana_al_env(self):
        self.assertEqual(mercadopago._token(), "TEST-del-env")
        self.crear_conexion()
        self.assertEqual(mercadopago._token(), "TEST-conectado")
        self.assertTrue(mercadopago.usa_sandbox())

    def test_cuenta_real_no_usa_sandbox(self):
        self.crear_conexion(produccion=True)
        self.assertFalse(mercadopago.usa_sandbox())

    def test_renueva_el_token_si_esta_por_vencer(self):
        self.crear_conexion(expira=timezone.now() + timedelta(days=2))
        nuevo = {"access_token": "TEST-renovado", "refresh_token": "TG-nuevo", "expires_in": 15552000}
        with mock.patch("ventas.mercadopago._llamar", return_value=nuevo) as llamar:
            self.assertEqual(mercadopago._token(), "TEST-renovado")
        self.assertEqual(llamar.call_args.args[2]["grant_type"], "refresh_token")
        self.assertEqual(ConexionMercadoPago.actual().refresh_token, "TG-nuevo")

    def test_si_falla_la_renovacion_usa_el_token_actual(self):
        self.crear_conexion(expira=timezone.now() + timedelta(days=2))
        with mock.patch("ventas.mercadopago._llamar", side_effect=mercadopago.MercadoPagoError("caído")):
            self.assertEqual(mercadopago._token(), "TEST-conectado")


@override_settings(**CREDENCIALES)
class CobroConCuentaConectadaTests(BaseCobro):
    def test_el_qr_se_cobra_con_la_cuenta_conectada(self):
        ConexionMercadoPago.objects.create(
            access_token="TEST-conectado", mp_user_id="1",
            expira=timezone.now() + timedelta(days=150),
        )
        self.login_cajero()
        self.agregar("7790000000001")
        with mock.patch(
            "ventas.mercadopago._llamar",
            return_value={"id": "pref-9", "init_point": "https://mp/real", "sandbox_init_point": "https://mp/sandbox"},
        ) as llamar:
            self.confirmar(metodo="mercado_pago", monto="")
        pago = PagoMercadoPago.objects.get()
        self.assertFalse(pago.simulado)
        self.assertEqual(pago.link_pago, "https://mp/sandbox")  # cuenta de prueba
        # Desde localhost no se manda webhook (Mercado Pago no puede llegar).
        self.assertNotIn("notification_url", llamar.call_args.args[2])

    def test_online_con_https_manda_el_webhook(self):
        ConexionMercadoPago.objects.create(
            access_token="APP_USR-real", mp_user_id="1", produccion=True,
            expira=timezone.now() + timedelta(days=150),
        )
        self.login_cajero()
        self.agregar("7790000000001")
        with mock.patch(
            "ventas.mercadopago._llamar",
            return_value={"id": "pref-9", "init_point": "https://mp/real"},
        ) as llamar:
            self.client.post(
                reverse("ventas:cobro_confirmar"),
                {"metodo_pago": "mercado_pago"},
                secure=True,
            )
        datos = llamar.call_args.args[2]
        self.assertTrue(datos["notification_url"].startswith("https://"))
        self.assertTrue(datos["notification_url"].endswith("/ventas/mercadopago/webhook/"))
        self.assertEqual(PagoMercadoPago.objects.get().link_pago, "https://mp/real")
