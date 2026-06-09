"""EOEPCA client library and CLI."""

from importlib.metadata import version as _version

from .client import Client

__version__ = _version("eoepca-client")

__all__ = ["Client", "__version__"]
