---
name: zebora-batch-release
description: Monthly batch release runbook — the end-to-end SOP for taking a brand's monthly batch from weekly capture to a live dashboard and the monthly report email. Sets the order, the gates and the human decisions; the checks and mechanical steps are scripts in brand-score-pipeline (scripts/batch_release). Calls zebora-scoring-vec and zebora-scoring-url at the right point. Triggers on: release a batch, get a batch live, monthly release, go-live, batch SOP, weekly pool check, setup check, preflight, monthly report email, batch readiness.
---

# zebora-batch-release — Monthly batch release runbook

**Invocation:** `/zebora-batch-release [stage] <brand or batch_id>`

One ordered process for a brand's monthly batch: **capture → score → check → review → refresh → PR
module → summaries → readiness → go-live → report email**.

Status: **draft v0.7 (6 Oct 2026)**, written from the September 2026 releases of Big Potato UK,
Big Potato US and Nationwide.

## How the process is held together

Four pieces, each with one job. Nothing here needs a schema change.

| Piece | Its one job | Where it lives | State |
|---|---|---|---|
| **Scripts** | Run the checks and the mechanical steps the same way every time | `brand-score-pipeline/scripts/batch_release/` | Setup check, weekly check, settings, readiness, go-live, the month-end chain and the report-email check built |
| **Brand settings** | What is different about this brand, decided once | `brands.config.release` | Built; saved for Big Potato UK, Big Potato US and Nationwide |
| **Release record** | Which stages have passed for this batch, when, and the key figures | `batches.batch_metadata.release` | Built; written by the checks with `--record` |
| **This runbook** | The order, what each gate means, and what a human decides | this file | Draft |

The rule for what goes where: if a step needs no judgement it is a script; if an answer is the same
every month it is a brand setting; if it happened it is in the release record; only what is left
belongs in this document.

## Commands

