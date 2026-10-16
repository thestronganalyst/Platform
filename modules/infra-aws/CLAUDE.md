# infra-aws

> The AWS foundation every aws-tier app deploys onto: network, Postgres, a container runtime, CDN, object storage and secrets, as one CDK stack per environment.

Layer: **foundation** · Status: **planned** · Drift: **platform-owned** · Hosting: aws · Platforms: infra only

This file is the agent-facing contract. Read it before touching anything in this folder, and keep it true when you do.

## Provides
- `infra.network@1` — VPC, subnets and security groups; exposes their ids to other constructs
- `infra.db.postgres@1` — a Postgres database plus a connection secret; migrations run against it
- `infra.container@1` — a place to run one container image with env and secret injection (App Runner or Fargate, per ADR)
- `infra.cdn@1` — a CDN distribution and bucket for static web assets
- `infra.object-store@1` — a private object bucket with per-tenant key prefixes
- `infra.secrets@1` — secret storage and injection into runtimes

## Requires (hard)
- none

## Optional (used when present, never assumed)
- none

## Config (set in `platform.yaml` as `infra-aws.<key>`)
- `region` (string, default `"us-east-1"`) — AWS region for every stack
- `db_size` (string, default `"small"`, one of ['small', 'medium', 'large']) — RDS instance class bucket; mapped to an instance type in the construct
- `runtime` (string, default `"app-runner"`, one of ['app-runner', 'fargate']) — Container runtime for infra.container (pending ADR)

## Wiring
- Other modules never import this module's code; they consume the interface outputs (db secret ARN, bucket name, service URL) that the CDK stack exports per environment.
- `ci-cd` deploys this stack first; every other module's infra construct is instantiated inside the app stack this module creates.

## Invariants (do not break; add a contract test if you touch one)
- One stack per environment listed in the manifest; no shared resources across environments.
- Every resource is tagged with app name and environment; untagged resources fail the construct's own tests.
- No public database endpoints. Ever.

## How to extend
- Add a new output interface (for example `infra.queue@1`) by adding a construct, exporting its outputs, and listing the interface under `provides`.
- Changing `runtime` must not change any interface a consumer sees; the service URL is the contract.

## Extraction notes
Extraction step 1 (with ci-cd). Pull the CDK stack out of the AveHealth repo, parameterize app name and environment, and prove it by deploying an empty shell from a fresh clone.

## Rules that apply to every module
1. Removable: deleting this module from a manifest leaves a buildable app; dependents fail loudly at `platform validate`, never silently at runtime.
2. Owns its data: only this module writes the tables in `migrations/`; others go through the interfaces above.
3. Interfaces, not names: never import another module by path; depend on an interface and let the manifest pick the provider.
4. Layering is one-way: `requires` may only point at this layer or below; `optional` may point up.
5. Two-app rule: this module is `stable` only once two apps use it unchanged. Until then it is `planned` or `incubating`.
