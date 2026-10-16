# ADR 0001 · Scaffolder: Copier, custom, or Copier wrapped by the CLI

- Status: **proposed** (decide before extraction step 5)
- Date: 2026-10-16
- Owner: platform

## Context
`platform new` must turn a manifest into an app and, for `drift: platform-owned` modules, push later changes into apps already generated. Today `new` is a plain copy of each module's `app/`, `infra/` and `migrations/` plus a lock file; there is no update path yet.

## Options
| Option | Pros | Cons |
| --- | --- | --- |
| **Copier** (`copier.yml` questions ← generated from `platform.yaml`; `copier update` pushes template changes) | update path exists and is battle-tested; answers file is effectively the manifest | Jinja templating inside module code; per-module templates need a convention for optional dependencies |
| **Custom** (keep the current copy + lock, write our own three-way merge for updates) | total control; no templating language in module code | we own a merge tool nobody else maintains |
| **Copier wrapped by the CLI** (CLI validates, resolves, writes the answers file, calls Copier) | validation stays ours, updates stay Copier's | two tools to keep in step |

## Leaning
Copier wrapped by the CLI. The validator is the part worth owning; the update mechanism is not.

## Decision
_Pending. Record here with the alternatives rejected._
