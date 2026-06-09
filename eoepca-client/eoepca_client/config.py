"""Platform configuration."""

from __future__ import annotations

import os
import tomllib
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

DEFAULT_SCOPE = "openid profile email"

_BUILTIN: dict[str, dict[str, str]] = {
    "develop": {
        "keycloak_url": "https://iam-auth.develop.eoepca.org",
        "realm": "eoepca",
        "client_id": "eoapi",
        "stac_url": "https://eoapi.develop.eoepca.org/stac",
    },
}
_ALIASES = {"develop.eoepca.org": "develop"}


class PlatformConfig(BaseModel):
    """EOEPCA platform endpoints and OAuth client settings."""

    model_config = ConfigDict(frozen=True)

    name: str
    keycloak_url: str = Field(
        description="Keycloak server base URL (no /realms/… path)."
    )
    realm: str
    client_id: str
    stac_url: str
    client_secret: str | None = None
    scope: str = DEFAULT_SCOPE

    @property
    def iam_issuer(self) -> str:
        return f"{self.keycloak_url.rstrip('/')}/realms/{self.realm}"


def config_path() -> Path:
    override = os.environ.get("EOEPCA_CONFIG")
    if override:
        return Path(override)
    return Path.home() / ".config" / "eoepca" / "config.toml"


@lru_cache
def _platform_registry() -> dict[str, PlatformConfig]:
    platforms: dict[str, PlatformConfig] = {
        name: PlatformConfig(name=name, **spec) for name, spec in _BUILTIN.items()
    }
    path = config_path()
    if path.is_file():
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        for name, spec in data.get("platforms", {}).items():
            platforms[name] = PlatformConfig(name=name, **spec)
    return platforms


def resolve_platform(name: str) -> PlatformConfig:
    """Resolve a named platform, api-catalog file, URL, or domain."""
    key = _ALIASES.get(name, name)
    registry = _platform_registry()
    if key in registry:
        return registry[key]

    path = Path(name)
    if path.is_file() or name.startswith(("http://", "https://")) or "." in name:
        from eoepca_client.catalog import platform_from_catalog

        return platform_from_catalog(name)

    known = ", ".join(sorted({*registry, *_ALIASES}))
    raise ValueError(
        f"Unknown platform {name!r}; known: {known}. "
        "Or pass a catalog file, URL, or domain."
    )


def resolve_auth(
    profile: PlatformConfig,
    *,
    client_id: str | None = None,
    client_secret: str | None = None,
) -> PlatformConfig:
    """Apply client ID/secret overrides (explicit args, then env)."""
    resolved_id = (
        client_id
        if client_id is not None
        else os.environ.get("EOEPCA_CLIENT_ID", profile.client_id)
    )
    resolved_secret = (
        client_secret
        if client_secret is not None
        else os.environ.get("EOEPCA_CLIENT_SECRET", profile.client_secret)
    )
    if resolved_id == profile.client_id and resolved_secret == profile.client_secret:
        return profile
    return profile.model_copy(
        update={"client_id": resolved_id, "client_secret": resolved_secret}
    )
