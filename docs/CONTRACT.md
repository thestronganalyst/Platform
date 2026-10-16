<!-- Exported from the living doc: https://claude.ai/code/artifact/3cd34991-50e7-4d5a-a1e0-ae6ebf1aee2b
     The doc is the editing surface; re-export here when it changes. Last export: 2026-10-16 (doc rev 13). -->

# Platform Module Contract & Module List

Oct 16, 2026 · @thestronganalyst

## Purpose

This page is the contract every module in the platform repo must meet, plus the first module list drawn from two real apps: AveHealth and the softball team app. Everything else in the platform (presets, the manifest, the scaffolder) is derived from these two things, so they are decided first and changed deliberately.

It is not a product spec for either app. Domain features (watch ingestion, scorekeeping, stats) stay in their apps; only the connective tissue both apps share becomes a module.

## Module contract

A module is one folder under `modules/<name>/` that can be added to or removed from an app by changing one line in the manifest. Every module folder contains the same eight things; a folder missing any of them is not a module yet.

| Item | What it holds | Why it exists |
| --- | --- | --- |
| `module.yaml` | Declaration: `name`, `version`, `layer`, `provides`, `requires`, `optional`, `config` schema with defaults, `hosting` tiers supported (`aws`, `free`), `platforms` it ships code into (`web`, `mobile`, `api`), `drift` policy, `status` | The scaffolder and the manifest validator read only this file |
| `infra/` | CDK construct for the `aws` tier; Supabase config and SQL for the `free` tier | Infra travels with the capability, not in a separate repo |
| `migrations/` | The database tables this module owns | A module owns its data; nothing else writes those tables |
| `app/web`, `app/mobile`, `app/api` | Code templates per platform it supports | Only the platforms listed in `module.yaml` |
| `CLAUDE.md` | Agent-facing contract: what it exposes, how to wire it to its `requires`, invariants not to break, how to extend it | This is what lets Claude Code compose and customize modules without you reading the code |
| `ADR.md` | Decisions made and alternatives rejected, dated | Replaces "best X" branches; experiments end here |
| `tests/` | Contract tests proving each `provides` interface works and each `requires` is actually used | A module that passes these is safe to update under a generated app |
| `README.md` | One paragraph for a human: what it is, when to pick it | Short on purpose |

`provides` and `requires` are named, versioned interface strings (`identity.session@1`, `tenancy.scope@1`), never module names. Modules depend on interfaces, so `identity` can be swapped for a different implementation without touching anything that uses it.

The `drift` field has two values. `platform-owned` means the platform keeps the module current and `copier update` pushes changes into generated apps; the app is expected not to edit it. `forked` means the module is copied once at generate time and the app owns it from then on, with no updates pushed. Shells (web, mobile) are usually forked; plumbing (identity, notifications, infra) is usually platform-owned.

## Rules

Five rules, enforced by the manifest validator and the contract tests, not by discipline.

1. **Removable.** Deleting a module from the manifest must leave a buildable, deployable app. If other modules require it, generation fails loudly and names them; it never silently breaks.
2. **Owns its data.** A module reads and writes only its own tables. Cross-module data access goes through a provided interface, never a shared query.
3. **Interfaces, not names.** `requires` lists interfaces, never module names. Two modules may provide the same interface (Cognito and Supabase Auth both provide `identity.session@1`); the manifest picks one.
4. **Layering is one-way.** Domain depends on capability depends on foundation. A foundation module that requires a capability interface is refused; it may list one as optional, because a shell must work with no identity present and gain role-aware behavior only when identity is selected.
5. **Two-app rule.** A module is `incubating` until two apps use it unchanged; only then is it `stable` and eligible for `platform-owned` drift. An incubating module lives inside the app that needs it, in the module folder layout, so promotion is a move, not a rewrite.

## Layers

```
  Domain       stays in each app, never in a preset
               AveHealth: device-ingestion · health-dashboards · rpm-workflows
               Softball:  roster · lineup · schedule · scorekeeping · stats · fundraising
                 │ depends on
                 ▼
  Capability   opt-in, generic, the payoff of the platform
               identity · [profiles] · [tenancy] · consent-sharing · notifications · storage
               mobile-shell · analytics-landing · (offline-sync) · (booking) · (payments) · (shared-lists) · (content)
                 │ depends on
                 ▼
  Foundation   every app; only the hosting tier changes
               infra-aws · infra-free · ci-cd · api-shell · web-shell · observability

  [brackets] = redesigned for softball, back-ported   (parens) = incubating in softball
```

A module may depend on the layer below it and never on the one above; the validator refuses the reverse. The two accented modules are the ones softball forces a redesign of, and the dashed ones are built inside softball first and promoted only when a second app wants them.

## Foundation modules

Every app gets these. The only choice is the hosting tier, which swaps `infra-aws` for `infra-free`; everything above it stays the same.

