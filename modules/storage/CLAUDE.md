# storage

> Uploads and signed downloads, keyed by tenant scope, with lifecycle rules.

Layer: **capability** · Status: **planned** · Drift: **platform-owned** · Hosting: aws, free · Platforms: api, web

This file is the agent-facing contract. Read it before touching anything in this folder, and keep it true when you do.

## Provides
- `storage.object@1` — upload, signed download URLs, and lifecycle per tenant

## Requires (hard)
- `infra.object-store@1` — a private object bucket with per-tenant key prefixes
- `tenancy.scope@1` — the scope key every tenant-owned row carries and every query filters on

## Optional (used when present, never assumed)
- `infra.cdn@1` — a CDN distribution and bucket for static web assets

## Config (set in `platform.yaml` as `storage.<key>`)
- `max_upload_mb` (integer, default `25`) — Upload size limit
- `virus_scan` (boolean, default `false`) — Scan uploads before they are readable

## Wiring
- Uploads go straight from the client to the bucket through a presigned PUT; the API never proxies file bytes.
- Keys are `<scope_id>/<module>/<object_id>`; a module never builds a key by hand, it asks `storage.object@1`.
- Downloads are signed URLs with short expiry; nothing in the bucket is public.

## Invariants (do not break; add a contract test if you touch one)
- An object is readable only by callers who pass `tenancy.scope@1` for its prefix; consent checks are the caller's job, enforced where the object is referenced.

## How to extend
- Image resizing or document previews are a separate module that consumes this one, not a feature added here.

## Extraction notes
Extraction step 3.

## Rules that apply to every module
1. Removable: deleting this module from a manifest leaves a buildable app; dependents fail loudly at `platform validate`, never silently at runtime.
2. Owns its data: only this module writes the tables in `migrations/`; others go through the interfaces above.
3. Interfaces, not names: never import another module by path; depend on an interface and let the manifest pick the provider.
4. Layering is one-way: `requires` may only point at this layer or below; `optional` may point up.
5. Two-app rule: this module is `stable` only once two apps use it unchanged. Until then it is `planned` or `incubating`.
