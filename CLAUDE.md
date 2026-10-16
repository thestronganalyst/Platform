# Working in this repo

This is the platform repo: modules, presets, schemas and the `platform` CLI. Apps are generated *from* it; they do not live in it. The owner builds almost entirely through Claude Code and does not read the code line by line, so the contracts in this repo are the control surface. Keep them true.

## Read first
1. `docs/CONTRACT.md` — the module contract, the five rules, the module list, the extraction order, the open ADRs. It is the source of truth; when code and contract disagree, fix one and say which.
2. The `CLAUDE.md` of any module you are about to touch.

## Before you change anything
- `platform validate examples/*/platform.yaml` and `pytest` must pass before and after. CI runs both.
- A change to a module's `provides`, `requires`, `optional`, `hosting` or `layer` is an interface change: bump `version`, add an ADR entry in that module's `ADR.md`, and re-run every example manifest.

## The five rules (the validator enforces 1, 3, 4, 5; contract tests enforce 2)
1. **Removable** — removing a module from a manifest leaves a buildable app; dependents fail at `platform validate`, never at runtime.
2. **Owns its data** — a module writes only the tables in its own `migrations/`; others go through its interfaces.
3. **Interfaces, not names** — `requires` lists `domain.name@major` strings. Never import another module by path.
4. **Layering is one-way** — domain → capability → foundation. `requires` may point at the same layer or below; `optional` may point up (a shell works without identity and gains role-aware behavior when identity is selected).
5. **Two-app rule** — `status: stable` only once two apps use the module unchanged. Until then `planned` (folder + contract, no code) or `incubating` (one app, lives there in the module layout).

## Adding a module
- Copy `templates/module/` to `modules/<name>/`; fill every field in `module.yaml`; write the `CLAUDE.md` for the agent who comes after you: wiring, invariants, how to extend.
- Prefer providing an existing interface over inventing one. New interfaces go in the catalog comment at the top of each `CLAUDE.md` that mentions them, and in `docs/CONTRACT.md`.
- Do not add a module nobody has asked for. The module list exists because two apps needed each entry.

## Extraction (from AveHealth, in this order)
1. `infra-aws` + `ci-cd` — prove by deploying an empty shell from a fresh clone.
2. `identity` → `profiles` (redesign: managed profiles) → `tenancy` (design against softball's league → team shape). Back-port all three into AveHealth before step 3; if AveHealth breaks, stop and redraw the boundary.
3. `consent-sharing`, `notifications`, `storage`.
4. `api-shell`, `web-shell`, `observability`.
5. Stop. Generate softball from `team-app`. Everything else incubates inside softball.

When you implement a module, change `status` from `planned` to `incubating`, put real code in `app/`, `infra/`, `migrations/`, add contract tests in `tests/`, and update the module's `README.md` status line.

## What not to do
- No "best X" branches. An experiment ends as a dated entry in an `ADR.md` with the alternatives rejected.
- No multi-cloud. Cloud-specific code stays inside modules; a second cloud is a new module later, not a refactor now.
- No picker UI before the modules are proven. The manifest is the picker.
- Never hand-edit a generated app's `platform.lock.yaml` or its copied `module.yaml` files; change the manifest or the platform and regenerate.

## Decisions still open (see `docs/CONTRACT.md` → Open decisions)
Identity provider per tier · managed-profile model · tenancy depth · API framework · container runtime · offline conflict policy · Stripe Connect type · Copier vs custom scaffolder (`docs/adr/0001-scaffolder.md`).
