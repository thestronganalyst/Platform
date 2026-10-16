# web-shell

> The React PWA frame: layout, routing, role-aware navigation, theming, error boundary. Forked on generate because every app restyles it.

Layer: **foundation** · Status: **planned** · Drift: **forked** · Hosting: aws, free · Platforms: web

This file is the agent-facing contract. Read it before touching anything in this folder, and keep it true when you do.

## Provides
- `web.shell@1` — the app frame: layout, providers, error boundary
- `web.route-registry@1` — modules register routes and nav entries at build time
- `web.role-nav@1` — navigation filtered by role when identity.roles is selected; flat otherwise
- `web.theme@1` — design tokens and light/dark theming

## Requires (hard)
- none

## Optional (used when present, never assumed)
- `identity.session@1` — a verified session for a request or client
- `identity.roles@1` — role assignment per user and role checks
- `infra.cdn@1` — a CDN distribution and bucket for static web assets
- `infra.static-host@1` — static site hosting (GitHub Pages)

## Config (set in `platform.yaml` as `web-shell.<key>`)
- `pwa` (boolean, default `true`) — Ship a service worker and manifest
- `theme` (string, default `"default"`) — Named theme token set

## Wiring
- Modules with an `app/web/` folder export a route manifest; the shell composes them through `web.route-registry@1` at build time.
- `web.role-nav@1` filters navigation by `identity.roles@1` when selected; with no identity the nav is flat and public.

## Invariants (do not break; add a contract test if you touch one)
- The shell renders with zero modules selected (an empty app with a home route) so removal of any module never breaks the build.
- No module imports another module's components; shared UI lives in the shell's design system.

## How to extend
- Because this module is forked, improvements made in an app are back-ported by hand into this folder; keep the change log in ADR.md.

## Extraction notes
Extraction step 4. Take AveHealth's frame, strip domain routes, prove it renders empty.

## Rules that apply to every module
1. Removable: deleting this module from a manifest leaves a buildable app; dependents fail loudly at `platform validate`, never silently at runtime.
2. Owns its data: only this module writes the tables in `migrations/`; others go through the interfaces above.
3. Interfaces, not names: never import another module by path; depend on an interface and let the manifest pick the provider.
4. Layering is one-way: `requires` may only point at this layer or below; `optional` may point up.
5. Two-app rule: this module is `stable` only once two apps use it unchanged. Until then it is `planned` or `incubating`.
