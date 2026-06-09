"""Shared data models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class TokenSet(BaseModel):
    access_token: str
    expires_at: int
    platform: str


class StacItemRef(BaseModel):
    id: str
    collection: str | None = None
    datetime: str | None = None
    bbox: list[float] | None = None

    @classmethod
    def from_stac_dict(cls, data: dict[str, Any]) -> StacItemRef:
        props = data.get("properties") or {}
        bbox = data.get("bbox")
        return cls(
            id=str(data["id"]),
            collection=data.get("collection"),
            datetime=props.get("datetime") or props.get("start_datetime"),
            bbox=[float(v) for v in bbox] if bbox else None,
        )
