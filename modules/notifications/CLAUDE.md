# notifications

> Email, push and SMS behind one send call, with templates, per-user preferences and digesting.

Layer: **capability** · Status: **planned** · Drift: **platform-owned** · Hosting: aws, free · Platforms: api

This file is the agent-facing contract. Read it before touching anything in this folder, and keep it true when you do.

## Provides
- `notify.send@1` — send one message over email, push or SMS with a template and variables
- `notify.templates@1` — versioned message templates per channel
- `notify.preferences@1` — per-user channel preferences and quiet hours
- `notify.digest@1` — batching of low-priority messages into a digest

## Requires (hard)
- `identity.user@1` — a login principal with a stable id
- `infra.db.postgres@1` — a Postgres database plus a connection secret; migrations run against it

## Optional (used when present, never assumed)
- `infra.secrets@1` — secret storage and injection into runtimes

## Config (set in `platform.yaml` as `notifications.<key>`)
- `channels` (array, default `["email"]`) — Enabled channels: email, push, sms
- `digest_hour_local` (integer, default `7`) — Local hour the daily digest sends

## Wiring
- Modules call `notify.send@1` with a template id and variables; they never talk to SES, a push service or an SMS provider directly.
- Email goes through SES on aws; switch the sender domain only after its SPF, DKIM and DMARC records are in place, or a strict DMARC policy stops delivery outright. Push goes through Firebase Cloud Messaging for iOS and Android.
- `mobile-shell` registers device tokens through `notify.preferences@1`.

## Invariants (do not break; add a contract test if you touch one)
- A user can turn off every non-essential channel; essential messages (security, consent changes) are flagged as such in the template and cannot be muted.
- Templates are versioned; a sent message records the template version used.

## How to extend
- A new channel is an adapter plus a config enum value; the send interface does not change.

## Extraction notes
Extraction step 3. Pull the SES/SNS wiring out of AveHealth and put templates behind the interface.

## Rules that apply to every module
1. Removable: deleting this module from a manifest leaves a buildable app; dependents fail loudly at `platform validate`, never silently at runtime.
2. Owns its data: only this module writes the tables in `migrations/`; others go through the interfaces above.
3. Interfaces, not names: never import another module by path; depend on an interface and let the manifest pick the provider.
4. Layering is one-way: `requires` may only point at this layer or below; `optional` may point up.
5. Two-app rule: this module is `stable` only once two apps use it unchanged. Until then it is `planned` or `incubating`.
