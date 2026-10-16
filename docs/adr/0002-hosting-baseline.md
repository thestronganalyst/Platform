# ADR 0002 · Hosting baseline: own account, us-east-1, one environment, two tiers

- Status: **accepted**
- Date: 2026-10-16
- Owner: platform

## Context
The owner answered four questions on 2026-10-16:
- Apps deploy to **his own AWS account**, not to any client's.
- Region: **us-east-1**.
- **No separate dev and prod.**
- The **free tier hosts multi-role apps too**, not only small tools.

## Decision
| Area | Decision | Where it lives |
| --- | --- | --- |
| Account | Comes from the deploying shell (`CDK_DEFAULT_ACCOUNT`). No account number is written in this repo. | `modules/infra-aws` |
| Region | `us-east-1` default (`infra-aws.region`). | `modules/infra-aws/module.yaml` |
| Environments | One, `prod`, unless a manifest lists more. Stacks keep per-environment names so adding `dev` later is a manifest change. | `platform_cli` default, example manifests |
| AWS tier | Lambda container image behind API Gateway; Aurora Serverless v2 in isolated subnets; Cognito; S3 + CloudFront. | `modules/infra-aws/ADR.md` |
| Free tier | Supabase (Postgres, Auth, Storage, Edge Functions) + GitHub Pages, with authorization in Postgres (RLS calling the same SQL functions the API calls on AWS). | `modules/infra-free/ADR.md`, `modules/consent-sharing/ADR.md` |

## Consequences
- With one environment there is no staging copy. Safety comes from the contract tests, the authorization boundary tests, `cdk diff` before every deploy, and the API image check before every API deploy.
- `identity` abstracts Cognito and Supabase Auth. Passkey-only sign-in is AWS-tier until Supabase Auth's passkey support is confirmed.
- `consent-sharing` and `observability` now support the free tier; `examples/league-lite` proves a multi-role free-tier manifest validates.

## Alternatives rejected
- Separate dev and prod: owner's call.
- Free tier for single-user tools only: would push every multi-role app onto the AWS fixed costs (NAT gateway, Aurora's capacity floor).

## Amendment (2026-10-16): a dedicated member account
The owner's existing personal account still runs the earlier AveHealth stack (database, user pool, uploads with health data). Rather than share it, the platform deploys to a **separate member account named `platform`** under an AWS Organization whose management account is that personal account. Experiments never share an account, or its admin rights, with patient data, and retiring the old AveHealth resources later does not touch the platform. The deploy runs through the member account's `OrganizationAccountAccessRole`, assumed from a browser sign-in (`aws login --remote`), with no stored keys. Account numbers stay out of this repo.

## Amendment (2026-10-16, later): the old AveHealth stack removed
At the owner's request the earlier AveHealth stack was shut down in the management account the same day, following AveHealth's own shutdown procedure: scheduled jobs disabled, a final database snapshot and the user list kept for 30 days (deleted automatically by EventBridge Scheduler), then every stack and retained resource removed in reverse order (finished 15:31 UTC; its old keys delete on 2026-10-23). The management account now holds only the organization, the owner's sign-in and that temporary copy; workloads go in member accounts.
