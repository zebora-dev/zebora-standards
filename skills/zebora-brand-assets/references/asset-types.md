# Asset types

`make_asset.py --list` prints the formats the renderer knows. Pick the format from where the image
will be used, then the layout.

| Asset | `--format` | Size (px) | Default layout | Notes |
|---|---|---|---|---|
| LinkedIn / Instagram post | `linkedin-post` | 1080 × 1080 | centre | Legible on a phone: headline up to ~10 words. |
| LinkedIn cover | `linkedin-header` | 1584 × 396 | header | Lower-left is covered by the avatar: text starts a quarter in, logo top right. Check on mobile, where the sides are cropped. |
| Link preview / Open Graph | `social-share` | 1200 × 630 | centre | For zebora.io pages use the site's own template (below). |
| Guide / article header | `blog-header` | 1600 × 900 | left | Use `split` with a product image for platform topics. |
| Slide image or title card | `slide` | 1920 × 1080 | left | One slide only. Whole decks go to `zebora-deck-refresh`. |
| Story / reel cover | `story` | 1080 × 1920 | centre | Keep the top and bottom 250 px free of text (app chrome). |
| Report or one-pager cover | `doc-cover` | 1240 × 1754 | left | A4 at 150 dpi. Light theme suits printed documents. |
| Email or newsletter banner | `email-header` | 1200 × 400 | left | Logo moves top right. Headline only; keep it short. |

Anything else: pick the nearest ratio and say so, or ask for the exact size.

## Layouts

- **centre**: eyebrow pill, centred headline, sub, logo top left, ring and signal waves at the
  bottom. Matches the zebora.io share images. `--image` adds a framed image under the text.
- **left**: left-aligned thesis, waves and rings to the right, registration mark bottom right.
  `--image` places the image on the right half.
- **split**: text on the left 40%, a product image on the right half. Needs `--image`. Best with a
  transparent tilted dashboard from `zebora-deck-refresh` (`image_recipes.py tilt`).
- **header**: the LinkedIn cover arrangement.

`--theme light` gives the slate-white canvas with a faint grid; the accent becomes deep teal.

## Existing tooling to use instead of, or with, this skill

| Need | Use | Where |
|---|---|---|
| A whole deck re-skinned, or several slides | `zebora-deck-refresh` | this repo |
| Tilted dashboard with floating cards, screenshot collage, browser-window cut-out | `zebora-deck-refresh/scripts/image_recipes.py` (`tilt`, `collage`, `cutout`) | this repo; output a transparent PNG and pass it as `--image` |
| An AI-generated background or illustration | Brand Asset Studio (GPT Image 2 with the brand base prompt; saves to the media library) | `https://brand.zebora.io/brand-guidelines/studio`, see `ai-backgrounds.md` |
| LinkedIn header and post templates with client logos | Template pages on the brand site | `https://brand.zebora.io/brand-guidelines/linkedin-headers` and `/linkedin-posts` |
| Share images for zebora.io pages | `docs/social-image-template.html` | `zebora-marketing`; edit the page's entry and screenshot the 1200 × 630 stage |
| Official logo files (SVG, EPS, PNG) and icons | Guidelines and icon library | `https://brand.zebora.io/brand-guidelines` and `/icons` |
| Product screenshots | `apps/marketing/public/platform/cards/` | `zebora-marketing` (no client data) |

Client logos appear on some brand-site templates. Only use a client's logo where that client has
agreed to be named publicly; ask if unsure.
