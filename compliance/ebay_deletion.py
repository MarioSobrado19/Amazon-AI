"""Marketplace Account Deletion: validación, idempotencia y borrado."""

import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import sqlite3
import threading
import time
from urllib.parse import quote

from infrastructure.oauth_client import ClientCredentialsTokenProvider, ApiError, default_transport


TOPIC = "MARKETPLACE_ACCOUNT_DELETION"
IDENTITY_KEYS = frozenset({"userid", "user_id", "username", "eiastoken", "eias_token", "seller_user_id", "seller_username", "seller_eias_token"})


def challenge_response(challenge_code, verification_token, endpoint):
    if not all(isinstance(item, str) and item for item in (challenge_code, verification_token, endpoint)):
        raise ValueError("Challenge, verification token y endpoint son obligatorios.")
    return hashlib.sha256(f"{challenge_code}{verification_token}{endpoint}".encode("utf-8")).hexdigest()


class EbayPublicKeyProvider:
    """Obtiene claves oficiales y las mantiene solo en memoria durante una hora."""

    def __init__(self, client_id, client_secret, *, environment="production", transport=default_transport, clock=time.time, ttl=3600):
        host = "api.sandbox.ebay.com" if environment == "sandbox" else "api.ebay.com"
        self.base_url = f"https://{host}"
        self.transport, self.clock, self.ttl = transport, clock, ttl
        self.tokens = ClientCredentialsTokenProvider(f"{self.base_url}/identity/v1/oauth2/token", client_id, client_secret, "https:" + "//api.ebay.com/oauth/api_scope", transport=transport, clock=clock)
        self._cache = {}
        self._lock = threading.Lock()

    def get(self, key_id):
        if not isinstance(key_id, str) or not key_id or "/" in key_id:
            raise ValueError("key_id inválido.")
        now = self.clock()
        with self._lock:
            cached = self._cache.get(key_id)
            if cached and cached[1] > now:
                return cached[0]
        try:
            token = self.tokens.get_token()
        except ApiError as exc:
            print(f"EBAY_AUTH_STAGE stage=oauth_token code={exc.code} status={exc.status}", flush=True)
            raise
        try:
            _, _, payload = self.transport("GET", f"{self.base_url}/commerce/notification/v1/public_key/{quote(key_id)}", headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})
        except ApiError as exc:
            print(f"EBAY_AUTH_STAGE stage=public_key code={exc.code} status={exc.status}", flush=True)
            raise
        key = payload.get("key") if isinstance(payload, dict) else None
        if not key:
            raise ApiError("public_key_unavailable", "eBay no devolvió la clave pública.", retryable=True)
        with self._lock:
            self._cache[key_id] = (key, now + self.ttl)
        return key


class EbaySignatureVerifier:
    def __init__(self, key_provider):
        self.key_provider = key_provider

    def verify(self, raw_body, signature_header):
        try:
            packed = json.loads(base64.b64decode(signature_header, validate=True))
            key_id, signature = packed["kid"], base64.b64decode(packed["signature"], validate=True)
            digest_name = str(packed.get("digest", "SHA256")).replace("-", "").upper()
            if str(packed.get("alg", "")).casefold() not in {"ecdsa", "ec"}:
                return False
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import ec
            digest = {"SHA1": hashes.SHA1, "SHA256": hashes.SHA256}.get(digest_name)
            if digest is None:
                return False
            key_text = self.key_provider.get(key_id)
            if "BEGIN PUBLIC KEY" not in key_text:
                key_text = f"-----BEGIN PUBLIC KEY-----\n{key_text}\n-----END PUBLIC KEY-----"
            public_key = serialization.load_pem_public_key(key_text.encode("ascii"))
            public_key.verify(signature, raw_body, ec.ECDSA(digest()))
            return True
        except ApiError as exc:
            print(
                f"EBAY_SIGNATURE_VERIFY_ERROR type=ApiError code={exc.code} status={exc.status}",
                flush=True,
            )
            return False
        except Exception as exc:
            print(
                f"EBAY_SIGNATURE_VERIFY_ERROR type={type(exc)}",
                flush=True,
            )
            return False

def validate_deletion_payload(payload):
    if not isinstance(payload, dict) or set(payload) - {"metadata", "notification"}:
        raise ValueError("Payload inválido.")
    metadata, notification = payload.get("metadata"), payload.get("notification")
    if not isinstance(metadata, dict) or metadata.get("topic") != TOPIC or not isinstance(notification, dict):
        raise ValueError("Topic o notification inválido.")
    notification_id, data = notification.get("notificationId"), notification.get("data")
    if not isinstance(notification_id, str) or not notification_id or not isinstance(data, dict):
        raise ValueError("notificationId o data inválido.")
    identities = {key: data[key] for key in ("userId", "username", "eiasToken") if isinstance(data.get(key), str) and data[key]}
    if not identities:
        raise ValueError("La notificación no contiene identidad eliminable.")
    return notification_id, identities


