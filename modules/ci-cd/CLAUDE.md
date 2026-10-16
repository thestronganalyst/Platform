# ci-cd

> GitHub Actions deploys through an OIDC role scoped to one repository and branch; workflow templates for publishing the web app.

Layer: **foundation** · Status: **incubating** · Drift: **platform-owned** · Hosting: aws, free · Platforms: infra only

This file is the agent-facing contract. Read it before touching anything in this folder, and keep it true when you do.

## Provides
- `ci.pipeline@1` — `.role` (the deploy role, or None when no repository is configured), `.repo`, `.branch`

## Requires (hard)
- none

## Optional (used when present, never assumed)
- `infra.cdn@1` — when present, the role may write the site bucket and invalidate the distribution
- `infra.container@1`, `infra.static-host@1` — reserved for the API and free-tier publish workflows

## Config (set in `platform.yaml` as `ci-cd.<key>`)
- `branch` (default `"main"`) — the only branch whose workflows can assume the role
- `github_repo` (default `""`) — `owner/repo`. Empty creates nothing in AWS: a deploy role nobody uses is standing access for no reason.
- `oidc_provider` (`create` | `import`, default `create`) — `import` when the account already has GitHub's OIDC provider (one per account).

## Wiring
- The role trusts `token.actions.githubusercontent.com` only for `repo:<github_repo>:ref:refs/heads/<branch>`, audience `sts.amazonaws.com`, sessions of one hour.
- Its only AWS power: assume the CDK bootstrap roles (`cdk-*`), and, with `infra.cdn@1`, write the site bucket and invalidate the distribution. No stored AWS keys anywhere.
- `app/ci/publish-web.yml` is the workflow template: build, upload hashed assets, then `index.html` with no-cache, then invalidate it, so a deploy never serves a blank page. It reads `AWS_DEPLOY_ROLE_ARN`, `WEB_BUCKET` and `WEB_DISTRIBUTION_ID` repository variables (the stacks' outputs).
- Backend stacks and migrations deploy by hand: the database has no internet route, so CI cannot reach it.

## Invariants (each has a test in `modules/infra-aws/tests/test_infra_aws.py`)
- The trust policy names one repository and one branch; never a wildcard repository.
- No `"*"` action in the role's policies.
- No repository configured → no AWS resources.

## How to extend
- A new workflow is a template under `app/ci/`; a new permission is a statement scoped to a resource another module provides, with a test.

## Extraction notes
Written fresh on 2026-10-16, modeled on AveHealth's CI role; no AveHealth code was copied.

## Rules that apply to every module
1. Removable: deleting this module from a manifest leaves a buildable app; dependents fail loudly at `platform validate`, never silently at runtime.
2. Owns its data: only this module writes the tables in `migrations/`; others go through the interfaces above.
3. Interfaces, not names: never import another module by path; depend on an interface and let the manifest pick the provider.
4. Layering is one-way: `requires` may only point at this layer or below; `optional` may point up.
5. Two-app rule: this module is `stable` only once two apps use it unchanged. Until then it is `planned` or `incubating`.