All run from the `brand-score-pipeline` repo root, on an up-to-date `main`. All are read-only unless
marked. Each check exits 1 when a line fails, so it can gate a scheduled run, and takes `--json`
and `--record` (save the result to the batch's release record — its only write).

| Stage | Command | State |
|---|---|---|
| 0 | `poetry run python scripts/batch_release/preflight.py --all-pool` (or `--batch-id <id>`) | Built |
| 2 | `poetry run python scripts/batch_release/weekly_check.py --all-pool` (or `--batch-id <id>`) | Built |
| any | `poetry run python scripts/batch_release/brand_settings.py --list` — every active brand's engagement and pool enrolment | Built |
| any | `poetry run python scripts/batch_release/brand_settings.py --brand-id <id>` — show a brand's settings; `--file <json> --apply --backup-dir <dir>` saves them (**writes**) | Built |
| 5–8 | `poetry run python scripts/batch_release/release_chain.py --batch-id <id>` — prints the plan; `--apply` runs entity refresh → URL refresh → PR facts → PR module → summaries → readiness, stopping at the first failure (**writes**). Also the `batch-release-chain` deployment | Built |
| 8 | `poetry run python scripts/batch_release/readiness.py --batch-id <id> --record` | Built |
| 8 | `readiness.py --batch-id <id> --waive "<line>" --reason "<why>" --by "<name>"` — accept one failing line (**writes** the release record) | Built |
| 9 | `poetry run python scripts/batch_release/go_live.py --batch-id <id>` — dry run; `--apply --by "<name>"` switches (**writes**); `--rollback --apply` reverses it | Built |
| 10 | `poetry run python scripts/batch_release/report_email_check.py --batch-id <id>` — campaign snapshot against the live dashboard; run before sending and again after | Built |

`--all-pool` means every batch the weekly pool is currently capturing into.

## Who does what

| Stage | When | Runs | A person decides |
|---|---|---|---|
| 0 · Setup checks | Month start, and before each Monday run | Script | Only how to fix a failed line |
| 1 · Capture and scoring | Weekly, usually four times | Scheduled flows | — |
| 2 · Weekly check | After each pool run | Script | Week 1: entity and alias fixes. Later weeks: only if a line fails |
| 3 · Visibility review | Month end | `/zebora-scoring-vec` | Which names are the same thing; which brands stay separate |
| 4 · URL review | Month end | `/zebora-scoring-url` | Labels for the unclear domains |
| 5 · Refresh | Once | Script | When to take the dashboard lock |
| 6 · PR module | Once | Script | — |
| 7 · Summaries | Last data step | Script | — |
| 8 · Readiness | Before go-live | Script | — |
| 9 · Go-live | — | Script | **Approve the switch** |
| 10 · Report email | Last | Admin app + check script | **Approve the send** |

## Operating rules

- **Fixed order.** A later stage never runs before an earlier one has passed. Summaries and the
  report email read the final numbers, so they come after every change to the data.
- **Read the brand settings first**, so settled questions are not asked again.
- **Refresh rules.** Per-batch `refresh_entity_metrics_v2` and `refresh_pr_scores` are safe at any
  time. `refresh_url_scores_v1` locks the live dashboard for every client for about 15 minutes per
  batch: run it once per release, at Stage 5, and say so before starting.
- **Run from current code.** A stale local branch cost three failed PR runs in September.
- **Long jobs run detached** or on the workers. Background jobs in a Claude Code session stop after
  30 minutes.
- **Never hand over a long review list.** Scripts and the independent checker decide the clear
  cases; a person sees the exceptions (aim for 20 or fewer).

---

## Brand settings (`brands.config.release`)

Read at the start of every run. Every key is optional and unknown keys are rejected, so a typo
cannot be silently ignored. Keys, with Nationwide as the example:

| Key | Meaning | Nationwide |
|---|---|---|
| `engagement.status` | `ongoing`, `one_off`, `demo` or `paused` — does the brand get a batch each month? | `demo` |
| `engagement.capture` | `scheduled` (pool runs start on the cron, workers expected online), `manual` (pool runs started by hand) or `none` | `none` |
| `engagement.release` | `full`, `dashboard_only` (no report email) or `none` | `dashboard_only` |
| `engagement.note` | Why, and until when | — |
| `entity_model` | `brands_only` or `brands_and_products`. Brand-only skips the canonicaliser (VEC Phase 4) | `brands_only` |
| `strict_titles` | Use strict title matching in the canonicaliser (needed for Vuse devices) | — |
| `separate_brands` | Subsidiaries that stay their own brand instead of rolling into the parent | The Mortgage Works, Virgin Money |
| `kept_brands` | Brands kept that the rules might exclude | MoneyHelper, Virgin Money |
| `canonicaliser_exclude` | Names the canonicaliser must leave alone (Big Potato US: Duel) | — |
| `new_brand_min_mentions` | Mentions in a month before a new brand row is created | 10 |
| `pool_runs_expected` | Weekly pool runs that make up a month (default 4) | — |
| `fix_misses_by` | `edit_stored_rows` or `rescore` | `edit_stored_rows` |
| `versions.dashboard`, `versions.reporting` | The setup check fails when a batch differs | `v2` / `v2` |
| `pr.value_percentile`, `pr.node_limit` | PR crawl settings | 0.6 / 1000 |
| `checks.accepted_aliases` | Aliases reviewed and kept, so the weekly check stops raising them | Clydesdale Bank → Virgin Money, … |
| `checks.under_extraction` | `false` where list answers are advice, not brands | `true` (to decide) |
| `notes` | Free text for anything that does not fit a key | — |

What the checks do with them today: accepted aliases are not raised again; the under-extraction
line can be switched off; a parent named only to describe a separate brand ("The Mortgage Works, a
specialist arm of Nationwide") is not a missed mention; versions are enforced. The other keys are
read by a person or by `zebora-scoring-vec` until the later scripts are built. Report-email
settings are not included yet.

**Engagement decides who is in the process at all.** Only an ongoing brand with capture
`scheduled` or `manual` belongs in the weekly pool. The setup check fails when a brand that is not
ongoing is still enrolled (its next capture would land in an old, possibly live, batch) or an
ongoing one is not; it does not ask a one-off or demo brand for a current-month batch; and it
skips the worker lines unless capture is `scheduled`. `brand_settings.py --list` shows every
active brand's engagement against its pool enrolment — read it at the start of each month.

State on 6 Oct 2026: Big Potato UK, Big Potato US, Vuse and Talking Futures are ongoing with
manual capture; Nationwide is a demo; Smart Energy GB and TransUnion are one-offs. The other
active brands have no engagement set and are not enrolled. Vuse and Talking Futures have only
their engagement and one or two notes saved; the rest of their settings are defaults.

## Release record (`batches.batch_metadata.release`)

One entry per stage, latest result only: `{status, at, by, failed, warned, figures}`. The checks
write `setup_check`, `weekly_check` and `readiness` when run with `--record`; go-live writes
`go_live` with the values it replaced. Waivers sit beside the stages: `{reason, by, at}` per line. The record carries its batch id, because creating a batch from last month's copies
`batch_metadata`: a record with another batch's id is discarded. Scripts write it; the readiness and go-live
commands read it. It makes a release resumable (anyone can see where a batch is) and auditable
(what was decided and when). The go-live rollback record is stored here too.

---

## Stage 0 · Setup checks

`preflight.py`. One pass/fail table per batch. Every line caused a real problem in September.

| Line | Fails when | Fix |
|---|---|---|
| Batch | Not dated the 1st, no `report_month`, or two batches for the month | Correct the batch |
| Weekly pool | Pool points at another batch, or still at last month's | Create this month's batch and point the pool at it |
| Prompts | No active visibility prompts | — |
| Model weightings | No rows, a captured surface has no weight, or weights do not sum to 1 | Copy from last month, adjust for surfaces |
| Category weights | A prompt category has no weight (Sep: "Use Case" against "Use Cases" dropped 24% of the weighting) | Rename or add |
| Tag weights | A prompt tag has no weight (Sep: none at all → every metrics view empty, no error) | Copy from last month |
| Versions | Dashboard or reporting version blank; warns if different from the live batch | Set them |
| Prompt context | Not exactly one active context | Deactivate the extras |
| Target brand | Not exactly one row flagged as the target | Fix the flag |
| Automatic scoring | Warns when the latest pool run has `score_on_complete` off | See Stage 1 |
| Capture workers, Scoring workers | The Prefect work pool has no worker online | Start the workers |

**Fix at source:** batch creation should copy category weights, tag weights, model weightings and
versions from the previous month, and move the pool to the new batch, in one step.

## Stage 1 · Weekly capture and automatic scoring

A monthly batch is built from the **weekly visibility pools**: one pool run per week, usually four,
each capturing one output per prompt per surface. Each output's weight is divided by the number of
weekly samples for that prompt and surface, so every prompt counts once and its score is the mean
across the weeks that sampled it.

What should happen with no manual steps:

1. Monday 06:00 UTC — `dataforseo-weekly-visibility-pool` creates the week's run
   (`visibility_pool_runs`, named `Visibility <year>-W<nn>`) and enrols every pool-enabled batch.
2. Captures are submitted per surface. ChatGPT and Gemini go through the asynchronous queue and are
   saved by the webhook app; Google AI Overview, Claude and Perplexity are captured live.
   `dataforseo-reconcile` and `dataforseo-pool-drain` sweep up anything outstanding.
3. Each saved output is scored: visibility, sentiment, URLs and output QA.
4. The pool run is marked completed.

**State on 6 Oct 2026:** capture is manual for now (pool runs are started by hand, so the ongoing
brands are set to capture `manual`), scoring is not automatic (every September run had `score_on_complete`
off), the capture and scoring workers are stopped, and two identical insert triggers on
`prompts_outputs` post every new output to a scoring address on Railway. Automatic scoring is being
rebuilt alongside a change of scoring model and may start from the second week of October.

**When the scoring model changes mid-month.** A month's numbers should come from one scoring model
and one prompt-context version. The weekly check's "Scoring model" line warns when a batch mixes
them. If the model changes after week 1, decide once whether to re-score the earlier weeks with the
new model or accept the mix, and record the decision in the release record.

## Stage 2 · Weekly check

`weekly_check.py`, after each pool run. It covers everything captured into the batch so far, with a
week-by-week table. Scoring may lag capture: unscored outputs are reported, and the lines that read
scores cover the scored outputs only.

| Line | What it catches |
|---|---|
| Pool runs | A run not completed, or a surface short of its prompt count |
| Scoring | Outputs not scored yet, by week (ids in the JSON output) |
| Model labels | A bare provider label (`gpt`) or a label with no provider mapping — both corrupt the views |
| Scoring model | More than one scoring model or prompt-context version in the batch |
| Metrics views | Scored outputs missing from the views — refresh the batch and re-run |
| Under-extraction | Answers listing five or more things with one or no entities — candidates to re-score |
| Unmatched names | Share of mentions matching no known brand, and the top names |
| Target brand | Answers that name the brand but do not count it, and the reverse |
| Visibility figures | Weighted visibility above 100%, or empty views when mentions exist |
| New aliases | Aliases written in the last 8 days that share no word with their target |
| By week | Captured, scored, under-extracted, unmatched share and target-counted share per week |

**Why not the full review every week, and why not only at month end.** A full review every week
repeats work that only matters once the month is complete (merges, websites, PR module, summaries).
Leaving everything to month end lets errors compound: a wrong alias makes the scorer store the
wrong name on every later output, and a prompt-context fix only applies to outputs scored after it.

So:

- **Week 1 — act on the check.** Run the parts of `zebora-scoring-vec` whose fixes carry forward:
  Phase 2 (QA triage), Phase 3 (entity review), the alias audit from Phase 9, and Phase 10 (prompt
  context, saved now so later weeks are scored with it). Fix week 1's stored data by editing the
  stored entity rows unless the brand settings say to re-score.
- **Weeks 2 and 3 — read the check.** Act only on a failed line or a clear week-on-week jump.
- **Final week — the full review** (Stage 3), which should be short.

## Stage 3 · Visibility review (month end)

Run `/zebora-scoring-vec <batch_id>`. On top of the skill:

- **Phase 3** — verify matches with the independent checker; apply only high-confidence results;
  respect `new_brand_min_mentions`.
- **Phase 4** — **skip when `entity_model` is `brands_only`.** With no product rows the
  canonicaliser matches nothing and its grouping step reassigns shared product names to the wrong
  brand.
- **Phase 8** — start from the weekly check's target-brand ids; fix per `fix_misses_by`.
- **Phase 10** — save the context as a new version; it only affects future scoring.

## Stage 4 · URL review

Run `/zebora-scoring-url <batch_id>`, plus:

1. **Completeness.** Outputs whose only sources are Google Shopping links are correctly unscored.
2. **Label unclassified domains and URLs.** The labels table is shared across brands, so later
   brands in the same cycle need far fewer.
3. **Junk citations.** Deactivate image-CDN and thumbnail rows, logged in metadata.

No refresh here.

## Stages 5–7 · The month-end chain

`release_chain.py --batch-id <id> --apply` runs Stages 5 to 8 in order for one batch and stops at
the first step that fails. Each step's result and duration is saved in the release record, so a
stopped chain shows where it got to.

| Step | What it runs | Notes |
|---|---|---|
| `entity_refresh` | `refresh_entity_metrics_v2` | About 3 minutes, no lock. Retries when another refresh holds the lock |
| `url_refresh` | `refresh_url_scores_v1` | About 15 minutes; **locks the live dashboard for every client** |
| `pr_scores` | `refresh_pr_scores` | Seconds. Before the PR module, or the crawl finds nothing to do |
| `pr_module` | crawl → status refresh → analysis without crawl | Skipped when the module is off. Crawl percentile and `node_limit` come from the brand settings (default 0.6 / 1000; the code default of 3 leaves a batch 50–80% scraped). A crawl that scrapes under 30% of its pages is run again once, then fails |
| `summaries` | `batch-summary` flow | Last data step. Fails if any summary task fails |
| `readiness` | Stage 8, recorded | What go-live reads |

**The dashboard lock is a person's call.** Without `--allow-dashboard-lock` the chain stops before
`url_refresh`. Announce the lock, then resume with `--from url_refresh --allow-dashboard-lock`.
Release several batches by running their chains one after another in the same window.

**Resuming.** `--from <step>` continues from a step; `--only a,b` runs the named steps in chain
order. If anything in Stages 3–4 is redone after the chain, run it again from `entity_refresh` so
the summaries are rewritten.

**Where to run it.** The chain takes an hour or more. Run it as the `batch-release-chain`
deployment on the workers, or detached (`nohup`) with `PREFECT_API_URL` reachable; a Claude Code
background job is stopped after 30 minutes. Run brands that share many URLs one after another.

After it finishes, confirm 12 active summaries plus the sentiment insights (the readiness table
shows this), and that "Brand presence coverage" fills in once a logged-in user opens the PR page.

## Stage 8 · Readiness gate

`readiness.py --batch-id <id> --record`. One table; go-live is blocked while any line fails.

| Area | Line | Fails when |
|---|---|---|
| Config | Brand settings, Batch, Model weightings, Category weights, Tag weights, Versions, Prompt context | As Stage 0 |
| Capture | Pool runs | Fewer completed runs than `pool_runs_expected`, or an LLM surface under 90% of its prompts |
| Scoring | Scoring, Model labels, Scoring model, Metrics views | Anything unscored; a bad label; mixed scoring models or context versions; views behind the scores |
| Visibility | Unmatched names, Target brand, Visibility figures | Unmatched above 5%; target-brand exceptions above 2% of answers; visibility above 100% |
| URLs | URL view, URL labels, Junk citations | Dashboard view differs from the source; over 5% unclassified; thumbnail rows present |
| PR | PR module | A blocking `compute_pr_batch_readiness` check is incomplete (coverage excepted); skipped when the module is off |
| Summaries | Summaries | Fewer than 12 active, or written before the latest scoring |

Under-extraction and New aliases only ever warn.

**Waivers.** When a line fails for a reason a person has accepted (for example, mixed scoring
models in the month the model changed), waive it: `--waive "<line>" --reason "<why>" --by
"<name>"`. The waiver is saved in the release record and the line shows as a warning carrying the
reason. Waive a line, never the gate.

## Stage 9 · Go-live

`go_live.py --batch-id <id>` shows what would change. With `--apply --by "<name>"`, after the
owner approves, it:

1. Refuses unless readiness has a recorded result from the last 24 hours with no failing line.
2. Saves the values it is about to replace (the brand's live batch, the batch's approval and
   active flags) in the release record.
3. Sets `batches.is_approved` (if blank) and `is_active = true`, and points `brands.batch_id` at
   the batch — in one transaction.

Then open the dashboard and the PR page as a logged-in user: this fills the PR coverage figure and
is the final visual check.

`--rollback --apply --by "<name>"` restores the saved values. It refuses if a later switch has
happened.

## Stage 10 · Monthly report email

Only after go-live and the visual check.

1. Create the report email campaign for the batch in the admin app (`report_email_campaigns`). The
   figures in the email are **taken when the campaign is created**, so create it after the chain
   has finished, never before.
2. Fill in the intro, highlights and the month's product updates.
3. Run `report_email_check.py --batch-id <id>`. Send only when it passes:

   | Line | Fails when |
   |---|---|
   | Campaign | No campaign exists for the batch |
   | Batch is live | The batch is not the brand's live batch |
   | Figures | Visibility, share of voice or rank in the email differ from the dashboard — delete the campaign and create it again |
   | Snapshot age | Warns when the campaign was created before the latest recorded refresh or summaries |
   | Intro | Warns when empty |
   | Delivery | After sending: any recipient not delivered, or no client recipients |

   Brand health and sentiment are worked out in the dashboard app, so the check says it has not
   compared them: read those two against the dashboard by eye.
4. Confirm the recipients and the internal copy mode in the admin app (recipients are only written
   to the database at send).
5. Send, on approval. Then run the check again with `--record` to confirm delivery and close the
   release record.

---

## Fix-at-source list

Each of these removes a check or a manual step from this runbook.

| Problem | Effect in September | Fix |
|---|---|---|
| Scoring is not automatic | Scored by hand every week | In progress, with the scoring-model change |
| Duplicate insert triggers posting to a Railway address | Unclear whether anything is listening | Remove one; point the other at the current API or drop both |
| Batches created without weights or versions; pool left on last month's batch | Empty views; blank dashboard version; October captures would land in September | Copy-forward on batch creation |
| Bare `gpt` label on captures | Visibility over 100% | Fixed (prompt-extractor #101) |
| Thumbnails scored as citations | 23 junk rows on the dashboard | Fix open (brand-score-pipeline #142) |
| PR facts not built during scoring | PR module did nothing | Run `refresh_pr_scores` in the scoring flow |
| PR crawl default `node_limit=3` | 50–80% scraped | Raise the default |
| Crawl errors swallowed | 513 of 522 pages silently failed | Log and fail the run |
| Canonicaliser reassigns brands for brand-only clients | Would have corrupted attribution | Disable grouping when no product rows exist |
| Resolver writes shifted aliases | 20 wrong aliases on Big Potato US | Ticket (not yet raised) |
| Scorer and reporting normalise names differently | Leading "the" handled inconsistently | Ticket (not yet raised) |
| `scores_visibility.scored_at` is never filled | Freshness has to be inferred from score ids | Set it when scoring |

## Build order

1. **Setup check and weekly check** — built (6 Oct 2026). Next: schedule both after the Monday pool
   run and post the tables to the team channel.
2. **Brand settings and the release record** — built (6 Oct 2026). Next: fill the remaining
   brands' settings.
3. **Readiness and go-live commands** — built (6 Oct 2026). The three September batches pass the
   gate as they stand; the go-live switch has been exercised in a rolled-back transaction but not
   yet used for a real release.
4. **Month-end chain** — built (6 Oct 2026) and registered as the `batch-release-chain`
   deployment. The refresh, PR-facts and readiness steps have been run for real; the URL refresh,
   PR module and summaries steps call the same functions used by hand in September but have not
   yet run through the chain. The deployment exists once the workers are redeployed and
   `register_deployments` is run.
5. **Report-email check** — built (6 Oct 2026). The four campaigns sent on 5 October all match
   the dashboard.
6. **Still to do:** schedule the setup and weekly checks after the Monday pool run and post the
   tables to the team channel; fill the remaining brands' settings; add brand health and sentiment
   to the report-email check once their formulas are available outside the dashboard app.

## Guardrails

- Data-quality writes follow the rules of the skill that owns them (`zebora-scoring-vec`,
  `zebora-scoring-url`).
- Never switch a batch live or send a report email without explicit approval in the conversation.
- Always save a rollback record before go-live.
- Never run `refresh_url_scores_v1` without saying that it locks the dashboard.
- Supabase production is the only database; every write is logged in the row's metadata or a dated
  folder under `db_backup/`.
