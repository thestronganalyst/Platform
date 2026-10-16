# ADR 0004 · Generated apps are flat: they don't reveal the platform

- Status: **accepted**
- Date: 2026-10-16
- Owner: platform

## Context
The owner keeps the platform private. Module code will reach apps other people see, AveHealth's company copy above all. That copy is published from AveHealthRepo with documents and comments stripped, but YAML and Python pass through. A modular app (its `platform.yaml`, `platform.lock.yaml`, `module.yaml` files, contracts and a composer full of platform vocabulary) would show anyone reading it that a module system sits behind the app.

## Decision
- `platform new` writes a **flat** app by default: module code in ordinary folders (`api/<pkg>/`, `web/<pkg>/`, `mobile/<pkg>/`, `migrations/<pkg>/`, `infra/<pkg>/`, `ci/`), a plain CDK entry (`infra/app.py`, `infra/compose.py`, `infra/settings.json`), and no manifest, lock, `module.yaml`, `CLAUDE.md` or `ADR.md`.
- The record of what was generated (manifest + lock) goes to `apps/<app>/` **in this repo**, which stays private.
- `--layout modular` keeps the old module layout for platform work only.
- Code under a module's `app/` and `migrations/` is what ships into apps, so it is plain code: ordinary imports, no contract strings (`identity.session@1`), no platform words, no module names. AWS resource tags say `app`, `environment` and `component`, nothing more. `tests/test_validator.py` enforces all of this.

## What still shows
- The module code itself. Back-porting sign-in or tenancy into AveHealth means that code reaches the company copy; what stays private is the concept: the catalog, the contracts, the manifests and the composition rules.
- On AWS-tier apps, the infra wiring uses contract strings inside `infra/` (deploy tooling). AveHealth keeps its own infrastructure and never receives `infra/` from here.

## How AveHealth takes a module
A back-port replaces code in AveHealth's existing layout, by hand or by agent, from the flat output; AveHealth gains no platform files. Each back-port still needs the owner's yes first (it changes sign-in or who sees what).

## Alternatives rejected
- Modular apps everywhere: reveals the platform in every app.
- Stripping platform files at AveHealth's publish: relies on a second repository's tooling to keep this one private.
