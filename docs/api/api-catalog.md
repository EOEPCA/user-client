# API Catalog

Every EOEPCA+ deployment exposes a machine-readable directory of its services at
`/.well-known/api-catalog`. User clients treat this as the only supported way to
discover endpoints, authentication, and deployment metadata, they MUST NOT
hard-code service URLs or assume a fixed hostname layout.

[RFC 9727](https://www.rfc-editor.org/rfc/rfc9727) well-known URI,
[RFC 9264](https://www.rfc-editor.org/rfc/rfc9264) Linkset JSON
(`application/linkset+json`). Services are link targets keyed by link relation
type (`rel`); relation URIs and extension properties are in
[schema/v1.json](schema/v1.json).

- **Schema:** [schema/v1.json](schema/v1.json)
- **Example:** [schema/example.json](schema/example.json), reference deployment to inspect or validate against

```bash
check-jsonschema --schemafile docs/api/schema/v1.json docs/api/schema/example.json
```

Deployments MUST serve a document that validates against the current schema.
Clients SHOULD fetch `service-desc` from the catalog for the live schema URL.
Look services up by `rel`. Absent `eoepca:auth`, means unauthenticated access 
is possible.

## Versioning

`eoepca:schema_version` is SemVer. Changes within a MAJOR are additive only. On a
MAJOR bump the previous schema stays at
