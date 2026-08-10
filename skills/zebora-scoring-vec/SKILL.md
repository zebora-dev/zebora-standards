---
name: zebora-scoring-vec
description: "Visibility Entity Checker (VEC) — interactive QA and management tool for the Zebora visibility scoring pipeline. Walks through the full lifecycle one phase at a time: matview refresh, QA triage, entity review, resolution, enrichment, brand/entity canonicalisation, and feedback loop suggestions. Use after any large batch run to validate scoring quality and close the loop on entity extraction accuracy."
user-invokable: true
argument-hint: "[phase] <batch_id>"
---

# zebora-scoring-vec — Visibility Entity Checker

**Invocation:** `/zebora-scoring-vec [phase] <batch_id_or_brand_id>`

## Quick reference

| Command | What it does |
|---|---|
| `/zebora-scoring-vec <batch_id>` | Start the guided walkthrough at Phase 0/1, then pause after each phase (all 10 phases in order) |
| `/zebora-scoring-vec qa <batch_id>` | Jump to QA triage only (Phase 2) |
| `/zebora-scoring-vec entities <batch_id>` | Jump to entity extraction review (Phase 3) |
| `/zebora-scoring-vec resolve <batch_id>` | Jump to resolution & canonicalization (Phase 4) |
| `/zebora-scoring-vec enrich <brand_id>` | Jump to enrichment — GPT + Gemini (Phase 5) |
| `/zebora-scoring-vec canonicalise <brand_id>` | Brand/entity duplicate merge review (Phase 6) |
| `/zebora-scoring-vec refresh` | Refresh matviews only (Phase 7) |
| `/zebora-scoring-vec target <batch_id>` | Target brand deep-dive (Phase 8) |
| `/zebora-scoring-vec review <batch_id>` | Entity metrics QA review (Phase 9) |
| `/zebora-scoring-vec feedback <batch_id>` | Generate prompt/context improvement suggestions (Phase 10) |

---

## Operating mode — phase-gated workflow

This skill must run **one phase at a time**. Do not execute the full lifecycle in
one uninterrupted run unless the user explicitly asks for a fully automated run.

Default behaviour:

1. Run the requested phase only.
2. Print a concise phase summary.
3. List recommended actions, separating:
   - actions already taken,
   - actions needing user approval,
   - suggested next phase.
4. Stop and wait for the user to approve actions or ask to continue.

When invoked as `/zebora-scoring-vec <batch_id>` with no phase argument:

1. Run Phase 0 setup and Phase 1 health check.
2. Print the Phase 1 review.
3. Ask whether to continue to Phase 2 QA triage.
4. Do not continue automatically.

For write phases, always use an explicit approval gate:

- Phase 4 resolution may write aliases/entities/candidate statuses.
- Phase 5 enrichment may write websites/logos/metadata.
- Phase 6 canonicalisation may write aliases and mark redundant rows inactive.
- Phase 10 prompt/context feedback must never update prompt contexts without an
  exact diff and explicit approval.

Use this handoff format after every phase:

```
=== Phase <n> Review — <phase name> ===

Summary
  <key counts and findings>

Actions taken
  <writes performed, or "None">

Recommended actions
  <approval-needed actions, or "None">

Next phase
  <phase number and name>

Waiting for approval/next instruction.
```

If a phase reveals a blocker, stop there and explain the blocker. Do not skip
ahead.

---

## Project context

- **Repo:** `/Users/grantsimmonds/Documents/dev/branded-llm/brand_score_pipeline`
- **Pipeline docs:** `docs/new_brand_visibility_setup.md` and `docs/ARCHITECTURE.md`
- **Key modules:** `db/entity_resolution_v3.py`, `db/entity_enrichment_v3.py`, `db/entity_enrichment_gemini.py`, `db/refresh_views.py`
- **Key scripts:** `scripts/refresh_entity_metrics_matviews.py`
- **DB:** PostgreSQL via `.env` (SUPABASE_URL / SUPABASE_SERVICE_KEY / DATABASE_URL)
- **Python env:** `poetry run python` from the repo root (`.venv/bin/python` does not exist)

When running any Python, always `cd` to the repo root first: `cd /Users/grantsimmonds/Documents/dev/branded-llm/brand_score_pipeline`

**Jump-in note:** When the user invokes a named phase directly (e.g. `/zebora-scoring-vec review <batch_id>`), always run Phase 0 first to resolve `batch_id → brand_id` and `brand_name` before executing the requested phase. These values are referenced throughout.

---

## Phase 0 · Setup — resolve batch_id to brand_id

Before starting, resolve the batch_id to a brand_id if needed:

