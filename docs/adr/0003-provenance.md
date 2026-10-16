# ADR 0003 · What may come into this repo from AveHealthRepo

- Status: **accepted**
- Date: 2026-10-16
- Owner: platform

## Context
Modules are extracted from AveHealthRepo. That repository's own rule (owner, 2026-10-06) is that code leaves it in working order and nothing else does: not its documents, not its Markdown, and not the notes written inside its code. Its comments carry decisions, to-do ids, risk analysis and paths into its `docs/`.

## Decision
- **Code** comes over through AveHealthRepo's stripper, never copied by hand with its comments:
  ```bash
  # from a clone of AveHealthRepo
  d=$(mktemp -d); mkdir -p "$d/$(dirname "$f")"; cp "$f" "$d/$f"
  tools/company-publish/.venv/bin/python tools/company-publish/strip_notes.py "$d"
  ```
  The stripped file is then generalized here (names, config, interfaces) and re-commented for this repo's own purposes.
- **No notes** come over: no AveHealth to-do ids, decision ids, risk ids, account numbers, runbook paths or document text. Module ADRs here record stack choices and the reason for them in this repo's own words.
- **Nothing goes back** to AveHealthRepo from here without the owner's explicit yes per change. A back-port of `identity`, `profiles` or `tenancy` changes sign-in and who sees what, which AveHealthRepo treats as a security change that stops for the owner's approval first.
- **Never** push anything from here to the company's copy of AveHealth. Its only writer is AveHealthRepo's own publish.

## Alternatives rejected
- Copying files with comments and cleaning up later: whatever reaches a remote stays in its history.
- Forking AveHealthRepo as the platform's starting point: would carry its whole history and documents.
