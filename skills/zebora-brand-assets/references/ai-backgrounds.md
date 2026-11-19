# AI-generated backgrounds

Claude cannot generate photographic or painterly images itself. When a brief needs one (an
abstract signal landscape, an editorial illustration), write a brief for the **Brand Asset Studio**
at `https://brand.zebora.io/brand-guidelines/studio`. The studio adds the brand base prompt below,
runs GPT Image 2 (other models through AI Gateway), and saves the result to the media library. The
user downloads it and gives it back; it then goes in as `make_asset.py --bg <file>`, and the real
logo and headline are added on top.

Source: `zebora-marketing/apps/brand/lib/brand-studio/` (`prompt.ts`, `intake.ts`) and
`lib/config/brand-guidelines.ts`.

## What to hand the user

Fill in the studio's fields for them:

| Field | Options |
|---|---|
| Purpose | LinkedIn post · LinkedIn header · Blog / article hero · Deck slide background · Document / report cover · General |
| Asset type | **Background only** (default; text added later) · Leave room for a logo + headline · Illustrative scene |
| Direction | `signal-field` · `editorial-system` · `marketplace-map` · `brand-orbit` (or none) |
| Placement | Quiet space left · right · top · central focal point |
| Avoid | anything specific to this brief |
| Brief | one or two plain sentences about the subject and mood |

Directions, as the studio words them:

- **signal-field**: fine waves, measured nodes, subtle topography, one vivid focal point.
- **editorial-system**: architectural whitespace, tactile depth, clean geometry, human strategic
  intelligence.
- **marketplace-map**: an AI recommendation marketplace: connected pathways, ranked signals, quiet
  movement, no dashboard UI.
- **brand-orbit**: one trusted central entity surrounded by recommendation pathways and sparse
  evidence signals.

Choose "Quiet space left" for the `left` and `split` layouts and "Quiet space top" or "central focal
point" for `centre`. Start at draft quality and move up once the composition is right.

## Base prompt (the studio adds it automatically)

> Create a premium editorial technology visual for Zebora, an AI brand intelligence consultancy +
> platform. Use a deep near-black green field (#081514 to #000B02), a single vivid signal-green
> accent (#00EB5B), fine measurement grids, restrained connected-node or topographic forms, generous
> negative space, crisp high contrast, and calm strategic authority. The image should feel precise,
> intelligent, modern, and human-led, not futuristic spectacle. No text, no logos, no humanoid
> robots, no glowing brains, no neon cyberpunk, no generic dashboard UI, no blue-purple SaaS
> gradient.

If the user has no studio login, they can paste the base prompt plus the brief into another image
tool the team has approved. Never ask any model to draw the logo or words.
