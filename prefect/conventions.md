# Zebora — Prefect Conventions

Extends `general/conventions.md`. Applies to all Prefect orchestration repos.

---

## Project layout

```
flows/
  <domain>/
    flow.py          # one Prefect @flow per file
    tasks.py         # @task definitions for that domain
tests/
  <domain>/
    test_flow.py
prefect.yaml         # deployment manifest
pyproject.toml
```

No deeply nested subpackages. If a flow file grows past ~200 lines, extract
tasks into a sibling `tasks.py`.

## Flow / task design

- **One flow, one concern.** Flows orchestrate; tasks do work. Don't put
  business logic directly in `@flow` bodies.
- **Task granularity:** tasks should be independently retriable. A task that
  calls an external API, hits a DB, or does meaningful computation is the right
  size. A task that just calls another task is noise.
- **Parameters over globals.** Pass config (run dates, env flags, thresholds)
  as explicit flow/task parameters. Never read environment variables deep
  inside a task — read them at flow entry and pass down.
- **Return typed values.** Annotate task return types; Prefect uses them for
  result serialisation.

## Retry and caching policy

- Transient-failure tasks (API calls, DB writes) default to `retries=3,
  retry_delay_seconds=60`. Adjust per task if SLA requires it.
- Use `@task(cache_key_fn=task_input_hash, cache_expiration=timedelta(hours=1))`
  for expensive idempotent fetches to avoid redundant work on re-runs.
- Never cache tasks with side effects (writes, sends, mutations).

## Database / materialized views

Layer naming is strict — a view may only depend on views in lower layers:

| Layer | Prefix convention | Examples |
|---|---|---|
| 0 — raw sources | (no prefix; source tables) | `public.entities`, `public.urls` |
| 1 — base metrics | `mv_` | `mv_url_scores`, `mv_entity_metrics` |
| 2 — enriched / joined | `mv_*_enriched` | `mv_url_scores_enriched` |
| 3 — tag / classification | `mv_*_tag_by_*` | `mv_entity_metrics_tag_by_llm_brand_entity` |

Refresh order must respect the layer hierarchy: Layer 1 before Layer 2 before
Layer 3. A Layer-3 view must never be refreshed before the Layer-2 view it
joins against.

**Open item (feed back in when resolved):** confirm whether
`mv_entity_metrics_tag_by_llm_brand_entity` belongs in the Layer-3 refresh
sequence, and whether `mv_url_scores_enriched` v1–v4 are correctly placed at
Layer 1 (or should be Layer 2).

## Deployments

- All deployments defined in `prefect.yaml`; no ad-hoc `flow.deploy()` calls
  in scripts.
- Deployment names follow `<flow-name>/<environment>` (e.g.
  `entity-refresh/production`).
- Schedules declared in `prefect.yaml`, not hard-coded in flow code.
- Use work pools for infrastructure isolation; don't run production and
  staging flows on the same worker pool.

## Secrets in Prefect

- Use Prefect Secret blocks for credentials accessed inside flows, not
  environment variables injected at deploy time (harder to rotate).
- Block names follow `<service>-<environment>` (e.g. `postgres-production`,
  `attio-api-key`).
- Reference blocks in task params, not via `os.environ` deep in task bodies.

## Logging

- Use `get_run_logger()` inside flows and tasks — not the root `logging` module.
- Log at the start and end of each flow with key parameters.
- Log warnings for retried tasks with the exception and retry count.

## Local dev

```sh
uv sync
prefect server start          # local Prefect server
prefect worker start -p local # local work pool
python flows/<domain>/flow.py # trigger a test run
```

Required env vars: see `.env.example` at repo root.
