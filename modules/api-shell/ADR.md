# ADRs — api-shell

Decisions and the alternatives rejected, newest first. Replaces "best X" branches: an experiment ends here as a dated entry, not as a branch.

## 0002 · Framework: FastAPI, SQLAlchemy 2, Alembic, on Lambda (2026-10-16)
- Status: accepted
- Context: AveHealth's API runs this stack and its test suite (including authorization boundary tests against Postgres) is the largest in that repo.
- Decision: Keep it as the only framework.
- Alternatives rejected: Node/Express: no app uses it, and a second API toolchain would split every module's `app/api` in two.

## 0001 · Module created from the contract (2026-10-16)
- Status: accepted
- Context: `api-shell` was defined in `docs/CONTRACT.md` from the AveHealth / softball paper split.
- Decision: the interfaces in `module.yaml` are the contract; implementation follows the extraction order in the contract doc.
- Alternatives rejected: keeping this capability inside each app (fails the two-app test the moment softball needs it).
