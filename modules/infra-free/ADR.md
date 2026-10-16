# ADRs — infra-free

Decisions and the alternatives rejected, newest first. Replaces "best X" branches: an experiment ends here as a dated entry, not as a branch.

## 0002 · The free tier hosts multi-role apps (2026-10-16)
- Status: accepted
- Context: The owner wants multi-role apps (orgs, guardians, consent) on the free tier, not only small tools.
- Decision: Authorization lives in Postgres: tenancy and consent checks are SQL functions used inside RLS policies. Privileged actions run in Edge Functions (`infra.functions@1`).
- Alternatives rejected: Free tier for single-user tools only: would force every multi-role app onto the AWS fixed costs.
- Consequences: `infra.functions@1` is declared now and built when this module is extracted (after softball ships).

## 0001 · Module created from the contract (2026-10-16)
- Status: accepted
- Context: `infra-free` was defined in `docs/CONTRACT.md` from the AveHealth / softball paper split.
- Decision: the interfaces in `module.yaml` are the contract; implementation follows the extraction order in the contract doc.
- Alternatives rejected: keeping this capability inside each app (fails the two-app test the moment softball needs it).