```sql
SELECT
  b.id AS batch_id,
  b.brand_id,
  br.name AS brand_name,
  b.status,
  (SELECT COUNT(*) FROM prompts_outputs WHERE batch_id = b.id AND active = true) AS active_outputs,
  (SELECT COUNT(*) FROM prompts_outputs WHERE batch_id = b.id) AS total_outputs,
  (SELECT COUNT(*) FROM scores_visibility WHERE batch_id = b.id AND active = true) AS scored_outputs
FROM batches b
JOIN brands br ON br.id = b.brand_id
WHERE b.id = '<batch_id>';
```

Run via psql or Supabase MCP. Print `brand_id`, `brand_name`, `active_outputs`, `total_outputs`, `scored_outputs` so the user can confirm the right batch before proceeding.

Flag if `scored_outputs < active_outputs` — some active outputs haven't been scored yet.

Phase gate: after Phase 0, confirm the resolved `brand_id` and `brand_name`.
If the batch looks wrong, stop. If it looks right, proceed only to Phase 1 unless
the user requested a different specific phase.

---

## Phase 1 · Refresh & health check

### 1a — Check llm_model_weightings

Before refreshing, warn if missing — views will return empty:

```sql
SELECT provider_key, weight, parent_provider_key
FROM llm_model_weightings
WHERE batch_id = '<batch_id>';
```

If no rows: tell the user this must be seeded first (see `docs/new_brand_visibility_setup.md` Step 5a). Do not proceed with refresh until confirmed.

### 1b — Run matview refresh

```bash
cd /Users/grantsimmonds/Documents/dev/branded-llm/brand_score_pipeline && \
poetry run python scripts/refresh_entity_metrics_matviews.py
```

Report each view refreshed. If `mv_entity_metrics_tag_by_llm_brand` times out, note it — the key reporting views complete before it.

### 1c — Batch health summary

After refresh, print a health summary table. Only active prompt outputs whose prompt
measurements include `Visibility` or `Sentiment` are expected to have visibility-v3
scores, so the summary counts against that eligible set rather than all outputs:

```sql
WITH eligible_outputs AS (
  SELECT po.id, po.brand_id
  FROM prompts_outputs po
  JOIN prompts p ON p.id = po.prompt_id AND p.active = true
  WHERE po.batch_id = '<batch_id>'
    AND po.active = true
    AND (
      p.measurements::text ILIKE '%Visibility%'
      OR p.measurements::text ILIKE '%Sentiment%'
    )
),
scored_outputs AS (
  SELECT DISTINCT ON (sv.output_id)
         sv.output_id,
         sv.metadata
  FROM scores_visibility sv
  JOIN eligible_outputs eo ON eo.id = sv.output_id
  WHERE sv.batch_id = '<batch_id>'
    AND sv.active = true
    AND sv.scorer_model = 'visibility-v3'
  ORDER BY sv.output_id, sv.id DESC
),
pending_candidates AS (
  SELECT brand_id, COUNT(*) AS pending_count
  FROM visibility_entity_resolution_candidates
  WHERE status = 'pending'
  GROUP BY brand_id
)
SELECT
  COUNT(eo.id) AS total_outputs,
  COUNT(so.output_id) AS scored,
  ROUND(COUNT(so.output_id)::numeric / NULLIF(COUNT(eo.id), 0) * 100, 1) AS pct_scored,
  COUNT(CASE WHEN so.metadata->'entity_qa'->>'overall_status' = 'pass' THEN 1 END) AS qa_pass,
  COUNT(CASE WHEN so.metadata->'entity_qa'->>'overall_status' = 'review' THEN 1 END) AS qa_review,
  COUNT(CASE WHEN so.metadata->'entity_qa'->>'overall_status' = 'fail' THEN 1 END) AS qa_fail,
  COALESCE(MAX(pc.pending_count), 0) AS pending_candidates
FROM eligible_outputs eo
LEFT JOIN scored_outputs so ON so.output_id = eo.id
LEFT JOIN pending_candidates pc ON pc.brand_id = eo.brand_id;
```

Flag if: `pct_scored < 95%`, `qa_fail > 0`, `qa_review > 10%`, or `pending_candidates > 20`.

Phase gate: after Phase 1, summarize health, refresh status, and any flags.
Recommend whether to continue to Phase 2 QA triage. Stop and wait.

---

## Phase 2 · QA triage

### 2a — QA distribution

