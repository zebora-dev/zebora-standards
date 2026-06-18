# Zebora — Python Conventions

Extends `general/conventions.md`. Applies to all Python repos.

Two Python repos at Zebora:

| Repo | Stack notes |
|---|---|
| `prompt-extractor` | Python 3.12+, uv, pyproject.toml, ruff, pytest |
| `brand-score-pipeline` | Python 3.13+, poetry, pyproject.toml, ruff + black + isort, pytest |

Both share the conventions below. Where tooling differs it is called out
explicitly.

---

## Python version

- Minimum Python 3.12 (`prompt-extractor`), 3.13 (`brand-score-pipeline`).
- Use `pyproject.toml` `requires-python` to pin the floor.
- Don't use deprecated stdlib APIs; enable `ruff` `UP` rules to catch them.

## Dependency management

| Repo | Tool |
|---|---|
| `prompt-extractor` | `uv` — `pyproject.toml` + `uv.lock` |
| `brand-score-pipeline` | `poetry` — `pyproject.toml` + `poetry.lock` |

Don't mix tools within a repo. Commit the lock file. Pin direct dependencies
with `>=X.Y,<NEXT_MAJOR`; let the lock file pin transitive deps.

## Linting and formatting

Both repos use `ruff` as the primary linter. Additional tools where already
present:

| Tool | Repos |
|---|---|
| `ruff` (lint + format) | both |
| `black` | brand-score-pipeline (formatter, consistent with ruff) |
| `isort` | brand-score-pipeline |
| `mypy` | both — `strict_optional`, `no_implicit_optional` |
| `bandit` | both — security linting |
| `pre-commit` | both — run hooks before commit |

Line length: 88 (`brand-score-pipeline` / black default), 120
(`prompt-extractor` / ruff config). Match the existing config in each repo.

## Type annotations

- Annotate all function signatures (params + return type). `mypy` must pass
  clean.
- Use `from __future__ import annotations` at the top of files targeting
  Python 3.12 to enable deferred evaluation of annotations.
- Prefer `X | None` over `Optional[X]` (Python 3.10+ union syntax).
- `Any` is banned except at genuine external-data boundaries; add a comment
  explaining why.

## Project structure

```
<package_name>/       # importable package (snake_case)
  __init__.py
  <module>.py
tests/                # pytest test suite
  test_<module>.py
pyproject.toml
.env.example
```

For repos with a FastAPI app (`brand-score-pipeline`):

```
api/                  # FastAPI routers and dependencies
  routers/
  dependencies.py
  main.py
config/               # pydantic Settings models
db/                   # SQLAlchemy models and session management
```

## FastAPI (brand-score-pipeline)

- Settings via pydantic `BaseSettings` in `config/` — never `os.environ` inside
  route handlers.
- Rate limiting via `slowapi`; add to any public-facing endpoint.
- Observability: Sentry SDK (`sentry-sdk[asyncio,sqlalchemy]`) + Langfuse for
  LLM traces.
- OpenAPI schema generated via `@asteasolutions/zod-to-openapi` equivalent on
  the Python side — keep route docstrings accurate.
- Validate all request bodies with Pydantic models. Return typed response models.

## External APIs and LLMs

- OpenAI / Anthropic calls always go through `brand-score-pipeline`'s abstraction
  layer — no naked `openai.chat.completions.create` calls outside `ai/`.
- Log LLM calls to Langfuse for cost tracking and debugging.
- Retry transient API errors (rate limits, 5xx) with exponential backoff.

## Testing

- pytest, collected from `tests/` (or `test/` in brand-score-pipeline —
  follow existing layout).
- Use `pytest-asyncio` for async tests.
- Use `pytest-mock` for mocking; avoid `unittest.mock` directly.
- Aim for integration tests over unit tests for API routes — spin up a test DB
  or use a sandbox API rather than mocking the ORM.
- `pytest-cov` reports coverage; don't decrease coverage on a PR.

## Environment variables

- All config via environment variables. Define them in `pyproject.toml`'s
  `[tool.pytest.ini_options]` for test overrides.
- `.env.example` documents every required var with a description and a safe
  placeholder value.
- Load with `python-dotenv` (`load_dotenv()`) at the entrypoint only —
  not deep inside modules.
- Pydantic `BaseSettings` is preferred for structured config in FastAPI apps.

## Local dev

```sh
# prompt-extractor
uv sync
python -m pytest

# brand-score-pipeline
poetry install
poetry run pytest
poetry run uvicorn api.main:app --reload
```
