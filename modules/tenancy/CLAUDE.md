# tenancy

> Organizations, their hierarchy, who belongs to them in what role, and the scope key every tenant-owned row carries.

Layer: **capability** · Status: **planned** · Drift: **platform-owned** · Hosting: aws, free · Platforms: api, web

This file is the agent-facing contract. Read it before touching anything in this folder, and keep it true when you do.

## Provides
- `tenancy.org@1` — an organization record (league, practice, company)
- `tenancy.hierarchy@1` — parent/child links between orgs (league → team, practice → panel)
- `tenancy.membership@1` — a person's role inside an org
- `tenancy.scope@1` — the scope key every tenant-owned row carries and every query filters on

## Requires (hard)
- `identity.user@1` — a login principal with a stable id
- `profiles.person@1` — a person record that is independent of any login
- `infra.db.postgres@1` — a Postgres database plus a connection secret; migrations run against it

## Optional (used when present, never assumed)
- `profiles.safeguarding@1` — when present, a minor can never hold a staff role

## Config (set in `platform.yaml` as `tenancy.<key>`)
- `levels` (array, default `["org"]`) — Named hierarchy levels, top first, e.g. [league, team] or [practice, panel]
- `staff_clearance` (boolean, default `false`) — staff roles need a dated clearance (background check and safeguarding training, checked outside the app) recorded by the top-level org's director

## Wiring
- Every module that stores tenant-owned data includes a `scope_id` column and filters on it; `tenancy.scope@1` is how a request resolves which scopes the acting person may touch.
- A person may hold memberships in many orgs (one parent, three teams, two leagues); the acting scope is chosen per request, never assumed from the login.

## Invariants (do not break; add a contract test if you touch one)
- No cross-scope query without an explicit, audited reason (for example a league director's roll-up).
- An org can invite a person but never activate a membership for them: activation is the member's, or their guardian's, yes. Memberships move pending → active → ended.
- Hierarchy depth is fixed per app by `levels`; arbitrary nesting is an ADR, not a config change.
- With `staff_clearance` on, a staff membership activates only for a person with a current clearance; a clearance records who set it, when, and when it expires, and an expired or withdrawn clearance ends staff rights at once.
- A kid's membership in a team or league activates only on their guardian's yes, team by team.

## How to extend
- A new level is a config change plus a migration; a new kind of relationship between orgs (affiliation, not parent/child) is a new interface.

## Extraction notes
Extraction step 2, third of three. AveHealth's org model is thin; design this against softball's needs, then back-port. If AveHealth breaks in the back-port, the boundary is wrong — stop and redraw.

## Rules that apply to every module
1. Removable: deleting this module from a manifest leaves a buildable app; dependents fail loudly at `platform validate`, never silently at runtime.
2. Owns its data: only this module writes the tables in `migrations/`; others go through the interfaces above.
3. Interfaces, not names: never import another module by path; depend on an interface and let the manifest pick the provider.
4. Layering is one-way: `requires` may only point at this layer or below; `optional` may point up.
5. Two-app rule: this module is `stable` only once two apps use it unchanged. Until then it is `planned` or `incubating`.
