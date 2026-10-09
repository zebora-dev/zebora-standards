# Slide patterns and design rules

Canvas is 10 × 5.625 in. Side margin 0.6 in, so the content width is 8.8 in. Title at y 0.42.
Content usually runs y 1.2 → 4.9. Footer (page number left, logo right) at y 5.1.

## Brand in one paragraph

Deep Field `#081514` canvas, Signal Green `#00EB5B` for the one thing to look at, Slate White
`#F8FAFC` headings, `#C5D1CE` body. Inter everywhere; Roboto Mono for small labels and page numbers.
Thin-bordered rounded cards, lucide icons in green-tinted circles, faint grid, signal-wave lines on
title and closing slides. Light slides (slate white with grid) are available for rhythm in longer
decks — the website alternates dark and light.

## Rules that kept the output good

- **One focal point per slide.** Exactly one card, row or phrase gets the green treatment
  (`card(..., { hi: true })`, green title). In three-card rows it is usually the Zebora / strategy
  one, or the last step.
- **Vary the pattern.** Do not put every slide on the same three-card row.
- **Never add words.** No invented eyebrows, labels or captions. Mono eyebrows only where the source
  already has a label ("01 / MONITORING").
- **Characters that are copy stay as text.** "+", "→", "↓" in the source go in `pill()` or a text
  box. If you redraw them as shapes or icons, say so in the hand-off.
- **Keep the author's emphasis.** Bold and green runs in the master stay bold / green.
- **De-emphasise with `quiet`** (dashed, see-through card, muted text) for the "can't influence",
  "old way", "other" item.
- **No decorative stripes or underlines.** Hairline dividers inside a card are fine.
- **Alternate `dark` and `darkAlt`** backgrounds on consecutive content slides.
- **Images:** reuse the master's. Screenshots get a frame and a shadow; logos on white get a white
  card; never stretch — pre-crop with sharp/Pillow to the frame's ratio.

## Sizes that fit (Google Slides, Inter)

| Element | Size | Fits |
|---|---|---|
| Slide title, one line | 26 pt bold | ~48 characters |
| Slide title, two lines | 24 pt, `h: 0.9` | ~100 characters; start content at y ≥ 1.5 |
| Card title in a 2.75 in card | 15–16 pt bold | ~20 characters per line; allow two lines |
| Card body in a 2.75 in card | 11–12 pt | ~34 characters per line |
| Dense card body | 10 pt | minimum; below this, restructure instead |
| Mono label / page number | 8–9 pt | |

Three-card row: `x = 0.6 + i * 3.025`, `w = 2.75`. Two-card row: `x = 0.6 + i * 4.5`, `w = 4.3`.
Five-step row: `w = 1.64`, gap `0.15`.

## Patterns (see the examples for code)

| Pattern | Use when the slide says | Example |
|---|---|---|
| **Cover / closing** | title, date, tagline | vitruvian 1, 10 |
| **Three-card row** | three parallel ideas, layers, pillars | vitruvian 2, 6, 9 |
| **Before → after pair** | "was X, now Y", "less this, more that" | vitruvian 3, 4 |
| **Chip chain** | a one-line sequence joined by arrows | vitruvian 4 (bottom) |
| **Hub and spokes** | one question or brand surrounded by sources | vitruvian 5 |
| **Tagged buckets** | columns with a category tag and a list | vitruvian 6 |
| **Two cards + callout bar** | two contrasting cases and a takeaway line | vitruvian 7 |
| **Labelled ladder** | a top-to-bottom chain with an example per step | vitruvian 8 |
| **Process flow** | the same chain as a left-to-right pipeline with icon nodes | process-flow.slide.js |
| **Prompt bar** | an example question someone asks an AI | vitruvian 8, creds 2 |
| **Steps + image** | numbered steps beside product screenshots | creds 6 |
| **2 × 2 reasons (light)** | four numbered reasons | creds 7 |
| **Case study** | image + challenge / diagnosis / framework / outcome | creds 8, 9 |
| **Logo strip + quote (light)** | client logos and a testimonial | creds 12 |

## Imagery recipes (`scripts/image_recipes.py`)

- **tilt** — a dashboard screenshot laid back at the website's platform-card angle
  (`perspective 1600px; rotateX(50deg) rotateZ(-20deg)`), with chosen cards cut out, enlarged and
  floating above it. `--card-rx 28` (cards tipped forward, readable) was the version the team chose;
  `50` keeps them flat on the plane, `12` nearly faces the viewer. Find card boxes by viewing the
  source image and reading pixel coordinates.
- **collage** — several screenshots or crops as browser windows, layered with shadows; `--tilt` for
  the leaning version. Lesson learned: showing whole screens makes text ~3 pt on a slide. Use
  focused crops of the important region, and offer variations (flat cascade, tilted, no-overlap
  grid, hero + call-outs).
- **cutout** — lift a four-cornered object (e.g. the tilted browser window in the Pimento brochure
  artwork) out of a larger image with rounded corners and a transparent background. Removes any
  labels outside the shape; pointer lines inside it remain and can be reused by placing the deck's
  own labels at their ends.

Slot sizes: half-slide image ≈ 5.05 × 3.64 in → render 2555 × 1843. Wide in-card image ≈
4.74 × 2.37 in → render 2180 × 1090.
