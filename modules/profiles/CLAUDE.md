# profiles

> People, separate from logins. A person may have zero logins or one; a guardian owns managed profiles (kids, dependents), acts for them, and may issue them a restricted login.

Layer: **capability** · Status: **planned** · Drift: **platform-owned** · Hosting: aws, free · Platforms: api, web

This file is the agent-facing contract. Read it before touching anything in this folder, and keep it true when you do.

## Provides
- `profiles.person@1` — a person record that is independent of any login
- `profiles.guardian@1` — guardian ownership of managed profiles: acting for them, and issuing or revoking their restricted login

## Requires (hard)
- `identity.user@1` — a login principal with a stable id
- `infra.db.postgres@1` — a Postgres database plus a connection secret; migrations run against it

## Optional (used when present, never assumed)
- none

## Config (set in `platform.yaml` as `profiles.<key>`)
- `managed` (boolean, default `true`) — Enable guardian-owned managed profiles
- `managed_age_threshold` (integer, default `13`) — Under this age COPPA's parental-consent rules apply
- `managed_logins` (boolean, default `false`) — Guardians may issue a managed profile a restricted, read-only login

## Wiring
- `identity.user@1` links to at most one `profiles.person@1`; a person may exist with no user.
- A guardian-issued login: the guardian creates it (no self sign-up, no email of the kid's own needed), it carries the restricted role, it reads only what the kid's memberships allow (in softball: schedule, games, scores), and the guardian can revoke it at any time.
- `profiles.guardian@1` is what `consent-sharing` and `tenancy.membership` consult when the acting user is not the person the data is about.

## Invariants (do not break; add a contract test if you touch one)
- A managed profile can be linked only to a guardian-issued restricted login; the API refuses any other login link, not just the UI.
- A restricted login cannot message anyone, edit any profile, pay, or see another person's contact details.
- Revoking a guardian-issued login ends its sessions at once.
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
