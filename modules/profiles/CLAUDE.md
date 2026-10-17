# profiles

> People, separate from logins. A person may have zero logins or one; a guardian owns managed profiles (kids, dependents), acts for them, and issues their login. The safeguarding rules for minors live here.

Layer: **capability** · Status: **planned** · Drift: **platform-owned** · Hosting: aws, free · Platforms: api, web, mobile

This file is the agent-facing contract. Read it before touching anything in this folder, and keep it true when you do.

## Provides
- `profiles.person@1` — a person record that is independent of any login
- `profiles.guardian@1` — guardian ownership of managed profiles: acting for them, and issuing, pausing or revoking their login
- `profiles.safeguarding@1` — the rules for minors as SQL functions every other module calls: `is_minor(person)`, `conversation_allowed(participants, author)`, and what one person may see of a minor

## Requires (hard)
- `identity.user@1` — a login principal with a stable id
- `infra.db.postgres@1` — a Postgres database plus a connection secret; migrations run against it

## Optional (used when present, never assumed)
- none

## Config (set in `platform.yaml` as `profiles.<key>`)
- `managed` (boolean, default `true`) — Enable guardian-owned managed profiles
- `guardian_required_under` (integer, default `18`, minimum `13`) — below this age only a guardian can create the person's profile and issue their login
- `kid_sign_in` (array of `pairing_code` | `parent_device` | `passkey` | `own_email`, default `[]`) — the ways a guardian may let a kid sign in; empty means kids get no login; `passkey` is refused until built
- `own_email_from_age` (integer, default `13`, minimum `13`) — youngest age for an `own_email` login
- `minors_post` (boolean, default `false`) — minors may post in team conversations; off means they read only

## Wiring
- `identity.user@1` links to at most one `profiles.person@1`; a person may exist with no user.
- A minor is anyone under 18, whatever `guardian_required_under` says. The age comes from the birth date the guardian enters when creating the profile; leagues need it for age divisions anyway.
- Kid sign-in, each chosen per kid by a guardian from what the app allows:
  - `parent_device`: no kid login at all. The guardian's app switches to the kid's view and needs the device's own lock to switch back.
  - `pairing_code`: the guardian's app shows a QR code or 6-digit code that works once, for 10 minutes. The kid's device that redeems it gets a long-lived sign-in bound to that device and the restricted role. On aws this is a Cognito custom-auth challenge; on the free tier an Edge Function mints the session.
  - `own_email` (age `own_email_from_age` and up): the guardian enters the teen's address and an invite goes out; the teen signs in like an adult, but the account stays a managed profile under these rules until 18.
- At the `guardian_required_under` birthday the guardians are told, and the person can take the account over with their own email; the guardian links end then, dated.
- `profiles.guardian@1` is what `consent-sharing` and `tenancy.membership` consult when the acting user is not the person the data is about.
- `profiles.safeguarding@1` is required by any module that carries person-to-person messages (a team conversation, a coach's announcement). It decides in Postgres; screens only reflect the answer.

## Invariants (do not break; add a contract test if you touch one)
- Below `guardian_required_under`, a profile and its login come only from a guardian; the API refuses self sign-up, a coach's or league's invite, and any other login link, not just the UI.
- Under 13, no personal information is collected before the guardian's act of creating the profile, which is the consent step and is audited.
- No conversation that includes a minor is ever one-to-one, between minors or with an adult: `conversation_allowed` refuses it. A group that includes a minor includes that minor's guardians, who see everything in it.
- With `minors_post: false`, a minor's login can read team conversations and announcements but cannot write to them.
- A minor's login cannot edit any profile, pay, or see another person's contact details, birth date or address.
- Revoking or pausing a kid's login ends its sessions on every device at once; the guardian sees each paired device and can remove any one.
- A pairing code works once and expires after 10 minutes; a redeemed or expired code is refused.
- Guardian links are many-to-many and dated; removing a guardian never deletes the person.
- No conversation rule is enforced only in a screen: every one has a boundary test against a real Postgres (who gets in, and every party who must not).

## How to extend
- New person attributes go in a side table owned by the module that needs them, keyed by person id; this table stays minimal.
- A new kid sign-in method is a `kid_sign_in` enum value plus its flow; the interfaces do not change.

## Extraction notes
Extraction step 2, second of three. This is a redesign, not a copy: AveHealth's patient record becomes a person with a guardian relationship, which also covers caregivers viewing a parent's data. The kid rules come from the owner's decisions of 2026-10-17 (ADR 0003).

## Rules that apply to every module
1. Removable: deleting this module from a manifest leaves a buildable app; dependents fail loudly at `platform validate`, never silently at runtime.
2. Owns its data: only this module writes the tables in `migrations/`; others go through the interfaces above.
3. Interfaces, not names: never import another module by path; depend on an interface and let the manifest pick the provider.
4. Layering is one-way: `requires` may only point at this layer or below; `optional` may point up.
5. Two-app rule: this module is `stable` only once two apps use it unchanged. Until then it is `planned` or `incubating`.
