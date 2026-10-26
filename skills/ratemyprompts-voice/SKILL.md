---
name: ratemyprompts-voice
description: Draft or review any RateMyPrompts copy in the brand's tone of voice (v1.1) and house rules. Use for ratemyprompts.com page copy, meta titles and descriptions, emails, form labels and errors, scorecard and assessment text, Reddit answers and posts, LinkedIn posts, Slack replies, agency outreach notes, podcast pitches and decks about RateMyPrompts. Triggers on: RateMyPrompts copy, RMP tone of voice, brand voice, on-brand, does this sound like RateMyPrompts, rewrite in our voice, check this post, review this email, Reddit answer, LinkedIn post for RMP. Runs a deterministic house-rules check (count rule, British English, no em dashes, banned SaaS words) and the zebora-ai-tells scorer, then judges the copy against the five-question writing test. Not for Zebora copy, which has its own voice.
---

# ratemyprompts-voice

Writes and reviews RateMyPrompts copy so it sounds like RateMyPrompts: a smart, slightly irreverent GEO measurement nerd who questions everything and can back it up.

**Tagline:** Easy to understand. Hard to dismiss.

**The source.** `references/tone-of-voice.md` is a copy of the tone of voice Google Doc (v1.1) plus the house rules. The Google Doc is the master: <https://docs.google.com/document/d/1X9TCaLPfGfB5h_Uqr7XBq3iAFpGsHbwecYRDO5gBDpc/edit>. The same file lives in the RateMyPrompts app at `apps/ratemyprompts/docs/tone-of-voice.md` in `zebora-marketing`.

**Not this skill:** Zebora copy (the consultancy is "considered and authoritative"; RateMyPrompts is the outspoken product brand, section 8). Legal text (terms, privacy, cookies) keeps the wording Liam approved; do not restyle it.

## The one rule

**The scripts count. You judge.** Use the numbers from `scripts/check.py` and `zebora-ai-tells` verbatim. Never re-count by hand. Your job is what comes after: does it make someone think, is it the right register for where it is going, and what to change.

## Procedure

### 1. Pin down the job

Before writing a word, settle three things (ask only if they cannot be inferred):

- **Mode:** draft new copy, or review existing copy.
- **Context**, from section 6 of the tone of voice. It sets the register:

  | Context | Register | Humour |
  | --- | --- | --- |
  | Homepage and brand messaging | Confident, challenging, memorable | Occasional |
  | Social media and campaigns (LinkedIn, Product Hunt) | Most expressive | Welcome, earned |
  | Educational content (Reddit answers, research posts, articles, podcast pitches) | Intelligent, questioning, evidence-led | Light, dry |
  | Product interface and onboarding (forms, steps, buttons) | Friendly, concise, direct | Rare |
  | Scorecards, assessments, methodology | Precise, objective, constructive | **None** |
  | Errors, data and privacy, complaints | Clear, respectful, helpful | **None** |

- **Channel rules** that sit on top of the voice:
  - **Reddit, Slack, forums:** first line discloses ("I work on RateMyPrompts at Zebora"). Answer the question in full in the thread. Links and offers only where that community's rules allow (see `apps/ratemyprompts/docs/outreach-playbook.md` in `zebora-marketing`).
  - **LinkedIn:** Grant's or Liam's own voice, first person, the RateMyPrompts personality underneath.
  - **Email to a named person:** short, one ask, an easy no.
  - **Site copy:** match the existing vocabulary in `references/tone-of-voice.md` (house rules table).

### 2. Read the voice

Read `references/tone-of-voice.md` in full the first time in a session (about 250 lines). After that, re-read sections 2, 6, 7 and the house rules for each new piece.

### 3. Draft (draft mode)

