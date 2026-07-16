# eoepca-client

Client library and CLI for EOEPCA.

## Requirements

- Python 3.12 or higher

## Quickstart

Install with [uv](https://docs.astral.sh/uv/):

```bash
uv tool install eoepca-client
```

Or add to a project and use `uv run`:

```bash
uv add eoepca-client
uv run eoepca login
```

Log in with your platform username and password:

```bash
uv run eoepca login --username USER --password PASS
```

Or interactively (prompts on a TTY):

```bash
uv run eoepca login
```

Or via environment variables:

```bash
export EOEPCA_USERNAME=... EOEPCA_PASSWORD=...
uv run eoepca login
```

Device flow is used only when `EOEPCA_CLIENT_SECRET` is set (confidential clients).

Search STAC items:

```bash
eoepca stac search --collection <collection-id> --bbox -10,40,5,55 --limit 5
```

```bash
eoepca stac item add <collection-id> ./item.geojson
eoepca stac item rm <collection-id> <item-id>
```

Check who you are logged in as:

```bash
eoepca whoami
```

Use `--output json` on any command for machine-readable output.

## Platform discovery

`-p` / `--platform` accepts:

- a **named platform** from builtins or `~/.config/eoepca/config.toml` (e.g. `develop`)
- a **local API catalog** file (RFC 9727 linkset JSON)
- a **catalog URL** (`https://…/.well-known/api-catalog`, or a base URL that is completed with that path)
- a **domain** (fetches `https://<domain>/.well-known/api-catalog`)

```bash
eoepca stac collections -p ./api-catalog.json
eoepca login -p https://develop.eoepca.org/.well-known/api-catalog
eoepca whoami -p staging.example.org
```

The catalog supplies the OIDC issuer (`eoepca:default_client_id`, realm) and the STAC endpoint (preferring a `data` target with `eoepca:auth: oidc-write`). See [PR #16](https://github.com/EOEPCA/user-client/pull/16).

## Library usage

```python
from eoepca_client import Client

c = Client(platform="develop")
c.login()

# Read — returns a pre-configured pystac_client.Client
stac = c.eoapi.stac()
for col in stac.get_collections():
    print(col.id, col.title)

search = stac.search(collections=["my-coll"], bbox=[-10, 40, 5, 55], limit=5)
for item in search.items():
    print(item.id)

# Write — STAC Transactions helper
tx = c.eoapi.stac_transactions
created = tx.add_item("my-coll", "./item.geojson")
tx.delete_item("my-coll", created.id)
```

## Installation (development)

From the repository:

```bash
cd eoepca-client
uv sync --extra dev --extra test
```

Verify the CLI:

```bash
uv run eoepca --help
```

## Testing

```bash
cd eoepca-client
uv sync --extra test
uv run pytest
```

Optional live test against develop (requires credentials and a writeable collection):

```bash
EOEPCA_E2E=1 \
EOEPCA_USERNAME=... \
EOEPCA_PASSWORD=... \
EOEPCA_COLLECTION=ws-... \
uv run pytest tests/test_e2e.py -v
```

## Development

Set up pre-commit hooks (config lives at the repository root):

```bash
cd ..  # repository root
uv run --project eoepca-client pre-commit install
```

## License

This project is licensed under the Apache License 2.0 — see the [LICENSE](../LICENSE) file at the repository root.