class DeletionInbox:
    """Cola SQLite mínima; borra identidades al completar y conserva solo hashes."""

    def __init__(self, path, hash_key):
        if not hash_key:
            raise ValueError("Se requiere una clave local para idempotencia.")
        self.path, self._hash_key = Path(path), hash_key.encode()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript("CREATE TABLE IF NOT EXISTS pending (notification_hash TEXT PRIMARY KEY, identities TEXT NOT NULL); CREATE TABLE IF NOT EXISTS completed (notification_hash TEXT PRIMARY KEY, completed_at INTEGER NOT NULL);")

    def _connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.execute("PRAGMA secure_delete=ON")
        return db

    def _hash(self, notification_id):
        return hmac.new(self._hash_key, notification_id.encode(), hashlib.sha256).hexdigest()

    def accept(self, notification_id, identities):
        digest = self._hash(notification_id)
        with self._connect() as db:
            if db.execute("SELECT 1 FROM completed WHERE notification_hash=? UNION SELECT 1 FROM pending WHERE notification_hash=?", (digest, digest)).fetchone():
                return False
            try:
                db.execute("INSERT INTO pending(notification_hash, identities) VALUES (?, ?)", (digest, json.dumps(identities, sort_keys=True)))
            except sqlite3.IntegrityError:
                return False
        return True

    def process_pending(self, eraser):
        processed = 0
        with self._connect() as db:
            rows = db.execute("SELECT notification_hash, identities FROM pending").fetchall()
        for digest, raw_identities in rows:
            eraser.erase(json.loads(raw_identities))
            with self._connect() as db:
                db.execute("DELETE FROM pending WHERE notification_hash=?", (digest,))
                db.execute("INSERT OR IGNORE INTO completed(notification_hash, completed_at) VALUES (?, ?)", (digest, int(time.time())))
            processed += 1
        if processed:
            with self._connect() as db:
                db.execute("VACUUM")
        return processed


def _contains_identity(value, targets):
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).casefold() in IDENTITY_KEYS and isinstance(item, str) and hmac.compare_digest(item, targets.get(str(key).casefold(), "")):
                return True
            if _contains_identity(item, targets):
                return True
    elif isinstance(value, list):
        return any(_contains_identity(item, targets) for item in value)
    return False


class EbayDataEraser:
    """Borra registros JSON/JSONL vinculados por identificadores eBay explícitos."""

    def __init__(self, roots):
        self.roots = tuple(Path(root).resolve() for root in roots)

    def erase(self, identities):
        targets = {}
        aliases = {"userId": ("userid", "user_id", "seller_user_id"), "username": ("username", "seller_username"), "eiasToken": ("eiastoken", "eias_token", "seller_eias_token")}
        for source, keys in aliases.items():
            if identities.get(source):
                targets.update({key: identities[source] for key in keys})
        deleted = 0
        for root in self.roots:
            if not root.exists():
                continue
            for path in root.rglob("*"):
                if not path.is_file() or path.suffix not in {".json", ".jsonl"} or not path.resolve().is_relative_to(root):
                    continue
                if path.suffix == ".jsonl":
                    lines = path.read_text(encoding="utf-8").splitlines()
                    kept = [line for line in lines if not _contains_identity(json.loads(line), targets)]
                    deleted += len(lines) - len(kept)
                    if len(kept) != len(lines):
                        path.write_text("".join(f"{line}\n" for line in kept), encoding="utf-8")
                else:
                    payload = json.loads(path.read_text(encoding="utf-8"))
                    if _contains_identity(payload, targets):
                        path.unlink()
                        deleted += 1
        return deleted


class EbayDeletionService:
    def __init__(self, verification_token, endpoint, signature_verifier, inbox):
        if not isinstance(verification_token, str) or not re.fullmatch(r"[A-Za-z0-9_-]{32,80}", verification_token) or not endpoint.startswith("https://"):
            raise ValueError("Verification token y endpoint HTTPS son obligatorios.")
        self.verification_token, self.endpoint = verification_token, endpoint
        self.signature_verifier, self.inbox = signature_verifier, inbox

    def get_challenge(self, challenge_code):
        return {"challengeResponse": challenge_response(challenge_code, self.verification_token, self.endpoint)}

    def accept_notification(self, raw_body, signature_header):
        if not signature_header or not self.signature_verifier.verify(raw_body, signature_header):
            return 412, False
        try:
            payload = json.loads(raw_body.decode("utf-8"))
            notification_id, identities = validate_deletion_payload(payload)
        except (UnicodeError, json.JSONDecodeError, ValueError):
            return 400, False
        accepted = self.inbox.accept(notification_id, identities)
        return 202 if accepted else 204, accepted
