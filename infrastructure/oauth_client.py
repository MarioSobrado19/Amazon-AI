"""OAuth2 client-credentials con transporte inyectable y errores seguros."""

import base64
import json
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class ApiError(RuntimeError):
    def __init__(self, code, message, *, retryable=False, status=None):
        super().__init__(message)
        self.code = code
        self.retryable = retryable
        self.status = status


def default_transport(method, url, *, headers=None, params=None, data=None, timeout=15):
    if params:
        url = f"{url}?{urlencode(params)}"
    request = Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read()
            return response.status, dict(response.headers), json.loads(body or b"{}")
    except HTTPError as error:
        code = "rate_limited" if error.code == 429 else "http_error"
        raise ApiError(code, f"La API respondió HTTP {error.code}.", retryable=error.code == 429 or error.code >= 500, status=error.code) from None
    except (URLError, TimeoutError):
        raise ApiError("network_error", "No se pudo conectar con la API.", retryable=True) from None


class ClientCredentialsTokenProvider:
    def __init__(self, token_url, client_id, client_secret, scope, *, transport=default_transport, clock=time.time):
        if not client_id or not client_secret:
            raise ValueError("Faltan credenciales OAuth2.")
        self.token_url = token_url
        self.client_id = client_id
        self._client_secret = client_secret
        self.scope = scope
        self.transport = transport
        self.clock = clock
        self._token = None
        self._expires_at = 0

    def get_token(self):
        now = self.clock()
        if self._token and now < self._expires_at - 30:
            return self._token
        basic = base64.b64encode(f"{self.client_id}:{self._client_secret}".encode()).decode()
        body = urlencode({"grant_type": "client_credentials", "scope": self.scope}).encode()
        _, _, payload = self.transport("POST", self.token_url, headers={"Authorization": f"Basic {basic}", "Content-Type": "application/x-www-form-urlencoded"}, data=body)
        token = payload.get("access_token") if isinstance(payload, dict) else None
        if not token:
            raise ApiError("authentication_failed", "OAuth2 no devolvió un access token.")
        self._token = token
        self._expires_at = now + max(0, int(payload.get("expires_in", 300)))
        return token
