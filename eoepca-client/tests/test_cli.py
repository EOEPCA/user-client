"""Tests for CLI."""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import jwt
import pytest
import respx
from typer.testing import CliRunner

from eoepca_client.cli import _expires_in, app
from eoepca_client.models import TokenSet

runner = CliRunner()
STAC_URL = "https://eoapi.develop.eoepca.org/stac"


@pytest.fixture
def token_file(tmp_path: Path) -> Path:
    path = tmp_path / "tokens.json"
    tokens = TokenSet(
        access_token="test-bearer", expires_at=9999999999, platform="develop"
    )
    path.write_text(json.dumps({"develop": tokens.model_dump()}), encoding="utf-8")
    return path


def test_login_password_success() -> None:
    with patch("eoepca_client.auth.login") as mock_login:
        mock_login.return_value = TokenSet(
            access_token="t", expires_at=int(time.time()) + 3600, platform="develop"
        )
        result = runner.invoke(app, ["login", "--username", "u", "--password", "p"])
    assert result.exit_code == 0
    assert "Login successful" in result.output


def test_login_already_logged_in() -> None:
    with patch("eoepca_client.auth.login", return_value=None):
        result = runner.invoke(app, ["login", "--username", "u", "--password", "p"])
    assert result.exit_code == 0
    assert "Already logged in" in result.output


def test_whoami_not_logged_in(tmp_path: Path) -> None:
    empty = tmp_path / "tokens.json"
    with patch("eoepca_client.auth.token_path", return_value=empty):
        assert runner.invoke(app, ["whoami"]).exit_code == 2


def test_whoami(token_file: Path) -> None:
    payload = {
        "preferred_username": "demo-user",
        "iss": "https://iam.example.com/realms/eoepca",
        "exp": int(time.time()) + 3600,
    }
    token = jwt.encode(payload, "secret", algorithm="HS256")
    token_file.write_text(
        json.dumps(
            {
                "develop": TokenSet(
                    access_token=token,
                    expires_at=int(time.time()) + 3600,
                    platform="develop",
                ).model_dump()
            }
        ),
        encoding="utf-8",
    )
    with patch("eoepca_client.auth.token_path", return_value=token_file):
        result = runner.invoke(app, ["whoami"])
    assert result.exit_code == 0
    assert "demo-user" in result.output


@patch("eoepca_client.cli.Client")
def test_stac_collections(mock_client: MagicMock) -> None:
    mock_client.return_value.eoapi.list_collections.return_value = [
        {"id": "coll-1", "title": "Collection One"}
    ]
    result = runner.invoke(app, ["stac", "collections"])
    assert result.exit_code == 0
    assert "coll-1" in result.output


@patch("eoepca_client.cli.Client")
def test_stac_search(mock_client: MagicMock) -> None:
    item = MagicMock()
    item.to_dict.return_value = {
        "id": "item-1",
        "collection": "coll-1",
        "properties": {"datetime": "2024-01-01T00:00:00Z"},
        "bbox": [-10, 40, 5, 55],
    }
    stac = mock_client.return_value.eoapi.stac.return_value
    stac.search.return_value.items.return_value = [item]
    result = runner.invoke(
        app, ["stac", "search", "-c", "coll-1", "--bbox", "-10,40,5,55", "--limit", "5"]
    )
    assert result.exit_code == 0
    assert "item-1" in result.output


@respx.mock
def test_stac_item_add(token_file: Path, tmp_path: Path) -> None:
    item_file = tmp_path / "item.geojson"
    item = {
        "type": "Feature",
        "stac_version": "1.0.0",
        "id": "new-item",
        "collection": "ws-test",
    }
    item_file.write_text(json.dumps(item), encoding="utf-8")
    respx.post(f"{STAC_URL}/collections/ws-test/items").mock(
        return_value=httpx.Response(201, json=item)
    )
    with patch("eoepca_client.auth.token_path", return_value=token_file):
        result = runner.invoke(app, ["stac", "item", "add", "ws-test", str(item_file)])
    assert result.exit_code == 0
    assert "new-item" in result.output


@respx.mock
def test_stac_item_add_forbidden(token_file: Path, tmp_path: Path) -> None:
    item_file = tmp_path / "item.geojson"
    item_file.write_text("{}", encoding="utf-8")
    respx.post(f"{STAC_URL}/collections/forbidden/items").mock(
        return_value=httpx.Response(403, text="forbidden")
    )
    with patch("eoepca_client.auth.token_path", return_value=token_file):
        result = runner.invoke(
            app, ["stac", "item", "add", "forbidden", str(item_file)]
        )
    assert result.exit_code == 3


def test_login_missing_credentials() -> None:
    with patch("eoepca_client.auth.get_bearer", return_value=None):
        result = runner.invoke(app, ["login"], input="")
    assert result.exit_code == 2


def test_logout() -> None:
    with patch("eoepca_client.auth.logout") as mock_logout:
        result = runner.invoke(app, ["logout"])
    assert result.exit_code == 0
    mock_logout.assert_called_once_with("develop")


def test_whoami_json(token_file: Path) -> None:
    payload = {
        "preferred_username": "demo-user",
        "iss": "https://iam.example.com/realms/eoepca",
        "exp": int(time.time()) + 3600,
    }
    token = jwt.encode(payload, "secret", algorithm="HS256")
    token_file.write_text(
        json.dumps(
            {
                "develop": TokenSet(
                    access_token=token,
                    expires_at=int(time.time()) + 3600,
                    platform="develop",
                ).model_dump()
            }
        ),
        encoding="utf-8",
    )
    with patch("eoepca_client.auth.token_path", return_value=token_file):
        result = runner.invoke(app, ["whoami", "--output", "json"])
    data = json.loads(result.output)
    assert data["preferred_username"] == "demo-user"
    assert "expires_in" not in data


def test_stac_search_requires_collection() -> None:
    assert runner.invoke(app, ["stac", "search"]).exit_code == 2


@patch("eoepca_client.cli.Client")
def test_stac_collections_json(mock_client: MagicMock) -> None:
    mock_client.return_value.eoapi.list_collections.return_value = [{"id": "coll-1"}]
    result = runner.invoke(app, ["stac", "collections", "--output", "json"])
    assert json.loads(result.output)[0]["id"] == "coll-1"


def test_cli_help_and_version() -> None:
    assert "login" in runner.invoke(app, ["--help"]).output
    assert "0.1.0" in runner.invoke(app, ["--version"]).output


@respx.mock
def test_stac_collections_from_catalog_file() -> None:
    catalog = Path(__file__).parent / "data" / "api-catalog.json"
    respx.get(f"{STAC_URL}/collections").mock(
        return_value=httpx.Response(
            200, json={"collections": [{"id": "from-catalog", "title": "Via catalog"}]}
        )
    )
    result = runner.invoke(app, ["stac", "collections", "-p", str(catalog.resolve())])
    assert result.exit_code == 0
    assert "from-catalog" in result.output


@pytest.mark.parametrize(
    ("offset", "expected"),
    [
        (-10, "expired"),
        (30, "30s"),
        (7200, "2h"),
        (172800, "2d"),
    ],
)
def test_expires_in(offset: int, expected: str) -> None:
    assert _expires_in(int(time.time()) + offset) == expected
