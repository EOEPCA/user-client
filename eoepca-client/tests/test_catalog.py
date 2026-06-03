"""Tests for API catalog platform resolution."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx

from eoepca_client.catalog import platform_from_catalog
from eoepca_client.config import resolve_platform
from eoepca_client.stac_tx import EoepcaError

FIXTURE = Path(__file__).parent / "data" / "api-catalog.json"


def test_platform_from_catalog_file() -> None:
    cfg = platform_from_catalog(str(FIXTURE))
    assert cfg.name == "develop.eoepca.org"
    assert cfg.keycloak_url == "https://iam-auth.develop.eoepca.org"
    assert cfg.realm == "eoepca"
    assert cfg.client_id == "eoapi"
    assert cfg.stac_url == "https://eoapi.develop.eoepca.org/stac"
    assert cfg.iam_issuer == "https://iam-auth.develop.eoepca.org/realms/eoepca"


def test_resolve_platform_from_catalog_file() -> None:
    cfg = resolve_platform(str(FIXTURE))
    assert cfg.stac_url == "https://eoapi.develop.eoepca.org/stac"
    assert cfg.client_id == "eoapi"


def test_prefers_oidc_write_stac(tmp_path: Path) -> None:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    # Drop eoapi oidc-write entry — should fall back to first STAC-conformant.
    data["linkset"][0]["data"] = [
        t
        for t in data["linkset"][0]["data"]
        if t.get("href") != "https://eoapi.develop.eoepca.org/stac"
    ]
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    cfg = platform_from_catalog(str(path))
    assert cfg.stac_url == "https://resource-catalogue.develop.eoepca.org"


@respx.mock
def test_platform_from_catalog_url() -> None:
    body = FIXTURE.read_text(encoding="utf-8")
    url = "https://example.com/.well-known/api-catalog"
    respx.get(url).mock(return_value=httpx.Response(200, text=body))
    cfg = platform_from_catalog(url)
    assert cfg.stac_url == "https://eoapi.develop.eoepca.org/stac"


@respx.mock
def test_platform_from_catalog_domain() -> None:
    body = FIXTURE.read_text(encoding="utf-8")
    respx.get("https://staging.example.org/.well-known/api-catalog").mock(
        return_value=httpx.Response(200, text=body)
    )
    cfg = platform_from_catalog("staging.example.org")
    assert cfg.name == "develop.eoepca.org"
    assert cfg.client_id == "eoapi"


@respx.mock
def test_platform_from_catalog_base_url_appends_well_known() -> None:
    body = FIXTURE.read_text(encoding="utf-8")
    respx.get("https://staging.example.org/.well-known/api-catalog").mock(
        return_value=httpx.Response(200, text=body)
    )
    cfg = platform_from_catalog("https://staging.example.org")
    assert cfg.realm == "eoepca"


def test_missing_issuer(tmp_path: Path) -> None:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    data["linkset"][0].pop("http://openid.net/specs/connect/1.0/issuer")
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(EoepcaError, match="OIDC issuer"):
        platform_from_catalog(str(path))


def test_missing_stac(tmp_path: Path) -> None:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    data["linkset"][0]["data"] = [
        {"href": "https://example.com/vector", "title": "vector only"}
    ]
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(EoepcaError, match="no STAC service"):
        platform_from_catalog(str(path))


@respx.mock
def test_catalog_http_error() -> None:
    respx.get("https://missing.example.org/.well-known/api-catalog").mock(
        return_value=httpx.Response(404, text="missing")
    )
    with pytest.raises(EoepcaError):
        platform_from_catalog("missing.example.org")
