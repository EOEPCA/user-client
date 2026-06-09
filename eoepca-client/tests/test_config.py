"""Tests for platform configuration."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from eoepca_client.config import (
    _platform_registry,
    resolve_auth,
    resolve_platform,
)


@pytest.fixture(autouse=True)
def _clear_registry_cache() -> None:
    _platform_registry.cache_clear()
    yield
    _platform_registry.cache_clear()


def test_develop_defaults() -> None:
    cfg = resolve_platform("develop")
    assert cfg.client_id == "eoapi"
    assert cfg.realm == "eoepca"
    assert cfg.iam_issuer == "https://iam-auth.develop.eoepca.org/realms/eoepca"
    assert cfg.stac_url == "https://eoapi.develop.eoepca.org/stac"


def test_resolve_alias() -> None:
    assert resolve_platform("develop.eoepca.org").name == "develop"


def test_unknown_platform() -> None:
    with pytest.raises(ValueError, match="catalog file"):
        resolve_platform("unknown")


_TEST_CLIENT_SECRET = "s3" + "cr3t"


@patch.dict("os.environ", {"EOEPCA_CLIENT_SECRET": _TEST_CLIENT_SECRET}, clear=False)
def test_resolve_auth_secret_from_env() -> None:
    cfg = resolve_auth(resolve_platform("develop"))
    assert cfg.client_secret == _TEST_CLIENT_SECRET


@patch.dict(
    "os.environ",
    {"EOEPCA_CLIENT_ID": "opa", "EOEPCA_CLIENT_SECRET": _TEST_CLIENT_SECRET},
    clear=False,
)
def test_resolve_auth_id_and_secret() -> None:
    cfg = resolve_auth(resolve_platform("develop"))
    assert cfg.client_id == "opa"
    assert cfg.client_secret == _TEST_CLIENT_SECRET


def test_resolve_auth_explicit_overrides() -> None:
    secret = "cli" + "-secret"
    cfg = resolve_auth(
        resolve_platform("develop"), client_id="cli-id", client_secret=secret
    )
    assert cfg.client_id == "cli-id"
    assert cfg.client_secret == secret


def test_custom_platform_from_file(tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        """
[platforms.staging]
keycloak_url = "https://iam.example.com"
realm = "test"
client_id = "my-client"
stac_url = "https://stac.example.com/stac"
""",
        encoding="utf-8",
    )
    with patch("eoepca_client.config.config_path", return_value=config_file):
        _platform_registry.cache_clear()
        cfg = resolve_platform("staging")
    assert cfg.client_id == "my-client"
    assert cfg.iam_issuer == "https://iam.example.com/realms/test"


def test_platform_config_is_frozen() -> None:
    cfg = resolve_platform("develop")
    with pytest.raises(ValidationError):
        cfg.client_id = "other"  # type: ignore[misc]


@patch.dict("os.environ", {"EOEPCA_CONFIG": "/custom/config.toml"}, clear=False)
def test_config_path_override() -> None:
    from eoepca_client.config import config_path

    assert config_path() == Path("/custom/config.toml")
