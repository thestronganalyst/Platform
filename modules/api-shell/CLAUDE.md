# api-shell

> The API process: routing, auth middleware, error envelope, health endpoint, DB connection, containerized for infra.container.

Layer: **foundation** · Status: **planned** · Drift: **platform-owned** · Hosting: aws · Platforms: api

This file is the agent-facing contract. Read it before touching anything in this folder, and keep it true when you do.

## Provides
- `api.router@1` — a mounted router that modules register endpoints on
- `api.auth-middleware@1` — request-scoped identity when identity.session is selected; anonymous otherwise
- `api.errors@1` — one error envelope for every endpoint

## Requires (hard)
- `infra.db.postgres@1` — a Postgres database plus a connection secret; migrations run against it
- `infra.container@1` — a place to run one container image with env and secret injection (App Runner or Fargate, per ADR)

## Optional (used when present, never assumed)
- `identity.session@1` — a verified session for a request or client
- `obs.logs@1` — structured logs with request and tenant correlation

## Config (set in `platform.yaml` as `api-shell.<key>`)
- `framework` (string, default `"keep"`, one of ['keep', 'fastapi', 'express']) — `keep` = whatever AveHealth runs today (pending ADR)

## Wiring
- Each selected module with an `app/api/` folder registers its routes through `api.router@1` at startup; the shell discovers them from the manifest, never from a hand-maintained list.
- `api.auth-middleware@1` attaches a verified principal when `identity.session@1` is selected and an anonymous principal when it is not. Routes declare the minimum they need.

## Invariants (do not break; add a contract test if you touch one)
- The shell owns no business tables; it may create nothing in `migrations/` except its own health check table if one is needed.
- Every response error passes through `api.errors@1`; raw framework errors never reach a client.

## How to extend
- New cross-cutting middleware is added here only if two or more modules need it; otherwise it belongs in the module.

## Extraction notes
Extraction step 4. Confirm the framework AveHealth uses first; the `framework` config exists so the decision is explicit, not accidental.

## Rules that apply to every module
1. Removable: deleting this module from a manifest leaves a buildable app; dependents fail loudly at `platform validate`, never silently at runtime.
2. Owns its data: only this module writes the tables in `migrations/`; others go through the interfaces above.
3. Interfaces, not names: never import another module by path; depend on an interface and let the manifest pick the provider.
4. Layering is one-way: `requires` may only point at this layer or below; `optional` may point up.
5. Two-app rule: this module is `stable` only once two apps use it unchanged. Until then it is `planned` or `incubating`.
