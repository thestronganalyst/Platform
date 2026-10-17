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
- Infrastructure code lives in `infra/<name_with_underscores>/__init__.py` and exposes `build(ctx)`. A generated app's `infra/compose.py` (from `templates/app/infra/`) calls each selected module's `build` in dependency order. Inside it: `ctx.stack("Part")` for a tagged stack named `<App><Env><Part>`, `ctx.provide(iface, value)` for every interface in `provides` (the synth fails if one is missing), `ctx.require(iface)` / `ctx.optional(iface)` for what it consumes, `ctx.finally_(fn)` to fill a gap after every module has built. The CLAUDE.md lists exactly what each provided value exposes.
- Code under a module's `app/` and `migrations/` ships inside apps and can reach a client's copy (AveHealth's company repository). Keep it plain: ordinary imports, no contract strings (`identity.session@1`), no platform words (platform, preset, manifest), no module names. `tests/test_validator.py` fails otherwise. Contract strings belong in `module.yaml` and `infra/` build code only.
- Infra tests synthesize a generated app (`platform new` into a temp folder) and assert on the templates; see `modules/infra-aws/tests/`. They need `pip install -r templates/app/infra/requirements.txt` and node.

## Extraction (from AveHealth, in this order)
Code comes over from AveHealthRepo only through its comment stripper, and none of its notes come with it (to-do ids, decision ids, account numbers, document text): `docs/adr/0003-provenance.md`.

AveHealth's stacks map to modules like this: network, security, database, SPA hosting and CI role → `infra-aws` / `ci-cd`; auth → `identity`; uploads bucket → `storage` (its ingest Lambda is domain code and stays there); API → `api-shell`; monitoring → `observability`.

1. `infra-aws` + `ci-cd` — prove by deploying an empty shell to the owner's account (us-east-1, one environment) from a fresh clone.
2. `identity` → `profiles` (redesign: guardian-issued kid logins) → `tenancy` (design against softball's league → team shape). Back-port all three into AveHealth before step 3; if AveHealth breaks, stop and redraw the boundary. Each back-port changes sign-in or who sees what, so it needs the owner's explicit yes before it is built.
3. `consent-sharing`, `notifications`, `storage`.
4. `api-shell`, `web-shell`, `observability`.
5. Stop. Generate softball from `team-app`. Everything else incubates inside softball.

When you implement a module, change `status` from `planned` to `incubating`, put real code in `app/`, `infra/`, `migrations/`, add contract tests in `tests/`, and update the module's `README.md` status line.

## What not to do
- No "best X" branches. An experiment ends as a dated entry in an `ADR.md` with the alternatives rejected.
- No multi-cloud. Cloud-specific code stays inside modules; a second cloud is a new module later, not a refactor now.
- No picker UI before the modules are proven. The manifest is the picker.
- Generated apps are flat by default and carry no platform files (docs/adr/0004-flat-apps.md); their record lives in `apps/<app>/` here. Never hand-edit a record's `platform.lock.yaml`; change the manifest or the platform and regenerate. `--layout modular` is for platform work only, never for an app someone else will see.

## Decisions
Decided 2026-10-16 (each in the owning module's `ADR.md`; the baseline in `docs/adr/0002-hosting-baseline.md`): own AWS account, us-east-1, one environment · free tier hosts multi-role apps · identity abstracts Cognito and Supabase Auth, invite-only by default · kids get guardian-issued restricted logins · tenancy levels fixed per app · FastAPI on Lambda behind API Gateway · Aurora Serverless v2 · bare React Native.

Decided 2026-10-17 (`profiles` ADR 0003, `tenancy` ADR 0004, `notifications` ADR 0003): under 18 only a guardian creates a kid's profile and login · no conversation that includes a minor is one-to-one; a kid's guardians are in every group the kid is in; kids read but don't post, to start · kid sign-in by pairing code, the guardian's phone, or a teen's own email · team staff must be cleared adults.

Still open: offline conflict policy (`offline-sync`) · Stripe Connect type (`payments`) · Copier vs custom scaffolder (`docs/adr/0001-scaffolder.md`) · passkeys on Supabase Auth (`identity`).

## Authorization pattern (both tiers)
Who may see what is decided in Postgres: tenancy and consent checks are SQL functions. On AWS the API calls them; on the free tier row-level-security policies call them. Every route or policy that serves a person's data ships boundary tests in the same change: who must get in, and every party who must not, against a real Postgres.
