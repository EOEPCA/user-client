# eoepca-client

Client library and CLI for EOEPCA.

## Requirements

- Python 3.12 or higher

## Installation

Install using `uv`:

```bash
uv add eoepca-client
```

## Testing

From the repository root, install test dependencies and run tests:

```bash
cd eoepca-client
uv sync --extra test
uv run pytest
```

## Development

From the `eoepca-client` directory:

```bash
uv sync --extra dev --extra test
```

Set up pre-commit hooks (config lives at the repository root):

```bash
cd ..  # repository root
uv run --project eoepca-client pre-commit install
```

Run pre-commit manually from the repository root:

```bash
uv run --project eoepca-client pre-commit run --all-files
```

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](../LICENSE) file at the repository root.
