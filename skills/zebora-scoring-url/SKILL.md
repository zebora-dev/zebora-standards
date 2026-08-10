---
name: zebora-scoring-url
description: Citation/URL Checker (UCC) — reporting-only QA for the Zebora URL scoring pipeline. Validates that only active prompts+outputs are scored, reconciles the url_scores → domain-rollup → dashboard-function chain, hunts suspect domains (image CDNs, trackers), finds duplicate/inflated counts, checks url_classification coverage, and detects anomalies/drift using a baseline LEARNED from the brand's prior batches. Triggers on: url scoring QA, citation check, domain scores, url_scores, url classification, dashboard url numbers, url drift, suspect domains, refresh_url_scores. Excludes the PR/citation-crawl module.
---

# zebora-scoring-url — Citation / URL Checker (UCC)

**Invocation:** `/zebora-scoring-url [phase] <batch_id>`

Post-batch QA for the **URL scoring** pipeline, mirroring `zebora-scoring-vec` (which does entities). **Reporting-only** — this skill NEVER writes data-quality changes (no denylists, no relabels, no dimension edits). Its only side effects are the two *pipeline* operations the QA depends on: running the URL-classification workflow and refreshing the URL rollups. Everything else is read + report.

**Scope:** URL scoring only — `url_scores` → rollups → dashboard functions → `url_classification`. **Out of scope (do not touch):** the PR/citation-crawl module (`url_crawl_*`, `url_page_answerability`, `url_page_evidence`, `url_node_framing`, `fact_citation_url`, `mv_citation_scores_url_*`).

## Project context
- **Repo:** `/Users/grantsimmonds/Documents/dev/branded-llm/brand_score_pipeline`
- **DB:** PostgreSQL via `.env` (`DATABASE_URL`). Read via Supabase MCP (read-only) or psql; the refresh needs psql (extended timeout).
- **API:** `https://brand-score-api.fly.dev` (public alias `https://workflow.zebora.io`) — used for the classification workflow.
- Always `cd /Users/grantsimmonds/Documents/dev/branded-llm/brand_score_pipeline` before running psql/poetry.

**The URL scoring chain (final output tables):**
```
url_scores (base table, has `active`)
  → url_scores_base (view: adds prompt_category / prompt_measurements / prompt_tags)
  → url_scores_list (per-URL: frequency, domain_type, url_type, is_brand_owned, is_competitor)
  → urls_scores_domain / _type / _by_category / _brand_url_type   (domain rollups)
  → get_url_scores_filtered_v5() / get_domain_scores_filtered_v5()  ← DASHBOARD reads these
url_classification (type = domain|url, classification = label)  ← labels feed domain_type
```
The rollups + dashboard functions are populated by `refresh_url_scores_v1(<batch_id>)` — **stale until refreshed.**

---

## Phase 0 · Setup
Resolve the batch and establish the history baseline used later.

```sql
SELECT b.id AS batch_id, b.brand_id, br.name AS brand_name, b.status,
       (SELECT count(*) FROM url_scores WHERE batch_id=b.id) AS url_rows_total,
       (SELECT count(*) FROM url_scores WHERE batch_id=b.id AND active) AS url_rows_active
FROM batches b JOIN brands br ON br.id=b.brand_id
WHERE b.id = '<batch_id>';
```
Then find **prior VIABLE batches for the same brand** (for Phase 8 drift + learned thresholds). Note: `batches` has no `created_at` — order by `date` (also available: `started_at`, `completed_at`). Exclude non-comparable batches (`cancelled`/`failed`) — a cancelled batch is not a valid baseline:
```sql
SELECT id, date, status FROM batches
WHERE brand_id = '<brand_id>' AND id <> '<batch_id>'
  AND lower(status) NOT IN ('cancelled','canceled','failed','error')
ORDER BY date DESC NULLS LAST LIMIT 6;
```
If this returns nothing (as for Talking Futures — its only prior batch is cancelled), state "no viable baseline" and Phase 8 reports current-batch absolutes only.
Print `brand_name`, active/total url rows, and the prior batch ids found (note if none — Phase 8 becomes "no baseline available").

---

## Phase 1 · Completeness & scope integrity
**Rule: only `prompts.active = true ∧ prompts_outputs.active = true` should be scored, and *only* these should be included.** Report both directions.

