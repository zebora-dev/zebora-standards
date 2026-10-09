---
name: zebora-ai-tells
description: >-
  Score written content for the surface signals that make it read as AI-generated,
  and produce a traffic-light scorecard with ranked rewrites. Use when the user asks
  whether copy "looks AI", wants an AI-tell / AI-detection audit, mentions em dashes
  or AI writing patterns, asks to humanise or de-slop a page, or wants a case study,
  article or landing page checked before publishing. Outputs a Human Read Score
  (0-100) from a deterministic script plus editorial judgement on what to change.
  Does not edit files unless asked, and does not claim to defeat AI detectors.
---

# zebora-ai-tells

Scores prose for the tells that make it read as machine-written, then says what to change.

**Tagline:** Does this read like a person wrote it?

**Not this skill:** whether the copy is *true*, well-argued, or on-brand — that is `zebora-case-study` (structure, voice, AEO) and human review.
**Not this skill:** beating AI-detection tools. Those tools are unreliable in both directions. This measures reader-visible tells, which is a different and more useful thing.

## The one rule

**The script counts. You judge.** Run `scripts/score.py` and use its numbers verbatim. Never re-count by hand, never adjust a count because a finding "feels" more or less severe — the whole point of the script is that the same copy scores the same on Tuesday as it did on Monday. Your job starts after the count: deciding which findings matter for this page, and writing the rewrites.

Hand-grepping for these patterns produces false positives in both directions. It over-counts plain negation as negative parallelism and over-counts glossary definitions as colon glosses; it under-counts the canonical `It isn't X. It's Y.` form because that spans a sentence boundary. The script handles all three.

## Run it

```sh
python3 ~/.claude/skills/zebora-ai-tells/scripts/score.py <file> [--format auto|text|html|ts] [--slug <slug>] [--json]
```

| Source | Command |
| --- | --- |
| Case study in the repo | `score.py apps/marketing/lib/case-studies/data.ts --format ts --slug <slug>` |
| Live page | `curl -s <url> -o /tmp/p.html && score.py /tmp/p.html --format html` |
| Markdown / draft | `score.py draft.md` |
| Pasted copy | `score.py - ` (reads stdin) |

`--json` adds every matched fragment under `detail`, which is what you quote in the scorecard. Under 120 words of prose the script refuses to score — rates are meaningless at that length.

**The two sources score differently, and both are right.** `--format ts` reads every prose field in the object, including `excerpt`, `metaTitle`, `metaDescription`, `baselineNote` and `methodologyNote`. `--format html` reads only what the page renders. The 4As study scores 56 from `data.ts` and 63 from the live URL for exactly this reason — the extra fields are dense with dashes and glosses. Score the **live page** when the question is "how does this read to a visitor", and the **source** when the question is "what do I need to edit". Say which one a scorecard used.

## Scoring

`ai_tells_rubric@0.1.0`. Fifteen signals, each scored 0–10 against a green and a red threshold, weighted mean × 10 = **Human Read Score, 0–100, higher reads more human.**

| Band | Score | Light |
| --- | --- | --- |
| Passes as human | 80–100 | 🟢 |
| Reads AI on a careful read | 60–79 | 🟠 |
| Reads AI immediately | 0–59 | 🔴 |

Weights, thresholds and provenance for each signal: `references/signals.md`. Never invent alternate weights under the same rubric id — bump the version instead.

### Calibration

Measured 15 Sep 2026, so a score has something to sit against:

| Corpus | Score |
| --- | --- |
| Paul Graham, *Startup = Growth* (2012, human control) | 84 |
| Paul Graham, *Do Things That Don't Scale* (2013, human control) | 83 |
| Zebora case studies, five published | 56–72 |

Human long-form business prose lands low-to-mid 80s, not 100. **A perfect score is not the target** — chasing 100 means stripping every dash, colon and emphasis from the page, which reads as stilted rather than human. Anything at 80+ is done.

## First, check it isn't transfer damage

