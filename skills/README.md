# skills

Shared Claude Code skills for the Zebora pipeline. Each skill is a directory
containing a `SKILL.md` with YAML frontmatter (`name`, `description`) followed
by the skill body (phases, queries, guardrails).

Skills that were previously local-only (`~/.claude/skills/…` on each machine)
live here so they are versioned, reviewed via PR, and shared across the team.

## Layout

```
skills/
  <skill-name>/
    SKILL.md        # frontmatter (name, description) + body
```

## Installing

Skills are loaded by Claude Code from `~/.claude/skills/`. Symlink (preferred —
updates with a `git pull`) or copy each skill directory:

```sh
# from the consuming machine, with zebora-standards checked out / submoduled
ln -s "$PWD/skills/zebora-scoring-url" ~/.claude/skills/zebora-scoring-url
```

Invoke with `/<skill-name> <args>` in Claude Code.

## Conventions

- One skill per directory; the directory name matches the frontmatter `name`.
- `description` must carry trigger keywords so the skill auto-suggests correctly.
- QA/analysis skills are **reporting-only by default** — no data-quality writes
  without explicit user confirmation; state permitted side effects (e.g. matview
  refreshes, workflow dispatches) explicitly in the body's guardrails.
- Keep DB object names, function signatures and access notes accurate to the
  live schema; call out auth-gated functions and known-inflated rollups.

## Skills

| Skill | Purpose |
|---|---|
| `zebora-scoring-url` | Citation/URL Checker (UCC) — reporting-only QA for the URL scoring pipeline (completeness, cross-path reconciliation, suspect domains, duplication, classification coverage, learned-baseline drift). |

Other pipeline skills (`zebora-scoring-vec`, `zebora-ops`, `zebora-batch-report`, …)
can be migrated here in follow-up PRs.