**1a — Stale leak (active url_scores on inactive output/prompt):**
```sql
SELECT count(*) AS stale_active_url_rows
FROM url_scores us
JOIN prompts_outputs po ON po.id = us.output_id
JOIN prompts p ON p.id = po.prompt_id
WHERE us.batch_id='<batch_id>' AND us.active AND (NOT po.active OR NOT p.active);
```
Any > 0 ⇒ stale rows will pollute the rollups (same failure class VEC found with W29/W30). **Flag critical.**

**1b — Under-scored (active outputs with source URLs in response but no active url_scores row):**
```sql
SELECT count(*) AS active_outputs_missing_url_scores
FROM prompts_outputs po JOIN prompts p ON p.id=po.prompt_id
WHERE po.batch_id='<batch_id>' AND po.active AND p.active
  AND (po.sources IS NOT NULL AND jsonb_array_length(po.sources) > 0)
  AND NOT EXISTS (SELECT 1 FROM url_scores us WHERE us.output_id=po.id AND us.active);
```

**1c — Confirm the chain filters on `active`.** Read the defs of `url_scores_base` and `refresh_url_scores_v1` and confirm they gate on `us.active` (and join `prompts_outputs.active`/`prompts.active`). Report the exact filter found; flag if any level omits an active gate.

---

## Phase 2 · Classify & refresh (the two pipeline ops)
Run in this order so labels flow into the rollups.

**2a — URL classification** (label URLs not yet classified):
```bash
cd /Users/grantsimmonds/Documents/dev/branded-llm/brand_score_pipeline && set -a && source .env && set +a
KEY="${API_KEY:-$BRAND_SCORE_API_KEY}"
curl -s -X POST "https://brand-score-api.fly.dev/api/workflows/batch/url-classification" \
  -H "Content-Type: application/json" -H "X-API-Key: $KEY" \
  -d '{"batch_id":"<batch_id>"}' | python3 -m json.tool
```
Poll the returned workflow id (`GET /api/workflows/<id>/status`) to completion. (Docs: `https://workflow.zebora.io/docs#/batch-scoring/start_url_classification_workflow_api_workflows_batch_url_classification_post`.)

**2b — Refresh the URL rollups** (long-running — REQUIRES the timeout):
```sql
SET LOCAL statement_timeout = '10min';
SELECT public.refresh_url_scores_v1('<batch_id>'::uuid);
```
Run via psql (`psql "$DATABASE_URL" -c "SET statement_timeout='10min'; SELECT public.refresh_url_scores_v1('<batch_id>'::uuid);"`), ideally in the background — it commonly takes several minutes. Everything below reads post-refresh data.

---

## Phase 3 · Dashboard output check ← what users actually see
The dashboard reads `get_domain_scores_filtered_v5` / `get_url_scores_filtered_v5`. **Do NOT call these functions for QA** — they are `SECURITY DEFINER` and gated by `can_access_batch(p_batch_id)` = `is_super_admin() OR batch.brand_id ∈ current_user_brand_ids()`. A headless psql/MCP connection has no `auth.uid()`, so the gate returns **false → the functions return 0 rows even when data exists** (a 0-row result here is an auth artifact, NOT a data bug).

**The dashboard's true source is `mv_url_scores_enriched_v3`** (what those functions aggregate); it matches the raw active `url_scores`. **Do NOT use `urls_scores_domain` / `url_scores_list` as the proxy — that family is inflated ~1.6× (see Phase 4) and is NOT what the dashboard shows.**

Batch totals (fast — plain `count(*)` on the mv is indexed by batch_id):
```sql
SELECT (SELECT count(*) FROM mv_url_scores_enriched_v3 WHERE batch_id='<batch_id>') AS dashboard_url_rows,
       (SELECT count(*) FROM mv_url_scores_enriched_v3 WHERE batch_id='<batch_id>' AND is_brand_owned) AS brand_owned;
```
Top domains **as the dashboard shows** — a GROUP BY over the mv is heavy, so run via **psql** (bounded timeout), not the MCP:
```bash
psql "$DATABASE_URL" -c "SET statement_timeout='4min';
  SELECT lower(domain) AS domain, bool_or(is_brand_owned) AS brand_owned, count(*) AS frequency
  FROM mv_url_scores_enriched_v3 WHERE batch_id='<batch_id>'
  GROUP BY lower(domain) ORDER BY frequency DESC LIMIT 25;"
```
For a quick top-domain *ranking* the `urls_scores_domain` order is usually similar, but its **counts are inflated** — always verify any surfaced count against the mv/raw (Phase 4b) before reporting it. If `mv_url_scores_enriched_v3` is empty for the batch, THAT is the real "refresh didn't run" signal. (`can_access_batch(<batch_id>)` is false headlessly, so the live dashboard view itself can only be confirmed by an authenticated user via the API.)

