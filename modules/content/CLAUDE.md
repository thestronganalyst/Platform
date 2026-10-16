# content

> Authored pages and media with role-scoped visibility: instruction, how-tos, fundraising pages.

Layer: **capability** · Status: **planned** · Drift: **forked** · Hosting: aws, free · Platforms: web, mobile

This file is the agent-facing contract. Read it before touching anything in this folder, and keep it true when you do.

## Provides
- `content.page@1` — an authored page with role-scoped visibility
- `content.media@1` — media attached to pages, stored through storage.object

## Requires (hard)
- `storage.object@1` — upload, signed download URLs, and lifecycle per tenant
- `tenancy.scope@1` — the scope key every tenant-owned row carries and every query filters on
- `infra.db.postgres@1` — a Postgres database plus a connection secret; migrations run against it

## Optional (used when present, never assumed)
- `identity.roles@1` — role assignment per user and role checks

## Config (set in `platform.yaml` as `content.<key>`)
- `editor` (string, default `"markdown"`, one of ['markdown', 'rich']) — Authoring format

## Wiring
- Pages belong to a scope; visibility is by role when `identity.roles@1` is selected, public otherwise.

## Invariants (do not break; add a contract test if you touch one)
- Media goes through `storage.object@1`; no inline binary in page records.

## How to extend
- Versioning and drafts are features here; comments are a separate module.

## Extraction notes
Incubates in softball. Forked because every app restyles its content pages.

## Rules that apply to every module
1. Removable: deleting this module from a manifest leaves a buildable app; dependents fail loudly at `platform validate`, never silently at runtime.
2. Owns its data: only this module writes the tables in `migrations/`; others go through the interfaces above.
3. Interfaces, not names: never import another module by path; depend on an interface and let the manifest pick the provider.
4. Layering is one-way: `requires` may only point at this layer or below; `optional` may point up.
5. Two-app rule: this module is `stable` only once two apps use it unchanged. Until then it is `planned` or `incubating`.
