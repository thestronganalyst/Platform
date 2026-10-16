# payments

> Stripe Connect: money moves to a team's or league's own account, not to you. Charges, payouts and receipts, all audited.

Layer: **capability** · Status: **planned** · Drift: **platform-owned** · Hosting: aws · Platforms: api, web

This file is the agent-facing contract. Read it before touching anything in this folder, and keep it true when you do.

## Provides
- `payments.account@1` — a connected payout account per org
- `payments.charge@1` — a charge against a payer, routed to an org's account
- `payments.payout@1` — payout status and history per org
- `payments.receipt@1` — a receipt record and email per charge

## Requires (hard)
- `tenancy.org@1` — an organization record (league, practice, company)
- `identity.user@1` — a login principal with a stable id
- `obs.audit@1` — an append-only audit event stream other modules write to
- `infra.db.postgres@1` — a Postgres database plus a connection secret; migrations run against it
- `infra.secrets@1` — secret storage and injection into runtimes

## Optional (used when present, never assumed)
- `notify.send@1` — send one message over email, push or SMS with a template and variables

## Config (set in `platform.yaml` as `payments.<key>`)
- `connect_type` (string, default `"express"`, one of ['express', 'standard', 'custom']) — Stripe Connect account type (pending ADR)
- `platform_fee_bps` (integer, default `0`) — Platform fee in basis points, 0 = none

## Wiring
- An org onboards a connected account through `payments.account@1`; charges reference the org and route to it.
- Every charge, refund and payout writes to `obs.audit@1`; receipts go out through `notify.send@1` when selected.

## Invariants (do not break; add a contract test if you touch one)
- No card data touches the platform; everything is tokenized by the provider.
- Amounts are integers in minor units; no floats anywhere in this module.

## How to extend
- Subscriptions and dues are a feature here once one-off charges are proven.

## Extraction notes
Incubates in softball. Likely back-port to AveHealth for RPM billing.

## Rules that apply to every module
1. Removable: deleting this module from a manifest leaves a buildable app; dependents fail loudly at `platform validate`, never silently at runtime.
2. Owns its data: only this module writes the tables in `migrations/`; others go through the interfaces above.
3. Interfaces, not names: never import another module by path; depend on an interface and let the manifest pick the provider.
4. Layering is one-way: `requires` may only point at this layer or below; `optional` may point up.
5. Two-app rule: this module is `stable` only once two apps use it unchanged. Until then it is `planned` or `incubating`.
