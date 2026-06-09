"""EOEPCA client and eoapi facade."""

from __future__ import annotations

from typing import Any

import httpx
import pystac_client

from eoepca_client import auth
from eoepca_client.config import PlatformConfig, resolve_platform
from eoepca_client.stac_tx import StacTx, http_error


class EoApi:
    def __init__(self, client: Client) -> None:
        self._client = client

    def _headers(self) -> dict[str, str]:
        bearer = auth.get_bearer(self._client.profile)
        return {"Authorization": f"Bearer {bearer}"} if bearer else {}

    def stac(self) -> pystac_client.Client:
        profile = self._client.profile
        headers = self._headers() or None
        return pystac_client.Client.open(profile.stac_url, headers=headers)

    def list_collections(self) -> list[dict[str, Any]]:
        """List collections via HTTP (avoids pystac strict typing on /collections)."""
        url = f"{self._client.profile.stac_url.rstrip('/')}/collections"
        with httpx.Client(
            headers=self._headers(), timeout=60.0, follow_redirects=True
        ) as client:
            response = client.get(url)
        if not response.is_success:
            raise http_error(response.status_code, response.text or f"GET {url} failed")
        return list(response.json().get("collections") or [])

    @property
    def stac_transactions(self) -> StacTx:
        return StacTx(
            self._client.profile, bearer=auth.get_bearer(self._client.profile)
        )


class Client:
    def __init__(self, platform: str = "develop") -> None:
        self._profile = resolve_platform(platform)
        self._eoapi = EoApi(self)

    @property
    def platform(self) -> str:
        return self._profile.name

    @property
    def profile(self) -> PlatformConfig:
        return self._profile

    @property
    def eoapi(self) -> EoApi:
        return self._eoapi

    def login(
        self, *, username: str | None = None, password: str | None = None
    ) -> None:
        auth.login(self._profile, username=username, password=password)

    def logout(self) -> None:
        auth.logout(self._profile.name)
