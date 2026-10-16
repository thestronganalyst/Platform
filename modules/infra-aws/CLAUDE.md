# infra-aws

> The AWS foundation every aws-tier app deploys onto, in your own account: VPC, Aurora Serverless v2 Postgres, the API image on Lambda behind API Gateway, S3 + CloudFront, object storage, secrets and a security baseline (CloudTrail, GuardDuty, flow logs, KMS keys, an alarms topic).

Layer: **foundation** · Status: **planned** · Drift: **platform-owned** · Hosting: aws · Platforms: infra only

This file is the agent-facing contract. Read it before touching anything in this folder, and keep it true when you do.

## Provides
- `infra.network@1` — VPC, subnets and security groups; exposes their ids to other constructs
- `infra.db.postgres@1` — a Postgres database plus a connection secret; migrations run against it
- `infra.container@1` — the API container image running on Lambda behind API Gateway, with env and secret injection
- `infra.cdn@1` — a CDN distribution and bucket for static web assets
- `infra.object-store@1` — a private object bucket with per-tenant key prefixes
- `infra.secrets@1` — secret storage and injection into runtimes
- `infra.security-baseline@1` — CloudTrail, GuardDuty, VPC flow logs, KMS keys and an alarms topic

## Requires (hard)
- none

## Optional (used when present, never assumed)
- none

## Config (set in `platform.yaml` as `infra-aws.<key>`)
- `region` (string, default `"us-east-1"`) — AWS region for every stack
- `db_size` (string, default `"small"`, one of ['small', 'medium', 'large']) — Aurora Serverless v2 capacity range (min/max ACU), mapped in the construct
- `runtime` (string, default `"lambda"`, one of ['lambda']) — API runtime: the API container image on Lambda behind API Gateway

## Wiring
- Other modules never import this module's code; they consume the outputs (database secret ARN, bucket names, API URL) the CDK stacks export.
- The account comes from the deploying shell (`CDK_DEFAULT_ACCOUNT`), the region defaults to us-east-1. No account number is written anywhere in the repo.
- The database sits in isolated subnets with no internet route. Migrations run by hand through an SSM bastion that is stopped between sessions; CI cannot reach the database.
- `ci-cd` deploys the web app; every other stack deploys by hand with `cdk deploy <stack> --exclusively`.

## Invariants (do not break; add a contract test if you touch one)
- Every resource is tagged with app name and environment; untagged resources fail the construct's own tests.
- No public database endpoint, ever. The bastion is stopped when nobody is using it.
- Stacks are named per environment even with one environment, so adding `dev` later is a manifest change.

## How to extend
- Add a new output interface (for example `infra.queue@1`) by adding a construct, exporting its outputs, and listing the interface under `provides`.
- Changing `runtime` must not change any interface a consumer sees; the service URL is the contract.

## Extraction notes
Extraction step 1 (with ci-cd). AveHealth's network, security, database, SPA hosting and CI-role stacks map here; its auth stack maps to `identity`, its uploads bucket to `storage` (the ingest Lambda stays in AveHealth's domain), its API stack to `api-shell`, its monitoring stack to `observability`. Code comes over through AveHealth's comment stripper (docs/adr/0003-provenance.md).

## Rules that apply to every module
1. Removable: deleting this module from a manifest leaves a buildable app; dependents fail loudly at `platform validate`, never silently at runtime.
2. Owns its data: only this module writes the tables in `migrations/`; others go through the interfaces above.
3. Interfaces, not names: never import another module by path; depend on an interface and let the manifest pick the provider.
4. Layering is one-way: `requires` may only point at this layer or below; `optional` may point up.
5. Two-app rule: this module is `stable` only once two apps use it unchanged. Until then it is `planned` or `incubating`.
