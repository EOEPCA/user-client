"""Optional end-to-end tests against develop.eoepca.org."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

import pytest

from eoepca_client.client import Client

pytestmark = pytest.mark.skipif(
    os.getenv("EOEPCA_E2E") != "1",
    reason="Set EOEPCA_E2E=1 to run live develop tests",
)


@pytest.fixture
def live_client() -> Client:
    username = os.environ["EOEPCA_USERNAME"]
    password = os.environ["EOEPCA_PASSWORD"]
    client = Client("develop")
    client.login(username=username, password=password)
    return client


def test_add_search_rm(live_client: Client, tmp_path: Path) -> None:
    collection = os.environ["EOEPCA_COLLECTION"]
    item_id = f"e2e-{uuid.uuid4()}"
    item = {
        "type": "Feature",
        "stac_version": "1.0.0",
        "id": item_id,
        "collection": collection,
        "geometry": {
            "type": "Point",
            "coordinates": [0.0, 0.0],
        },
        "properties": {"datetime": "2024-01-01T00:00:00Z"},
        "links": [],
        "assets": {},
    }
    item_path = tmp_path / f"{item_id}.geojson"
    item_path.write_text(json.dumps(item), encoding="utf-8")

    created = live_client.eoapi.stac_transactions.add_item(collection, str(item_path))
    assert created.id == item_id

    stac = live_client.eoapi.stac()
    results = stac.search(collections=[collection], ids=[item_id], limit=1)
    found = list(results.items())
    assert any(i.id == item_id for i in found)

    live_client.eoapi.stac_transactions.delete_item(collection, item_id)
