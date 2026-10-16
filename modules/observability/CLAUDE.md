# observability

> Structured logs, error capture and an append-only audit stream. consent-sharing and anything health- or money-adjacent writes to the audit stream.

Layer: **foundation** · Status: **planned** · Drift: **platform-owned** · Hosting: aws · Platforms: api, web

This file is the agent-facing contract. Read it before touching anything in this folder, and keep it true when you do.

## Provides
- `obs.logs@1` — structured logs with request and tenant correlation
- `obs.errors@1` — error capture with release tagging
- `obs.audit@1` — an append-only audit event stream other modules write to

## Requires (hard)
- `infra.container@1` — a place to run one container image with env and secret injection (App Runner or Fargate, per ADR)
- `infra.db.postgres@1` — a Postgres database plus a connection secret; migrations run against it

## Optional (used when present, never assumed)
- none

## Config (set in `platform.yaml` as `observability.<key>`)
- `audit_retention_days` (integer, default `365`) — How long audit events are kept

## Wiring
- Logs and errors go to the container runtime's log group; the audit stream is a table this module owns, written only through `obs.audit@1`.
- `api-shell` attaches request and tenant ids to every log line when this module is selected.

## Invariants (do not break; add a contract test if you touch one)
- Audit rows are never updated or deleted by application code; retention is a scheduled job, not a DELETE in a handler.

## How to extend
- A new audit event type is a new enum value plus a line in ADR.md saying who reads it and why.

## Extraction notes
Extraction step 4. AveHealth already has the audit need; make the stream a module so softball's payments and consent can use it.

## Rules that apply to every module
1. Removable: deleting this module from a manifest leaves a buildable app; dependents fail loudly at `platform validate`, never silently at runtime.
2. Owns its data: only this module writes the tables in `migrations/`; others go through the interfaces above.
3. Interfaces, not names: never import another module by path; depend on an interface and let the manifest pick the provider.
4. Layering is one-way: `requires` may only point at this layer or below; `optional` may point up.
5. Two-app rule: this module is `stable` only once two apps use it unchanged. Until then it is `planned` or `incubating`.
