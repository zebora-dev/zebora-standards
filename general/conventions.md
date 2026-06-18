# Zebora — General Conventions

Applies to every repo at zebora.io. Stack-specific files in sibling directories
add to these rules; they never override them.

---

## Repository structure

- Each repo has a `CLAUDE.md` (canonical) and `AGENTS.md` symlinked to it or
  containing an explicit "read X" preamble for Codex compatibility.
- `.standards/` is a git submodule pointing at `zebora-standards` at a pinned
  tag. Never copy-paste content from it directly.
- `.mcp.json` (project-scoped) holds MCP server config with `${VAR}` expansion
  for any credentials. Never commit real secrets.
- A gitignored `.env` supplies credential values locally.

## Secrets and credentials

- No API keys, tokens, or passwords in any committed file — ever.
- Use `${ENV_VAR_NAME}` placeholders in `.mcp.json` and resolve via shell env.
- OAuth-authenticated MCP servers use Claude Code's built-in browser flow
  (`claude mcp auth <server>`), not hand-rolled token handling.
- `.env` must be in `.gitignore` of every repo.

## Agent context (CLAUDE.md / AGENTS.md)

- Import standards via `@.standards/...` (Claude Code) or explicit "read this
  file" instruction (Codex / AGENTS.md). Never duplicate the content.
- Keep repo-specific CLAUDE.md additions minimal: project purpose (1–2 lines),
  local dev commands, links to relevant `.mcp.json` vars.

## Code style

- Match the language and style already present in the repo. Don't introduce new
  patterns without discussing them first.
- Prefer explicit over implicit: clear variable names, typed function
  signatures, no magic globals.
- Functions do one thing. If a function needs a comment to explain what it does,
  split or rename it.
- No commented-out code committed. Use git to track history.
- Keep diffs small and reviewable; one logical change per commit.

## Naming

| Thing | Convention |
|---|---|
| Python files / modules | `snake_case` |
| Python classes | `PascalCase` |
| Python functions / vars | `snake_case` |
| TypeScript files | `kebab-case.ts` or `PascalCase.tsx` for React components |
| TypeScript types/interfaces | `PascalCase` |
| Environment variables | `SCREAMING_SNAKE_CASE` |
| Git branches | `type/short-description` (e.g. `feat/add-attio-sync`) |
| Git tags | `vMAJOR.MINOR.PATCH` (semver) |

## Testing

- Tests live in a `tests/` directory at the repo root (or co-located for
  frontend components: `ComponentName.test.tsx`).
- New behaviour ships with at least one test. Bug fixes include a regression
  test.
- Don't mock external services unless the service has no test mode — prefer a
  real integration test against a sandbox/staging instance.

## Dependency management

- Python: `pyproject.toml` + `uv` (or `poetry` if the repo already uses it —
  don't mix). Pin direct dependencies; let the lock file pin transitive ones.
- Node/frontend: `package.json` + `pnpm`. Commit `pnpm-lock.yaml`.
- Don't add a dependency if the stdlib or an already-present package covers it.

## Error handling

- Errors surface early. Don't silently swallow exceptions.
- Log enough context to diagnose: what was being attempted, what the error was.
- Use structured logging (JSON or key=value) in services; plain text is fine for
  scripts.

## Documentation

- Write no comments for obvious code. Write a comment only when the WHY is
  non-obvious (hidden constraint, workaround for a specific bug, subtle
  invariant).
- README covers: what the service does, how to run it locally, required env
  vars.
