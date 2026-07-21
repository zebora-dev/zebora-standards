# Changelog

All notable changes to `zebora-standards` are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org).

## [Unreleased]

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
