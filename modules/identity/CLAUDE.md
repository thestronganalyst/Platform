# identity

> Login, sessions and roles. Cognito on the aws tier, Supabase Auth on the free tier, one interface either way. Invite-only by default.

Layer: **capability** · Status: **incubating** (aws tier built; free tier, web and mobile not yet) · Drift: **platform-owned** · Hosting: aws, free · Platforms: api, web, mobile

This file is the agent-facing contract. Read it before touching anything in this folder, and keep it true when you do.

## Provides
All three are one `Identity` value in infrastructure code: `.user_pool`, `.client`, `.issuer`, `.roles`, `.grant_invite(principal)`.
- `identity.user@1` — a login principal with a stable id (the Cognito `sub`, stored as `users.subject`)
- `identity.session@1` — a verified session: API code calls `current_principal` (`app/api/auth.py`) for a `Principal(subject, username, roles)`
- `identity.roles@1` — app-level roles as Cognito groups; API code guards routes with `require_role(...)`

## Requires (hard)
- `infra.db.postgres@1` — a Postgres database plus a connection secret; migrations run against it

## Optional (used when present, never assumed)
- `infra.secrets@1` — secret storage and injection into runtimes
- `infra.container@1` — when present, the API function gets `USER_POOL_ID`, `USER_POOL_CLIENT_ID`, `APP_ROLES` and the four admin actions invites need, scoped to this pool

## Config (set in `platform.yaml` as `identity.<key>`)
- `providers` (default `["email"]`) — email is built; google and apple are refused at synth until built
- `mfa` (`off` | `optional` | `required` | `passkey`, default `optional`) — authenticator app; `passkey` is refused at synth until built (needs a relying-party domain)
- `signup` (`invite-only` | `open`, default `invite-only`)
- `roles` (default `["admin", "member"]`) — app-level roles, one Cognito group each
- `deletion_protection` (default true) — keep the pool when stacks are deleted

## What is built (aws tier)
| Part | Where (flat app) | What it does |
| --- | --- | --- |
| Cognito user pool + client + role groups | `infra/identity/` → stack `<App><Env>Identity` | Email sign-in; invite-only unless `signup: open`; admin-only recovery when invite-only; 12-character passwords; optional/required authenticator-app MFA; SRP-only client with no secret; token revocation on |
| Token verification | `api/identity/auth.py` | Verifies Cognito **access** tokens: RS256 only, issuer, `client_id`, expiry; signing keys cached and refetched at most every 5 minutes |
| Role guard | `api/identity/auth.py` | `require_role("admin")` → 403 for anyone without the group |
| Invites | `api/identity/invites.py` | `invite(email, role)`: validates, creates the account with a temporary password emailed by Cognito, adds the role group |
| `users` table | `migrations/identity/0001_users.sql` | `subject` (unique), `email` (unique, case-insensitive), `role`, `status` pending/active/disabled, `invited_by` |

Not built yet: free tier (Supabase Auth), web and mobile sign-in screens, Google/Apple providers, passkeys. Each raises a clear error at synth rather than half-working.

## Wiring
- Provides the principal that `api.auth-middleware@1` and `web.role-nav@1` consume. Neither shell requires this module; both gain behavior when it is present.
- Invite-only: an account is created on someone's behalf (admin → member → their invitees) and the person receives a temporary credential. Every sign-in screen handles the forced new-password step that follows.
- App-level roles are coarse (admin, member). What someone may do inside an org lives in `tenancy.membership@1`: one parent may coach another team.
- On the free tier, creating a user needs the service-role key, so invites run in an Edge Function (`infra.functions@1`), never in the browser.

## Invariants (each has a test in `tests/`)
- Only access tokens from this pool's issuer, for this app's client, signed RS256 with a published key, unexpired, are accepted; `alg: none`, forged signatures, ID tokens and other clients are refused.
- A route without a valid bearer token answers 401; a valid token without the role answers 403.
- The API function's Cognito permissions are exactly the four invite actions, on this pool only.
- A user id is stable for the life of the account and never reused.
- No person data lives here beyond what login needs; names, birth dates and relationships belong to `profiles`.
- A managed profile gets a login only when its guardian issues one, and that login carries only the restricted role (see `profiles`).
- Admin and service-role credentials never reach a client.

## How to extend
- A new provider is a config enum value plus an adapter in `app/api/providers/`; the interface does not change.

## Extraction notes
Written fresh on 2026-10-16, modeled on AveHealth's invite-only Cognito design; no AveHealth code was copied. Back-porting into AveHealth changes its sign-in and needs the owner's yes first. Next: `profiles` (guardian-issued kid logins), then `tenancy`.

## Rules that apply to every module
1. Removable: deleting this module from a manifest leaves a buildable app; dependents fail loudly at `platform validate`, never silently at runtime.
2. Owns its data: only this module writes the tables in `migrations/`; others go through the interfaces above.
3. Interfaces, not names: never import another module by path; depend on an interface and let the manifest pick the provider.
4. Layering is one-way: `requires` may only point at this layer or below; `optional` may point up.
5. Two-app rule: this module is `stable` only once two apps use it unchanged. Until then it is `planned` or `incubating`.
