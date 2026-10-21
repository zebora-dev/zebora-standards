---
name: zebora-onboard-preview-brand
description: "Onboard a new Zebora demo / preview brand end to end, from a prompt sheet to a live dashboard. Steps: create the brand, batch, prompts and weightings; extract via DataForSEO (no workers); build the visibility context; score with the parallel fan-out dispatcher; review with zebora-scoring-train; correct stored entities instead of re-scoring; seed entity dimensions; enrich websites; classify URLs; run the release chain (refresh, summaries, readiness with the preview profile); review summaries; go live. Use when the user says 'new demo brand', 'preview brand', 'run X through the system like TransUnion / Twinkl / Smart Energy GB', or gives a brand + URL + prompt sheet to set up. Encodes which tool to use at each step and the gotchas that cost time on the Twinkl run."
user-invokable: true
argument-hint: "<brand name> <url> <prompt sheet url or file>"
---

# zebora-onboard-preview-brand: demo / preview brand onboarding

**Invocation:** `/zebora-onboard-preview-brand <brand> <url> <prompt sheet>`

Built from the Twinkl onboarding (14 Oct 2026), modelled on TransUnion and Smart Energy GB. That run took far longer than it should have. Each stage was improvised, the wrong tool was used several times, and the steps ran in an order that forced three metric refreshes. This skill fixes the order and names the right tool for every step.

Background:
- Retro: `brand_score_pipeline/docs/refresh/twinkl-onboarding-retro.md`
- Tickets: ZEB-1044 to ZEB-1053, ZEB-1086 (readiness profile)

**This skill orchestrates; it does not replace these skills.** Call them at the marked points:
- `zebora-scoring-train` (accuracy review)
- `zebora-scoring-vec` (entity QA)
- `zebora-scoring-url` (URL QA)
- `zebora-batch-release` (the release chain it shares with pool brands)

## Operating mode

- Run **one phase at a time**, print a short summary, then continue. Stop and ask only at the marked **GATE** points.
- These always need the user:
  - **policy decisions** in the context review (Phase 5)
  - **anything that changes production cost** (scaling or starting workers)
  - **anything a prospect will see before it is reviewed** (summaries, Phase 11)
  - **the go-live switch** (Phase 13)
- Never print secrets. Scripts read keys at runtime from the `.env` files below. Never write a key to a file or a ticket.
- Every script defaults to a **dry run**. Pass `--go` to write.
- Put scratch files in the session scratchpad. Copy reusable outputs (configs, specs) next to the brand notes afterwards.

## Setup (once per machine)

The scripts find the other checkouts relative to the folder that holds `zebora-standards` (the "workspace"). Override any of these with an environment variable:

| Variable | Default | What it is |
|---|---|---|
| `ZEBORA_WORKSPACE` | the folder containing `zebora-standards` | where the checkouts sit side by side |
| `ZEBORA_PIPELINE` | `<workspace>/brand_score_pipeline` | its `.env` has `DATABASE_URL`; its `.venv` has psycopg2, sqlalchemy and dotenv |
| `ZEBORA_DATAFORSEO_ENV` | `<workspace>/prompt-extractor/.env` | DataForSEO credentials |
| `ZEBORA_BACKUP_ROOT` | `<workspace>/db_backup` | backups of stored rows before corrections |
| `ZEBORA_EXTRACTION_REPO` | none (required for Phase 2) | an up-to-date `automated-extraction` checkout (zebora-dev/prompt-extractor) on `main`. It holds the DataForSEO modules and the `.env` with `BRANDSIGHT_SUPABASE_URL` / `BRANDSIGHT_SUPABASE_SERVICE_KEY` |

```bash
export ZEBORA_EXTRACTION_REPO=<path to automated-extraction on main>
SKILL=~/.claude/skills/zebora-onboard-preview-brand/scripts
PIPE=${ZEBORA_PIPELINE:-<workspace>/brand_score_pipeline}
PY_DB=$PIPE/.venv/bin/python        # run the skill scripts with this
```

Install: `ln -s <workspace>/zebora-standards/skills/zebora-onboard-preview-brand ~/.claude/skills/zebora-onboard-preview-brand`.

## Use this, not that

