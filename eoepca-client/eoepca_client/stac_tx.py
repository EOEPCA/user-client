"""STAC transaction writes and HTTP error mapping."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

import httpx

from eoepca_client.config import PlatformConfig
from eoepca_client.models import StacItemRef


class EoepcaError(Exception):
    exit_code: int = 1

    def __init__(self, message: str) -> None:
        super().__init__(message)


class AuthError(EoepcaError):
    exit_code = 2


class ForbiddenError(EoepcaError):
    exit_code = 3


class NotFoundError(EoepcaError):
    exit_code = 4


class ServerError(EoepcaError):
    exit_code = 5


def http_error(status: int, message: str) -> EoepcaError:
    if status == 401:
        return AuthError(message)
    if status == 403:
        return ForbiddenError(message)
    if status == 404:
        return NotFoundError(message)
    if status >= 500:
        return ServerError(message)
    return EoepcaError(message)


class StacTx:
    def __init__(self, profile: PlatformConfig, *, bearer: str | None = None) -> None:
        self._profile = profile
        self._headers = {"Authorization": f"Bearer {bearer}"} if bearer else {}

    def _url(self, collection: str, item_id: str | None = None) -> str:
        base = f"{self._profile.stac_url.rstrip('/')}/collections/{collection}/items"
        return f"{base}/{item_id}" if item_id else base

    @staticmethod
    def _body(path_or_url: str) -> bytes:
        if urlparse(path_or_url).scheme in ("http", "https"):
            response = httpx.get(path_or_url, timeout=60.0)
            response.raise_for_status()
            return response.content
        return Path(path_or_url).read_bytes()

    def add_item(self, collection: str, path_or_url: str) -> StacItemRef:
        url = self._url(collection)
        with httpx.Client(headers=self._headers, timeout=60.0) as client:
            response = client.post(
                url,
                content=self._body(path_or_url),
                headers={"Content-Type": "application/geo+json"},
            )
        if response.status_code not in (200, 201):
            raise http_error(
                response.status_code, response.text or f"POST {url} failed"
            )
        return StacItemRef.from_stac_dict(response.json())

    def delete_item(self, collection: str, item_id: str) -> None:
        url = self._url(collection, item_id)
        with httpx.Client(headers=self._headers, timeout=60.0) as client:
            response = client.delete(url)
        if response.status_code not in (200, 204):
            raise http_error(
                response.status_code, response.text or f"DELETE {url} failed"
            )
