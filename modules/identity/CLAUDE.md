# identity

> Login, sessions and roles. Cognito on the aws tier, Supabase Auth on the free tier, one interface either way. Invite-only by default.

Layer: **capability** · Status: **planned** · Drift: **platform-owned** · Hosting: aws, free · Platforms: api, web, mobile

This file is the agent-facing contract. Read it before touching anything in this folder, and keep it true when you do.

## Provides
- `identity.user@1` — a login principal with a stable id
- `identity.session@1` — a verified session for a request or client
- `identity.roles@1` — role assignment per user and role checks

## Requires (hard)
- `infra.db.postgres@1` — a Postgres database plus a connection secret; migrations run against it

## Optional (used when present, never assumed)
- `infra.secrets@1` — secret storage and injection into runtimes

## Config (set in `platform.yaml` as `identity.<key>`)
- `providers` (array, default `["email"]`) — Login providers: email, google, apple
- `mfa` (string, default `"optional"`, one of ['off', 'optional', 'required', 'passkey']) — Second factor: `passkey` means a passkey is the only one that counts (aws tier; free tier to be confirmed)
- `signup` (string, default `"invite-only"`, one of ['invite-only', 'open']) — Invite-only: accounts are created on someone's behalf, never by self sign-up

## Wiring
- Provides the principal that `api.auth-middleware@1` and `web.role-nav@1` consume. Neither shell requires this module; both gain behavior when it is present.
- Invite-only: an account is created on someone's behalf (admin → member → their invitees) and the person receives a temporary credential. Every sign-in screen handles the forced new-password step that follows.
- App-level roles are coarse (admin, member). What someone may do inside an org lives in `tenancy.membership@1`: one parent may coach another team.
- On the free tier, creating a user needs the service-role key, so invites run in an Edge Function (`infra.functions@1`), never in the browser.

## Invariants (do not break; add a contract test if you touch one)
- A user id is stable for the life of the account and never reused.
- No person data lives here beyond what login needs; names, birth dates and relationships belong to `profiles`.
- A managed profile gets a login only when its guardian issues one, and that login carries only the restricted role (see `profiles`).
- Admin and service-role credentials never reach a client.

## How to extend
- A new provider is a config enum value plus an adapter in `app/api/providers/`; the interface does not change.

## Extraction notes
Extraction step 2, first of three. Pull Cognito setup and session handling out of AveHealth; then redesign `profiles` and `tenancy` against softball and back-port all three before step 3.

## Rules that apply to every module
1. Removable: deleting this module from a manifest leaves a buildable app; dependents fail loudly at `platform validate`, never silently at runtime.
2. Owns its data: only this module writes the tables in `migrations/`; others go through the interfaces above.
3. Interfaces, not names: never import another module by path; depend on an interface and let the manifest pick the provider.
4. Layering is one-way: `requires` may only point at this layer or below; `optional` may point up.
5. Two-app rule: this module is `stable` only once two apps use it unchanged. Until then it is `planned` or `incubating`.