| Job | Use | Do NOT use |
|---|---|---|
| Extraction (GPT + Google AI Overview) | `extract_dataforseo.py`: one-off submit plus `reconcile_pending`. About 3 min, about 13 US cents per 100 outputs | Selenium workers, the Prefect extraction pool or the webhook machines. A preview brand needs none of them |
| Scoring a whole batch | **Fan-out dispatcher**: `POST https://brand-score-api.fly.dev/api/workflows/score-single-output` with `output_id` as an **array of ints**. That makes one flow run per output, spread across all workers | `POST /batch/init` or the `batch-scoring-test` deployment. They run every output in ONE process, so extra workers do nothing (36 min for 106 outputs) |
| Re-scoring one output | the same endpoint with `output_id` as a string and `force: true` | A forced re-score while a batch flow is still running. It can leave two active score rows |
| DB writes | `supabase-py` with `BRANDSIGHT_SUPABASE_SERVICE_KEY` (the scripts do this) | The Supabase MCP (read-only) |
| DDL / long statements | Supabase **SQL Editor** (the user runs it) | Direct port 5432 (blocked). Long jobs through the 6543 pooler without progress logging |
| Refreshing views, summaries, readiness | **The release chain** (Phase 10): `POST /api/workflows/batch/release`, or `scripts/batch_release/release_chain.py` from the pipeline | `refresh_entity_metrics_v2(batch)` or `refresh_url_scores_v1` by hand. The deprecated `POST /api/batches/refresh-views[/v2]` endpoints. `scripts/refresh_entity_metrics_matviews.py`. The UI refresh button. They skip steps and record nothing |
| Fixing entity names / misses | `apply_corrections.py` on the stored rows | Re-scoring. The scorer is non-deterministic, drops items from long lists and ignores exclusion rules |
| Python env | Skill scripts and the release chain: `$PIPE/.venv/bin/python`. DataForSEO code: `$ZEBORA_EXTRACTION_REPO` on `main` | A stale worktree (it may lack the DataForSEO modules), or a venv without `psycopg2` |

## Target order (this is what saves the time)

```
0 prompts file  ->  1 setup  ->  2 extract  ->  3 context v1  ->  4 score (fan-out)  ->  5 review (scoring-train)
 ->  6 stored-row corrections  ->  7 seed entity dims  ->  8 enrich websites  ->  9 classify URLs  ->  9b brand sites
 ->  10 release chain (refresh + summaries + readiness)  ->  11 review summaries  ->  12 verify  ->  13 go live + hand-off
```

Enrich and classify **before** the release chain. On Twinkl the refresh ran three times because websites and URL labels were added after it.

---

## Phase 0 · Inputs

Collect four things: brand name, primary URL, market / region (`uk`/`us`), and the prompt sheet.

The Google Sheet may not export (HTTP 401). If so, read it with the Drive connector and write `prompts.json`: a list of `{"prompt": ..., "category": ..., "label": ...}` from the sheet columns `Prompt`, `Prompt Category` and `Prompt Reporting Label`. A CSV with those three headers also works. Confirm the counts back to the user: prompts, categories, and labels per category.

Check for an existing brand: `$PY_DB $SKILL/status.py --slug <slug>` (read-only).

## Phase 1 · Brand, batch, prompts, weightings

```bash
$PY_DB $SKILL/onboard_setup.py --name "Twinkl" --url https://www.twinkl.co.uk --category "Teaching resources" \
  --market UK --localization "UK English" --system-intro "response about ..." \
  --prompts prompts.json --sheet-id <google sheet id>            # dry run
$PY_DB $SKILL/onboard_setup.py ... --go                          # write (add --resume to continue a partial run)
```

The script models every field on the `--like` reference brand (default `transunion`) and creates:
- the target `competitors` row
- the `brands` row: `is_demo`, `status onboarding`, **not** in the weekly pool
- release settings `engagement: one_off / capture none / release dashboard_only`. This puts the brand on the **preview readiness profile** (Phase 10).
- the batch: `paused`, `dashboard_type preview`, GPT + Google AI Overview
- the prompts, with equal category and tag weightings
- `llm_model_weightings`: gpt 0.6, google 0.4

Checks the script enforces:
- prompts are unique
- weights sum to exactly 1.0 (the last node absorbs rounding)
- tag weightings exist (**missing tag weights silently empty every entity view**)

Known traps:
- `competitors.normalized_name` is a generated column. Never insert it.
- Tenant defaults to 1, like TransUnion (Smart Energy GB used a different tenant). Confirm with the user.
- **A regional brand has two names.** The display name carries the market (`--name "Twinkl (US)"`, like "Big Potato (US)"), but the answers say "Twinkl". The script sets `name_canonical`, `config.target_brand` and the company record to the **target name**. By default that's `--name` without its market tag; override it with `--target-name`. The scorer, the corrections and the dimension seeding all match on it. Before this fix, Twinkl (US) came out with 0 target rows.