```sql
SELECT
  sv.metadata->'entity_qa'->>'overall_status' AS status,
  COUNT(*) AS count,
  ROUND(AVG((sv.metadata->'entity_qa'->>'overall_score')::numeric), 3) AS avg_score,
  MIN((sv.metadata->'entity_qa'->>'overall_score')::numeric) AS min_score
FROM scores_visibility sv
JOIN prompts_outputs po ON po.id = sv.output_id
WHERE po.batch_id = '<batch_id>' AND sv.active = true
  AND sv.metadata->'entity_qa' IS NOT NULL
GROUP BY 1 ORDER BY 1;
```

**Thresholds to flag:**
- Pass rate < 85% → warning
- Any `fail` → critical
- Avg pass score < 0.93 → worth investigating

### 2b — Surface top failing outputs

Fetch the 10 lowest-scoring outputs with their QA summaries and entity reviews:

```sql
SELECT sv.output_id,
       ROUND((sv.metadata->'entity_qa'->>'overall_score')::numeric, 3) AS score,
       sv.metadata->'entity_qa'->>'overall_status' AS status,
       sv.metadata->'entity_qa'->>'summary' AS summary,
       sv.metadata->'entity_qa'->'entity_reviews' AS entity_reviews
FROM scores_visibility sv
JOIN prompts_outputs po ON po.id = sv.output_id
WHERE po.batch_id = '<batch_id>'
  AND sv.active = true
  AND sv.metadata->'entity_qa' IS NOT NULL
ORDER BY (sv.metadata->'entity_qa'->>'overall_score')::numeric ASC
LIMIT 10;
```

For each failing output, parse `entity_reviews` and summarise the issue types (wrong entity type, bad canonicalization, hallucinated entity, missing brand attribution). Group similar issues to spot patterns.

### 2c — Pattern clustering

After reviewing the failures, cluster them into categories:
- **Canonicalization errors** — entity name not mapping to canonical form
- **Wrong entity type** — e.g. book extracted as organisation
- **Noise extraction** — generic terms extracted as entities
- **Missing brand** — brand field empty when it should be set
- **Target brand confusion** — target brand extracted as a competitor entity

Present a ranked list: `Issue type | Count | Example entities`

---

## Phase 3 · Entity extraction review

### 3a — Top entities for the batch

Use the entity metrics matview (already normalised via `normalize_company_name()`) rather than joining raw extracted strings, which would miss "the " stripping and "&→and" rules:

```sql
SELECT
  entity_brand_name,
  entity_name,
  entity_id,
  entity_key,
  ROUND(mention_total::numeric, 2) AS mention_total,
  mentions_count,
  competitor_type,
  target_brand,
  target_entity
FROM mv_entity_metrics_overall_llm_brand_entity_v2
WHERE batch_id = '<batch_id>'
  AND entity_id IS NOT NULL
ORDER BY mention_total DESC
LIMIT 30;
```

### 3b — Pending resolution candidates

```sql
SELECT raw_brand, raw_entity, observed_count,
       match_source, confidence,
       suggested_entity_brand_id, suggested_visibility_entity_id,
       metadata->>'qa_flag_reason' AS qa_flag_reason,
       LEFT(sample_source_text::text, 150) AS sample
FROM visibility_entity_resolution_candidates
WHERE brand_id = '<brand_id>'
  AND status = 'pending'
ORDER BY observed_count DESC
LIMIT 25;
```

Highlight: candidates with `observed_count > 3` (high-frequency unresolved entities — most impactful to fix).

### 3c — Unenriched dimension rows

```sql
SELECT 'brand' AS type, name, normalized_brand_key AS key, website
FROM visibility_entity_brands
WHERE brand_id = '<brand_id>' AND active = true AND website IS NULL
UNION ALL
SELECT 'entity', ve.name, ve.normalized_entity_key, ve.website
FROM visibility_entities ve
WHERE ve.brand_id = '<brand_id>' AND ve.active = true AND ve.website IS NULL
ORDER BY type, name;
```

---

## Phase 4 · Resolution & canonicalization

### 4a — Run entity resolution

```python
import sys, os
sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv()
from db.entity_resolution_v3 import entity_resolution_v3

result = entity_resolution_v3(batch_id=BATCH_ID)
print(f"Status: {result['status']}")
print(f"Phase 1 auto-resolved: {result.get('phase1_resolved', 0)}")
print(f"Phase 2 LLM resolved: {result.get('phase2_resolved', 0)}")
print(f"Alias QA flagged: {result.get('alias_qa_flagged', 0)}")
print(f"Still pending: {result.get('still_pending', 0)}")
```

Then run rescan to catch anything missed:

```python
from db.entity_resolution_v3 import rescan_unmatched_for_batch
rescan_result = rescan_unmatched_for_batch(batch_id=BATCH_ID)
print(f"Rescan pushed {rescan_result.get('pushed', 0)} new candidates")
```