| Module | Provides | Requires | Source app | Drift | Status |
| --- | --- | --- | --- | --- | --- |
| `infra-aws` | `infra.network`, `infra.db.postgres`, `infra.container`, `infra.cdn`, `infra.secrets` | none | AveHealth | platform-owned | extract first |
| `infra-free` | `infra.db.postgres` (Supabase), `infra.static-host` (GitHub Pages) | none | project-tracker | platform-owned | later |
| `ci-cd` | `ci.pipeline` (build, test, deploy per environment) | `infra.*` | AveHealth + project-tracker | platform-owned | extract first |
| `api-shell` | `api.router`, `api.auth-middleware`, `api.errors` | `infra.db.postgres`, `infra.container`; optional `identity.session` | AveHealth | platform-owned | extract |
| `web-shell` | `web.shell`, `web.route-registry`, `web.role-nav`, `web.theme` | optional `identity.session` | AveHealth | forked | extract |
| `observability` | `obs.logs`, `obs.errors`, `obs.audit` | `infra.*` | AveHealth | platform-owned | extract |

Open question: confirm the API framework and database AveHealth actually runs on today; the module boundaries above don't depend on the answer, but the extraction order does.

## Capability modules

Opt-in, generic, and the real payoff of the platform. The first four are the ones both apps need and the ones most apps get wrong; they are extracted from AveHealth but redesigned against softball's harder requirements (managed profiles, deep tenancy) and back-ported.