**Before recommending a single edit, find the source draft and score that too.** Copy moved from Google Docs, Notion or a slide deck into the CMS routinely acquires em dashes, smart punctuation and mid-sentence bold that the author never wrote — some editors substitute them automatically, and a human "tidying up" a paste adds more.

This is not a rare case. On the 4As case study (15 Sep 2026) the source doc scored **84/100 with one em dash**, and that one sat inside an editorial placeholder, not body copy. What shipped scored **56/100 with 27 em dashes and 15 bold spans**. **Twenty-six of the twenty-seven dashes were introduced in transfer.** Restoring the doc's own punctuation took the page from 56 to 81 without changing a single word of the author's prose.

Score both, then split the findings:

| Signal present in | What it is | What to do |
| --- | --- | --- |
| Published only | Transfer damage | Restore the source punctuation. No editorial judgement needed, no author sign-off |
| Both | The author's own habit | A rewrite. Needs the author's review |

Telling a writer to fix prose they never wrote wastes their time and loses their trust. Always separate the two, and say which bucket each finding sits in.

## Procedure

1. **Run the script.** Use `--json` so you have the matched fragments.
2. **Read the copy yourself.** The script cannot tell a deliberate stylistic choice from a tic, and it cannot see whether a finding sits in a spot that matters (a hero paragraph) or one that doesn't (a methodology footnote).
3. **Rank the reds by weight, then by how early they appear on the page.** A tell in the first two paragraphs costs more than the same tell in an FAQ.
4. **Write rewrites, not instructions.** Quote the real sentence and give a replacement. `references/rewrites.md` has the pattern-by-pattern fix table.
5. **Name what to leave alone.** Every scorecard states the greens explicitly. Writers over-correct, and stripping a page's few good human touches makes it worse.
6. **Report the score, the band, and the three counts** (fix now / tighten / keep).

## Guardrails

- **Never claim a score means a detector will or won't flag the page.** Detection tools disagree with each other and with this rubric. Say "reads as AI to a human reader", never "will pass detection".
- **Never say content *is* AI-generated based on a score.** The rubric measures style, not provenance. Human writers who lean on dashes score badly, and heavily-edited AI copy scores well.
- **FAQ questions are exempt from the Wh-heading signal.** Question-shaped FAQs are correct for AEO; the script already excludes them. Do not tell a writer to de-question their FAQs.
- **Rule-of-three lists at normal density are not a tell.** The flag is stacked back-to-back tricolons. Do not strip ordinary English.
- **Repetition between body and FAQ is usually legitimate** — an FAQ answer has to stand alone when extracted. Only flag self-echo inside the body.
- **British English in all rewrites.** The site is en-GB: *optimisation*, *programme*, *£*.
- **Do not edit files unless asked.** Default output is a scorecard. Apply changes only on an explicit go-ahead, and show the diff.

## Output template

```markdown
# AI tells — <Title>

**Human Read Score:** NN / 100 — <band>
**Rubric:** ai_tells_rubric@0.1.0 · <N> prose words · <N> sentences

🔴 <n> fix now · 🟠 <n> tighten · 🟢 <n> keep

## The register
| | Signal | Measured | Weight | Verdict | Evidence |
(script output, verbatim)

## What to change, in order
1. **<Fix>** — <why it reads as AI, one or two sentences>
   - ✗ "<real sentence from the copy>"
   - ✓ "<rewrite>"

## What's already working
- **<Signal>** — <why it earns its keep; do not touch>

## In one line
<the single habit driving the score, and what fixing it is worth>
```

For a richer deliverable, publish the scorecard as an Artifact: traffic-light register, ranked fixes with marked-up before/after pairs, and an explicit keep list. Zebora brand tokens are Signal Green `#00EB5B`, Deep teal `#008A5C`, Deep Field `#081514`, Slate White `#F8FAFC`.

## Files

| Path | What's in it |
| --- | --- |
| `scripts/score.py` | The rubric. Stdlib only, no install. |
| `references/signals.md` | All fifteen signals: weights, thresholds, research provenance, known false positives. |
| `references/rewrites.md` | Fix patterns with before/after pairs. |
