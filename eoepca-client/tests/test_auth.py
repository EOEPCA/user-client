"""Tests for auth module."""

from __future__ import annotations

import os
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import jwt
import pytest
from keycloak.exceptions import KeycloakPostError

from eoepca_client import auth
from eoepca_client.config import resolve_platform
from eoepca_client.models import TokenSet
from eoepca_client.stac_tx import AuthError


@pytest.fixture
def token_file(tmp_path: Path) -> Path:
    path = tmp_path / "tokens.json"
    with patch("eoepca_client.auth.token_path", return_value=path):
        yield path


def _tokens(exp_offset: int = 3600) -> TokenSet:
    return TokenSet(
        access_token="access-token",
        expires_at=int(time.time()) + exp_offset,
        platform="develop",
    )


def test_save_and_load_tokens(token_file: Path) -> None:
    auth.save_tokens(_tokens())
    assert token_file.stat().st_mode & 0o777 == 0o600
    loaded = auth.load_tokens("develop")
    assert loaded is not None
    assert loaded.access_token == "access-token"


def test_get_bearer_expired(token_file: Path) -> None:
    auth.save_tokens(_tokens(exp_offset=-120))
    assert auth.get_bearer(resolve_platform("develop")) is None


def test_get_bearer_valid(token_file: Path) -> None:
    auth.save_tokens(_tokens())
    assert auth.get_bearer(resolve_platform("develop")) == "access-token"


def test_logout_platform(token_file: Path) -> None:
    auth.save_tokens(_tokens())
    auth.logout("develop")
    assert auth.load_tokens("develop") is None


def test_logout_all(token_file: Path) -> None:
    auth.save_tokens(_tokens())
    auth.logout()
    assert not token_file.exists()


def test_decode_whoami() -> None:
    token = jwt.encode(
        {
            "preferred_username": "demo-user",
            "iss": "https://iam.example.com/realms/eoepca",
            "exp": int(time.time()) + 3600,
        },
        "secret",
        algorithm="HS256",
    )
    identity = auth.decode_whoami(token)
    assert identity["preferred_username"] == "demo-user"
    assert "expires_in" not in identity


def test_decode_whoami_falls_back_to_sub() -> None:
    token = jwt.encode(
        {
            "sub": "user-123",
            "iss": "https://iam.example.com/realms/eoepca",
            "exp": int(time.time()) + 3600,
        },
        "secret",
        algorithm="HS256",
    )
    assert auth.decode_whoami(token)["preferred_username"] == "user-123"


def test_decode_whoami_userinfo(respx_mock) -> None:
    iss = "https://iam.example.com/realms/eoepca"
    token = jwt.encode(
        {"iss": iss, "exp": int(time.time()) + 3600},
        "secret",
        algorithm="HS256",
    )
    import httpx

    respx_mock.get(f"{iss}/protocol/openid-connect/userinfo").mock(
        return_value=httpx.Response(200, json={"preferred_username": "demo-user"})
    )
    assert auth.decode_whoami(token)["preferred_username"] == "demo-user"


@patch("eoepca_client.auth.get_bearer")
def test_login_skips_when_logged_in(mock_bearer: MagicMock) -> None:
    mock_bearer.return_value = "existing"
    assert auth.login(resolve_platform("develop")) is None


@patch("eoepca_client.auth._keycloak")
def test_login_password(mock_kc: MagicMock, token_file: Path) -> None:
    mock_kc.return_value.token.return_value = {
        "access_token": "new-access",
        "expires_in": 3600,
    }
    profile = resolve_platform("develop")
    tokens = auth.login_password(profile, "user", "pass")
    assert tokens.access_token == "new-access"


@patch("eoepca_client.auth._keycloak")
def test_login_device(mock_kc: MagicMock, token_file: Path) -> None:
    mock_kc.return_value.device.return_value = {"device_code": "abc", "interval": 1}
    mock_kc.return_value.token.return_value = {
        "access_token": "device-access",
        "expires_in": 3600,
    }
    tokens = auth.login_device(
        resolve_platform("develop"), device_callback=lambda _: None
    )
    assert tokens.access_token == "device-access"


@patch("eoepca_client.auth._keycloak")
def test_login_password_auth_error(mock_kc: MagicMock) -> None:
    mock_kc.return_value.token.side_effect = KeycloakPostError(
        response_code=401,
        response_body=b'{"error":"invalid_grant"}',
    )
    with pytest.raises(AuthError):
        auth.login_password(resolve_platform("develop"), "u", "p")


@patch("eoepca_client.auth._keycloak")
def test_login_device_unauthorized_client(mock_kc: MagicMock) -> None:
    mock_kc.return_value.device.side_effect = KeycloakPostError(
        response_code=401,
        response_body=b'{"error":"unauthorized_client"}',
    )
    with pytest.raises(AuthError, match="EOEPCA_CLIENT_SECRET"):
        auth.login_device(resolve_platform("develop"), device_callback=lambda _: None)


@patch("eoepca_client.auth._keycloak")
@patch.dict(
    "os.environ",
    # Concatenate so scanners do not treat this test double as a real secret.
    {"EOEPCA_USERNAME": "env-user", "EOEPCA_PASSWORD": "env" + "-pass"},
    clear=False,
)
def test_login_env_credentials(mock_kc: MagicMock, token_file: Path) -> None:
    mock_kc.return_value.token.return_value = {
        "access_token": "live-token",
        "expires_in": 3600,
    }
    result = auth.login(resolve_platform("develop"))
    assert result is not None
    assert result.access_token == "live-token"


@patch("eoepca_client.auth._keycloak")
def test_login_prompt(mock_kc: MagicMock, token_file: Path) -> None:
    mock_kc.return_value.token.return_value = {
        "access_token": "prompt-token",
        "expires_in": 3600,
    }
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("EOEPCA_USERNAME", "EOEPCA_PASSWORD", "EOEPCA_CLIENT_SECRET")
    }
    with patch.dict("os.environ", env, clear=True):
        result = auth.login(resolve_platform("develop"), prompt=lambda: ("u", "p"))
    assert result is not None
    assert result.access_token == "prompt-token"


def test_login_requires_credentials() -> None:
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("EOEPCA_USERNAME", "EOEPCA_PASSWORD", "EOEPCA_CLIENT_SECRET")
    }
    with (
        patch.dict("os.environ", env, clear=True),
        patch("eoepca_client.auth.get_bearer", return_value=None),
        pytest.raises(AuthError, match="Username and password"),
    ):
        auth.login(resolve_platform("develop"))


@patch("eoepca_client.auth._keycloak")
def test_login_device_poll(mock_kc: MagicMock, token_file: Path) -> None:
    mock_kc.return_value.token.side_effect = [
        KeycloakPostError(response_body=b'{"error":"authorization_pending"}'),
        {"access_token": "tok", "expires_in": 3600},
    ]
    tokens = auth.login_device(
        resolve_platform("develop"), device_callback=lambda _: None
    )
    assert tokens.access_token == "tok"


@patch("eoepca_client.auth._keycloak")
def test_login_passes_client_overrides(mock_kc: MagicMock, token_file: Path) -> None:
    mock_kc.return_value.token.return_value = {
        "access_token": "tok",
        "expires_in": 3600,
    }
    auth.login(
        resolve_platform("develop"),
        username="u",
        password="p",
        client_id="custom",
        client_secret="secret",
    )
    profile = mock_kc.call_args.args[0]
    assert profile.client_id == "custom"
    assert profile.client_secret == "secret"
