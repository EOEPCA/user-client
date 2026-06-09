"""Tests for client and eoapi."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from eoepca_client.client import Client
from eoepca_client.config import resolve_platform
from eoepca_client.models import TokenSet


def test_client_platform() -> None:
    client = Client("develop")
    assert client.platform == "develop"


def test_resolve_alias() -> None:
    assert Client("develop.eoepca.org").platform == "develop"


def test_unknown_platform() -> None:
    with pytest.raises(ValueError, match="Unknown platform"):
        Client("unknown")


@patch("eoepca_client.auth.login")
def test_client_login_delegates(mock_login: MagicMock) -> None:
    Client("develop").login(username="u", password="p")
    mock_login.assert_called_once_with(
        resolve_platform("develop"), username="u", password="p"
    )


@patch("eoepca_client.client.pystac_client.Client.open")
def test_stac_client_sends_bearer(mock_open: MagicMock, tmp_path: Path) -> None:
    token_path = tmp_path / "tokens.json"
    tokens = TokenSet(
        access_token="test-bearer",
        expires_at=9999999999,
        platform="develop",
    )
    token_path.write_text(
        json.dumps({"develop": tokens.model_dump()}), encoding="utf-8"
    )
    mock_open.return_value = MagicMock()
    with patch("eoepca_client.auth.token_path", return_value=token_path):
        Client("develop").eoapi.stac()
    assert (
        mock_open.call_args.kwargs["headers"]["Authorization"] == "Bearer test-bearer"
    )


@patch("eoepca_client.client.pystac_client.Client.open")
def test_stac_client_no_bearer(mock_open: MagicMock, tmp_path: Path) -> None:
    mock_open.return_value = MagicMock()
    missing = tmp_path / "missing.json"
    with patch("eoepca_client.auth.token_path", return_value=missing):
        Client("develop").eoapi.stac()
    assert mock_open.call_args.kwargs["headers"] is None


def test_profile_uses_eoapi_client() -> None:
    assert resolve_platform("develop").client_id == "eoapi"


def test_profile_urls() -> None:
    profile = resolve_platform("develop")
    assert profile.realm == "eoepca"
    assert profile.keycloak_url == "https://iam-auth.develop.eoepca.org"
