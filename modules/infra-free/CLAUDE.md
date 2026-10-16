# infra-free

> The low-cost foundation: Supabase for Postgres, auth, storage and Edge Functions, GitHub Pages for the static site. Hosts small tools and multi-role apps alike.

Layer: **foundation** · Status: **planned** · Drift: **platform-owned** · Hosting: free · Platforms: infra only

This file is the agent-facing contract. Read it before touching anything in this folder, and keep it true when you do.

## Provides
- `infra.db.postgres@1` — a Postgres database plus a connection secret; migrations run against it
- `infra.object-store@1` — a private object bucket with per-tenant key prefixes
- `infra.static-host@1` — static site hosting (GitHub Pages)
- `infra.functions@1` — server-side functions for privileged actions (Supabase Edge Functions on the free tier)

## Requires (hard)
- none

## Optional (used when present, never assumed)
- none

## Config (set in `platform.yaml` as `infra-free.<key>`)
- `supabase_project_ref` (string, default `""`) — Supabase project reference; empty until the project exists

## Wiring
- Supabase project settings live in this module's `infra/` as declarative config and SQL; GitHub Pages is configured by `ci-cd` using `infra.static-host@1`.
- `identity` on this tier uses Supabase Auth; the interface it provides is identical to the Cognito implementation.

## Invariants (do not break; add a contract test if you touch one)
- Row-level security is on for every table a module creates; a module that ships a table without an RLS policy fails validation on this tier.
- No long-running server. Privileged work (invites, guardian-issued logins, payment webhooks) runs as Supabase Edge Functions through `infra.functions@1`; anything that needs `api.router@1` cannot run on this tier.
- The service-role key lives only in Edge Function secrets, never in the static site.

## How to extend
- A new interface on this tier must have an aws counterpart or be marked tier-specific in both `module.yaml` and `docs/CONTRACT.md`.

## Extraction notes
After softball ships. Extracted from project-tracker (React + Supabase + GitHub Pages CI/CD).

## Rules that apply to every module
1. Removable: deleting this module from a manifest leaves a buildable app; dependents fail loudly at `platform validate`, never silently at runtime.
2. Owns its data: only this module writes the tables in `migrations/`; others go through the interfaces above.
3. Interfaces, not names: never import another module by path; depend on an interface and let the manifest pick the provider.
4. Layering is one-way: `requires` may only point at this layer or below; `optional` may point up.
5. Two-app rule: this module is `stable` only once two apps use it unchanged. Until then it is `planned` or `incubating`.
