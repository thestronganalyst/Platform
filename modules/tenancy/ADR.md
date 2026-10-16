# ADRs — tenancy

Decisions and the alternatives rejected, newest first. Replaces "best X" branches: an experiment ends here as a dated entry, not as a branch.

## 0003 · Memberships need the member's yes (2026-10-16)
- Status: accepted
- Context: AveHealth's provider can invite a patient but never make the connection active; the patient's yes does. That is what makes a revoke final.
- Decision: Same rule for every membership: invited → pending; the member or their guardian activates it.
- Alternatives rejected: Org-side activation: lets an org claim people who never agreed.

## 0002 · Fixed levels per app (2026-10-16)
- Status: accepted
- Context: Softball needs league → team; AveHealth needs practice → panel. No known app needs deeper or variable nesting.
- Decision: Levels are fixed per app through `tenancy.levels`.
- Alternatives rejected: Arbitrary nesting: costs a recursive query in every scope check and no app needs it.

## 0001 · Module created from the contract (2026-10-16)
- Status: accepted
- Context: `tenancy` was defined in `docs/CONTRACT.md` from the AveHealth / softball paper split.
- Decision: the interfaces in `module.yaml` are the contract; implementation follows the extraction order in the contract doc.
- Alternatives rejected: keeping this capability inside each app (fails the two-app test the moment softball needs it).
