# The fifteen signals

`ai_tells_rubric@0.1.0`. Weights sum to 100. Each signal scores 0–10 linearly between its green and red threshold; the weighted mean × 10 is the Human Read Score.

Thresholds were set against two reference points: pre-LLM human business prose (Paul Graham essays, 2012–13, scoring 83–84) and the five published Zebora case studies (56–72). They are provisional. If a signal starts firing on copy a careful reader would pass, loosen the threshold and bump the rubric version — do not argue with the number in a scorecard.

## Structural — the ones that actually drive the score

### 1. Appositive elaboration · 20%
**Green ≥ 1:80 words · Red ≤ 1:45**

Composite of em-dash glosses, colon glosses and negative frames. Measures the rate at which sentences explain themselves twice: a claim, then a restatement of the claim in weightier language.

This is the highest-weighted signal because it is the *generative* habit behind several of the others. Fix only the em dashes and the tic migrates to colons; the page still reads AI. The pattern to break is **claim, then gloss the claim**, whatever punctuation carries it.

### 2. Negative parallelism · 15%
**Green < 1.0 per 1k words · Red > 3.5**

"It's not X, it's Y." The single most-cited tell in current research. Both clauses describe the same thing: the "not" sets up a modest baseline and the "it's" delivers the same idea dressed up. The reader gets no new information — the sentence performs depth instead of providing it.

*Detection:* negation followed by a contrastive pivot within ~120 characters, allowing **one** sentence boundary, because the canonical form is written as two sentences.

*Known false positive:* the possessive "its". A regex of `it'?s` matches it and turns every "wasn't measuring its presence" into a hit. The script uses `it['’]s`. If you ever hand-write this pattern, do the same.

### 3. Em-dash density · 10%
**Green < 5 per 1k words · Red > 11**

Weighted lower than most people expect. Em dash *alone* is now a weak signal — The Economist's testing found only Claude uses them more than human writers, and plenty of good human writers lean on them.

What makes it count is monotony of function. Check the `detail` output: if most dashes are `statement — restatement` rather than true parenthetical pairs, the signal is real regardless of count. Say that in the scorecard rather than just quoting the rate.

### 4. Colon glosses · 5%
**Green ≤ 3 · Red ≥ 8**

Mid-sentence colon introducing a restatement of the clause before it. Scored separately from dashes so that stripping dashes alone cannot hide the elaboration habit.

*Known false positives, both excluded by the script:* a short label introducing a definition ("AI visibility: how often it appears") is a glossary entry, not a tic; a colon followed by a coordinated list is a list. The script also strips section headings out of the prose stream first — otherwise every "Section: subtitle" heading counts as a gloss.

## Lexical

### 5. AI vocabulary · 8%
**Green ≤ 0.4 per 1k · Red > 3**

delve, leverage, robust, seamless, tapestry, testament, harness, unlock, pivotal, plethora, crucial, cutting-edge, "in today's", "it is important to note", "when it comes to". The list in the script is deliberately tight: every entry is a word a careful writer rarely reaches for unprompted. **Do not pad it with ordinary business vocabulary** or every page scores red.

This is the signal most AI copy fails outright, so a clean result here is worth stating explicitly in the scorecard.

### 6. Magic adverbs · 5%
**Green ≤ 1.5 per 1k · Red > 6**

genuinely, fundamentally, deeply, remarkably, noticeably, essentially, significantly, truly, quietly. Intensifiers that inflate a claim without adding information. Nearly always deletable with no loss.

### 7. Stakes inflation · 5%
**Green 0 · Red ≥ 3**

"is itself a significant outcome", "cannot be overstated", "in its own right", "nothing short of", "a new era", "paradigm shift". Making a mundane finding feel world-historic.

*Note:* the patterns overlap by design ("a significant outcome" sits inside "is itself a significant outcome"). The script dedupes by span. Without that, one phrase scores three times.

### 8. Vague sourcing · 3%
**Green 0 · Red ≥ 3**

"experts argue", "studies show", "research suggests", "industry reports indicate" — attribution with nobody behind it. Rare in Zebora copy, which cites its own measurement, but it is the signal that most damages credibility when present.

