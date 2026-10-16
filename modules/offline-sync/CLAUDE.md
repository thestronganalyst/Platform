# offline-sync

> A local store with queued writes and a declared conflict policy, for work done at a field with no signal.

Layer: **capability** · Status: **planned** · Drift: **platform-owned** · Hosting: aws · Platforms: mobile, web

This file is the agent-facing contract. Read it before touching anything in this folder, and keep it true when you do.

## Provides
- `sync.store@1` — a local store with queued writes and a declared conflict policy

## Requires (hard)
- `api.router@1` — a mounted router that modules register endpoints on

## Optional (used when present, never assumed)
- none

## Config (set in `platform.yaml` as `offline-sync.<key>`)
- `conflict_policy` (string, default `"event-log"`, one of ['event-log', 'last-write-wins']) — Pending ADR; event-log expected for scorekeeping

## Wiring
- Modules opt in per table; the sync endpoint is registered through `api.router@1`.

## Invariants (do not break; add a contract test if you touch one)
- A queued write is never silently dropped; conflicts are resolved by the declared policy and surfaced to the user when they cannot be.

## How to extend
- A second conflict policy is an enum value plus an implementation; callers do not change.

## Extraction notes
Incubates in softball. Promote when a second app needs offline writes.

## Rules that apply to every module
1. Removable: deleting this module from a manifest leaves a buildable app; dependents fail loudly at `platform validate`, never silently at runtime.
2. Owns its data: only this module writes the tables in `migrations/`; others go through the interfaces above.
3. Interfaces, not names: never import another module by path; depend on an interface and let the manifest pick the provider.
4. Layering is one-way: `requires` may only point at this layer or below; `optional` may point up.
5. Two-app rule: this module is `stable` only once two apps use it unchanged. Until then it is `planned` or `incubating`.
