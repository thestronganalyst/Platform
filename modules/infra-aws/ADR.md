# ADRs — infra-aws

Decisions and the alternatives rejected, newest first. Replaces "best X" branches: an experiment ends here as a dated entry, not as a branch.

## 0005 · Implemented: five stacks composed through interfaces (2026-10-16)
- Status: accepted
- Context: Extraction step 1. The module had to deploy on its own (the `shell` example) and hand its resources to later modules without them importing this package.
- Decision: `infra/infra_aws/build(ctx)` builds Security, Network, Web, Data and Api stacks and `ctx.provide`s seven interfaces. A placeholder Lambda answers `/healthz` until `api-shell` mounts the real image. `db_size: small` pauses Aurora to 0 ACU when idle. Written fresh, modeled on AveHealth's layout; nothing copied.
- Alternatives rejected: one stack for everything (one failed resource rolls back the whole foundation); a zip-only API runtime (the contract is the container image; the zip is only the placeholder, so step 1 needs no Docker); `secret.grant_read` across stacks (writes the consumer into the key policy and cycles).
- Consequences: `nat_gateways`, `guardduty`, `cloudtrail`, `bastion`, `deletion_protection` and `account` are now config. Version 0.3.0.

## 0004 · One account, one region, one environment (2026-10-16)
- Status: accepted
- Context: The owner deploys the platform to his own AWS account in us-east-1, with no separate dev and prod.
- Decision: Each app gets one environment, `prod`. The account comes from the deploying shell. Stacks keep per-environment names.
- Alternatives rejected: Separate dev and prod accounts or environments: the owner's call. Without a staging copy, safety comes from tests, `cdk diff` before every deploy, and the image check before every API deploy.

## 0003 · Database: Aurora Serverless v2 Postgres in isolated subnets (2026-10-16)
- Status: accepted
- Context: AveHealth runs this, reached only through an SSM bastion. The NAT gateway and Aurora's capacity floor are the fixed monthly costs.
- Decision: Keep it. Migrations run by hand through the bastion.
- Alternatives rejected: A provisioned RDS instance (fixed size, no scale-down). Any public endpoint. Apps where the fixed cost matters use the free tier.

## 0002 · API runtime: the API image on Lambda behind API Gateway (2026-10-16)
- Status: accepted
- Context: AveHealth runs FastAPI as a Lambda container image (Mangum adapter) behind API Gateway; its ingest Lambda shares the image.
- Decision: Keep it. `infra.container@1` means a Lambda container image plus an API Gateway route.
- Alternatives rejected: App Runner and ECS Fargate: both bill while idle and no running app proves them. Revisit only if a module needs work longer than Lambda's 15-minute limit.

## 0001 · Module created from the contract (2026-10-16)
- Status: accepted
- Context: `infra-aws` was defined in `docs/CONTRACT.md` from the AveHealth / softball paper split.
- Decision: the interfaces in `module.yaml` are the contract; implementation follows the extraction order in the contract doc.
- Alternatives rejected: keeping this capability inside each app (fails the two-app test the moment softball needs it).
