# ADRs — consent-sharing

Decisions and the alternatives rejected, newest first. Replaces "best X" branches: an experiment ends here as a dated entry, not as a branch.

## 0002 · Consent checks live in Postgres (2026-10-16)
- Status: accepted
- Context: The free tier now hosts multi-role apps and has no API layer.
- Decision: `consent.check@1` is a SQL function used by the API on aws and by RLS policies on free.
- Alternatives rejected: Separate implementations per tier: two copies of the rule that decides who sees whom.

## 0001 · Module created from the contract (2026-10-16)
- Status: accepted
- Context: `consent-sharing` was defined in `docs/CONTRACT.md` from the AveHealth / softball paper split.
- Decision: the interfaces in `module.yaml` are the contract; implementation follows the extraction order in the contract doc.
- Alternatives rejected: keeping this capability inside each app (fails the two-app test the moment softball needs it).
