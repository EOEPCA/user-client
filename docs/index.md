# Introduction

The **User Client** building block defines how tools, CLIs, and libraries
discover and interact with an EOEPCA+ deployment. Instead of baking in hostnames
or URL patterns, clients start from a single well-known entry point and follow
typed links to each service.

## About User Client

An EOEPCA+ deployment exposes many APIs (workspace, catalogue, processing,
OpenEO, object storage, identity, …) across different subdomains and auth modes.
User clients need a stable contract for:

- finding the correct base URL for each capability,
- knowing which authentication flow applies,
- adapting to deployment-specific naming (e.g. workspace prefixes).

That contract is the **[API Catalog](api/api-catalog.md)** at
`/.well-known/api-catalog` — a Linkset document keyed by standard and EOEPCA+
relation types.

## Capabilities

- **Service discovery** — resolve endpoints by `rel`; [schema](api/schema/v1.json) defines extension properties.
- **Auth hints** — `eoepca:auth` on each link; if missing, try unauthenticated first — a 401 from the service means auth is required.
- **Deployment metadata** — schema version, environment, and revision via
  `eoepca:deployment` for cache invalidation and support diagnostics.

## Documentation map

| Section | Contents |
|---|---|
| [Getting Started](getting-started/quick-start.md) | Install a client and point it at a deployment. |
| [Design](design/overview.md) | How discovery fits into client architecture. |
| [Usage](usage/tutorials.md) | Tutorials and how-tos for common tasks. |
| [Administration](admin/configuration.md) | Configuration for operators serving the catalog. |
| [API](api/api-catalog.md) | API Catalog specification and schema. |
