"""Tests for STAC transactions."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import respx

from eoepca_client.config import resolve_platform
from eoepca_client.stac_tx import (
    AuthError,
    EoepcaError,
    ForbiddenError,
    NotFoundError,
    ServerError,
    StacTx,
)

PROFILE = resolve_platform("develop")
ITEM_BODY = (
    b'{"type":"Feature","stac_version":"1.0.0","id":"new-item",'
    b'"collection":"ws-test","geometry":null,"properties":{},'
    b'"links":[],"assets":{}}'
)
ITEM_JSON = {
    "type": "Feature",
    "stac_version": "1.0.0",
    "id": "new-item",
    "collection": "ws-test",
    "geometry": None,
    "properties": {},
    "links": [],
    "assets": {},
}


@respx.mock
def test_add_item(tmp_path: Path) -> None:
    item_file = tmp_path / "item.geojson"
    item_file.write_bytes(ITEM_BODY)
    url = f"{PROFILE.stac_url}/collections/ws-test/items"
    respx.post(url).mock(return_value=httpx.Response(201, json=ITEM_JSON))
    assert (
        StacTx(PROFILE, bearer="token").add_item("ws-test", str(item_file)).id
        == "new-item"
    )


@respx.mock
def test_add_item_from_url() -> None:
    body_url = "https://example.com/item.geojson"
    respx.get(body_url).mock(return_value=httpx.Response(200, content=ITEM_BODY))
    respx.post(f"{PROFILE.stac_url}/collections/ws-test/items").mock(
        return_value=httpx.Response(201, json=ITEM_JSON)
    )
    assert (
        StacTx(PROFILE, bearer="token").add_item("ws-test", body_url).id == "new-item"
    )


@respx.mock
def test_delete_item() -> None:
    url = f"{PROFILE.stac_url}/collections/ws-test/items/new-item"
    respx.delete(url).mock(return_value=httpx.Response(204))
    StacTx(PROFILE, bearer="token").delete_item("ws-test", "new-item")


@pytest.mark.parametrize(
    ("status", "exc_type"),
    [
        (401, AuthError),
        (403, ForbiddenError),
        (404, NotFoundError),
        (409, EoepcaError),
        (500, ServerError),
    ],
)
@respx.mock
def test_add_item_errors(
    tmp_path: Path, status: int, exc_type: type[Exception]
) -> None:
    item_file = tmp_path / "item.geojson"
    item_file.write_bytes(ITEM_BODY)
    url = f"{PROFILE.stac_url}/collections/ws-test/items"
    respx.post(url).mock(return_value=httpx.Response(status, text="fail"))
    with pytest.raises(exc_type):
        StacTx(PROFILE, bearer="token").add_item("ws-test", str(item_file))