---

## Phase 4 · Cross-path reconciliation ← THE important check
There are **two rollup paths and they can disagree**. Reconcile the DASHBOARD source against the raw truth, and treat `urls_scores_domain` as a *separate, historically-inflated* rollup — never as ground truth.

**4a — Dashboard vs raw (must match, ± small exclusion delta):**
```sql
SELECT (SELECT count(*) FROM url_scores WHERE batch_id='<batch_id>' AND active) AS raw_active,
       (SELECT count(*) FROM mv_url_scores_enriched_v3 WHERE batch_id='<batch_id>') AS dashboard_mv,
       (SELECT SUM(frequency) FROM urls_scores_domain WHERE batch_id='<batch_id>') AS urls_scores_domain_family;
```
- `dashboard_mv` should ≈ `raw_active` (differ only by the documented exclusions — `url_scores_base` drops `images.openai.com` + brand-pillar categories). This is what the dashboard (`get_*_filtered_v5` → `mv_url_scores_enriched_v3`) actually shows.
- **`urls_scores_domain_family` is inflated** — observed **11,245 vs ~6,700–7,000** (~1.6×) on batch 3110a4d0. **Flag the ratio; do NOT treat this family as the dashboard.** (The `url_scores_list`/`urls_scores_domain`/`urls_scores_domain_type` trio agree *with each other* but not with the dashboard — reconciling them against each other is a false pass.)

**4b — Per-domain spot check** (repeat for the top few domains): raw active `url_scores` count for a domain **must equal** its `mv_url_scores_enriched_v3` count; note where `urls_scores_domain.frequency` diverges.
```sql
SELECT (SELECT count(*) FROM url_scores WHERE batch_id='<batch_id>' AND active AND domain='<d>') AS raw_active,
       (SELECT count(*) FROM mv_url_scores_enriched_v3 WHERE batch_id='<batch_id>' AND lower(domain)='<d>') AS dashboard_mv,
       (SELECT frequency FROM urls_scores_domain WHERE batch_id='<batch_id>' AND domain='<d>') AS urls_scores_domain;
```
Row counts across granularity levels still differ legitimately — but a `raw_active ≠ dashboard_mv` per domain, or a large `urls_scores_domain_family / dashboard_mv` ratio, is a real inflation bug to report.

---

## Phase 5 · Suspect-domain QA
Flag domains that shouldn't be scored as citations — **image/asset CDNs, thumbnails, trackers, raw asset URLs**. Read the **dashboard source `url_scores_base`** (not `urls_scores_domain`) so you only flag domains that actually reach users — a domain that appears *only* in `urls_scores_domain` (e.g. `images.openai.com`, already excluded by `url_scores_base` + the mv) is NOT on the dashboard and is a false alarm:
```sql
SELECT domain, count(*) AS frequency
FROM url_scores_base WHERE batch_id='<batch_id>'
  -- anchor asset/CDN patterns to a subdomain boundary to avoid false positives
  -- (e.g. `s3[.-]` alone matches "stmartinS3-16.org"; require a leading dot)
  AND ( domain ~* '(\.cloudfront\.net|\.akamai|\.fastly|\.cdn\.|^cdn\.|imgix|\.gstatic\.|googleusercontent|fbcdn|\.ytimg\.|cloudinary|\.s3[.-]|\.rackcdn\.|blob\.core\.windows|\.wp\.com)'
     -- image / asset subdomains + known LLM asset hosts (e.g. images.openai.com was #5 by freq on a real batch)
     OR domain ~* '^(images?|img|static|assets|media)\.'
     OR domain ~* '(images\.openai\.com|oaidalle|oaiusercontent|files\.oai|dalle)'
     OR domain ~* '(doubleclick|googletagmanager|google-analytics|gravatar|scorecardresearch)'
     OR domain ~* '^(encrypted-tbn|lookaside)' )
GROUP BY domain ORDER BY frequency DESC;
```
Plus raw asset URLs:
```sql
SELECT url, domain FROM url_scores_base
WHERE batch_id='<batch_id>' AND url ~* '\.(png|jpe?g|gif|svg|webp|ico|css|js|woff2?|pdf|mp4)(\?|$)'
LIMIT 50;
```
**Report only** — present as candidates for a suspect-domain denylist; do NOT write one.