## Phase 2 · Extraction

The DataForSEO code needs the **extraction repo's own Python environment**: the pipeline venv lacks its packages (`pyperclip` and others). Use a clean worktree of the extraction repo on `origin/main` with its own venv. Don't use a long-lived checkout, which may be on another branch and far behind (on 19 Oct 2026 it was 59 commits behind and had no DataForSEO modules):

```bash
EX=<scratch dir>/ae_main
git -C "$ZEBORA_EXTRACTION_REPO" fetch -q origin main && git -C "$ZEBORA_EXTRACTION_REPO" worktree add -q --detach "$EX" origin/main
(cd "$EX" && uv sync --frozen -q)
set -a; source "$ZEBORA_EXTRACTION_REPO/.env" >/dev/null 2>&1; set +a      # Supabase keys for the extraction code (never echo)
"$EX/.venv/bin/python" -u $SKILL/extract_dataforseo.py <batch_id> --repo "$EX" --region us   # or uk
```

This submits GPT and GAO to the DataForSEO Standard queue without a pingback, then collects with `reconcile_pending`. Expect about 3 to 5 minutes. If only AI Overview tasks are left pending and nothing changes for `--stall-minutes` (default 5), it stops waiting: a missing AI Overview never blocks readiness.

Google shows no AI Overview for some searches. Those outputs come back empty with `metadata.ai_overview = false`, and the script deactivates them at the end, with `deactivated_reason` recorded. That's 2 of 54 for Twinkl UK and 13 of 54 for Twinkl US, so expect more in the US. They aren't answers, and scoring them would count the target as "not visible". The readiness Capture line only warns below 50%.

## Phase 3 · Context v1 and the primary tier

```bash
$PY_DB $SKILL/create_context.py --config context.json            # dry run
$PY_DB $SKILL/create_context.py --config context.json --go
```

`context.json` supplies (see `examples/twinkl_context.json`):
- the category description
- extractable types
- brand-specific exclusions
- product-collapse lines
- canonical provider names
- target aliases
- the **primary competitors**

`templates/category_rules_base.md` already contains the generic rules learned on TransUnion and Twinkl:
- **extract every provider with its own list item, heading or table row**
- the canonical list is for spelling only
- products collapse into their company
- titles and headings are not entities
- names that appear only in image captions are not entities
- local authorities and shops are out
- `entity_type` is never `unknown`

**Primary tier:** pick the most-named competitors across the extracted responses, counting how many prompts name each. Ignore citation noise (e.g. `utm_source=chatgpt.com` makes "ChatGPT" look universal) and tools the rules exclude. **Flag the tier as provisional** in `metadata.notes`, and confirm it with the user at the Phase 5 gate.

If the brand already has a preview in another market, ask whether to add that market's primaries too, so the two dashboards line up. Twinkl US kept its 8 and added the UK 8, for 16 in total. To change primaries after Phase 3:
1. Insert `competitors` and `competitors_primary` rows (next `order`).
2. Set `is_primary_competitor` on existing `visibility_entity_brands` rows, or add brand and entity rows for primaries that aren't seeded yet.
3. Re-run `apply_corrections.py --go` so the stored rows are re-tagged.

## Phase 4 · Score with the fan-out dispatcher

```bash
# all active output ids for the batch (read-only SQL), then:
curl -s -X POST https://brand-score-api.fly.dev/api/workflows/score-single-output \
  -H "Content-Type: application/json" \
  -d '{"batch_id":"<batch>","output_id":[<ids...>],"force":false,"priority":3}'
```

- **Track progress.** Poll `GET /api/workflows/<workflow_run_id>/status`, or run `$PY_DB $SKILL/status.py --batch <id>` for scored and QA counts.
- **Workers (GATE).** Workers are **stopped between jobs** (ZEB-1087). Until one is running, flow runs sit in Late.
  - The pool limit is 40 and each worker runs `--limit 5`, so 8 workers fill it.
  - Start: `fly machine start <id> -a brand-score-worker`. Scale: `fly scale count 8 --app brand-score-worker`.
  - **Starting or scaling workers changes production cost, so ask the user first.** Report the worker count you saw online, and stop the workers afterwards if they were stopped before.
- **Score in stages.** Don't score the whole batch first. Score 10, and start the review while the rest runs (scoring-train Phase 0a).
- **Catch stragglers.** Finish by listing active outputs that have no active score row, and submit those individually (`output_id` as a string). A batch flow can complete with an output still unscored.
- **No forced re-scores mid-run.** Never force a re-score of an output while a batch flow is running.

