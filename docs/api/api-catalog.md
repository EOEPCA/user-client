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

!!! note
    The develop deployment does not serve `/.well-known/api-catalog` yet;
    [schema/example.json](schema/example.json) is the reference document until it does.

## Selecting among multiple targets

A `rel` may list several targets (e.g. `data` carries both an open resource
catalogue and a transactional eoAPI STAC). Clients that need write access
SHOULD prefer the target whose `conformsTo` includes a STAC API core
conformance class and whose `eoepca:auth` is `oidc-write`, falling back to the
first STAC-conformant target otherwise.

## Known service behaviours

- eoAPI on develop only accepts tokens issued for the `eoapi` OIDC client
  (`eoepca:default_client_id` above); tokens from other clients are rejected
  with 401.
- eoAPI answers item `DELETE` with `200` and a JSON body rather than `204`.

## Versioning

`eoepca:schema_version` is SemVer. Changes within a MAJOR are additive only. On a
MAJOR bump the previous schema stays available at its versioned URL
(e.g. `/schemas/discovery/v1.json`) and the new one is published alongside it;
deployments state the version they implement in `eoepca:schema_version`.
