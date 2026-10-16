# ADRs — profiles

Decisions and the alternatives rejected, newest first. Replaces "best X" branches: an experiment ends here as a dated entry, not as a branch.

## 0002 · Kids log in through a guardian-issued restricted login (2026-10-16)
- Status: accepted
- Context: The owner wants kids to log in and see games. Under 13, COPPA requires verifiable parental consent before collecting a child's personal information.
- Decision: A kid is a managed profile. Their guardian may issue them a read-only login scoped to their teams; the guardian's act of issuing it is the consent step, recorded in the audit stream.
- Alternatives rejected: Profile-only, no kid logins (owner wants kids in). Kid self sign-up (no parental consent step).
- Consequences: Before kids under 13 use it, counsel confirms the guardian-issued login meets COPPA's verifiable-parental-consent standard. How a kid signs in (passkey on a family device, a guardian-generated code) is decided when the module is built.

## 0001 · Module created from the contract (2026-10-16)
- Status: accepted
- Context: `profiles` was defined in `docs/CONTRACT.md` from the AveHealth / softball paper split.
- Decision: the interfaces in `module.yaml` are the contract; implementation follows the extraction order in the contract doc.
- Alternatives rejected: keeping this capability inside each app (fails the two-app test the moment softball needs it).
