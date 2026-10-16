# consent-sharing

> Who may see what about whom. A patient decides what a provider sees; a parent decides what a coach and a league see about a kid. Every check is audited.

Layer: **capability** · Status: **planned** · Drift: **platform-owned** · Hosting: aws · Platforms: api, web

This file is the agent-facing contract. Read it before touching anything in this folder, and keep it true when you do.

## Provides
- `consent.grant@1` — a scoped grant: who may see which categories about whom, until when
- `consent.check@1` — a yes/no check callers must make before returning another person's data
- `consent.revoke@1` — revocation that takes effect immediately and is audited

## Requires (hard)
- `profiles.person@1` — a person record that is independent of any login
- `profiles.guardian@1` — guardian ownership of managed profiles (kids, dependents, charges)
- `tenancy.scope@1` — the scope key every tenant-owned row carries and every query filters on
- `obs.audit@1` — an append-only audit event stream other modules write to
- `infra.db.postgres@1` — a Postgres database plus a connection secret; migrations run against it

## Optional (used when present, never assumed)
- `notify.send@1` — send one message over email, push or SMS with a template and variables

## Config (set in `platform.yaml` as `consent-sharing.<key>`)
- `categories` (array, default `["basic"]`) — Data categories a grant can cover, e.g. [basic, health, performance]
- `default_posture` (string, default `"deny"`, one of ['deny', 'allow-within-org']) — What is visible with no grant

## Wiring
- Any endpoint that returns data about a person other than the acting person calls `consent.check@1` first; the api-shell provides a decorator so this is one line.
- Grants are made by the person or their guardian (`profiles.guardian@1`), scoped to a category and a `tenancy.scope@1`, and expire or are revoked.

## Invariants (do not break; add a contract test if you touch one)
- Default is deny unless configured otherwise; a missing grant is never treated as consent.
- Every check and every grant change writes to `obs.audit@1`.
- Revocation is immediate; no caches outlive a revoke.

## How to extend
- New categories are config; a new kind of grantee (a tool, an API client) is an interface change and an ADR.

## Extraction notes
Extraction step 3. AveHealth has the sharing model; generalize the grantee from 'provider' to 'any membership in a scope'.

## Rules that apply to every module
1. Removable: deleting this module from a manifest leaves a buildable app; dependents fail loudly at `platform validate`, never silently at runtime.
2. Owns its data: only this module writes the tables in `migrations/`; others go through the interfaces above.
3. Interfaces, not names: never import another module by path; depend on an interface and let the manifest pick the provider.
4. Layering is one-way: `requires` may only point at this layer or below; `optional` may point up.
5. Two-app rule: this module is `stable` only once two apps use it unchanged. Until then it is `planned` or `incubating`.