### 4b — Human review queue

After resolution, show what needs human attention:

```sql
SELECT id, raw_brand, raw_entity, observed_count,
       match_source, confidence,
       suggested_entity_brand_id,
       suggested_visibility_entity_id,
       metadata->>'qa_flag_reason' AS qa_flag_reason,
       LEFT(sample_source_text::text, 150) AS sample
FROM visibility_entity_resolution_candidates
WHERE brand_id = '<brand_id>'
  AND status = 'pending'
  AND (suggested_visibility_entity_id IS NOT NULL
       OR match_source = 'llm_qa_flagged'
       OR observed_count >= 3)
ORDER BY observed_count DESC;
```

For each row, present to the user:
- The raw entity name
- The suggested canonical mapping (if any)
- The QA flag reason
- A sample of the source text it appeared in

Ask the user: **accept suggestion / provide correct mapping / mark as noise**

Based on their answer, either:
- Write the alias: `INSERT INTO visibility_entity_aliases (brand_id, visibility_entity_id, alias_name, alias_key, active) VALUES (...)`  — both `alias_name` (display) and `alias_key` (normalised lowercase) are required NOT NULL
- Write brand alias: `INSERT INTO visibility_entity_brand_aliases (brand_id, entity_brand_id, alias_name, alias_key, active) VALUES (...)`
- Mark ignored: `UPDATE visibility_entity_resolution_candidates SET status = 'ignored' WHERE id = ...`
- When resolving candidates: `confidence` column is **numeric** (use `1.0` not `'high'`)

After writing, confirm back how many were resolved.

---

## Phase 5 · Enrichment

### 5a — Run GPT enrichment first

```python
from db.entity_enrichment_v3 import entity_enrichment_v3
result = entity_enrichment_v3(brand_id=BRAND_ID)
print(f"Brands enriched: {result['brands_enriched']}")
print(f"Entities enriched: {result['entities_enriched']}")
```

### 5b — Run Gemini enrichment for remaining nulls

```python
from db.entity_enrichment_gemini import entity_enrichment_gemini
result = entity_enrichment_gemini(brand_id=BRAND_ID, overwrite=False, use_grounding=True)
print(f"Brands enriched: {result['brands_enriched']}")
print(f"Entities enriched: {result['entities_enriched']}")
print(f"Skipped (low confidence): {result['skipped_low_confidence']}")
for r in result['results']:
    if r['action'] == 'updated':
        print(f"  {r['name']}: {r['new_website']} ({r['confidence']})")
```

### 5c — Report final enrichment coverage

After both passes, re-run the unenriched query from Phase 3c and report how many remain. If > 10 entities still missing websites, suggest the user inspect them manually — they may be generic/unresolvable.

---

## Phase 6 · Brand & entity canonicalisation review

After resolution and enrichment, the pipeline may have created near-duplicate
dimension rows. Run a separate merge review for canonical brands and canonical
entities before producing final feedback suggestions.

This phase has two independent passes:

1. **Brand canonicalisation** — merge duplicate `visibility_entity_brands` rows.
2. **Entity canonicalisation** — merge duplicate `visibility_entities` rows.

Do not delete rows. For approved merges, write an alias pointing the redundant
surface form at the canonical row, then mark the redundant dimension row
`active = false`.

### 6a — Inventory all active brands

Fetch the full active brand list:

```sql
SELECT id, name, normalized_brand_key, website, metadata
FROM visibility_entity_brands
WHERE brand_id = '<brand_id>'
  AND active = true
ORDER BY normalized_brand_key, name;
```

Analyse this list for duplicate or near-duplicate canonical brands. Look for:

- Same website/domain with different names.
- Same normalized key except suffixes such as `uk`, `official`, `guide`,
  `resources`, `parent`, `parents`, `hub`.
- Punctuation/plural variants.
- Brand aliases that were promoted into separate brand rows.
- LLM-created variants that should be an alias of a known canonical brand.

Use SQL to surface obvious exact/domain overlaps:

```sql
SELECT lower(regexp_replace(coalesce(website, ''), '^https?://(www\.)?', '')) AS domain_key,
       COUNT(*) AS rows,
       jsonb_agg(jsonb_build_object('id', id, 'name', name, 'key', normalized_brand_key)) AS brands
FROM visibility_entity_brands
WHERE brand_id = '<brand_id>' AND active = true AND website IS NOT NULL
GROUP BY 1
HAVING COUNT(*) > 1
ORDER BY rows DESC;
```

Then do a fuzzy/semantic review over the full list. Present proposed merges as:

`Canonical brand | Redundant brand | Reason | Evidence`

Example:

