"""OAuth login and token cache."""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import httpx
import jwt
from keycloak import KeycloakOpenID
from keycloak.exceptions import KeycloakPostError

from eoepca_client.config import DEFAULT_SCOPE, PlatformConfig, resolve_auth
from eoepca_client.models import TokenSet
from eoepca_client.stac_tx import AuthError, EoepcaError

_TOKEN_SKEW = 60
_DEVICE_GRANT = "urn:ietf:params:oauth:grant-type:device_code"


def token_path() -> Path:
    return Path.home() / ".config" / "eoepca" / "tokens.json"


def _load_all() -> dict[str, dict[str, Any]]:
    path = token_path()
    if not path.is_file():
        return {}
    return cast(dict[str, dict[str, Any]], json.loads(path.read_text(encoding="utf-8")))


def load_tokens(platform: str) -> TokenSet | None:
    data = _load_all().get(platform)
    return TokenSet.model_validate(data) if data else None


def save_tokens(tokens: TokenSet) -> None:
    path = token_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    store = _load_all()
    store[tokens.platform] = tokens.model_dump()
    path.write_text(json.dumps(store, indent=2), encoding="utf-8")
    os.chmod(path, 0o600)


def logout(platform: str | None = None) -> None:
    path = token_path()
    if not path.is_file():
        return
    if platform is None:
        path.unlink(missing_ok=True)
        return
    store = _load_all()
    store.pop(platform, None)
    if store:
        path.write_text(json.dumps(store, indent=2), encoding="utf-8")
        os.chmod(path, 0o600)
    else:
        path.unlink(missing_ok=True)


def _keycloak(profile: PlatformConfig) -> KeycloakOpenID:
    return KeycloakOpenID(
        server_url=f"{profile.keycloak_url.rstrip('/')}/",
        client_id=profile.client_id,
        realm_name=profile.realm,
        client_secret_key=profile.client_secret,
    )


def _keycloak_error(exc: KeycloakPostError) -> EoepcaError:
    body = (exc.response_body or b"").decode("utf-8", errors="replace")
    try:
        error = json.loads(body).get("error", "")
    except json.JSONDecodeError:
        error = ""
    if error == "unauthorized_client":
        return AuthError(
            "Keycloak rejected the client credentials. "
            "Check EOEPCA_CLIENT_ID / EOEPCA_CLIENT_SECRET or use password login."
        )
    if exc.response_code == 401:
        return AuthError(body or str(exc))
    return EoepcaError(body or str(exc))


def _to_token_set(response: dict[str, Any], platform: str) -> TokenSet:
    return TokenSet(
        access_token=str(response["access_token"]),
        expires_at=int(time.time()) + int(response.get("expires_in", 3600)),
        platform=platform,
    )


def login_device(
    profile: PlatformConfig,
    *,
    device_callback: Callable[[dict[str, Any]], None] | None = None,
) -> TokenSet:
    kc = _keycloak(profile)
    try:
        device = kc.device(scope=DEFAULT_SCOPE)
    except KeycloakPostError as exc:
        raise _keycloak_error(exc) from exc

    def _print_device(response: dict[str, Any]) -> None:
        uri = response.get(
            "verification_uri_complete", response.get("verification_uri", "")
        )
        print(f"Visit: {uri}\nCode:  {response.get('user_code', '')}")

    (device_callback or _print_device)(device)
    interval = int(device.get("interval", 5))
    while True:
        try:
            response = kc.token(
                grant_type=_DEVICE_GRANT,
                device_code=str(device["device_code"]),
                scope=DEFAULT_SCOPE,
            )
        except KeycloakPostError as exc:
            body = exc.response_body or b""
            if b"authorization_pending" in body or b"slow_down" in body:
                time.sleep(interval * (2 if b"slow_down" in body else 1))
                continue
            raise _keycloak_error(exc) from exc
        tokens = _to_token_set(response, profile.name)
        save_tokens(tokens)
        return tokens


def login_password(profile: PlatformConfig, username: str, password: str) -> TokenSet:
    try:
        response = _keycloak(profile).token(username, password, scope=DEFAULT_SCOPE)
    except KeycloakPostError as exc:
        raise _keycloak_error(exc) from exc
    tokens = _to_token_set(response, profile.name)
    save_tokens(tokens)
    return tokens


def login(
    profile: PlatformConfig,
    *,
    username: str | None = None,
    password: str | None = None,
    client_id: str | None = None,
    client_secret: str | None = None,
    prompt: Callable[[], tuple[str, str]] | None = None,
) -> TokenSet | None:
    """Log in via password grant, or device flow when a client secret is configured."""
    profile = resolve_auth(profile, client_id=client_id, client_secret=client_secret)
    if username and password:
        return login_password(profile, username, password)
    if get_bearer(profile):
        return None
    env_user = os.environ.get("EOEPCA_USERNAME")
    env_pass = os.environ.get("EOEPCA_PASSWORD")
    if env_user and env_pass:
        return login_password(profile, env_user, env_pass)
    if profile.client_secret:
        return login_device(profile)
    if prompt is not None:
        user, pwd = prompt()
        return login_password(profile, user, pwd)
    raise AuthError(
        "Username and password required "
        "(--username/--password or EOEPCA_USERNAME/EOEPCA_PASSWORD)."
    )


def get_bearer(profile: PlatformConfig) -> str | None:
    tokens = load_tokens(profile.name)
    if tokens is None or tokens.expires_at <= int(time.time()) + _TOKEN_SKEW:
        return None
    return tokens.access_token


def decode_whoami(access_token: str) -> dict[str, Any]:
    claims = jwt.decode(access_token, options={"verify_signature": False})
    username = claims.get("preferred_username") or claims.get("sub")
    if not username and (iss := claims.get("iss")):
        try:
            response = httpx.get(
                f"{iss}/protocol/openid-connect/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10.0,
            )
            if response.is_success:
                info = response.json()
                username = info.get("preferred_username") or info.get("sub")
        except httpx.HTTPError:
            pass
    return {
        "preferred_username": str(username or "unknown"),
        "iss": str(claims.get("iss", "")),
        "exp": int(claims["exp"]),
    }
