---
name: zebora-deck-refresh
description: Re-skin and restructure an existing Google Slides deck into the Zebora brand without changing its copy. Makes a copy (never edits the master), rebuilds every slide with the website's look (Deep Field + Signal Green, signal-wave backgrounds, Inter, cards, icon badges, process flows), verifies the copy word-for-word, uploads it as native Google Slides and checks Google's own render. Also builds slide imagery (tilted dashboards with floating cards, screenshot collages, browser-window cut-outs) and swaps single slides or images into a live deck without losing hand edits. Triggers on: re-skin deck, restyle deck, brand refresh, deck redesign, creds deck, make this deck on-brand, improve the look of this presentation, Google Slides styling, better slide image, process flow slide.
---

# zebora-deck-refresh — re-skin a deck into the Zebora brand

**Invocation:** `/zebora-deck-refresh <Google Slides link or deck name>`

Takes a deck that is mostly correct in *content* but weak in *look and structure*, and produces a
brand-aligned copy as a native Google Slides file next to the original. Proven on the agencies creds
deck (13 slides) and the Vitruvian GEO deck (10 slides) in October 2026.

## House rules (do not relax without the user saying so)

1. **Never touch the master.** Always work on a new file named `<original title> - brand refresh`.
2. **Never change the copy.** Every word, number and punctuation mark stays. Restructuring means
   layout, hierarchy, grouping and imagery — not wording. This includes typos: leave them, and list
   them for the user at the end. The only permitted additions are a page number (`03 / 10`) and
   purely decorative glyphs (e.g. a large quotation mark); declare both in the hand-off.
3. **Prove the copy.** Run `deck_tools.py textcheck` after every build. "Missing" must be empty.
4. **Check Google's render, not your own.** Fonts and wrapping only resolve in Google Slides. Export
   the converted deck to PDF and look at every slide before telling the user it is done.
5. **Check for hand edits before replacing anything.** Once the user has the link they will edit the
   deck. Run `deck_tools.py livecheck` first. If anything differs, do not replace the file — paste
   single slides or images in, and mirror their edits in the build script.
6. **Show image options before placing them.** For any new image, render a preview on the dark
   canvas, send it, and wait for a choice. Offer 2–4 variations when the brief is open.
7. **Say what was left out.** If a crop, overlap or layout hides content, name what is hidden.
8. **Only bin files you created.** Interim uploads go to the Drive bin (recoverable). Never permanently
   delete, and never bin a file the user made.

## What you need

| Need | Why | If missing |
|---|---|---|
| Google Drive connector | read the master, export PPTX/PDF, find and bin files | stop — cannot read the deck |
| Claude in Chrome, signed in to the same Google account | upload and convert (the Drive connector cannot take a multi-MB file) | hand the user the `.pptx` and ask them to drag it into Drive and use File → Save as Google Slides |
| Node 20+ and Python 3.10+ | build and checks | install them |
| `zebora-marketing` repo (optional) | product screenshots and the site's styling for imagery | ask the user for the image files |

First run on a machine, from this skill's folder:

```sh
npm install                       # pptxgenjs, sharp, react-icons (node_modules is git-ignored)
pip3 install -r requirements.txt  # python-pptx, PyMuPDF, Pillow, numpy
```

Work in a scratch folder per deck. Temp areas get cleared after a few days: **if the user is likely
to come back to a deck, keep the build script somewhere durable** and say where.

## The process

`$SKILL` is this skill's folder. `$T` is the Drive tool-result JSON path the connector saves large
downloads to.

### 1. Find and read the master

- If given a name rather than a link, search Drive and confirm which file (prefer the one the user
  viewed most recently; say which you picked).
- Read the text with the Drive connector, then download it twice: as PPTX and as PDF.

```sh
python3 $SKILL/scripts/deck_tools.py decode "$T_pptx" original.pptx
python3 $SKILL/scripts/deck_tools.py decode "$T_pdf"  original.pdf
python3 $SKILL/scripts/deck_tools.py render original.pdf orig          # look at orig_grid*.png
python3 $SKILL/scripts/deck_tools.py dump original.pptx --images img   # exact runs, tables, notes, images
```

- Read the dump carefully: it is the source of truth for copy. Note bold/colour emphasis (keep it),
  soft line breaks (`\x0b`, free to re-flow), tables, speaker notes (carry over with `addNotes`),
  and text that is baked into images (it is not copy you can check — leave those images intact).

### 2. Generate the brand kit

```sh
node $SKILL/scripts/brand_assets.js     # writes ./bg and ./assets
```

### 3. Write the build script

Copy the structure of `examples/vitruvian-geo.build.js` (uses `scripts/lib.js`). One block per slide.
Choose a pattern per slide from `references/patterns.md`; vary them, and give each slide one green
focal point. Reuse the master's images from `./img`. Paste copy from the dump — never retype it.

```sh
node build.js
python3 $SKILL/scripts/deck_tools.py textcheck original.pptx "<Title> - brand refresh.pptx"
```

### 4. Upload, convert, check

Follow `references/drive-workflow.md` exactly (upload into the master's folder → File → Save as
Google Slides → export PDF via the connector → render → inspect every slide). Typical first-render
defects: titles wrapping into the content below, card titles wrapping, text overflowing a card.
Fix in the build script, rebuild, re-run textcheck, re-upload. Bin the interim `.pptx` and any
superseded converted copy.

### 5. Hand off

Give the link, state that the master is untouched, summarise what changed slide by slide, and list:
additions (page numbers, decorative glyphs), typos left as written, anything hidden or dropped, and
which files you binned. Leave the new deck open in a Chrome tab.

### 6. Follow-up changes

Always `livecheck` the live deck against your last build first.

- **No hand edits:** rebuild and replace the file (new link — tell the user), or paste one slide.
- **Hand edits found:** paste only the changed slide or image (`references/drive-workflow.md`), and
  copy the user's positions into the build script with a comment so a future rebuild keeps them.
- **New imagery:** `scripts/image_recipes.py` (`tilt`, `collage`, `cutout`). Preview first (rule 6).
- **"Copy this slide and try a better X":** build a standalone one-slide script
  (`examples/process-flow.slide.js`) and paste it in after the original, leaving the original alone.

## Files

```
scripts/brand_assets.js    backgrounds + logos                     -> ./bg ./assets
scripts/lib.js             pptxgenjs helpers and brand tokens
scripts/deck_tools.py      decode | dump | render | textcheck | livecheck | extract
scripts/image_recipes.py   tilt | collage | cutout
references/patterns.md     slide patterns, sizes that fit, design rules
references/drive-workflow.md  upload, convert, paste-a-slide, paste-an-image, known failure modes
examples/                  vitruvian-geo.build.js (uses lib.js) · process-flow.slide.js (standalone)
                           creds-agencies.build.js (first deck, pre-lib; reference only)
assets/                    zebora-logo.svg, google.svg, openai.svg
```

## Guardrails

- Side effects are limited to: creating files in the master's Drive folder, binning files this run
  created, and editing the *copy* deck. No sharing-permission changes, no emailing, no edits to the
  master.
- Uploading drives the user's real Chrome session. Open your own tab, close it when done (leave only
  the finished deck open), and do not touch other tabs.
- Client names and figures appear in decks. Keep working files in the scratch folder; do not commit
  client decks or screenshots to this repo.
- Do not use product screenshots containing one client's data in a deck for a different client
  without telling the user whose data is shown.