`Amazing Apprenticeships | Amazing Apprenticeships (Parents) | parent-facing variant of same brand | same domain / same normalized prefix`

Ask for explicit user approval before writing any merge.

### 6b — Apply approved brand merges

For each approved brand merge:

1. Insert or reactivate a brand alias from the redundant brand name/key to the canonical brand.
2. Re-parent child entities from the redundant brand to the canonical brand where there is no entity-key conflict.
3. For child entity conflicts, merge the redundant entity into the canonical entity using the entity merge process in Phase 6d.
4. Mark the redundant brand row inactive.

Use one transaction per approved merge:

```sql
BEGIN;

-- 1. Alias redundant brand to canonical brand.
INSERT INTO visibility_entity_brand_aliases (
  brand_id, entity_brand_id, alias_name, alias_key, active
)
VALUES (
  '<brand_id>',
  <canonical_entity_brand_id>,
  '<redundant_brand_name>',
  '<redundant_normalized_brand_key>',
  true
)
ON CONFLICT (brand_id, alias_key) DO UPDATE
SET entity_brand_id = EXCLUDED.entity_brand_id,
    alias_name = EXCLUDED.alias_name,
    active = true,
    updated_at = now();

-- 2. Move non-conflicting child entities to the canonical brand.
UPDATE visibility_entities ve
SET entity_brand_id = <canonical_entity_brand_id>,
    updated_at = now()
WHERE ve.brand_id = '<brand_id>'
  AND ve.entity_brand_id = <redundant_entity_brand_id>
  AND ve.active = true
  AND NOT EXISTS (
    SELECT 1
    FROM visibility_entities existing
    WHERE existing.brand_id = ve.brand_id
      AND existing.entity_brand_id = <canonical_entity_brand_id>
      AND existing.normalized_entity_key = ve.normalized_entity_key
      AND existing.active = true
  );

-- 3. Deactivate redundant brand row.
UPDATE visibility_entity_brands
SET active = false, updated_at = now()
WHERE id = <redundant_entity_brand_id>
  AND brand_id = '<brand_id>';

COMMIT;
```

After brand merges, report:

- Brand aliases written.
- Brand rows deactivated.
- Child entities re-parented.
- Child entity conflicts that need Phase 6d handling.

### 6c — Inventory all active entities

Fetch the full active entity list, grouped by canonical parent brand:

```sql
SELECT ve.id,
       veb.id AS entity_brand_id,
       veb.name AS brand,
       ve.name AS entity,
       ve.normalized_entity_key,
       ve.entity_type,
       ve.website,
       ve.metadata
FROM visibility_entities ve
JOIN visibility_entity_brands veb
  ON veb.id = ve.entity_brand_id
 AND veb.brand_id = ve.brand_id
 AND veb.active = true
WHERE ve.brand_id = '<brand_id>'
  AND ve.active = true
ORDER BY veb.name, ve.normalized_entity_key, ve.name;
```

Analyse this list for duplicate or near-duplicate canonical entities. Keep the
brand pass separate from the entity pass: entity duplicates should normally be
reviewed within the same canonical parent brand unless there is clear evidence
the parent brand merge in Phase 6a should happen first.

Look for:

- Same website/domain under the same parent brand.
- Resource-title variants under the same parent brand.
- Parent-resource suffix variants such as `for parents`, `parent hub`,
  `resources`, `guide`, `guides`, `parents and carers`, `parent and carer`.
- Entity rows where one is clearly the parent canonical resource and the other
  is a verbose surface variant.

Example:

`Amazing Apprenticeships resources` and
`Amazing Apprenticeships resources for parents` should usually merge into the
cleaner canonical entity, with the redundant name retained as an alias.

Present proposed merges as:

`Parent brand | Canonical entity | Redundant entity | Reason | Evidence`

Ask for explicit user approval before writing any merge.

### 6d — Apply approved entity merges

For each approved entity merge:

1. Insert or reactivate an entity alias from the redundant entity name/key to the canonical entity.
2. Mark the redundant entity row inactive.
3. Preserve metadata by appending a merge note to the redundant row.

Use one transaction per approved merge:

```sql
BEGIN;

INSERT INTO visibility_entity_aliases (
  brand_id, visibility_entity_id, alias_name, alias_key, active
)
VALUES (
  '<brand_id>',
  <canonical_visibility_entity_id>,
  '<redundant_entity_name>',
  '<redundant_normalized_entity_key>',
  true
)
ON CONFLICT (brand_id, alias_key) DO UPDATE
SET visibility_entity_id = EXCLUDED.visibility_entity_id,
    alias_name = EXCLUDED.alias_name,
    active = true,
    updated_at = now();

UPDATE visibility_entities
SET active = false,
    metadata = metadata || jsonb_build_object(
      'merged_into_visibility_entity_id', <canonical_visibility_entity_id>,
      'merged_reason', '<short_reason>',
      'merged_at', now()::text,
      'merged_by', 'zebora-scoring-vec'
    ),
    updated_at = now()
WHERE id = <redundant_visibility_entity_id>
  AND brand_id = '<brand_id>';

COMMIT;
```

