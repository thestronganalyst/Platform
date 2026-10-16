# ADRs — mobile-shell

Decisions and the alternatives rejected, newest first. Replaces "best X" branches: an experiment ends here as a dated entry, not as a branch.

## 0002 · Bare React Native, not Expo (2026-10-16)
- Status: accepted
- Context: AveHealth's phone app is bare React Native with a native HealthKit bridge and Amplify passkeys.
- Decision: Keep bare React Native so both apps share one shell unchanged.
- Alternatives rejected: Expo with a dev client: could host the native modules, but nothing proves it, and the two-app rule needs one shell.

## 0001 · Module created from the contract (2026-10-16)
- Status: accepted
- Context: `mobile-shell` was defined in `docs/CONTRACT.md` from the AveHealth / softball paper split.
- Decision: the interfaces in `module.yaml` are the contract; implementation follows the extraction order in the contract doc.
- Alternatives rejected: keeping this capability inside each app (fails the two-app test the moment softball needs it).
