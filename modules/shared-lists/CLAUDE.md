# shared-lists

> Lists with items and claims: who brings what, sign-up sheets, volunteer slots.

Layer: **capability** · Status: **planned** · Drift: **platform-owned** · Hosting: aws, free · Platforms: api, web, mobile

This file is the agent-facing contract. Read it before touching anything in this folder, and keep it true when you do.

## Provides
- `lists.list@1` — a shared list owned by a scope
- `lists.item@1` — an item on a list, with quantity and notes
- `lists.claim@1` — a person claiming an item (sign-up, who-brings-what)

## Requires (hard)
- `tenancy.scope@1` — the scope key every tenant-owned row carries and every query filters on
- `profiles.person@1` — a person record that is independent of any login
- `infra.db.postgres@1` — a Postgres database plus a connection secret; migrations run against it

## Optional (used when present, never assumed)
- `notify.send@1` — send one message over email, push or SMS with a template and variables

## Config (set in `platform.yaml` as `shared-lists.<key>`)
- `allow_partial_claims` (boolean, default `true`) — An item with quantity 6 can be claimed 2 + 4

## Wiring
- A list belongs to a scope (a team, a game); claims are by person so a parent can claim for a kid.

## Invariants (do not break; add a contract test if you touch one)
- A claim never exceeds remaining quantity; checked in one transaction.

## How to extend
- Reminders for unclaimed items go through notifications; they are not built here.

## Extraction notes
Incubates in softball.

## Rules that apply to every module
1. Removable: deleting this module from a manifest leaves a buildable app; dependents fail loudly at `platform validate`, never silently at runtime.
2. Owns its data: only this module writes the tables in `migrations/`; others go through the interfaces above.
3. Interfaces, not names: never import another module by path; depend on an interface and let the manifest pick the provider.
4. Layering is one-way: `requires` may only point at this layer or below; `optional` may point up.
5. Two-app rule: this module is `stable` only once two apps use it unchanged. Until then it is `planned` or `incubating`.
