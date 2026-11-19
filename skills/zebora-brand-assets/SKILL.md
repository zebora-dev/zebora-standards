---
name: zebora-brand-assets
description: Make on-brand Zebora images and assets from a chat brief - LinkedIn posts and covers, link-preview (Open Graph) images, blog and guide headers, single slide images and title cards, story covers, report covers and email banners. Applies the brand (Deep Field + Signal Green, Inter, signal-wave backgrounds, grids and registration marks, one green focal point, the supplied logo only), renders a PNG with the bundled script, and shows it before anything is used. Reuses zebora-deck-refresh for decks and product imagery (tilted dashboards, collages, browser-window cut-outs) and the Brand Asset Studio for AI-generated backgrounds. Works in Claude Code and in the Claude desktop / claude.ai app. Triggers on: make an image, social image, LinkedIn post image, LinkedIn banner, header image, OG image, blog header, hero image, slide image, cover image, email banner, on-brand graphic, Zebora asset.
---

# zebora-brand-assets: on-brand images from a brief

**Invocation:** `/zebora-brand-assets <what it is for, and the words if known>`

Turns a plain-English request ("a LinkedIn post announcing our Web Summit talk") into a finished,
correctly sized PNG in the Zebora brand. Works for anyone on the team: the user never needs to
know a size, a hex value or a command.

`$SKILL` below is this skill's folder (in the claude.ai sandbox, find it with
`find / -name make_asset.py -path "*zebora-brand-assets*" 2>/dev/null`).

## House rules (do not relax without the user saying so)

1. **The logo is supplied artwork.** Use only `assets/logo/`. Never redraw, retype, recolour or
   stretch it, and never ask an image model to draw it or any words.
2. **One green focal point.** Exactly one phrase, node or object gets Signal Green.
3. **The user's words, checked.** Use their copy where they give it. Where you write it, keep it
   short, in British English, sentence case, with no em dashes and no hype words
   (`references/brand.md`, "Words on images"). Show the copy before rendering if you wrote it.
4. **Show before it's used.** Render, look at the result yourself, then show it. Offer 2 or 3
   variations (layout, theme, headline split) when the brief is open.
5. **No client data by accident.** Product screenshots must not show a client's data unless the
   asset is for that client, or the user confirms. Only use client logos where the client has agreed
   to be named. Say whose data is visible.
6. **Private stays private.** The brand guidelines and media library are behind a team login. Don't
   publish them, and don't post or send the asset anywhere: hand the file to the user.

## The process

### 1. Pin down the brief (ask only what you can't infer)

- **Where it goes** → the format (`references/asset-types.md`). "For LinkedIn" means a post unless
  they say banner or cover.
- **The words**: headline, the phrase to make green, optional eyebrow (1 to 4 words) and sub
  (one sentence).
- **Imagery**: none (brand background), a product screenshot, or an AI-generated background.
- **Theme**: dark unless they ask for light or it's for print.

If it is a whole deck, or several slides restyled together, stop and use `zebora-deck-refresh`.

### 2. Prepare any imagery

- **Product screenshot, tilted with floating cards / collage / cut-out:** use
  `zebora-deck-refresh/scripts/image_recipes.py` (`tilt`, `collage`, `cutout`; needs Pillow and
  numpy). It writes a transparent PNG. Pass that as `--image`. Do not reimplement these recipes.
- **Plain screenshot:** pass it straight to `--image`; it gets a browser-window frame and shadow.
- **AI background:** write the Brand Asset Studio brief from `references/ai-backgrounds.md`, give it
  to the user, and wait for the downloaded image. Pass it as `--bg`.

### 3. Render

```sh
python3 $SKILL/scripts/make_asset.py --list
python3 $SKILL/scripts/make_asset.py --format linkedin-post \
  --eyebrow "Web Summit 2026" --headline "Know why you're winning or losing in AI." \
  --accent "winning or losing" --sub "Join our talk on AI brand visibility." --out post.png
```

| Flag | Meaning |
|---|---|
| `--format` | where it goes (sets the size and the default layout) |
| `--layout` | `centre`, `left`, `split` (needs `--image`), `header` |
| `--theme` | `dark` (default) or `light` |
| `--headline` / `--accent` | headline, and the phrase inside it set in green; `\n` forces a line break |
| `--eyebrow` / `--sub` | small mono label above; one supporting sentence below |
| `--image` / `--bg` | an image to place; a finished background to sit under everything |
| `--out` | `.png` (default) or `.jpg` |

The script refuses copy with an em dash or a word on the brand's avoid list. Fix the copy; don't
work around the check. Needs only Python 3 and Pillow (`pip install Pillow` if missing).

### 4. Look, then show

Open the PNG and check: nothing clipped or crowding the logo, the headline wraps sensibly (use `\n`
to choose the break), the green phrase is the one that matters, text is readable at the size it
will be seen (a LinkedIn post on a phone is ~350 px wide). Fix and re-render before showing.

Then give the user the file. In the desktop / claude.ai app, attach it to the reply; in Claude
Code, say where it is saved. Offer the variations from rule 4.

### 5. Hand off

Say what was made (format, size, layout), list any copy you wrote, name any client data or logos
visible, and mention the next step if there is one (upload to LinkedIn, add to Contentful, drop into
a deck with `zebora-deck-refresh`).

## Files

```
scripts/make_asset.py       renderer: formats, layouts, copy check          -> PNG / JPG
references/brand.md         colour, type, visual language, logo and copy rules (from the guidelines)
references/asset-types.md   sizes and layouts per asset, and which existing tool to use when
references/ai-backgrounds.md  Brand Asset Studio brief fields, directions, base prompt
assets/logo/                supplied logo artwork (SVG + PNG): on-dark, on-light, green icon
assets/fonts/               Inter (Regular, Medium, SemiBold), Roboto Mono (Medium, SemiBold; Latin), OFL licences
examples/                   sample outputs
```

## Guardrails

- Side effects: writing image files to the working folder only. No uploads, posts, emails or
  sharing changes.
- Keep client screenshots and finished client assets out of this repo; work in a scratch folder.
- When the brand guidelines change (`zebora-marketing/apps/brand/lib/config/brand-guidelines.ts`),
  update `references/brand.md` and the colours at the top of `make_asset.py` in the same PR. The
  deck tokens in `zebora-deck-refresh/scripts/lib.js` follow the same source.
