---
name: zebora-scoring-train
description: "Scoring-train: build and train a brand's visibility-v3 prompt context (category_rules, brand_profile, target, primaries, mappings) before the batch is scored for real. Starts from the brand's core facts and the nearest existing contexts, reads the first 10 outputs for themes, scores them in a sandbox with the draft (nothing saved), labels the result, iterates, then repeats on 3-5 fresh sets of 10 until accuracy holds, and only then promotes the draft to the active context version. Also retrains a live brand's context. Triggers on: scoring train, train the context, build the prompt context, new brand context, training round, label outputs, extraction accuracy, category_rules, context version, policy decisions for a brand."
user-invokable: true
argument-hint: "[phase] <batch_id>"
---

# zebora-scoring-train — build and train a brand's prompt context

**Invocation:** `/zebora-scoring-train [phase] <batch_id>`

Training builds the context the scorer reads, and proves it on real outputs **before** the batch is scored
for real. Each draft is scored in a sandbox: production's own scorer runs with the draft swapped in, and
nothing is written. A draft only becomes the active version at the end, once fresh sets of outputs score well.

> Rebuilt 2026-11-08. The original was kept only in `~/.claude/skills` and was lost with a laptop. Its runs
> (TransUnion v1→v4, Twinkl v1→v3, Nationwide v2, Vuse 2026-08) re-scored stored rows after each change,
> which caused duplicate active rows, batches scored under several versions, and hand corrections (see
> the Twinkl retro). This version trains in the sandbox instead.

## Where this sits

| Skill | Job |
|---|---|
| **`zebora-scoring-train`** | Build the context and train it on sets of 10 outputs, before full scoring. Also retrains a live brand. |
| `zebora-onboard-preview-brand` | Calls this skill in place of writing context v1 by hand, then scores the whole batch with the promoted version. |
| `zebora-scoring-vec` | Checks the whole scored batch afterwards. Its Phase 10 suggestions start the next retraining. |
| `zebora-batch-release` | Unchanged. |

## What the scorer actually reads (what we are training)

| Input | Source | Trained here |
|---|---|---|
| `category_rules` | context row | What counts as an entity in this category: extractable types, exclusions, collapse rules, examples |
| `brand_profile` | context row | The target: names, surface forms, hierarchy, what not to credit |
| `target_brand` / `visibility_brand_override` | context row (or dimension tables) | Who the target is, as the LLM sees it |
| `primary_competitors` | `competitors_primary` (or dimension tables), **not** the context row | The primary tier. A wrong tier mis-tags every row (Vuse v3). |
| `canonical_entity_mappings`, `brand_canonical_aliases` | context row JSON (fallback) | Applied by code after the LLM, never shown to it. Prefer the alias tables for spelling. |
| Alias tables (`visibility_entity_aliases`, `visibility_entity_brand_aliases`) | dimension tables | Read by the sandbox exactly as in production. Maintained through VEC. |

The base prompts (`visibility-v3`, `visibility-v3-qa` in Langfuse) are shared by every brand and are **not**
changed here. Phase 8 recommends prompt changes when a problem is not brand-specific.

The QA verdict (gpt-5-nano) is a hint, not a label: it checks what was extracted far more than what was
missed, and it is sometimes wrong (Twinkl 118604: "pass 1.00" while missing the top recommendation).

## Quick reference

| Command | Phase |
|---|---|
| `/zebora-scoring-train <batch_id>` | 0 then 1, then stop |
| `/zebora-scoring-train draft <batch_id>` | 1 · brand core → draft d0 |
| `/zebora-scoring-train discover <batch_id>` | 2 · first 10 outputs: themes → draft d1 + questions |
| `/zebora-scoring-train score <batch_id>` | 3 · sandbox score the current set with the current draft |
| `/zebora-scoring-train label <batch_id>` | 4 · label, report, cluster |
| `/zebora-scoring-train iterate <batch_id>` | 5 · next draft, re-score the same set, compare |
| `/zebora-scoring-train next <batch_id>` | 6 · a fresh set of 10 |
| `/zebora-scoring-train promote <batch_id>` | 7 · make the draft the active version (GATE) |
| `/zebora-scoring-train handoff <batch_id>` | 8 · record, precedents, prompt recommendations |

