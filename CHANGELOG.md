# Changelog

All notable changes to `zebora-standards` are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org).

## [Unreleased]

### Added

- **`skills/zebora-batch-release`** (draft v0.4) — monthly batch release runbook: one ordered,
  gated process from weekly pool capture to go-live and the monthly report email, written from the
  September 2026 releases. Lists the gaps to close before it can be automated.

### Changed

- **`skills/zebora-scoring-vec` Phase 4** — replaced alias-writing resolution with a
  batch canonicaliser (`scripts/canonicalise_batch.py` + `scripts/vec_titles.py`). It
  rewrites the batch's stored `scores_visibility.entities[*].entity` / `.brand` to the
  confirmed game (exact name → alias → unique cleaned title), keeps the original wording
  in `raw_entity` / `raw_brand` with a `canonicalised` note, and groups unmatched
  variants. No aliases, no new rows, no schema change; dry run by default. Aliases are
  now reserved for verified judgement calls (edition/family roll-ups). Warns against
  running `entity_resolution_v3` in write mode (row explosion + shift-by-one aliases).
- **`skills/zebora-scoring-vec` Phase 1b / 7** — refresh with per-batch
  `refresh_entity_metrics_v2`; never `refresh_entity_metrics_matviews.py` /
  `refresh_url_scores_v1` without go-ahead (they lock the live dashboard).

## [1.2.1] - 2026-08-10

### Changed

- **`skills/zebora-scoring-vec`** — synced to the canonical phase-gated, 10-phase
  version (from `brand-score-pipeline`). The v1.2.0 migration inadvertently used
  an older 9-phase snapshot from machine-local `~/.claude/skills/`.

## [1.2.0] - 2026-08-10

### Added

- **`skills/` directory** — shared Claude Code skills, versioned and reviewed via
  PR instead of living local-only in each machine's `~/.claude/skills/`. See
  `skills/README.md` for layout, install (symlink), and conventions
  (reporting-only by default; declare side effects; keep schema refs accurate).
- **`skills/zebora-scoring-url`** — Citation/URL Checker (UCC): reporting-only QA
  for the URL scoring pipeline (active-scope completeness, cross-path
  reconciliation, suspect-domain hunt, duplication, classification coverage,
  learned-baseline drift).
- **`skills/zebora-scoring-vec`** — Visibility Entity Checker (VEC): interactive
  QA for the visibility scoring pipeline (refresh, QA triage, entity review,
  resolution & canonicalization, enrichment, feedback loop). Migrated from
  machine-local `~/.claude/skills/`.

## [1.1.0] - 2026-07-21

### Added

- **Changelog convention** in `general/conventions.md` — every repo keeps a
  root `CHANGELOG.md` (Keep a Changelog + SemVer); log meaningful completed/
  shipped changes. Per-repo CHANGELOGs feed the org-wide production roll-up in
  the ops vault (`zebora-ops/Changelog.md`).

## [1.0.0] - 2026-06-18

### Added

- General conventions (`general/conventions.md`): repo structure, secrets,
  agent context, code style, naming, testing, dependencies, error handling, docs.
- Stack conventions: `python/`, `prefect/` (extends python), `frontend/`.
- Submodule consumption model (`.standards` pinned to a tag; `@.standards/...`
  imports in CLAUDE.md; explicit-read preamble for AGENTS.md / Codex).

## [0.1.0] - 2026-06-18

### Added

- Initial repository scaffold and structure.
