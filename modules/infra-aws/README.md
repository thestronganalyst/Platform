# infra-aws

The AWS foundation every aws-tier app deploys onto, in your own account: VPC, Aurora Serverless v2 Postgres, the API image on Lambda behind API Gateway, S3 + CloudFront, object storage, secrets and a security baseline (CloudTrail, GuardDuty, flow logs, KMS keys, an alarms topic).

- Pick it when: you need `infra.network@1`, `infra.db.postgres@1`, `infra.container@1`, `infra.cdn@1`, `infra.object-store@1`, `infra.secrets@1`, `infra.security-baseline@1`.
- Status: `planned` — folder and contract exist, no implementation yet.
- Source: AveHealth.

See `CLAUDE.md` for the contract and `ADR.md` for decisions.
