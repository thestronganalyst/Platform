# booking

> Resources, availability, holds, reservations and an optional owner approval step. Fields and parks & rec now; provider appointment slots later.

Layer: **capability** · Status: **planned** · Drift: **platform-owned** · Hosting: aws · Platforms: api, web

This file is the agent-facing contract. Read it before touching anything in this folder, and keep it true when you do.

## Provides
- `booking.resource@1` — a bookable resource (field, room, provider slot)
- `booking.availability@1` — availability windows and blackout rules per resource
- `booking.reservation@1` — a hold or confirmed reservation against a resource
- `booking.approval@1` — an optional approval step by the resource owner (parks & rec, a practice)

## Requires (hard)
- `tenancy.org@1` — an organization record (league, practice, company)
- `tenancy.scope@1` — the scope key every tenant-owned row carries and every query filters on
- `notify.send@1` — send one message over email, push or SMS with a template and variables
- `infra.db.postgres@1` — a Postgres database plus a connection secret; migrations run against it

## Optional (used when present, never assumed)
- `payments.charge@1` — a charge against a payer, routed to an org's account

## Config (set in `platform.yaml` as `booking.<key>`)
- `approval_required` (boolean, default `true`) — Reservations wait for the resource owner's approval
- `hold_minutes` (integer, default `15`) — How long an unconfirmed hold lasts

## Wiring
- A resource belongs to an org; availability and reservations are scoped; approval notifies through `notify.send@1`.
- With `payments.charge@1` selected, a reservation can require payment to confirm.

## Invariants (do not break; add a contract test if you touch one)
- No double booking: reservations are checked against availability and existing holds in one transaction.

## How to extend
- Recurring reservations are a feature here; pricing rules belong to payments.

## Extraction notes
Incubates in softball. Likely back-port to AveHealth as appointment scheduling.

## Rules that apply to every module
1. Removable: deleting this module from a manifest leaves a buildable app; dependents fail loudly at `platform validate`, never silently at runtime.
2. Owns its data: only this module writes the tables in `migrations/`; others go through the interfaces above.
3. Interfaces, not names: never import another module by path; depend on an interface and let the manifest pick the provider.
4. Layering is one-way: `requires` may only point at this layer or below; `optional` may point up.
5. Two-app rule: this module is `stable` only once two apps use it unchanged. Until then it is `planned` or `incubating`.