## Rhythm and formatting

### 9. Sentence burstiness · 6%
**Green σ ≥ 10 · Red σ < 6** *(higher is better)*

Population standard deviation of sentence length in words. Human writing varies; model output clusters. Report the mean and range alongside σ — "mean 23 words, range 3–80" tells a writer more than the sigma does.

### 10. Bold-scatter · 5%
**Green ≤ 4 per 1k · Red ≥ 9**

Mid-sentence bold. Bolding a *figure* earns its keep; bolding an *editorial claim* reads as a model signposting its own argument. The count alone won't tell you which — read the matched spans. A bold span that closes mid-phrase is always a defect.

### 11. Scare-quoted phrases · 5%
**Green ≤ 1 · Red ≥ 5**

`"why 4As"`, `"how visible is X"`. Quoting a question in order to answer it. Almost always deletable by stating the finding directly.

### 12. Staged reframing · 4%
**Green 0 · Red ≥ 3**

"shifted the question from X to Y", "move past X and start asking Y", "the real question is". Staging a question so the copy can appear to transcend it.

*Known over-count:* one construction can match two patterns at different spans ("move past X **and start asking** Y"). Read the fragments before quoting a count.

### 13. Wh-word headings · 4%
**Green ≤ 0.4 ratio · Red = 1.0**

Share of **section** headings opening Why / What / How / Where / When / Who.

**FAQ questions are excluded and must stay excluded.** Question-shaped FAQs are correct for AEO — they are the highest-value citation field on a case study page. Never tell a writer to de-question their FAQs on the strength of this signal.

The ratio is coarse on pages with few headings: 4 of 5 is amber, 5 of 5 is red. Fixing two headings is usually enough.

### 14. Long cascades · 3%
**Green ≤ 3 · Red ≥ 9**

Coordinated lists of four or more items. Threshold is loose on purpose: a genuine list of what an organisation provides is not a tell. What counts is the *abstract* cascade used rhetorically ("where, for what, among whom, against which competitors and where that mattered most"), especially when it recurs.

### 15. Self-echo · 2%
**Green ≤ 25 · Red ≥ 70**

Repeated 6-grams. Lowest weight, because the measure is noisy.

*Major caveat:* repetition between body copy and FAQ answers is **legitimate** — an FAQ answer has to stand alone when an assistant extracts it. The script cannot separate the two, so treat a red here as advisory and check whether the repeats are body-internal before flagging anything.

---

## Signals deliberately excluded

**Rule of three.** Tricolons at normal density are just English. The research flags *stacked back-to-back* tricolons, which a whole-document count cannot distinguish from ordinary prose. Including it produced false positives on every human control. Mention it in a scorecard only to tell a writer to leave their threes alone.

**Perplexity / burstiness via a language model.** Needs a model in the loop, which breaks the determinism that makes this rubric worth having.

**Hedging density.** Modal verbs (may, might, could) are genuinely lower in AI text per the literature, but Zebora copy is measurement writing, where hedging is correct and desirable. Penalising it would push writers toward overclaiming, which is a worse failure than sounding synthetic.

## Sources

- [tropes.fyi](https://tropes.fyi/) — the fullest catalogue of AI writing patterns; most of the structural signals above map to entries there.
- [Humanized Copy on negative parallelism](https://humanizedcopy.com/posts/the-it-s-not-just-x-it-s-y-tell-ai-negative-parallelism) — why "not just X, it's Y" is the strongest single tell.
- [SearchAtlas, AI writing patterns](https://searchatlas.com/blog/ai-patterns-in-writing/) — uniform sentence length, transitional phrases, hedging, absent detail, vague sourcing.
- [AIAdventureClub, How to spot AI writing in 2026](https://aiadventureclub.substack.com/p/how-to-spot-ai-writing-in-2026) — the em-dash finding, monotonous sentence length, Rule of Threes.
- [Linguistic Characteristics of AI-Generated Text: A Survey](https://arxiv.org/pdf/2510.05136) — punctuation frequency and lexical diversity differences.