A named phase always runs Phase 0 first.

## Operating mode

- **One phase at a time**, then the hand-off block, then stop.
- **Writes are limited to:** files in the training folder; and in Phase 7 (GATE) the new context version,
  plus the primary tier with `--with-primaries`. Sandbox runs write nothing to the database.
- **Never force a re-score of stored rows to test a rule.** Use the sandbox.
- **Precedents first.** Read `references/precedents.md` before drafting and before asking anything.
  Ask only what it does not settle, with a recommendation each time.
- **Cost:** a sandbox run of 10 outputs is about 10 extraction calls plus 10 QA calls (`--no-qa` halves it).
  A full training (5 sets, 2–3 drafts each) is roughly 150–300 calls.
- **Never print secrets.**

Hand-off after every phase:

```
=== Scoring-train Phase <n> — <name> · <brand> · set <k> · draft <d> ===
Summary            <counts, findings>
Accuracy so far    <the table from the training log>
Actions taken      <files written / DB writes, or "None">
Needs your call    <questions with a recommendation each, or "None">
Next               <phase>
```

## Setup

```bash
SKILL=~/.claude/skills/zebora-scoring-train/scripts
PIPE=${ZEBORA_PIPELINE:-<workspace>/brand-score-pipeline}   # .env: DATABASE_URL, OpenAI and Langfuse keys
PY=$PIPE/.venv/bin/python                                   # every script runs with the pipeline venv
```

**Training folder** (default): `zebora-ops/Clients/<Brand>/Research/Scoring train/<YYYY-MM-DD>/`, kept in the
ops vault so it survives the machine. Override with `ZEBORA_TRAIN_DIR` (or `--dir`). Layout:

```
drafts/d0/ d1/ …          category_rules.md · brand_profile.md · draft.json
sets/set-1.json · .md      the outputs (fresh each set) · set-1__discovery.md
runs/set-1__d0.json · .md  sandbox results · labelling pack
labels/set-1__d0.csv       output_id,entity,brand,competitor_type,label,note
log.md                     decisions and the accuracy table (you keep it up to date)
```

---

## Phase 0 · Setup

```sql
SELECT b.id, b.name, br.name AS brand, br.slug, br.id AS brand_id, br.category,
  (SELECT count(*) FROM prompts_outputs WHERE batch_id = b.id AND active) AS active_outputs,
  (SELECT count(*) FROM scores_visibility WHERE batch_id = b.id AND active
     AND scorer_model = 'visibility-v3') AS scored
FROM batches b JOIN brands br ON br.id = b.brand_id WHERE b.id = '<batch_id>';

SELECT version, active, created_at::date, change_summary FROM visibility_prompt_contexts
WHERE brand_id = '<brand_id>' AND context_name = 'default' ORDER BY version;
```

Report: active outputs (training needs outputs, not scores), whether a context exists, earlier training
folders in the vault. If a folder for today exists, continue it (read its `log.md`) instead of starting over.
Stop if there is more than one active `default` context.

## Phase 1 · Brand core → draft d0

1. **Brand core.** Collect from the user, the brand row and the onboarding inputs:
   target name and the forms it appears in (domain, short names, products); market; category in one line;
   what the brand offers the buyer; a **provisional** primary tier (onboarding uses the most-named brands in
   the prompts) with URLs.
2. **Look up what we already have:**
   ```bash
   $PY $SKILL/draft_context.py --list
   ```
   Pick the nearest category (education → Twinkl; measurement/B2B services → TransUnion; financial products →
   Nationwide; consumer products with ranges → Vuse; publisher/product → Big Potato; campaign body → Smart
   Energy GB / Talking Futures). Read its rules and profile. Note which of its decisions carry over (they are
   in `references/precedents.md`).
