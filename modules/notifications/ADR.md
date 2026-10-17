# ADRs — notifications

Decisions and the alternatives rejected, newest first. Replaces "best X" branches: an experiment ends here as a dated entry, not as a branch.

## 0003 · Person-written messages pass the minors check (2026-10-17)
- Status: accepted
- Context: The owner's rule: no private messaging between or with children (profiles ADR 0003). A coach's announcement sent through this module is a message from a person.
- Decision: When `profiles.safeguarding@1` is present, every person-written message is checked with `conversation_allowed`; a minor never receives one alone, and their guardians receive whatever they receive. System messages (a schedule change, a security notice) are not person-written.
- Alternatives rejected: Leaving the check to each calling module (one missed caller breaks the rule).

## 0002 · SES for email, Firebase Cloud Messaging for push (2026-10-16)
- Status: accepted
- Context: AveHealth sends email through Cognito/SES and push through Firebase.
- Decision: Same providers, behind `notify.send@1`.
- Alternatives rejected: Amazon SNS mobile push: AveHealth already runs Firebase on both platforms.

## 0001 · Module created from the contract (2026-10-16)
- Status: accepted
- Context: `notifications` was defined in `docs/CONTRACT.md` from the AveHealth / softball paper split.
- Decision: the interfaces in `module.yaml` are the contract; implementation follows the extraction order in the contract doc.
- Alternatives rejected: keeping this capability inside each app (fails the two-app test the moment softball needs it).
