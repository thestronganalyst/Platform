# ci-cd

> GitHub Actions workflows that build, test and deploy every environment; adapts to whichever infra interfaces are selected.

Layer: **foundation** · Status: **planned** · Drift: **platform-owned** · Hosting: aws, free · Platforms: infra only

This file is the agent-facing contract. Read it before touching anything in this folder, and keep it true when you do.

## Provides
- `ci.pipeline@1` — build, test and deploy per environment on push

## Requires (hard)
- none

## Optional (used when present, never assumed)
- `infra.container@1` — the API container image running on Lambda behind API Gateway, with env and secret injection
- `infra.static-host@1` — static site hosting (GitHub Pages)
- `infra.cdn@1` — a CDN distribution and bucket for static web assets

## Config (set in `platform.yaml` as `ci-cd.<key>`)
- `branch` (string, default `"main"`) — Branch that deploys to prod
- `preview_environments` (boolean, default `false`) — Deploy a preview per pull request

## Wiring
- Emits one workflow per environment in the manifest. Runs `platform validate` and the tests first; a red check stops every deploy step.
- Publishes the web app through GitHub OIDC (no stored AWS keys): new assets first, then the index, old assets cleared later, so a deploy never serves a blank page.
- Backend stacks and migrations deploy by hand: the database has no internet route, so CI cannot reach it.

## Invariants (do not break; add a contract test if you touch one)
- Deploys only from the configured branch and only after every check passes.
- Secrets come from OIDC roles or GitHub environments, never from the repo.

## How to extend
- Add a job template under `app/ci/` and reference it from the workflow generator; never hand-edit a generated workflow in an app.

## Extraction notes
Extraction step 1 (with infra-aws). Pull the workflows out of AveHealth, parameterize by manifest, add the validate job.

## Rules that apply to every module
1. Removable: deleting this module from a manifest leaves a buildable app; dependents fail loudly at `platform validate`, never silently at runtime.
2. Owns its data: only this module writes the tables in `migrations/`; others go through the interfaces above.
3. Interfaces, not names: never import another module by path; depend on an interface and let the manifest pick the provider.
4. Layering is one-way: `requires` may only point at this layer or below; `optional` may point up.
5. Two-app rule: this module is `stable` only once two apps use it unchanged. Until then it is `planned` or `incubating`.