After entity merges, report:

- Entity aliases written.
- Entity rows deactivated.
- Any merges skipped because the canonical target was ambiguous.

### 6e — Post-merge checks

After approved brand/entity merges, re-run these checks:

```sql
SELECT COUNT(*) AS active_brands
FROM visibility_entity_brands
WHERE brand_id = '<brand_id>' AND active = true;

SELECT COUNT(*) AS active_entities
FROM visibility_entities
WHERE brand_id = '<brand_id>' AND active = true;
```

If merges were applied, run Phase 7 (refresh) so the metric matviews pick up the
merges before any downstream review. Do not refresh automatically unless the user
confirms.

Phase gate: after Phase 6, summarize proposed merges or applied merges. If only
proposals were generated, stop for approval. If merges were applied, report
post-merge counts and recommend a Phase 7 metrics refresh. Do not refresh
automatically unless the user confirms.

---

## Phase 7 · Refresh matviews

Run this phase whenever aliases, dimension rows, or enrichment data have changed — after Phase 4 (if aliases were written), after Phase 5 (if enrichment ran), after Phase 6 (if merges were applied), and again after Phase 9d (if further aliases were written). It is safe to run multiple times.

### 7a — Refresh entity metrics matviews

```sql
SELECT public.refresh_entity_metrics_v2('<batch_id>'::uuid);
```

Run via psql with an extended timeout:

```bash
psql "$DATABASE_URL" -c "SET statement_timeout = '10min'; SELECT public.refresh_entity_metrics_v2('<batch_id>'::uuid);"
```

Report the refresh result JSON (view names + ms). If `refresh_url_scores_v1` is also needed (e.g. URL scores changed), prompt the user — it takes ~5 min and requires their confirmation before running.

---

## Phase 8 · Target brand deep-dive

This phase focuses specifically on the target brand and its entities — checking whether the pipeline has captured all mentions, and whether any have been missed.

### 8a — Target brand entity summary

Fetch the target brand and all its entities from the view:

```sql
SELECT
  entity_name,
  entity_id,
  entity_key,
  ROUND(mention_total::numeric, 2) AS mention_total,
  ROUND(visibility_raw::numeric, 4) AS visibility_raw,
  mentions_count,
  array_length(output_ids, 1) AS output_count,
  output_ids
FROM v_entity_metrics_with_sources
WHERE batch_id = '<batch_id>'
  AND target_brand = true
ORDER BY mention_total DESC;
```

Present as a table. Note which entities are fully resolved (`entity_id IS NOT NULL`) vs unresolved-keyed (`entity_id IS NULL`).

### 8b — Raw response scan for missed mentions

For each entity name and key aliases, scan `prompts_outputs.response` directly to find outputs where the brand/entity appears in the raw text but was NOT captured in scoring:

```sql
SELECT po.id AS output_id, LEFT(po.response, 300) AS response_preview
FROM prompts_outputs po
WHERE po.batch_id = '<batch_id>'
  AND po.active = true
  AND po.response ILIKE '%<target_brand_name>%'
  AND po.id NOT IN (
    SELECT UNNEST(output_ids)
    FROM v_entity_metrics_with_sources
    WHERE batch_id = '<batch_id>'
      AND target_brand = true
      AND output_ids IS NOT NULL
  )
LIMIT 20;
```

Use `brand_name` resolved in Phase 0. Run for the primary brand name, and repeat for each top entity name from Phase 8a (e.g. sub-brands, products). If misses are found:
- Show the output preview and explain why the entity likely wasn't captured (entity not in alias tables, extraction missed it, wrong entity type, etc.)
- Flag how many outputs are affected
- Suggest whether the fix is an alias, a prompt context change, or a re-score

### 8c — Cross-check output_ids vs entity mention counts

For each target brand entity row, verify that `mentions_count` roughly aligns with `array_length(output_ids, 1)`. A large discrepancy (e.g. 50 mention_total but only 3 output_ids) suggests aggregation issues or missing fact rows. Flag any rows where:

```
mention_total > array_length(output_ids, 1) * 3
```

These may indicate duplicate scoring, over-counting, or an alias that is pulling in unrelated outputs.

---

## Phase 9 · Entity metrics QA review

