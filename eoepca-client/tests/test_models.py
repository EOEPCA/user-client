"""Tests for models."""

from eoepca_client.models import StacItemRef


def test_stac_item_ref() -> None:
    ref = StacItemRef.from_stac_dict(
        {
            "id": "item-1",
            "collection": "coll-a",
            "properties": {"datetime": "2024-01-01T00:00:00Z"},
            "bbox": [-10.0, 40.0, 5.0, 55.0],
        }
    )
    assert ref.id == "item-1"
    assert ref.bbox == [-10.0, 40.0, 5.0, 55.0]
