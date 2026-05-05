"""
PeopleSoft REST API client.

Handles authentication (Basic Auth or OAuth 2.0) and provides low-level HTTP
helpers used by every tool in server.py.
"""

import base64
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx


class PeopleSoftClient:
    """Thin async HTTP client for the PeopleSoft Integration Broker REST API."""

    # Base path for the Integration Broker REST Listening Connector
    _IB_BASE = "/PSIGW/RESTListeningConnector"
    # OAuth 2.0 token endpoint (PeopleTools 8.54+)
    _OAUTH_TOKEN_PATH = "/PSIGW/oauth2/v1/token"

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        *,
        auth_method: str = "basic",
        oauth_client_id: str = "",
        oauth_client_secret: str = "",
        timeout: float = 30.0,
        verify_ssl: bool = True,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.auth_method = auth_method.lower()
        self.oauth_client_id = oauth_client_id
        self.oauth_client_secret = oauth_client_secret
        self.timeout = timeout
        self.verify_ssl = verify_ssl

        self._oauth_token: str | None = None
        self._oauth_expires_at: datetime | None = None
        self._http: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------
    # Lifecycle helpers
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "PeopleSoftClient":
        self._http = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            verify=self.verify_ssl,
        )
        return self

    async def __aexit__(self, *_: Any) -> None:
        if self._http:
            await self._http.aclose()
            self._http = None

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def _basic_auth_header(self) -> str:
        encoded = base64.b64encode(
            f"{self.username}:{self.password}".encode()
        ).decode()
        return f"Basic {encoded}"

    async def _get_oauth_token(self) -> str:
        """Fetch or refresh an OAuth 2.0 bearer token."""
        now = datetime.now(timezone.utc)
        if self._oauth_token and self._oauth_expires_at and now < self._oauth_expires_at:
            return self._oauth_token

        assert self._http is not None, "Client not started — use async with"
        response = await self._http.post(
            self._OAUTH_TOKEN_PATH,
            data={
                "grant_type": "password",
                "client_id": self.oauth_client_id,
                "client_secret": self.oauth_client_secret,
                "username": self.username,
                "password": self.password,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        payload = response.json()
        self._oauth_token = payload["access_token"]
        expires_in = int(payload.get("expires_in", 3600))
        # Refresh 60 seconds before actual expiry to avoid edge-case failures.
        self._oauth_expires_at = now + timedelta(seconds=expires_in - 60)
        return self._oauth_token

    async def _auth_headers(self) -> dict[str, str]:
        if self.auth_method == "oauth":
            token = await self._get_oauth_token()
            return {"Authorization": f"Bearer {token}"}
        # Default: Basic Auth
        return {"Authorization": self._basic_auth_header()}

    # ------------------------------------------------------------------
    # Low-level HTTP helpers
    # ------------------------------------------------------------------

    async def get(self, path: str, **params: Any) -> Any:
        """Perform a GET request and return the parsed JSON response."""
        assert self._http is not None, "Client not started — use async with"
        headers = await self._auth_headers()
        headers["Accept"] = "application/json"
        response = await self._http.get(path, params=params, headers=headers)
        response.raise_for_status()
        return response.json()

    async def post(self, path: str, body: dict[str, Any]) -> Any:
        """Perform a POST request with a JSON body and return parsed JSON."""
        assert self._http is not None, "Client not started — use async with"
        headers = await self._auth_headers()
        headers["Content-Type"] = "application/json"
        headers["Accept"] = "application/json"
        response = await self._http.post(path, json=body, headers=headers)
        response.raise_for_status()
        return response.json()

    # ------------------------------------------------------------------
    # PeopleSoft Integration Broker REST helpers
    # ------------------------------------------------------------------

    def ib_path(self, service: str, operation: str, *segments: str) -> str:
        """Build a full Integration Broker REST path."""
        parts = [self._IB_BASE, service, operation, *segments]
        return "/".join(p.strip("/") for p in parts)


def client_from_env() -> PeopleSoftClient:
    """Build a PeopleSoftClient from environment variables.

    Required:
        PEOPLESOFT_BASE_URL  — e.g. https://ps.example.com:8000

    For Basic Auth (default):
        PEOPLESOFT_USERNAME
        PEOPLESOFT_PASSWORD

    For OAuth 2.0 (set AUTH_METHOD=oauth):
        PEOPLESOFT_AUTH_METHOD=oauth
        PEOPLESOFT_USERNAME
        PEOPLESOFT_PASSWORD
        PEOPLESOFT_OAUTH_CLIENT_ID
        PEOPLESOFT_OAUTH_CLIENT_SECRET
    """
    return PeopleSoftClient(
        base_url=os.environ["PEOPLESOFT_BASE_URL"],
        username=os.environ.get("PEOPLESOFT_USERNAME", ""),
        password=os.environ.get("PEOPLESOFT_PASSWORD", ""),
        auth_method=os.environ.get("PEOPLESOFT_AUTH_METHOD", "basic"),
        oauth_client_id=os.environ.get("PEOPLESOFT_OAUTH_CLIENT_ID", ""),
        oauth_client_secret=os.environ.get("PEOPLESOFT_OAUTH_CLIENT_SECRET", ""),
        timeout=float(os.environ.get("PEOPLESOFT_TIMEOUT", "30")),
        verify_ssl=os.environ.get("PEOPLESOFT_VERIFY_SSL", "true").lower() != "false",
    )
