# Architecture

User clients are thin orchestration layers over EOEPCA+ platform services. The
platform advertises those services through a single discovery document; clients
never embed deployment-specific URLs.

## Discovery layer

```
  User client                    EOEPCA+ deployment
  ───────────                    ──────────────────

  1. GET /.well-known/api-catalog
     ─────────────────────────────►  Linkset JSON
                                    (rel → href + metadata)

  2. Pick rel (workspace-api, data, openeo, …)
     Read eoepca:auth, eoepca:naming, conformsTo

  3. Authenticate via OIDC issuer link
     (eoepca:default_client_id from catalog)

  4. Call target service API
     ─────────────────────────────►  Workspace, STAC, OpenEO, …
```

The catalog is specified in [API Catalog](../api/api-catalog.md) ([schema/v1.json](../api/schema/v1.json)).

## Design principles

- **Rel-based lookup** — clients select services by registered `rel` URIs, not
  by position or informal key names.
- **Server decides auth** — `eoepca:auth` in the catalog is a hint; a 401 from the service means you need credentials.
- **Additive evolution** — new rels and properties are MINOR changes; removing
  or renaming rels is MAJOR and follows the catalog versioning rules.
- **Cache-friendly** — deployments MUST emit a stable ETag tied to
  `eoepca:deployment.git_revision` so clients can revalidate cheaply.

## Interfaces

| Interface | Role |
|---|---|
| `/.well-known/api-catalog` | Platform → client; full service directory. |
| OIDC issuer (`openid issuer` rel) | Client ↔ Keycloak; token acquisition. |
| Per-service APIs | Client ↔ individual building blocks; discovered via catalog. |
