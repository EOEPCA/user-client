"""Load PlatformConfig from an RFC 9727 API catalog (linkset JSON)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlparse

import httpx

from eoepca_client.config import PlatformConfig
from eoepca_client.stac_tx import EoepcaError, http_error

ISSUER_REL = "http://openid.net/specs/connect/1.0/issuer"
DATA_REL = "data"
CATALOG_SUFFIX = "/.well-known/api-catalog"


def _load_json(source: str) -> dict[str, Any]:
    path = Path(source)
    if path.is_file():
        return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))

    url = source
    if not url.startswith(("http://", "https://")):
        url = f"https://{source.rstrip('/')}{CATALOG_SUFFIX}"
    elif not urlparse(url).path.rstrip("/").endswith("api-catalog"):
        url = f"{url.rstrip('/')}{CATALOG_SUFFIX}"

    response = httpx.get(url, timeout=30.0, follow_redirects=True)
    if not response.is_success:
        raise http_error(response.status_code, response.text or f"GET {url} failed")
    return cast(dict[str, Any], response.json())


def _link_context(data: dict[str, Any]) -> dict[str, Any]:
    for ctx in data.get("linkset") or []:
        if str(ctx.get("anchor", "")).rstrip("/").endswith(CATALOG_SUFFIX.rstrip("/")):
            return cast(dict[str, Any], ctx)
    raise EoepcaError("API catalog has no linkset with an api-catalog anchor")


def _issuer_fields(ctx: dict[str, Any]) -> tuple[str, str, str]:
    targets = ctx.get(ISSUER_REL) or []
    if not targets:
        raise EoepcaError(f"API catalog missing OIDC issuer ({ISSUER_REL})")
    target = targets[0]
    href = str(target["href"]).rstrip("/")
    marker = "/realms/"
    if marker not in href:
        raise EoepcaError(f"OIDC issuer href is not a Keycloak realm URL: {href}")
    keycloak_url, realm_from_path = href.split(marker, 1)
    realm = str(target.get("eoepca:realm") or realm_from_path.split("/")[0])
    client_id = str(target.get("eoepca:default_client_id") or "eoapi")
    return keycloak_url, realm, client_id


def _is_stac_core(target: dict[str, Any]) -> bool:
    for uri in target.get("conformsTo") or []:
        text = str(uri)
        if "api.stacspec.org" in text and text.rstrip("/").endswith("core"):
            return True
    return False


def _stac_url(ctx: dict[str, Any]) -> str:
    candidates = [t for t in (ctx.get(DATA_REL) or []) if _is_stac_core(t)]
    if not candidates:
        raise EoepcaError("API catalog has no STAC service under the data relation")
    for target in candidates:
        if target.get("eoepca:auth") == "oidc-write":
            return str(target["href"])
    return str(candidates[0]["href"])


def platform_from_catalog(source: str) -> PlatformConfig:
    """Build a PlatformConfig from a local catalog file, URL, or domain."""
    data = _load_json(source)
    ctx = _link_context(data)
    keycloak_url, realm, client_id = _issuer_fields(ctx)
    stac_url = _stac_url(ctx)
    anchor = str(ctx["anchor"])
    name = urlparse(anchor).hostname or anchor
    return PlatformConfig(
        name=name,
        keycloak_url=keycloak_url,
        realm=realm,
        client_id=client_id,
        stac_url=stac_url,
    )
