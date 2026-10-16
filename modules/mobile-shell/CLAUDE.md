# mobile-shell

> The Expo app frame: auth, navigation, push registration. Forked on generate; domain screens are added by the app.

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
- With `sync.store@1` selected (softball), screens read and write through the local store; without it, they call the API directly.

## Invariants (do not break; add a contract test if you touch one)
- Builds and runs with no domain screens (an authenticated empty app) so removing any module never breaks it.

## How to extend
- Native capabilities (HealthKit, camera) are their own modules that depend on this one; they are not added to the shell.

## Extraction notes
Built inside softball first (incubating there), then compared with AveHealth's app to settle the shared shell. Promote when both apps use it unchanged.

## Rules that apply to every module
1. Removable: deleting this module from a manifest leaves a buildable app; dependents fail loudly at `platform validate`, never silently at runtime.
2. Owns its data: only this module writes the tables in `migrations/`; others go through the interfaces above.
3. Interfaces, not names: never import another module by path; depend on an interface and let the manifest pick the provider.
4. Layering is one-way: `requires` may only point at this layer or below; `optional` may point up.
5. Two-app rule: this module is `stable` only once two apps use it unchanged. Until then it is `planned` or `incubating`.