A systematic row-by-row review of `v_entity_metrics_with_sources` to validate extraction quality, counts, and entity correctness.

### 9a — Full entity metrics pull

```sql
SELECT
  entity_brand_name,
  entity_name,
  entity_id,
  entity_key,
  ROUND(mention_total::numeric, 2) AS mention_total,
  mentions_count,
  array_length(output_ids, 1) AS output_count,
  entities
FROM v_entity_metrics_with_sources
WHERE batch_id = '<batch_id>'
ORDER BY mention_total DESC;
```

### 9b — Row-by-row validation

For each row, check:

1. **Source text plausibility** — read `entities[*].source_text` values. Does the source text actually reference this entity? Flag rows where source text is just the entity name (no context) or references a different entity entirely.

2. **Mention count vs output count alignment** — `mention_total` should be roughly proportional to `array_length(output_ids, 1)`. Flag rows where `mention_total / output_count > 5` (entity mentioned many times per output — unusual) or where `output_count` is 0 but `mention_total > 0` (data inconsistency).

3. **Entity name correctness** — does the entity name look like a real brand/product, or is it a generic term, a URL, a heading, or noise? Flag candidates for:
   - Promotion to a proper alias or entity record
   - Demotion (mark as noise / ignored in resolution candidates)
   - Merge into an existing entity (create alias)

4. **Unresolved keyed rows** (`entity_id IS NULL`) — for any with `mention_total > 1`, surface them as alias candidates. Group by `entity_brand_name` and present to the user for a resolution decision.

### 9c — Compare with raw matview

Compare `v_entity_metrics_with_sources` against `mv_entity_metrics_overall_llm_brand_entity_v2` directly to surface discrepancies:

```sql
SELECT
  m.entity_brand_name,
  m.entity_name,
  m.entity_id,
  m.entity_key,
  ROUND(m.mention_total::numeric, 2) AS matview_mention_total,
  ROUND(v.mention_total::numeric, 2) AS view_mention_total,
  CASE
    WHEN v.entity_id IS NULL AND m.entity_id IS NULL THEN 'unresolved-keyed'
    WHEN v.entity_id IS NULL AND m.entity_id IS NOT NULL THEN 'missing-from-view'
    WHEN v.mention_total IS NULL THEN 'missing-from-view'
    WHEN ABS(m.mention_total - v.mention_total) > 0.1 THEN 'count-mismatch'
    ELSE 'ok'
  END AS status
FROM mv_entity_metrics_overall_llm_brand_entity_v2 m
LEFT JOIN v_entity_metrics_with_sources v
  ON v.batch_id = m.batch_id
  AND v.entity_brand_id IS NOT DISTINCT FROM m.entity_brand_id
  AND v.entity_id IS NOT DISTINCT FROM m.entity_id
  AND v.batch_id = '<batch_id>'
WHERE m.batch_id = '<batch_id>'
  AND (m.entity_id IS NOT NULL OR m.entity_key IS NOT NULL)
ORDER BY status, m.mention_total DESC;
```

Flag any rows with status `count-mismatch` or `missing-from-view`. These indicate:
- **count-mismatch**: aggregation discrepancy between the raw matview and the view JOIN — could be a missing fact row or a LATERAL join condition issue
- **missing-from-view**: row exists in the matview but not the QA view — check whether `entity_brand_id` or `entity_id` is NULL causing a JOIN failure

### 9d — Alias and entity correction actions

After the review, present a consolidated action list to the user:

| Entity name | Issue | Suggested action |
|---|---|---|
| "Talking Futures guide" | Generic variant of known entity | Add alias → Talking Futures (entity_id X) |
| "NCS website" | URL-style noise | Mark as ignored in resolution candidates |
| "Careers & Enterprise" | Short form of "Careers & Enterprise Company" | Add brand alias |

For each: show the alias INSERT SQL and ask the user to confirm before writing. After any writes, re-run Phase 7 (refresh) before continuing to Phase 10.

---

## Phase 10 · Feedback loop

After reviewing QA failures and entity patterns from Phases 2–3, synthesise actionable suggestions. For each category:

### Alias suggestions

If raw entity names appeared repeatedly but weren't in the alias tables, suggest:
```sql
-- Suggested new alias (alias_name and alias_key are both NOT NULL)
INSERT INTO visibility_entity_aliases
  (brand_id, visibility_entity_id, alias_name, alias_key, active)
VALUES ('<brand_id>', <entity_id>, '<raw_display_name>', public.normalize_company_name('<raw_display_name>'), true)
ON CONFLICT (brand_id, alias_key) DO UPDATE
  SET visibility_entity_id = EXCLUDED.visibility_entity_id,
      alias_name = EXCLUDED.alias_name,
      active = true,
      updated_at = now();
```

