# mobile-shell

> The phone app frame: bare React Native with Amplify Auth and passkeys. Auth, navigation, push registration. Forked on generate; domain screens are added by the app.

Layer: **capability** · Status: **planned** · Drift: **forked** · Hosting: aws · Platforms: mobile

This file is the agent-facing contract. Read it before touching anything in this folder, and keep it true when you do.

## Provides
- `mobile.shell@1` — the Expo app frame: auth, navigation, push registration

## Requires (hard)
- `identity.session@1` — a verified session for a request or client
- `notify.send@1` — send one message over email, push or SMS with a template and variables

## Optional (used when present, never assumed)
- `sync.store@1` — a local store with queued writes and a declared conflict policy

## Config (set in `platform.yaml` as `mobile-shell.<key>`)
- `bundle_id` (string, default `""`) — iOS bundle id / Android application id

## Wiring
- Shares the identity session with web through the same token flow; no separate mobile auth.
- Registers its push token through `notify.preferences@1`; pushes arrive through Firebase Cloud Messaging on both platforms.
- With `sync.store@1` selected (softball), screens read and write through the local store; without it, they call the API directly.

## Invariants (do not break; add a contract test if you touch one)
- Builds and runs with no domain screens (an authenticated empty app) so removing any module never breaks it.

## How to extend
- Native capabilities (HealthKit, Health Connect, camera) are their own modules that depend on this one; they are never added to the shell.

## Extraction notes
Extract AveHealth's frame minus its HealthKit sync, which becomes a domain module depending on this one. Softball builds on the same frame; promote when both apps use it unchanged.

## Rules that apply to every module
1. Removable: deleting this module from a manifest leaves a buildable app; dependents fail loudly at `platform validate`, never silently at runtime.
2. Owns its data: only this module writes the tables in `migrations/`; others go through the interfaces above.
3. Interfaces, not names: never import another module by path; depend on an interface and let the manifest pick the provider.
4. Layering is one-way: `requires` may only point at this layer or below; `optional` may point up.
5. Two-app rule: this module is `stable` only once two apps use it unchanged. Until then it is `planned` or `incubating`.
