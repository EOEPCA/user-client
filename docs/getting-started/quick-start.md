# Quick Start

Point any user client at an EOEPCA+ deployment by its apex domain. The client
fetches the [API Catalog](../api/api-catalog.md) and resolves services from there.

## Discover a deployment

```bash
DEPLOY=https://develop.eoepca.org

curl -sS "$DEPLOY/.well-known/api-catalog" \
  | jq '.linkset[0] | {
      schema: ."eoepca:schema_version",
      deployment: ."eoepca:deployment".name,
      workspace: ."https://eoepca.org/rel/workspace-api"[0].href,
      issuer: ."http://openid.net/specs/connect/1.0/issuer"[0].href
    }'
```

## What to read next

- [API Catalog](../api/api-catalog.md) — schema and serving requirements.
- [Architecture](../design/overview.md) — how discovery fits into client design.
