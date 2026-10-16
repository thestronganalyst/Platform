# ADRs — ci-cd

Decisions and the alternatives rejected, newest first. Replaces "best X" branches: an experiment ends here as a dated entry, not as a branch.

## 0002 · CI ships the web app; backend deploys by hand (2026-10-16)
- Status: accepted
- Context: AveHealth's CI checks every push and publishes the web app through OIDC; stacks and migrations are deployed from a clone.
- Decision: Same split here.
- Alternatives rejected: CI running migrations: needs a network path into the isolated subnets, not worth it at one environment.

## 0001 · Module created from the contract (2026-10-16)
- Status: accepted
- Context: `ci-cd` was defined in `docs/CONTRACT.md` from the AveHealth / softball paper split.
- Decision: the interfaces in `module.yaml` are the contract; implementation follows the extraction order in the contract doc.
- Alternatives rejected: keeping this capability inside each app (fails the two-app test the moment softball needs it).