3. **Build d0**, one of:
   ```bash
   $PY $SKILL/draft_context.py --batch <id> --template <brand config.json>   # new brand, onboarding base template
   $PY $SKILL/draft_context.py --batch <id> --from-brand <nearest slug>      # adapt the nearest context
   $PY $SKILL/draft_context.py --batch <id> --from-active                    # retrain a live brand
   ```
   Then edit the files: apply the universal precedents, the category precedents that fit, the brand core and
   the primaries (in `draft.json`). From another brand: replace every target name, alias, mapping and example.
4. Start `log.md`: brand core, nearest context used, precedents applied, open questions.

Show the user the brand core, the primaries and the main rules. **GATE: confirm the target and primaries.**

## Phase 2 · Discovery on set 1 (before any scoring)

```bash
$PY $SKILL/pick_set.py --batch <id> --n 10                       # spread across LLMs and prompts
$PY $SKILL/discover.py --set <dir>/sets/set-1.json --draft <dir>/drafts/d0
```

Read all 10 responses (`sets/set-1.md`) alongside the discovery report. Look for:
- **who gets recommended**, and what kind of thing each is (company, product, tool, body, publication, person)
- **names the draft does not cover yet**, and names that need a canonical spelling
- **traps the precedents warn about:** citation-only names, link text, image captions, widget or shopping
  attributions "(brand)", page and article titles, descriptors used as names, AI Overview labels glued to names
- **long lists** (where the scorer drops items) and tables
- **how the target appears**, and whether it is ever implied without being named

Compare with the nearest context: does its structure fit what these responses contain?

Then write **d1** (`draft_context.py --copy d0 --name d1`, then edit). List the policy questions the responses
raise that precedents do not settle. **GATE: decisions.** Record each in `log.md` as "confirmed with <name> <date>".

## Phase 3 · Sandbox score

```bash
$PY $SKILL/sandbox_score.py --set <dir>/sets/set-<k>.json --draft <dir>/drafts/<d> [--repeat 2] [--no-qa]
```

Use `--repeat 2` on the first set and whenever results look unstable: the pack then lists what differs
between two runs of the same draft. That is scorer noise, and no rule will fix it.

## Phase 4 · Label and review

Label every entity in `runs/set-<k>__<d>.md`, and add a `missing` row for each recommendation not extracted.
Save it as `labels/set-<k>__<d>.csv`.

| Label | Meaning |
|---|---|
| `ok` | Right entity, brand and role |
| `wrong-canon` | Real recommendation, wrong name or brand |
| `wrong-type` | Wrong `entity_type`, `competitor_type` or target/primary flag |
| `wrong-context` | Real brand, wrong evidence: citation only, or `source_text` from a neighbouring item |
| `noise` | Not an entity here: descriptor, source/review site, title, device type |
| `missing` | A recommendation that was not extracted (response wording in `note`) |
| `escalate` | A policy call the rules and precedents do not settle (question in `note`) |

Label the clear cases yourself, using the draft and the precedents. Escalate only real policy calls.

```bash
$PY $SKILL/train_report.py <dir>/labels/set-<k>__<d>.csv
```

Group the non-ok rows into clusters (P1, P2…, target and primary errors first) and give each a fix route:

| Route | When |
|---|---|
| **Draft rule** | The extractor would follow it if told: exclusions, collapse, type rules, an example |
| **Mapping / alias** | Spelling or brand mapping only: `canonical_entity_mappings` in the draft for now; alias tables through VEC once live |
| **Primaries / target** | Mis-tagged roles: fix `primaries` / `target_brand` in `draft.json` |
| **Scorer / prompt** | Not brand-specific, or the draft already says it and it is ignored. Goes to Phase 8. |
| **Noise / residual** | Varies between runs, or a one-off. Accept it and say so. |

Add the set's line to the accuracy table in `log.md`.

## Phase 5 · Iterate on the same set

```bash
$PY $SKILL/draft_context.py --batch <id> --copy <d> --name <d+1>       # then edit the new draft
$PY $SKILL/sandbox_score.py --set <dir>/sets/set-<k>.json --draft <dir>/drafts/<d+1>
$PY $SKILL/compare_runs.py <dir>/runs/set-<k>__<d>.json <dir>/runs/set-<k>__<d+1>.json \
    --labels <dir>/labels/set-<k>__<d>.csv
```

