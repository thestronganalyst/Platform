# infra-aws

The AWS foundation every aws-tier app deploys onto: network, Postgres, a container runtime, CDN, object storage and secrets, as one CDK stack per environment.

- Pick it when: you need `infra.network@1`, `infra.db.postgres@1`, `infra.container@1`, `infra.cdn@1`, `infra.object-store@1`, `infra.secrets@1`.
- Status: `planned` — folder and contract exist, no implementation yet.
- Source: AveHealth.

See `CLAUDE.md` for the contract and `ADR.md` for decisions.