## Phase 5 · Review: `zebora-scoring-train` (GATE: policy decisions)

Run `/zebora-scoring-train <batch_id>`. Auto-review the clear cases, and escalate only policy calls, each with a recommendation. Reuse precedents instead of re-asking. Decisions that typically come up:
- Are general AI assistants extractable?
- Are advice or evidence bodies providers?
- Exam boards, bare book titles, admin software, heritage bodies

Apply approved changes as a new context version: copy the previous version, change the rules, and set the old one to `active=false`. Never write without the user's confirmation. **Do not re-score to apply them** (see Phase 6).

Expect the scorer's known weaknesses: long lists lose items, exclusion rules are ignored, and runs vary. A passing QA verdict does not prove recall.

## Phase 6 · Correct the stored rows (instead of re-scoring)

```bash
$PY_DB $SKILL/apply_corrections.py --batch <id> --find-candidates      # writes candidates.json (numbered / bold items not extracted)
$PY_DB $SKILL/apply_corrections.py --batch <id> --spec corrections.json  # dry run
$PY_DB $SKILL/apply_corrections.py --batch <id> --spec corrections.json --go
```

The spec lists:
- `mappings`: alias to canonical brand (also read from the active context)
- `remove`
- `remove_by_output`
- `merge_by_output`
- `add`: output, brand, entity type, text variants
- `type_fix`

