# zebora-standards

Org-wide architectural and coding conventions for Zebora (zebora.io).

## Structure

```
general/          # Conventions that apply to every repo
  conventions.md
prefect/          # Prefect orchestration conventions
  conventions.md
frontend/         # Frontend conventions (framework, styling, state, API)
  conventions.md
```

## Consuming this repo

Add as a git submodule (pinned to a tag) in any consuming repo:

```sh
git submodule add https://github.com/zebora/zebora-standards .standards
git -C .standards checkout v1.0.0
```

Then in your repo's `CLAUDE.md`:

```md
@.standards/general/conventions.md
@.standards/<stack>/conventions.md
```

For Codex / AGENTS.md (which does not expand `@imports`), add an explicit
instruction at the top of `AGENTS.md`:

```md
Before doing anything else, read:
- .standards/general/conventions.md
- .standards/prefect/conventions.md   # (or frontend/, etc.)
```

## Updating a consuming repo to a new standards version

```sh
cd .standards
git fetch --tags
git checkout v1.1.0
cd ..
git add .standards
git commit -m "chore: bump zebora-standards to v1.1.0"
```

## Releasing a new version

Tag from the `main` branch:

```sh
git tag v1.0.0
git push origin main --tags
```
