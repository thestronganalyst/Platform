# profiles

> People, separate from logins. A person may have zero logins (a kid, a dependent) or one; a guardian owns managed profiles and acts for them.

Layer: **capability** · Status: **planned** · Drift: **platform-owned** · Hosting: aws, free · Platforms: api, web

This file is the agent-facing contract. Read it before touching anything in this folder, and keep it true when you do.

## Provides
- `profiles.person@1` — a person record that is independent of any login
- `profiles.guardian@1` — guardian ownership of managed profiles (kids, dependents, charges)

## Requires (hard)
- `identity.user@1` — a login principal with a stable id
- `infra.db.postgres@1` — a Postgres database plus a connection secret; migrations run against it

## Optional (used when present, never assumed)
- none

## Config (set in `platform.yaml` as `profiles.<key>`)
- `managed` (boolean, default `true`) — Enable guardian-owned managed profiles
- `managed_age_threshold` (integer, default `13`) — Under this age a person is a managed profile, never a login (COPPA)

## Wiring
- `identity.user@1` links to at most one `profiles.person@1`; a person may exist with no user.
- `profiles.guardian@1` is the relationship `consent-sharing` and `tenancy.membership` consult when the acting user is not the person the data is about.

## Invariants (do not break; add a contract test if you touch one)
- A person under `managed_age_threshold` cannot be linked to a login; the API refuses, not just the UI.
- Guardian links are many-to-many and dated; removing a guardian never deletes the person.

## How to extend
- New person attributes go in a side table owned by the module that needs them, keyed by person id; this table stays minimal.

## Extraction notes
Extraction step 2, second of three. This is a redesign, not a copy: AveHealth's patient record becomes a person with a guardian relationship, which also covers caregivers viewing a parent's data.

## Rules that apply to every module
1. Removable: deleting this module from a manifest leaves a buildable app; dependents fail loudly at `platform validate`, never silently at runtime.
2. Owns its data: only this module writes the tables in `migrations/`; others go through the interfaces above.
3. Interfaces, not names: never import another module by path; depend on an interface and let the manifest pick the provider.
4. Layering is one-way: `requires` may only point at this layer or below; `optional` may point up.
5. Two-app rule: this module is `stable` only once two apps use it unchanged. Until then it is `planned` or `incubating`.
