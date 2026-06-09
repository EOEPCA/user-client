"""EOEPCA client library and CLI."""

from importlib.metadata import version as _version

from .logging import get_logger, logger, setup_logging

__version__ = _version("eoepca-client")


__all__ = ["__version__", "version", "get_logger", "setup_logging", "logger"]


def version() -> None:
    """Print the current version."""
    print(f"eoepca-client version: {__version__}")


if __name__ == "__main__":
    version()
