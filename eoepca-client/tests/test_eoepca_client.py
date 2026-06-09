"""Tests for eoepca_client package exports."""

from eoepca_client import Client, __version__


def test_version_attribute() -> None:
    assert isinstance(__version__, str)
    assert __version__ != ""
    parts = __version__.split(".")
    assert len(parts) >= 3
    for part in parts[:3]:
        assert part.isdigit()


def test_client_import() -> None:
    client = Client("develop")
    assert client.platform == "develop"
