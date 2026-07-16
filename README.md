# EOEPCA User Client

How tools, CLIs, and libraries discover and talk to an [EOEPCA+](https://eoepca.org/) deployment.

Clients start from a single entry point, `/.well-known/api-catalog`, and follow typed links to workspace, catalogue, processing, identity, and other services.

## What’s in this repo

| Path | Purpose |
|---|---|
| [`docs/`](docs/) | Building-block docs: design, API Catalog spec, getting started |
| [`eoepca-client/`](eoepca-client/) | Python library and `eoepca` CLI |

Full documentation: [Read the Docs](https://eoepca.readthedocs.io/projects/user-client/)

## Quick start

Fetch the catalog for a deployment:

```bash
curl -sS https://develop.eoepca.org/.well-known/api-catalog | jq .
```

Or use the Python client:

```bash
uv tool install eoepca-client
eoepca login -p develop
eoepca whoami
```

See [`eoepca-client/README.md`](eoepca-client/README.md) for library usage, STAC commands, and development setup.
