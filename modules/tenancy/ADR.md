# ADRs — tenancy

Decisions and the alternatives rejected, newest first. Replaces "best X" branches: an experiment ends here as a dated entry, not as a branch.

## 0004 · Cleared adults only as team staff (2026-10-17)
- Status: accepted
- Context: Softball puts adult volunteers around kids. Youth-sports bodies expect screened, trained adults; the owner wants that from the first version.
- Decision: `staff_clearance` (on in the team preset): a staff membership needs a current clearance recorded by the top-level org's director, dated and expiring. The check itself (background check, safeguarding training) happens outside the app; the app records the outcome, not the report. A minor never holds a staff role.
- Alternatives rejected: Any invited adult as staff (the owner chose clearance from the start). Storing background-check reports (sensitive data the app doesn't need; the yes/no and dates are enough).

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