Present as a list for the user to approve before writing.

### category_rules improvements

Based on QA failure patterns, suggest specific additions to `visibility_prompt_contexts.category_rules`:
- New entity types to add or exclude
- Specific canonicalization rules for recurring mismatches
- Standalone exclusion terms that are appearing as noise

Fetch the current rules first:
```sql
SELECT category_rules FROM visibility_prompt_contexts
WHERE brand_id = '<brand_id>' AND active = true LIMIT 1;
```

Show the user a diff — current rules vs. suggested additions. Do NOT write to `visibility_prompt_contexts` without explicit user confirmation.

### brand_profile surface_references gaps

If the target brand itself was being extracted inconsistently (e.g. a shortened name or website domain not in the profile), surface this:
```sql
SELECT raw_entity, observed_count FROM visibility_entity_resolution_candidates
WHERE brand_id = '<brand_id>'
  AND (lower(raw_entity) LIKE lower('%<brand_name>%')
       OR lower(raw_brand) LIKE lower('%<brand_name>%'))
  AND status IN ('pending', 'ignored')
ORDER BY observed_count DESC;
```

Suggest additions to the `Surface references:` block in `brand_profile`.

### Prompt version check

Check the prompt versions currently in use for the batch:
```sql
SELECT DISTINCT
  sv.version_info->'visibility_prompt_context'->>'prompt_name' AS prompt,
  sv.version_info->'visibility_prompt_context'->>'prompt_version' AS version
FROM scores_visibility sv
JOIN prompts_outputs po ON po.id = sv.output_id
WHERE po.batch_id = '<batch_id>' AND sv.active = true;
```

Flag if any outputs used an older prompt version than what's currently live in Langfuse.

---

## End of run summary

After all phases complete, print a structured summary:

```
=== Visibility Entity Check — <brand_name> (<batch_id>) ===

Health
  Scored:       X / Y outputs (Z%)
  QA pass:      X (Z%)
  QA review:    X
  QA fail:      X

Actions taken
  Matviews refreshed:    X times (Phase 1 + Phase 7 if changes made)
  Candidates resolved:   X (Phase 1 deterministic: X · Phase 2 LLM: X)
  Human aliases written: X
  Candidates ignored:    X
  Brands enriched:       X (GPT: X · Gemini: X)
  Entities enriched:     X (GPT: X · Gemini: X)

Canonicalisation (Phase 6)
  Brand merges applied:  X (aliases written · rows deactivated)
  Entity merges applied: X (aliases written · rows deactivated)
  Merges pending approval: X

Target brand review (Phase 8)
  Target brand entities: X resolved · X unresolved-keyed
  Raw response misses:   X outputs mention brand but not captured
  Count anomalies:       X rows flagged

Entity metrics QA (Phase 9)
  Rows reviewed:         X
  Source text issues:    X
  Count mismatches:      X
  Alias candidates:      X (pending approval)
  Noise / ignored:       X

Feedback suggestions (Phase 10)
  Alias additions:       X (pending approval)
  category_rules edits:  X (pending approval)
  brand_profile gaps:    X (pending approval)

Next steps
  [ ] Apply any pending merges from Phase 6, then re-run Phase 7 refresh
  [ ] Apply any pending aliases from Phase 9 review, then re-run Phase 7 refresh
  [ ] Apply any pending category_rules / brand_profile changes from Phase 10
  [ ] Re-score low-QA outputs after fixes: POST /api/workflows/score-single-output
  [ ] Re-run /zebora-scoring-vec review to validate fixes landed correctly
```

---

## Important rules

- **Run one phase at a time.** Unless the user explicitly asks for a fully automated run, stop after each phase, summarise, and wait for approval before continuing (see *Operating mode — phase-gated workflow* above).
- **Never update `visibility_prompt_contexts`** without showing the user the exact diff and getting explicit confirmation.
- **Never mark candidates as `auto_resolved`** manually — only the resolution pipeline should do this.
- **Never delete dimension rows** — mark `active = false` only, and only with user confirmation.
- When writing aliases, always compute `alias_key` using `public.normalize_company_name('<name>')` — never by hand. The function: strips leading "the ", replaces "&" with "and", removes all non-alphanumeric characters (lowercase). Do NOT pass raw display names as alias_key.
- If `DATABASE_URL` / `SUPABASE_URL` env vars are not set, stop immediately and tell the user to check `.env`.
- Always run the Bash tool from inside the repo root: `cd /Users/grantsimmonds/Documents/dev/branded-llm/brand_score_pipeline`
