# platform

A personal platform-scaffolding repo: reusable **modules** (identity, profiles, tenancy, consent, notifications, infra, shells…), named **presets** that compose them, and a one-file **manifest** per app that says which to use. `platform new` turns a manifest into a deployable app on AWS (or the free tier).

The modules are extracted from two real apps — AveHealth (an RPM provider/patient app) and a softball team/league app — and only what both need unchanged becomes a module. The contract that governs all of it is [`docs/CONTRACT.md`](docs/CONTRACT.md).

## Status

Extraction step 1 is built: `infra-aws` and `ci-cd` are `incubating` and `examples/shell` generates and synthesizes. Every other module carries its contract (`module.yaml`, `CLAUDE.md`, `ADR.md`) and is `status: planned`; `platform new` refuses any manifest that selects one, and that refusal list is the extraction to-do list.

## Layout

```
platform.yaml            ← (in each app) the manifest: preset + hosting + remove/add + config
modules/<name>/          ← one folder per module
  module.yaml            ← declaration: layer, status, drift, hosting, provides, requires, optional, config
  CLAUDE.md              ← agent-facing contract: wiring, invariants, how to extend
  ADR.md                 ← decisions and rejected alternatives (replaces "best X" branches)
  infra/  app/  migrations/  tests/
presets/<name>.yaml      ← named module compositions: aws-foundation, aws-app, free-app, rpm-app, team-app
schemas/                 ← JSON Schemas for module.yaml, presets and the manifest
apps/<app>/              ← private record of each generated app (manifest + lock)
examples/<app>/          ← example manifests: shell (aws-foundation), avehealth (rpm-app), softball (team-app), league-lite and tracker (free-app)
templates/app/infra/     ← the CDK composer copied into every generated aws-tier app
templates/module/        ← copy this to start a new module
docs/CONTRACT.md         ← the module contract and the module list; source of truth
docs/adr/                ← platform-level decisions
platform_cli/            ← the `platform` command
```

## Quickstart

```bash
pip install -e ".[dev]"

platform list modules                               # every module, by layer
platform list interfaces                            # every interface and who provides it
platform validate examples/softball/platform.yaml   # the five rules, enforced
platform plan     examples/softball/platform.yaml   # resolved modules + effective config
platform new      examples/softball/platform.yaml ../softball   # refuses while modules are planned
pytest
```

## Deploying an app (aws tier)

```bash
platform new examples/shell/platform.yaml ../shell    # any manifest whose modules are implemented
cd ../shell/infra
pip install -r requirements.txt && npm install -g aws-cdk
cdk bootstrap                                         # once per account and region
cdk deploy --all
```

Apps are **flat** by default: ordinary folders (`api/`, `web/`, `mobile/`, `migrations/`, `infra/`, `ci/`) and no platform files, so they read like any hand-built app. The record of what was generated goes to `apps/<app>/` in this repo (`--record-dir` to change it). `--layout modular` keeps the module layout for platform work. See docs/adr/0004-flat-apps.md.

`examples/shell` is the empty shell from extraction step 1: the AWS foundation with a placeholder API that answers `/healthz`. It is throwaway (`deletion_protection: false`), so `cdk destroy --all` removes it.

## The manifest

```yaml
app: softball
preset: team-app          # aws-app | free-app | rpm-app | team-app
hosting: aws              # aws | free
modules:
  remove: [content]       # drop a preset module — dependents fail loudly, never silently
  add: []                 # add any module from modules/
config:
  profiles.managed: true  # <module>.<key>; keys are validated against each module's schema
  tenancy.levels: [league, team]
environments: [dev, prod]
```

## The five rules

1. **Removable** — every `requires` is provided by a selected module, or validation names the gap.
2. **Owns its data** — a module writes only its own tables; others go through interfaces.
3. **Interfaces, not names** — dependencies are `domain.name@major` strings; the manifest picks the provider.
4. **Layering is one-way** — domain → capability → foundation. `requires` may not point up; `optional` may.
5. **Two-app rule** — a module is `stable` only once two apps use it unchanged.

## Next

Extraction order and the open ADRs are in `docs/CONTRACT.md`. Step 1 is `infra-aws` + `ci-cd`, proven by deploying an empty shell from a fresh clone.
