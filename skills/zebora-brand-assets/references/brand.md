# Zebora brand, for images

Condensed from the private brand guidelines (v1.1, 24 June 2026) in `zebora-marketing`:
`apps/brand/lib/config/brand-guidelines.ts` (source of truth), served at
`https://brand.zebora.io/brand-guidelines` (team login) and as `/brand-guidelines/brand.md`.
If the two disagree, the guidelines win: update this file in the same PR.

These guidelines are private. Do not paste them into public posts, prompts to third-party tools the
team has not approved, or client-facing files.

## Colour

| Name | Hex | Use |
|---|---|---|
| **Deep Field** | `#081514` | The canvas. Most assets are dark. |
| **True Dark** | `#000B02` | Gradient end, footers, maximum contrast. |
| **Signal Green** | `#00EB5B` | The one thing to look at: a highlighted phrase, a focal node, an active state. |
| Deep teal | `#008A5C` | Secondary glow; the accent colour on light backgrounds (Signal Green is too bright on white). |
| Mark Green | `#60BB51` | Only inside the supplied logo artwork. Never use it elsewhere and never recolour the logo. |
| **Slate White** | `#F8FAFC` | Headlines on dark; the light canvas. |
| Signal Grey | `#94A3B8` | Supporting text, labels, metadata. |

Print: Signal Green is outside CMYK and prints darker. For anything printed, hand over the SVG or
EPS logo and flag the green to the printer (the guidelines page has the CMYK builds).

## Type

- **Inter** for everything. Headlines 500 to 600 weight, sentence case, tight, one short phrase in
  Signal Green. Body 400, short sentences. The renderer sets headlines as the zebora.io hero does:
  Inter Medium, letter spacing -0.055em, line height 0.98, Inter's display optical size (the variable
  font, as browsers pick it at large sizes).
- **Roboto Mono** for small uppercase labels (eyebrows, scores, metadata), as on zebora.io (the
  site loads it under the CSS variable `--font-geist-mono`; the font is Roboto Mono). The bundled
  files are the Latin subset the site serves.
- **Source Serif 4** only for a quotation or a principle that needs an editorial tone.

## Visual language

- Dark, spacious canvas with **one** vivid green signal. Never two competing highlights.
- Measurement cues: a fine grid, thin rings, small registration marks (crosshairs), dashed borders.
- **Signal waves**: fine flowing lines, mostly faint white with every third line green. They stand for
  AI systems and shifting perception. Keep them behind or beside the text, never through it.
- **Cards**: flat or lightly graded, thin borders, rounded corners, restrained shadows, never glossy.
- **Icon badges**: Lucide outline icons (stroke 1.5 editorial, 2 interface) in a green-tinted circle.
- **Product imagery**: real dashboard screenshots, tilted back at the website's platform angle with
  key cards lifted and floating, or set in browser-window frames. Use focused crops, not whole
  screens, so text stays legible.
- Composition: a strong left-aligned or centred thesis, one focal signal, modular evidence, generous
  negative space.

Avoid: humanoid robots, glowing brains, neon cyberpunk, blue-purple SaaS gradients, generic stock
dashboards, clip-art AI icons, busy textures under text.

## Logo

- Use only the supplied artwork (`assets/logo/`). Never redraw, retype, stretch, outline or recolour
  it, and never ask an image model to draw it.
- Dark surfaces: `logo-on-dark` (white wordmark, green mark). Light surfaces: `logo-on-light`.
- Clear space at least the height of the icon's central cross. The icon alone only where the name
  is already established or space is tight.
- Strapline lockups exist on the guidelines page; never typeset the strapline yourself.

## Words on images

- Voice: clear, authoritative, direct, human. Confident, not inflated.
- British English (optimise, colour, organisation). No em dashes. Sentence case.
- Avoid "AI-powered" without the value, "revolutionary", "game-changing", fear-led claims and vague
  dashboard language.
- Preferred lines: "Own your narrative.", "Measure. Diagnose. Act.", "Black-and-white clarity.",
  "Consultancy + platform.", "Visible, trusted, and preferred."
- Keep image copy short: a headline of up to about 10 words, an optional eyebrow of 1 to 4 words and
  an optional one-sentence sub.
