"""WSGI HTTPS-ready; TLS debe terminar en el servicio de hosting."""

import json
import os
from urllib.parse import parse_qs

from compliance.ebay_deletion import DeletionInbox, EbayDataEraser, EbayDeletionService, EbayPublicKeyProvider, EbaySignatureVerifier


def build_service_from_env():
    provider = EbayPublicKeyProvider(os.getenv("EBAY_CLIENT_ID"), os.getenv("EBAY_CLIENT_SECRET"), environment=os.getenv("EBAY_ENVIRONMENT", "production"))
    verifier = EbaySignatureVerifier(provider)
    inbox = DeletionInbox(os.getenv("EBAY_DELETION_INBOX_PATH", "work/ebay_deletion.sqlite3"), os.getenv("EBAY_DELETION_IDEMPOTENCY_KEY"))
    return EbayDeletionService(os.getenv("EBAY_MARKETPLACE_DELETION_VERIFICATION_TOKEN"), os.getenv("EBAY_MARKETPLACE_DELETION_ENDPOINT_URL", ""), verifier, inbox)


def create_app(service=None):
    service = service or build_service_from_env()

    def app(environ, start_response):
        method = environ.get("REQUEST_METHOD", "")
        path = environ.get("PATH_INFO", "/compliance/ebay/account-deletion")
        if method == "GET" and path == "/healthz":
            body, status = b'{"status":"ok"}', "200 OK"
        elif path != "/compliance/ebay/account-deletion":
            body, status = b"", "404 Not Found"
        elif method == "GET":
            challenge = parse_qs(environ.get("QUERY_STRING", "")).get("challenge_code", [None])[0]
            try:
                body, status = json.dumps(service.get_challenge(challenge)).encode(), "200 OK"
            except ValueError:
                body, status = b'{"error":"invalid_challenge"}', "400 Bad Request"
        elif method == "POST":
            try:
                length = int(environ.get("CONTENT_LENGTH") or 0)
            except ValueError:
                length = 0
            if length <= 0 or length > 65536:
                code, body = 400, b'{"error":"invalid_payload"}'
            else:
                raw = environ["wsgi.input"].read(length)
                code, _ = service.accept_notification(raw, environ.get("HTTP_X_EBAY_SIGNATURE"))
                body = b""
            statuses = {202: "202 Accepted", 204: "204 No Content", 400: "400 Bad Request", 412: "412 Precondition Failed"}
            status = statuses[code]
        else:
            body, status = b"", "405 Method Not Allowed"
        headers = [("Content-Type", "application/json"), ("Content-Length", str(len(body))), ("Cache-Control", "no-store")]
        start_response(status, headers)
        return [body]

    return app


def process_deletions_from_env():
    """Worker separado: procesa la cola después del acknowledgement HTTP."""
    roots = [item for item in os.getenv("EBAY_DATA_ROOTS", "data").split(os.pathsep) if item]
    inbox = DeletionInbox(os.getenv("EBAY_DELETION_INBOX_PATH", "work/ebay_deletion.sqlite3"), os.getenv("EBAY_DELETION_IDEMPOTENCY_KEY"))
    return inbox.process_pending(EbayDataEraser(roots))