- Lead with the point of view, then explain it simply. Aim at the 50/30/20 mix (Challenger, Measurement Expert, Straight Talker) as a feel, not a formula.
- Challenge the practice, never the person or a named tool.
- Every number comes from the claims register in the house rules, with its source and sample in the same passage. If the piece needs a figure that is not in the register, say so and leave a `[figure needed: ...]` marker. Never invent one.
- One joke at most per short piece, and only where the context allows it.
- Then review your own draft with step 4 before showing it.

### 4. Review (both modes)

Save the copy to a file (or pipe it), then run both checks:

```sh
python3 ~/.claude/skills/ratemyprompts-voice/scripts/check.py <file>        # add --html for a page
python3 ~/.claude/skills/zebora-ai-tells/scripts/score.py <file>
```

For a live page: `curl -s <url> -o /tmp/page.html` and pass that file.

- `check.py` "must fix" findings are house-rule breaches: fix every one before the copy ships. "To check" findings need a decision: keep (say why) or change.
- In the tone of voice document itself, the banned words appear as examples. That is expected.
- `zebora-ai-tells`: 84 is the human baseline, not 100. Under about 70, fix the top findings it ranks.

Then judge the copy against the five-question test (section 9), one line each:

1. **Does it make someone think?** What assumption does it challenge?
2. **Does it sound human?** Would an intelligent, opinionated person say it out loud?
3. **Is it clear?** Any jargon a reader would have to decode?
4. **Can we back it up?** Every claim sourced, nothing that implies validity we have not shown, nothing from the scoring rubric while it is being finalised.
5. **Does it sound like RateMyPrompts?** Or could any AI SaaS company have written it?

And two more for RateMyPrompts specifically:

6. **Right register for the context?** (step 1 table)
7. **Kind to the reader?** It questions their numbers, never them. Low scores are not proof that their GEO platform is unreliable (section 7).

### 5. Report

Keep it short. For a review:

```
House rules: N must fix, M to check        (check.py)
Human Read Score: NN                       (zebora-ai-tells)
Writing test: 1 ✓  2 ✓  3 ✗  4 ✓  5 ✗  6 ✓  7 ✓
Context: <context>, register <right / too playful / too flat>

Fix first
1. <quote> → <rewrite>   (why, in a few words)
2. ...

Optional
- ...
```

For a draft: the draft, then the same three-line summary under it. Offer two or three alternatives only for headlines, subject lines and opening lines.

Do not edit files unless asked. When asked to apply changes to the site, edit the copy where it lives (for example `apps/ratemyprompts/lib/beta/signup.ts`) and run the app's tests, because many tests pin exact copy.

## Guardrails

- **Never** state or imply how many founding places are taken or left. "50 founding places" only.
- **Never** invent or round up a statistic, and never attribute a figure to the wrong source.
- **Never** quote rubric weightings, thresholds or score bands in public copy until Grant says the scoring system is confirmed.
- **Never** name a Zebora client, or criticise a named tool or a named person's prompt set.
- **Never** post, send or publish. This skill writes and reviews; a person sends.
- British English, no em dashes, no emoji. The checker enforces these; do not argue with it.

## Keeping it current

When the Google Doc moves past v1.1:

1. Read the Doc and update `references/tone-of-voice.md` here and `apps/ratemyprompts/docs/tone-of-voice.md` in `zebora-marketing` with the same text. Keep the house rules section at the foot.
2. Update the version line in both, and in the app's `CLAUDE.md` if it names the version.
3. If the Doc changes the banned words or the vocabulary, update `RULES` in `scripts/check.py` and run it on a known-bad sample and on the live homepage (expect 0 must fix).
4. Add new figures to the claims register only with their source and sample.

## Related

`zebora-ai-tells` (the human-sounding check) · `zebora-icp` (who the copy is for) · `zebora-linkedin` (posting mechanics) · `apps/ratemyprompts/docs/outreach-playbook.md`, `docs/outreach-posts.md` and `docs/gtm-founding-partners.md` in `zebora-marketing` (channels, drafted posts and templates)