---

## Phase 6 · Duplication & count integrity
- Same `(output_id, url)` scored more than once (dup rows inflating frequency):
```sql
SELECT url, output_id, count(*) rows
FROM url_scores WHERE batch_id='<batch_id>' AND active
GROUP BY url, output_id HAVING count(*) > 1 ORDER BY rows DESC LIMIT 30;
```
- URL variants that should collapse but don't (trailing slash, `?utm_*`, `#fragment`, `http` vs `https`, `www.`): group by a normalized url and show where >1 raw form maps to it.
- Domain whose `frequency` is implausible vs its distinct-URL / distinct-output count (over-counting).
Report counts + worst examples.

---

## Phase 7 · Classification QA
- **Unclassified / weak:** count + top-frequency domains where `domain_type IS NULL OR domain_type='other'` (surface for hand-labelling — report only).
- **Label anomalies:** singleton / near-duplicate classes in `url_classification.classification` (e.g. `industry-author` vs `industry-authority`, `testimonials-reviews`) — merge candidates.
```sql
SELECT classification, count(*) FROM url_classification GROUP BY 1 HAVING count(*) <= 2 ORDER BY 2;
```
- **`is_brand_owned` sanity:** brand-owned domains that don't match the brand's own domain(s); competitor domains flagged brand-owned.

---

## Phase 8 · Anomaly detection & drift (baseline LEARNED from history)
Build a baseline from the brand's prior batches (Phase 0 list) — do **not** use fixed thresholds.

**8a — Learn the baseline.** For the prior N batches, compute per-metric mean + stddev:
- total distinct domains, total distinct URLs, total frequency
- brand-owned domain share, `other`/null domain-type share
- domain_type distribution (share per type, from `urls_scores_domain_type`)
- top-domain concentration (share of the #1 domain)
```sql
WITH per_batch AS (
  SELECT batch_id,
         sum(sum) AS total_freq,
         sum(sum) FILTER (WHERE domain_type='other') / NULLIF(sum(sum),0) AS other_share
  FROM urls_scores_domain_type
  WHERE batch_id = ANY (:prior_batch_ids)
  GROUP BY batch_id )
SELECT avg(total_freq) mean_freq, stddev_pop(total_freq) sd_freq,
       avg(other_share) mean_other, stddev_pop(other_share) sd_other
FROM per_batch;
```
**8b — Flag current-batch deviations.** Compute the same metrics for the target batch; flag any that fall outside `mean ± 2·stddev` (or, with <3 priors, outside ±25% of the single prior — state which rule was used). Report as a ranked "worth a look" list, not pass/fail.

**8c — Top-domain drift.** Diff top-15 domains (by frequency) current vs most-recent prior batch: new entrants, dropped domains, and any domain whose frequency moved > the learned band. Early warning for extraction/classification regressions.

If no prior batch exists: state that plainly and skip 8 (report current-batch absolutes only).

---

## End-of-run summary
```
=== URL / Citation Check — <brand_name> (<batch_id>) ===
Completeness   stale-active leak: X · under-scored: Y · active-gate on chain: ok/❌
Pipeline ops   classification run: ✔ (N labelled) · refresh_url_scores_v1: ✔ (ms)
Dashboard      domains: X · urls: Y · brand-owned: Z% · other/null: W%
Reconciliation base==list==domain==dashboard: ✓/✗ (list mismatches)
Suspect domains  N flagged (image CDN / tracker / asset)  [report only]
Duplication    dup rows: N · uncollapsed variants: M
Classification other/null: X · singleton labels: [...]
Anomalies (learned baseline, n_prior=K)  [ranked list]
Drift vs <prior_batch>  [top-domain in/out, metrics outside band]
```

## Guardrails
- **Reporting-only.** NEVER write denylists, relabels, alias/dimension edits, or `active` flips. Surface findings + the SQL a human *could* run, but do not run it.
- The only permitted side effects are **Phase 2** (classification workflow + `refresh_url_scores_v1`) — both are pipeline operations, not data-quality writes. Confirm before triggering the classification workflow if the batch is large.
- Anomaly thresholds are **learned from the brand's prior batches**, never hard-coded. Always report `n_prior` and which rule was applied.
- **Out of scope:** the PR/citation-crawl module (`url_crawl_*`, page answerability/evidence/framing, `fact_citation_url`). Do not query or refresh those here.
- If `DATABASE_URL` isn't set, stop and tell the user to check `.env`.
