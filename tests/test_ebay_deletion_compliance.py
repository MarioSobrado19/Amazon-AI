import base64
from io import BytesIO
import json
import tempfile
import unittest
from pathlib import Path

from compliance.ebay_deletion import (
    DeletionInbox,
    EbayDataEraser,
    EbayDeletionService,
    EbayPublicKeyProvider,
    challenge_response,
)
from compliance.ebay_deletion_wsgi import create_app
from infrastructure.oauth_client import ApiError


TOKEN = "verification-token-at-least-32-characters"
ENDPOINT = "https://oriva.example.invalid/compliance/ebay/account-deletion"


def payload(notification_id="notification-1", **identity):
    return {
        "metadata": {"topic": "MARKETPLACE_ACCOUNT_DELETION", "schemaVersion": "1.0", "deprecated": False},
        "notification": {"notificationId": notification_id, "eventDate": "2026-08-31T12:00:00Z", "publishDate": "2026-08-31T12:00:01Z", "publishAttemptCount": 1, "data": identity or {"userId": "user-123"}},
    }


class FakeVerifier:
    def __init__(self, valid=True):
        self.valid = valid

    def verify(self, raw_body, signature_header):
        return self.valid and signature_header == "valid-signature"


class EbayDeletionComplianceTests(unittest.TestCase):
    def make_service(self, directory, valid=True):
        inbox = DeletionInbox(Path(directory) / "inbox.sqlite3", "local-hmac-secret")
        return EbayDeletionService(TOKEN, ENDPOINT, FakeVerifier(valid), inbox), inbox

    def test_challenge_get_usa_concatenacion_exacta_sha256(self):
        expected = "eb884e49519603c6caef7cc4ce8aed6f8a59f3ea3488b0d45f548b55c9c05969"
        self.assertEqual(challenge_response("challenge", TOKEN, ENDPOINT), expected)

    def test_rechaza_verification_token_fuera_del_contrato_ebay(self):
        with tempfile.TemporaryDirectory() as directory:
            inbox = DeletionInbox(Path(directory) / "inbox.sqlite3", "key")
            for token in ("short", "x" * 81, "invalid token with spaces........"):
                with self.subTest(token=token), self.assertRaises(ValueError):
                    EbayDeletionService(token, ENDPOINT, FakeVerifier(), inbox)

    def test_post_valido_se_acepta_sin_procesar_borrado_en_request(self):
        with tempfile.TemporaryDirectory() as directory:
            service, inbox = self.make_service(directory)
            raw = json.dumps(payload()).encode()
            status, accepted = service.accept_notification(raw, "valid-signature")
            self.assertEqual(status, 202)
            self.assertTrue(accepted)
            self.assertEqual(inbox.process_pending(EbayDataEraser([Path(directory) / "data"])), 1)

    def test_post_duplicado_es_idempotente(self):
        with tempfile.TemporaryDirectory() as directory:
            service, _ = self.make_service(directory)
            raw = json.dumps(payload()).encode()
            self.assertEqual(service.accept_notification(raw, "valid-signature")[0], 202)
            self.assertEqual(service.accept_notification(raw, "valid-signature")[0], 204)

    def test_firma_invalida_retorna_412_y_no_encola(self):
        with tempfile.TemporaryDirectory() as directory:
            service, inbox = self.make_service(directory, valid=False)
            self.assertEqual(service.accept_notification(json.dumps(payload()).encode(), "bad")[0], 412)
            self.assertEqual(inbox.process_pending(EbayDataEraser([directory])), 0)

    def test_payload_invalido_retorna_400(self):
        with tempfile.TemporaryDirectory() as directory:
            service, _ = self.make_service(directory)
            for raw in (b"not-json", json.dumps({"metadata": {"topic": "OTHER"}}).encode(), json.dumps(payload(userId="")).encode()):
                with self.subTest(raw=raw):
                    self.assertEqual(service.accept_notification(raw, "valid-signature")[0], 400)

    def test_borrado_real_jsonl_y_snapshot_es_idempotente(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "data"
            root.mkdir()
            history = root / "history.jsonl"
            history.write_text(json.dumps({"market": {"seller_user_id": "user-123"}}) + "\n" + json.dumps({"market": {"seller_user_id": "other"}}) + "\n", encoding="utf-8")
            snapshot = root / "snapshot.json"
            snapshot.write_text(json.dumps({"seller": {"username": "private-name"}}), encoding="utf-8")
            eraser = EbayDataEraser([root])
            self.assertEqual(eraser.erase({"userId": "user-123", "username": "private-name"}), 2)
            self.assertFalse(snapshot.exists())
            self.assertNotIn("user-123", history.read_text())
            self.assertEqual(eraser.erase({"userId": "user-123", "username": "private-name"}), 0)

    def test_worker_elimina_identidades_de_cola_y_conserva_solo_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            inbox = DeletionInbox(Path(directory) / "inbox.sqlite3", "hmac-key")
            inbox.accept("notification-private", {"eiasToken": "token-private"})
            inbox.process_pending(EbayDataEraser([Path(directory) / "empty"]))
            raw = (Path(directory) / "inbox.sqlite3").read_bytes()
            self.assertNotIn(b"notification-private", raw)
            self.assertNotIn(b"token-private", raw)

    def test_wsgi_challenge_y_errores_http(self):
        with tempfile.TemporaryDirectory() as directory:
            service, _ = self.make_service(directory)
            app = create_app(service)
            statuses = []
            result = app({"REQUEST_METHOD": "GET", "QUERY_STRING": "challenge_code=challenge"}, lambda status, headers: statuses.append(status))
            self.assertEqual(statuses[-1], "200 OK")
            self.assertIn(b"challengeResponse", b"".join(result))
            result = app({"REQUEST_METHOD": "POST", "CONTENT_LENGTH": "999999", "wsgi.input": BytesIO()}, lambda status, headers: statuses.append(status))
            self.assertEqual(statuses[-1], "400 Bad Request")

    def test_wsgi_health_y_rutas_desconocidas(self):
        with tempfile.TemporaryDirectory() as directory:
            service, _ = self.make_service(directory)
            app, statuses = create_app(service), []
            body = app({"REQUEST_METHOD": "GET", "PATH_INFO": "/healthz"}, lambda status, headers: statuses.append(status))
            self.assertEqual(statuses[-1], "200 OK")
            self.assertEqual(b"".join(body), b'{"status":"ok"}')
            app({"REQUEST_METHOD": "GET", "PATH_INFO": "/other"}, lambda status, headers: statuses.append(status))
            self.assertEqual(statuses[-1], "404 Not Found")


class PublicKeyCacheTests(unittest.TestCase):
    def test_clave_publica_se_cachea_una_hora_solo_en_memoria(self):
        calls = []
        def transport(method, url, **kwargs):
            calls.append(url)
            if "oauth2/token" in url:
                return 200, {}, {"access_token": "token", "expires_in": 7200}
            return 200, {}, {"key": "public-key"}
        provider = EbayPublicKeyProvider("id", "secret", transport=transport, clock=lambda: 100)
        self.assertEqual(provider.get("kid-1"), "public-key")
        self.assertEqual(provider.get("kid-1"), "public-key")
        self.assertEqual(sum("public_key" in url for url in calls), 1)

    def test_error_de_clave_no_incluye_identificadores_privados(self):
        def transport(method, url, **kwargs):
            if "oauth2/token" in url:
                return 200, {}, {"access_token": "token"}
            return 200, {}, {}
        provider = EbayPublicKeyProvider("id", "secret", transport=transport)
        with self.assertRaises(ApiError) as raised:
            provider.get("kid-1")
        self.assertNotIn("kid-1", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
