# ADRs — ci-cd

Decisions and the alternatives rejected, newest first. Replaces "best X" branches: an experiment ends here as a dated entry, not as a branch.

## 0003 · Implemented: OIDC deploy role, nothing without a repository (2026-10-16)
- Status: accepted
- Context: Extraction step 1. The shell has no repository yet.
- Decision: with `github_repo` set, a role trusted only for that repository's branch, able to assume the CDK bootstrap roles and publish the site. With it empty, no AWS resources. `preview_environments` removed: one environment per app (docs/adr/0002).
- Alternatives rejected: a role for the platform repo itself (deploy power from a repository that only holds templates); stored access keys in GitHub.
- Consequences: the role is proven when the first real app repository exists. Version 0.3.0.

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
