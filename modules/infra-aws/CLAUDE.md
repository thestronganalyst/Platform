# infra-aws

> The AWS foundation every aws-tier app deploys onto, in your own account: VPC, Aurora Serverless v2 Postgres, the API image on Lambda behind API Gateway, S3 + CloudFront, object storage, secrets and a security baseline (CloudTrail, GuardDuty, flow logs, KMS keys, an alarms topic).

Layer: **foundation** · Status: **incubating** · Drift: **platform-owned** · Hosting: aws · Platforms: infra only

This file is the agent-facing contract. Read it before touching anything in this folder, and keep it true when you do.

## Provides (and what a consumer gets from `ctx.require(...)`)
- `infra.network@1` — `.vpc`, `.app_subnets`, `.data_subnets`, `.app_security_group`
- `infra.db.postgres@1` — `.cluster`, `.secret`, `.key`, `.endpoint`, `.port`, `.database_name`, `.allow_from(peer_sg, description)`
- `infra.container@1` — `.http_api`, `.url`, `.mount(id, image=DockerImageCode, environment=..., memory_size=..., timeout=...)`; one function per app on the API's default route
- `infra.cdn@1` — `.bucket`, `.distribution`, `.domain`, `.origin` (`https://<domain>`)
- `infra.object-store@1` — `.bucket` (KMS-encrypted with the app key; CORS allows presigned PUT/GET from the web origin)
- `infra.secrets@1` — `.key`, `.create(scope, id, description)` → a Secrets Manager secret under the app key
- `infra.security-baseline@1` — `.key` (rotating KMS key), `.alarms` (SNS topic), `.trail`

## Requires (hard)
- none

## Optional (used when present, never assumed)
- none

## Config (set in `platform.yaml` as `infra-aws.<key>`)
- `region` (default `"us-east-1"`)
- `account` (default `""`) — when set, any other account is refused at synth. Quote it: `"123456789012"`.
- `db_size` (`small` | `medium` | `large`, default `small`) — small is 0–2 ACU and pauses after 10 idle minutes; medium 0.5–4; large 1–16.
- `runtime` (`lambda`) — the only runtime (ADR 0002).
- `nat_gateways` (0–2, default 1) — the largest fixed cost. 0 leaves the app subnets with no outbound internet, so Lambda cannot reach AWS APIs outside the VPC.
- `guardduty` (default true) — false when the account already has a detector in the region (one per account and region).
- `cloudtrail` (default true) — a multi-region trail with its own bucket.
- `bastion` (default true) — needs a NAT gateway; refused without one.
- `deletion_protection` (default true) — true keeps the database (snapshot + protection), buckets and the key when stacks are deleted; false lets a throwaway app tear down.

## Stacks (one set per environment, named `<App><Env><Part>`)
| Stack | Contents |
| --- | --- |
| `Security` | KMS key (rotation on), alarms topic, CloudTrail trail + bucket, GuardDuty detector |
| `Network` | VPC 10.40.0.0/16, 2 AZs: public, app (with NAT egress), data (isolated); S3 gateway endpoint; flow logs |
| `Web` | private site bucket, CloudFront with origin access control, SPA fallback to /index.html, security headers |
| `Data` | Aurora Serverless v2 Postgres 16.9 in the data subnets, its secret, the bastion, the object bucket |
| `Api` | HTTP API (throttled 50 rps / burst 100), one Lambda on `$default`; a placeholder answers `/healthz` until a module mounts the API image |

## Wiring
- Other modules get these through `ctx.require(...)`, never by importing this package.
- The account comes from the deploying credentials; the region from config. No account number is written in the repo unless the owner pins `account` in an app's manifest.
- The database sits in isolated subnets with no internet route. Migrations run by hand through the SSM bastion; stop it afterwards (`BastionStopCommand` output). CI cannot reach the database.
- `ci-cd` publishes the web app; stacks deploy by hand from the generated app's `infra/` folder.
- **Cross-stack grants on KMS-encrypted resources go on the consumer's own role** (`fn.add_to_role_policy(...)`), never through `secret.grant_read` / `key.grant_*`: those write the consumer into the key policy in the `Security` stack, which is built first, and CDK fails with a dependency cycle.

## Invariants (each has a test in `tests/test_infra_aws.py`)
- Every taggable resource carries `app` and `environment` tags.
- The database is encrypted with the app key, never publicly accessible, and accepts 5432 only from security groups named through `allow_from` (the app security group by default). No `0.0.0.0/0` ingress anywhere.
- Every bucket blocks public access and denies requests without TLS.
- The web is HTTPS-only through CloudFront.
- The KMS key rotates; the trail validates its log files.
- The API function may read only the database secret, and decrypt only through Secrets Manager (`kms:ViaService`).
- A pinned `account` refuses every other account.
- Stacks are named per environment even with one environment, so adding `dev` later is a manifest change.

## How to extend
- A new output interface (for example `infra.queue@1`): build it in its own file, `ctx.provide` it in `build()`, declare it in `module.yaml`, add a test.
- Changing `runtime` must not change any interface a consumer sees; the API URL is the contract.

## Cost floor (us-east-1, approximate, idle)
NAT gateway ≈ $33/month; Aurora `small` ≈ storage only while paused; bastion ≈ $3/month if left running (≈ $0.64 stopped); KMS key $1; Secrets Manager $0.40/secret; GuardDuty a few dollars; CloudTrail management events free for the first trail; CloudFront, S3, API Gateway and Lambda cents at idle.

## Extraction notes
Written fresh on 2026-10-16, modeled on AveHealth's stack layout; no AveHealth code was copied (docs/adr/0003-provenance.md). AveHealth's auth stack maps to `identity`, its uploads bucket to `storage`, its API stack to `api-shell` (which mounts its image here), its monitoring stack to `observability`.

## Rules that apply to every module
1. Removable: deleting this module from a manifest leaves a buildable app; dependents fail loudly at `platform validate`, never silently at runtime.
2. Owns its data: only this module writes the tables in `migrations/`; others go through the interfaces above.
3. Interfaces, not names: never import another module by path; depend on an interface and let the manifest pick the provider.
4. Layering is one-way: `requires` may only point at this layer or below; `optional` may point up.
5. Two-app rule: this module is `stable` only once two apps use it unchanged. Until then it is `planned` or `incubating`.