`compare_runs` reports what the change **fixed**, what it **broke** (an `ok` row that disappeared or changed
role) and what is **still wrong**. Keep a change only if it fixes more than it breaks, net of the noise seen in
Phase 3. Label the new run only where it differs. Two or three drafts per set is normal. Stop iterating on a
set when the remaining errors are noise, scorer issues or accepted residuals.

**Write rules, not lists.** A general rule ("a product counts as its company") carries over to the next set.
A list of names fits this set only, and the extractor copies names from the context into results (Vuse, Oct
2026: 516 device mentions copied from a lookup list). Use lists only for spelling, and label them
lookup-only.

## Phase 6 · Fresh sets (3–5 more)

```bash
$PY $SKILL/pick_set.py --batch <id> --n 10 [--mode long-lists]   # never reuses an output
```

For each new set:
1. Run discovery quickly. Check for new kinds of name or new traps.
2. **Score it with the current draft before changing anything.** This first-pass result is the honest
   measure of accuracy on outputs the draft has never seen, so log it.
3. Label it (Phase 4), then iterate (Phase 5) if needed.

Include at least one `--mode long-lists` set. For a live brand, `--mode flagged` targets outputs that QA
already doubts.

**Accuracy table** (in `log.md`):

| Set | Mode | Draft | First pass OK | After iterating | Main clusters |
|---|---|---|---|---|---|
| 1 | spread | d0→d2 | 74% | 91% | citations, product collapse |
| 2 | spread | d2→d3 | 86% | 93% | … |

**Ready to promote when:** first-pass OK is **≥ 90% on two fresh sets in a row**, no new escalations, and what
is left is noise, scorer issues or accepted residuals. Past runs needed 2–4 drafts. Expect 3–5 sets.

## Phase 7 · Promote (GATE)

```bash
$PY $SKILL/promote_context.py --batch <id> --draft <dir>/drafts/<final> [--with-primaries] \
  --summary "v<n>: scoring-train, <S> sets of 10 -- <main decisions in a line>" \
  --notes "scoring-train <date>: <S> sets / <O> outputs / <E> entities; first-pass OK <a>% -> <b>% (sets 1 -> <S>); drafts d0-d<n>. Decisions confirmed with <name> <date>: ... Training folder: <vault path>."
```

The dry run prints the exact diff (both texts, the JSON fields, target, and the primaries with
`--with-primaries`). **Show it and wait for approval**, then add `--go`. One transaction: the new row (v1 if
there is none, else version+1 with `created_from_context_id`), and the old row deactivated. Primaries are added
or reordered, never deleted. Remove extras by hand if intended.

Then score for real:
- **Onboarding / preview brand:** return to `zebora-onboard-preview-brand` Phase 4 (fan-out scoring of the
  whole batch with the promoted version).
- **Live pool brand:** the next batch uses it. Re-scoring the current batch is a separate decision, made
  with the release owner.

## Phase 8 · Hand-off and feedback

1. **Precedents:** add every newly confirmed decision to `references/precedents.md` (zebora-standards PR).
2. **Prompt recommendations** for `visibility-v3` / `visibility-v3-qa`: only clusters that are not
   brand-specific, or that the draft states and the extractor ignores (long-list drops, exclusions ignored,
   run variance, brand-row suppression). Give evidence: output ids and counts. Do not edit Langfuse here.
3. **Aliases:** spelling mappings learned here belong in the alias tables. List them for
   `zebora-scoring-vec` Phase 4/10.
4. Close `log.md` and print:

```
=== Scoring-train — <brand> (<batch_id>) ===
Sets          <S> × 10 outputs (<modes>), <E> entities labelled
Accuracy      first pass <a>% (set 1) -> <b>% (set <S>) · after iterating <c>%
Drafts        d0 … d<n> (based on <nearest context / template>)
Decisions     <confirmed, with who and when>
Promoted      v<n> (id …), primaries <written / unchanged>
Residuals     <accepted issues>
Prompt recs   <list, or none>
Aliases       <for VEC, or none>
Folder        <vault path>
Next          <full scoring (onboarding Phase 4) | VEC | next batch>
```