The script:
- backs up every row first, to `$ZEBORA_BACKUP_ROOT/<slug>_<date>/`
- records each change on the row (`metadata.manual_edits`, `canonicalised.rule`)
- merges duplicates produced by renames
- re-tags every entity whose target / primary flags disagree with the DB (the target is matched on the brand's `name_canonical`). Re-run it after you change the primary tier
- renumbers positions

It is idempotent: a second run reports 0 changes.

Review `candidates.json` yourself. Add only clear misses: a named provider with its own numbered item, heading or table row. List ambiguous ones for the user instead of guessing.

Scoring QA verdicts on edited rows go stale, so note that in the hand-off. The batch ends up with answers scored under several context versions. The preview readiness profile shows that as a warning, not a failure.

## Phase 7 · Seed entity dimensions

```bash
$PY_DB $SKILL/seed_entity_dims.py --slug <slug>            # dry run: counts, key clashes, alias clashes
$PY_DB $SKILL/seed_entity_dims.py --slug <slug> --go
```

This mirrors TransUnion:
- one `visibility_entity_brands` row and one `visibility_entities` row per canonical provider
- aliases on entities
- target and primary flags from the brand and `competitors_primary`

Keys come from the SQL function `normalize_company_name`, never by hand. **Read the printed brand list for near-duplicates before `--go`** ("Widgit" and "Widgit Resources" slipped through on Twinkl).

## Phase 8 · Enrich websites

From the pipeline repo root (`cd $PIPE`, an up-to-date `main`):

```python
from db.entity_enrichment_v3 import entity_enrichment_v3
entity_enrichment_v3(brand_id="<brand_id>")      # GPT pass, about 5 min for 136 brands
```

Optionally, run the Gemini pass for the remainder (`db.entity_enrichment_gemini`; slow and rate limited). Expect about 65% coverage from the GPT pass. Ignore Langfuse "403 ingestion suspended" noise (ZEB-1052).

## Phase 9 · Classify URLs

```bash
curl -s -X POST https://brand-score-api.fly.dev/api/workflows/batch/url-classification \
  -H "Content-Type: application/json" -d '{"batch_id":"<batch>"}'      # then poll status; about 7 min
```

Add `-H "X-API-Key: ..."` if the key has been enforced since ZEB-796.
- **Only after scoring has finished.** Classification labels the citations (`url_scores`) that scoring creates. On Lavazza it was started alongside scoring, "completed" in a minute with nothing to classify, and readiness then failed on 63% unclassified.
- **It needs a worker** (deployment `url-classification-test` on `scoring-pool`). With no worker online the run sits in Late, so start one (cost GATE) or run it while the scoring workers are still up.
- It can run in parallel with Phase 8, since they're independent.
- For QA of the URL chain, use `zebora-scoring-url` (reporting only).

## Phase 9b · The brand's own sites

```bash
$PY_DB $SKILL/brand_sites.py --slug <slug>                      # report
$PY_DB $SKILL/brand_sites.py --slug <slug> --go                 # set the target's and primaries' websites
$PY_DB $SKILL/brand_sites.py --slug <slug> --go --add-owned     # also count the listed brand-named domains as owned
```

Run this after Phases 8 and 9, before the release chain.
- **Target website.** Enrichment looks the brand up by name, so a brand with sites in several countries can get the wrong one: Twinkl US got `twinkl.co.uk`. The script sets the target's website (dimension rows and company record) to the primary url from setup.
- **Primary competitors' websites.** Enrichment matches competitors by name too, so a name shared with another company gets that company's site. Lavazza's Sage (the coffee machines) got `sage.com`, the accountancy software, and the dashboard showed it next to the competitor. The script lists any primary whose website is empty or on a different host from its competitor record (`competitors.url`, from the primaries the user confirmed), and `--go` sets it to that url. Read the list: a same-host difference such as a country path isn't flagged.
- **Owned domains.** A citation counts as the brand's own only if its domain is in `brands.urls`. The script lists cited domains that contain the brand name but aren't owned, such as the help centre or other-country sites (Twinkl US: `twinkl.zendesk.com`, `twinkl.com.br`, `twinkl.fr`). **Confirm the list with the user, then pass `--add-owned`.** A domain containing the name isn't always the brand's.

## Phase 10 · The release chain (refresh, summaries, readiness)

This is the same chain the monthly pool brands use (see `zebora-batch-release`). It runs, in order, stopping at the first step that fails:

| Step | What it does | Time |
|---|---|---|
| `entity_refresh` | 27 steps, nested loops off | about 3 min |
| `url_refresh` | refreshes the URL views | about 2 min |
| `pr_scores` | refreshes PR scores | seconds |
| `pr_module` + `pr_payloads` | skipped, because a preview has no PR module | — |
| `summaries` | only the 6 summaries a preview dashboard shows (ZEB-1092) | about 2 min, about 1 US cent |
| `readiness` | the gate, saved in the batch's release record | — |

Every refresh is `CONCURRENTLY`, so live dashboards keep working. The views are global, so the time doesn't depend on batch size.

**Plan first, then apply.** Either use the API:

```bash
curl -s -X POST https://brand-score-api.fly.dev/api/workflows/batch/release \
  -H "Content-Type: application/json" -d '{"batch_id":"<batch>"}'                  # plan only
curl -s -X POST https://brand-score-api.fly.dev/api/workflows/batch/release \
  -H "Content-Type: application/json" -d '{"batch_id":"<batch>","apply":true}'     # run it
# then poll GET /api/workflows/<workflow_run_id>/status
```

`apply` returns **503 when no Prefect worker is online**. Start one first (cost GATE, as in Phase 4). It returns 409 while an earlier `apply` run for the batch, started under 6 hours ago, is still running.

Or run it locally, with no worker needed. Set `PREFECT_API_URL=https://brand-score-prefect.fly.dev/api` first: the pipeline `.env` points at a local Prefect (`127.0.0.1:4200`), and the summaries step fails against it. It takes about 10 minutes, so run it detached:

```bash
cd $PIPE && nohup .venv/bin/python -u scripts/batch_release/release_chain.py --batch-id <batch> --apply > /tmp/release_<slug>.log 2>&1 &
```

Resume a stopped chain with `--from <step>` (API: `start_from`). Run only some steps with `--only a,b` (API: `steps`).

**Readiness uses the preview profile** (ZEB-1086), picked automatically from the brand's `capture none` setting:
- **Capture** replaces Pool runs. It counts answers per surface against the brand's active Visibility prompts. Fail under 90% on an LLM surface; warn under 50% on AI Overview.
- A mixed **Scoring model** warns instead of blocking.
- Everything else blocks exactly as for a pool brand: scoring complete, metrics views fresh, unmatched names, target brand, URL view, URL labels (5% or fewer unclassified), junk citations, summaries.

Fix a failing line at its source and re-run from that step. Waive a line only when the user accepts the reason:
```bash
$PY_DB scripts/batch_release/readiness.py --batch-id <id> --waive "<line>" --reason "<why>" --by "<name>"
```

## Phase 11 · Review the summaries (GATE)

A preview dashboard opens only Overview, Visibility, Competitors and Signals. So the `summaries` step writes just the 6 summaries those pages read: `visibility`, `visibility-insights`, `competitors`, `competitors-insights`, `signals` and `signals-insights`. It skips sentiment insights and pillar caveats (ZEB-1092), and readiness requires those 6. **They show on the dashboard as soon as they are active. The dashboard does not check `is_approved`.** So the prospect sees them unreviewed unless you check them first.

Read them in the admin app (`/batches/<batch_id>/summaries`), or read-only:
```sql
select location, type, left(content, 300) from scores_summaries where batch_id = '<batch>' and is_active order by location;
```

Check each figure against the run's inputs (`analysis_runs.artifact_data` for the batch). Flag anything that:
- names the wrong brand, or names a domain instead of its brand (Twinkl: "The National Academy" for Oak National Academy)
- leaves out the largest source
- quotes a figure the dashboard doesn't show
- reads like a draft

Two prompt bugs found on Twinkl were fixed on 16 Oct 2026 (ZEB-1093): `visibility-summary` v5 no longer says "in ChatGPT" for a blended score, and `competitor-insights` v3 has the right heading. Summaries written before that may still carry the old wording. The user approves or edits them in the admin app before the brand is shown to the prospect.

## Phase 12 · Verify

Run `$PY_DB $SKILL/status.py --batch <id>`. It should show:
- all active outputs scored, with exactly one active row each
- dims seeded
- website coverage
- rows in the metric views and the URL view
- the headline numbers: target visibility and rank against the primaries, on the same scale as TransUnion

Compare view row counts with the reference brand. The chain's readiness result is in the batch's release record. Re-run read-only with `readiness.py --batch-id <id>`.

## Phase 13 · Go live and hand off (GATE: the user approves)

Run this from a pipeline checkout on an up-to-date `main`. On 20 Oct 2026 the main checkout was on an old branch that had no `go_live.py`; a fresh worktree on `origin/main` with the pipeline `.env` copied in works.

1. **Approve the summaries** the user signed off in Phase 11: set `is_approved = true` on the batch's 6 active `scores_summaries` rows (supabase-py, as the other scripts do).
2. **Approve and activate the batch:**
   ```bash
   cd $PIPE && .venv/bin/python scripts/batch_release/go_live.py --batch-id <id>                       # dry run
   cd $PIPE && .venv/bin/python scripts/batch_release/go_live.py --batch-id <id> --apply --by "<name>"
   ```
   `go_live.py` approves and activates the batch and points `brands.batch_id` at it. For a preview, setup already pointed `brands.batch_id` at the batch, so only the approval and activation change. It needs a **recorded readiness pass from the last 24 hours**, and it saves the values it replaces so the switch can be reversed (`--rollback --apply`).
   Before brand-score-pipeline#184, `go_live.py` refused a preview with "this batch is already the brand's live batch", because setup had already pointed the brand at it. If you get that message, update `$PIPE`. Lavazza (20 Oct 2026) was switched by hand instead: `batches.is_approved = now()`.
3. **Set `brands.status = 'live'`**, as for TransUnion. Keep `visibility_pool_enabled = false`. The rollback values are `onboarding` and the batch's previous `is_approved` (blank for a new preview).

Save a memory note with the ids, decisions and gotchas. List what is not done:
- empty views
- brands without websites
- duplicate entity rows
- provisional primaries
- stale QA verdicts
- unapproved summaries

---

## Time budget (Twinkl actuals, and what it should look like)

| Phase | Twinkl actual | Target |
|---|---|---|
| 1 setup | minutes (2 script fixes) | 2 min |
| 2 extraction | 2.6 min | 3 min |
| 4 scoring | 36 min | 2 to 5 min (fan-out, 8 workers; untested) |
| 5 review rounds | 3 context versions | 1 round using the base template |
| 6 corrections | built from scratch | 5 min with the spec |
| 7 to 10 | 30+ min, 5 refresh attempts | about 20 min: seed 2, enrich + classify in parallel 7, release chain about 10 |

## Checklist before saying "done"

- [ ] tag weightings and `llm_model_weightings` exist for the batch
- [ ] every active output has exactly one active score row
- [ ] a stored-row backup exists under `$ZEBORA_BACKUP_ROOT`
- [ ] entity dims seeded, with no near-duplicate brand rows
- [ ] websites enriched and URLs classified, target website, primaries' websites and owned domains checked (`brand_sites.py`), **then** the release chain (its `entity_refresh` copies the websites into the views, per batch: refreshing one brand's batch does not update another's)
- [ ] release chain finished, and readiness recorded as a pass (preview profile) or with agreed waivers
- [ ] summaries reviewed and approved by the user
- [ ] `go_live.py --apply` run with the user's name; brand `live`; not in the weekly pool
- [ ] workers stopped again if you started them
- [ ] user told which views are empty and why
