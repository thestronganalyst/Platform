# ADRs — observability

Decisions and the alternatives rejected, newest first. Replaces "best X" branches: an experiment ends here as a dated entry, not as a branch.

## 0002 · Audit on both tiers (2026-10-16)
- Status: accepted
- Context: `consent-sharing` requires `obs.audit@1`, and the free tier now hosts multi-role apps.
- Decision: The audit stream is a Postgres table on both tiers; only the log sink differs.
- Alternatives rejected: Audit on aws only: would block consent-sharing on the free tier.

## 0001 · Module created from the contract (2026-10-16)
- Status: accepted
- Context: `observability` was defined in `docs/CONTRACT.md` from the AveHealth / softball paper split.
- Decision: the interfaces in `module.yaml` are the contract; implementation follows the extraction order in the contract doc.
- Alternatives rejected: keeping this capability inside each app (fails the two-app test the moment softball needs it).