| Module | Provides | Requires | Source | Drift | Status |
| --- | --- | --- | --- | --- | --- |
| `identity` | `identity.user`, `identity.session`, `identity.roles` (Cognito on `aws`, Supabase Auth on `free`) | `infra.*` | AveHealth | platform-owned | extract |
| `profiles` | `profiles.person`, `profiles.guardian` (managed profiles: a person record that is not a login — kids under 13, dependents, caregivers' charges) | `identity.user` | redesign for softball, back-port to AveHealth | platform-owned | redesign |
| `tenancy` | `tenancy.org`, `tenancy.hierarchy` (league → team; practice → panel), `tenancy.membership`, `tenancy.scope` | `identity.user`, `profiles.person` | defined by softball | platform-owned | redesign |
| `consent-sharing` | `consent.grant`, `consent.check`, `consent.revoke` (who may see what about whom, scoped, audited) | `profiles.*`, `tenancy.scope`, `obs.audit` | AveHealth | platform-owned | extract |
| `notifications` | `notify.send` (email, push, SMS), `notify.templates`, `notify.preferences`, `notify.digest` | `identity.user`, `infra.*` | AveHealth | platform-owned | extract |
| `storage` | `storage.object` (upload, signed URLs, per-tenant prefixes) | `infra.*`, `tenancy.scope` | AveHealth | platform-owned | extract |
| `mobile-shell` | `mobile.shell` (Expo app, auth, navigation, push registration) | `identity.session`, `notify.send` | AveHealth | forked | extract |
| `analytics-landing` | `analytics.emit` (events → S3 / Databricks landing) | `infra.*` | AveHealth | platform-owned | optional |
| `offline-sync` | `sync.store` (local store, queued writes, conflict policy) | `api.router` | softball | platform-owned | incubating |
| `booking` | `booking.resource`, `booking.availability`, `booking.reservation`, `booking.approval` (fields now; provider appointments later) | `tenancy.*`, `notify.send` | softball | platform-owned | incubating |
| `payments` | `payments.account` (Stripe Connect per org), `payments.charge`, `payments.payout`, `payments.receipt` | `tenancy.org`, `identity.user` | softball | platform-owned | incubating |
| `shared-lists` | `lists.list`, `lists.item`, `lists.claim` (sign-ups, who brings what) | `tenancy.scope`, `notify.send` | softball | platform-owned | incubating |
| `content` | `content.page`, `content.media` with role-scoped visibility (instruction, how-tos) | `storage.object`, `tenancy.scope` | softball | forked | incubating |

Two of the incubating modules are likely to flow back to AveHealth once stable: `booking` is the same shape as provider appointment scheduling, and `payments` is the same shape as RPM billing.

## Domain modules (stay in the app)

These use the module folder layout so they can be promoted later, but they are not in the platform repo and no preset includes them. If a third app wants one, that's the signal to promote it.

| App | Domain module | Built on |
| --- | --- | --- |
| AveHealth | `device-ingestion` (HealthKit, watch, smart scale) | `profiles`, `consent-sharing`, `storage`, `analytics-landing` |
| AveHealth | `health-dashboards` (provider and patient views) | `web-shell`, `consent-sharing` |
| AveHealth | `rpm-workflows` (monitoring, alerts, review) | `notifications`, `tenancy` |
| Softball | `roster` and `lineup` (the existing lineup engine moves here) | `profiles`, `tenancy` |
| Softball | `schedule` (games, practices) | `booking`, `notifications` |
| Softball | `scorekeeping` (event log per game, at the field) | `offline-sync`, `tenancy` |
| Softball | `stats` (derived from the scorekeeping event log, never entered by hand) | `scorekeeping` |
| Softball | `fundraising` (campaigns, goals, donor pages) | `payments`, `content` |

## Presets

A preset is a named list of modules plus default config. Four cover everything you build today; two are bases and two are apps.

| Preset | Builds on | Adds | Use it for |
| --- | --- | --- | --- |
| `aws-app` | — | `infra-aws`, `ci-cd`, `api-shell`, `web-shell`, `observability`, `identity`, `profiles`, `tenancy`, `consent-sharing`, `notifications`, `storage` | Any multi-role app on your AWS account |
| `free-app` | — | `infra-free`, `ci-cd`, `web-shell`, `identity`, `profiles`, `notifications` (email only) | Small tools on GitHub Pages + Supabase, like project-tracker |
| `rpm-app` | `aws-app` | `mobile-shell`, `analytics-landing` | AveHealth-shaped apps |
| `team-app` | `aws-app` | `mobile-shell`, `booking`, `payments`, `shared-lists`, `content`, `offline-sync` | Softball and any team or league app |

Presets never contain domain modules. Generating `team-app` gives you login, leagues and teams, parents and managed kid profiles, notifications, field booking and payments wired and deployable, with no softball in it yet.

## Manifest

One file per app, `platform.yaml`, at the repo root. It is the only input to the scaffolder and the only thing the CDK stack reads to decide what to deploy. Copier's answers file is generated from it, not the other way around.

```yaml
app: softball
preset: team-app
hosting: aws            # aws | free
modules:
  remove: [content]     # drop a preset module
  add: []               # add any stable module
config:
  identity.providers: [email, google, apple]
  profiles.managed: true          # kids are guardian-owned profiles, never logins
  tenancy.levels: [league, team]
  notifications.channels: [email, push]
  payments.connect_type: express  # pending ADR
environments: [dev, prod]
```

Validation runs before generation: every `requires` of every selected module must be provided by another selected module, every `config` key must exist in some module's schema, and every selected module must support the chosen `hosting` tier. Any failure names the module and the missing interface.

## Extraction order from AveHealth

Extract in dependency order, prove each step by deploying, and stop early. The point of stopping is to get softball generated from the preset as soon as the foundation holds; everything after that incubates inside softball.

1. `infra-aws` + `ci-cd` — prove it by deploying an empty shell to your AWS account from a fresh clone.
2. `identity`, then `profiles` (redesigned for managed profiles), then `tenancy` (designed against softball's league → team → player shape). Back-port all three into AveHealth before moving on; if AveHealth breaks, the boundaries are wrong.
3. `consent-sharing`, `notifications`, `storage`.
4. `api-shell`, `web-shell`, `observability`.
5. Stop. Write the `aws-app` and `team-app` presets, run `platform new`, and generate softball. `mobile-shell`, `booking`, `payments`, `shared-lists`, `offline-sync` and `content` are built inside softball as incubating modules and promoted only when a second app wants them.

`infra-free` and the `free-app` preset come after softball ships, extracted from project-tracker.

## Open decisions (ADRs to write)

Each of these ends as a dated entry in the owning module's `ADR.md`, with the alternatives rejected. None blocks step 1 of extraction; the first three block step 2.

| Decision | Owning module | Options on the table | Blocks |
| --- | --- | --- | --- |
| Identity provider per tier: one abstraction over Cognito and Supabase Auth, or pick one and drop the `free` tier for multi-role apps | `identity` | abstract both · Cognito only · Supabase Auth only | step 2 |
| Managed-profile model: is a kid a profile with zero login, or a restricted login under a guardian? COPPA applies under 13 | `profiles` | profile-only · restricted login · both, by age | step 2 |
| Tenancy depth: fixed levels per app (league → team) or arbitrary nesting | `tenancy` | fixed per app via config · arbitrary tree | step 2 |
| API framework and ORM: keep whatever AveHealth runs, or standardize | `api-shell` | keep · standardize | step 4 |
| Container runtime: App Runner vs ECS Fargate | `infra-aws` | App Runner (simpler) · Fargate (more control) | step 1 |
| Offline conflict policy for scorekeeping | `offline-sync` | last-write-wins · append-only event log (likely) | softball |
| Stripe Connect account type | `payments` | Express · Standard · Custom | softball |
| Scaffolder: Copier vs a thin custom CLI reading `platform.yaml` directly | platform | Copier · custom · Copier wrapped by a CLI | step 5 |

## Definition of v1 done

v1 is done when `platform new --preset team-app --without content` on a fresh machine produces an app on your AWS account, deployed and reachable, with working login, a league → team → parent → managed-kid structure, and a test notification delivered, in under one hour of wall-clock time.

Time-box: two weekends for extraction steps 1 and 2. If step 2 isn't back-ported into AveHealth by then, stop, write down which boundary fought you, and redraw it before touching step 3. Missing the time-box is information, not failure; ignoring it is how these repos end up as a third thing to maintain instead of a tool that removes work.

- [ ] Step 1 deployed from a fresh clone
- [ ] Step 2 back-ported into AveHealth without breaking it
- [ ] Steps 3–4 extracted
- [ ] `aws-app` and `team-app` presets written
- [ ] Softball generated from `team-app` and deployed
- [ ] Under one hour, measured
