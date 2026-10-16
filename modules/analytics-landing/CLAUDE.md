# analytics-landing

> Fire-and-forget events written as newline JSON to object storage for Databricks to pick up. Optional; nothing depends on it.

Layer: **capability** · Status: **planned** · Drift: **platform-owned** · Hosting: aws · Platforms: api

This file is the agent-facing contract. Read it before touching anything in this folder, and keep it true when you do.

## Provides
- `analytics.emit@1` — fire an analytics event that lands in object storage for Databricks

## Requires (hard)
- `infra.object-store@1` — a private object bucket with per-tenant key prefixes

## Optional (used when present, never assumed)
- `tenancy.scope@1` — the scope key every tenant-owned row carries and every query filters on

## Config (set in `platform.yaml` as `analytics-landing.<key>`)
- `landing_prefix` (string, default `"landing/"`) — Bucket prefix Databricks Auto Loader reads from

## Wiring
- Events carry app, environment, scope id (when tenancy is selected) and a schema version; Databricks owns everything after the landing zone.

## Invariants (do not break; add a contract test if you touch one)
- Emit never blocks a request; failures are logged, not raised.
- No PII beyond ids; joins back to people happen in the lakehouse under its own controls.

## How to extend
- A direct Databricks ingest (not via object storage) is a new provider behind the same interface.

## Extraction notes
Optional; extract from AveHealth when its landing zone is in place.

## Rules that apply to every module
1. Removable: deleting this module from a manifest leaves a buildable app; dependents fail loudly at `platform validate`, never silently at runtime.
2. Owns its data: only this module writes the tables in `migrations/`; others go through the interfaces above.
3. Interfaces, not names: never import another module by path; depend on an interface and let the manifest pick the provider.
4. Layering is one-way: `requires` may only point at this layer or below; `optional` may point up.
5. Two-app rule: this module is `stable` only once two apps use it unchanged. Until then it is `planned` or `incubating`.
