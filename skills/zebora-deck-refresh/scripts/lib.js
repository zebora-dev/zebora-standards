// Shared Zebora deck helpers for pptxgenjs build scripts.
// Usage (from a build script in the deck's working folder):
//   const { create } = require('<skill>/scripts/lib.js');
//   const z = create({ title: 'Deck name', total: 10 });
//   const s = z.pres.addSlide(); z.frame(s, 2, 'darkAlt'); z.title(s, 'Slide title'); ...
//   await z.pres.writeFile({ fileName: 'Deck - brand refresh.pptx' });
// Expects ./bg and ./assets to exist (run brand_assets.js first).
const pptxgen = require('pptxgenjs');
const sharp = require('sharp');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const Lu = require('react-icons/lu');

// Brand tokens — keep in step with zebora-marketing design-tokens/brand-tokens.css
const T = {
  G: '00EB5B',          // Signal Green: accent, highlights, the one thing to look at
  TEAL: '008A5C',       // Deep teal: secondary
  DEEP: '081514',       // Deep Field: dark canvas
  WHITE: 'F8FAFC',      // Slate White: headings on dark
  BODY: 'C5D1CE',       // body text on dark
  MUTED: '8A9E9A',      // captions, page numbers, de-emphasised items
  CARD: '0E1E1C', CARD_LINE: '21403A',   // standard card
  HI_FILL: '0B2A1C', HI_LINE: '1F6B45',  // highlighted card
  L_TEXT: '0B1A18', L_BODY: '475569', L_LINE: 'E2E8F0',  // light slides
  HEAD: 'Inter', MONO: 'Roboto Mono',    // both are native Google Slides fonts
};

function create({ title, total }) {
  const pres = new pptxgen();
  pres.layout = 'LAYOUT_16x9';                 // 10 x 5.625 in — matches Google Slides default
  pres.title = title;
  pres.theme = { headFontFace: T.HEAD, bodyFontFace: T.HEAD };
  const A = (f) => `assets/${f}`;

  async function icon(Comp, color = '#00EB5B') {
    const svg = renderToStaticMarkup(React.createElement(Comp, { color, size: 256, strokeWidth: 1.75 }));
    return 'image/png;base64,' + (await sharp(Buffer.from(svg)).png().toBuffer()).toString('base64');
  }

  // Background, footer logo and "03 / 10" page number. Skip on title and closing slides.
  function frame(s, n, bg = 'dark', { light = false } = {}) {
    s.background = { path: `bg/${bg}.jpg` };
    s.addImage({ path: A(light ? 'logo-dark.png' : 'logo-white.png'), x: 8.55, y: 5.1, w: 0.85, h: 0.25, objectName: 'Zebora logo' });
    s.addText(String(n).padStart(2, '0') + ' / ' + total, { x: 0.6, y: 5.1, w: 1.2, h: 0.25, margin: 0, fontFace: T.MONO, fontSize: 8, color: light ? '94A3B8' : T.MUTED, charSpacing: 1, isTextBox: true });
  }

  // `runs` is a string, or [{ text, color?, breakLine? }] for a green-highlighted phrase.
  // A 26pt title fits ~48 characters on one line; use { size: 24, h: 0.9 } for two lines.
  function title(s, runs, { h = 0.6, size = 26, w = 8.8, light = false } = {}) {
    const arr = typeof runs === 'string' ? [{ text: runs }] : runs;
    s.addText(arr.map((r) => ({ text: r.text, options: { bold: true, color: r.color || (light ? T.L_TEXT : T.WHITE), breakLine: r.breakLine } })), {
      x: 0.6, y: 0.42, w, h, margin: 0, fontSize: size, valign: 'top', isTextBox: true, objectName: 'Title',
    });
  }

  // hi = the one card to look at (green outline). quiet = de-emphasised (dashed, see-through).
  function card(s, x, y, w, h, { hi = false, quiet = false, light = false, name = 'Card' } = {}) {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x, y, w, h, rectRadius: 0.08, objectName: name,
      fill: { color: light ? 'FFFFFF' : hi ? T.HI_FILL : T.CARD, transparency: light ? 0 : quiet ? 45 : 8 },
      line: { color: light ? T.L_LINE : hi ? T.G : T.CARD_LINE, width: hi ? 1.25 : 0.75, dashType: quiet ? 'dash' : 'solid' },
      shadow: light ? { type: 'outer', color: '0F172A', opacity: 0.08, blur: 10, offset: 2, angle: 90 } : undefined,
    });
  }

  // Lucide icon in a green-tinted circle. Browse icons: https://lucide.dev (names are Lu + PascalCase).
  async function badge(s, Comp, x, y, d, { light = false, solid = false } = {}) {
    s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: solid ? T.G : light ? 'DCFCE7' : T.HI_FILL }, line: { color: solid ? T.G : light ? 'BBF7D0' : '1F5A3A', width: 0.75 } });
    const p = d * 0.26;
    s.addImage({ data: await icon(Comp, solid ? '#081514' : light ? '#008A5C' : '#00EB5B'), x: x + p, y: y + p, w: d - 2 * p, h: d - 2 * p });
  }

  // Round connector holding a character that is part of the copy ("+", "→").
  function pill(s, text, cx, cy, d = 0.42) {
    s.addShape(pres.shapes.OVAL, { x: cx - d / 2, y: cy - d / 2, w: d, h: d, fill: { color: T.DEEP }, line: { color: T.G, width: 1 } });
    s.addText(text, { x: cx - d / 2, y: cy - d / 2, w: d, h: d, margin: 0, align: 'center', valign: 'middle', fontSize: 15, bold: true, color: T.G, isTextBox: true });
  }
  // Round connector with a drawn arrow, for when the arrow is NOT part of the copy.
  async function arrowPill(s, cx, cy, d = 0.42) {
    s.addShape(pres.shapes.OVAL, { x: cx - d / 2, y: cy - d / 2, w: d, h: d, fill: { color: T.DEEP }, line: { color: T.G, width: 1 } });
    s.addImage({ data: await icon(Lu.LuArrowRight), x: cx - 0.11, y: cy - 0.11, w: 0.22, h: 0.22 });
  }

  // Mono uppercase-style label, e.g. "01 / MONITORING". Never add one that is not in the source copy.
  function eyebrow(s, text, x, y, w, { color = T.G } = {}) {
    s.addText(text, { x, y, w, h: 0.25, margin: 0, fontFace: T.MONO, fontSize: 9, bold: true, color, charSpacing: 1, isTextBox: true });
  }

  // Full-width green-tinted bar for the slide's takeaway line.
  function callout(s, runs, y, { h = 0.55, size = 12.5 } = {}) {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y, w: 8.8, h, rectRadius: 0.08, fill: { color: T.G, transparency: 90 }, line: { color: T.G, width: 0.75, transparency: 60 } });
    s.addText(runs, { x: 0.85, y, w: 8.3, h, margin: 0, valign: 'middle', fontSize: size, color: T.BODY, isTextBox: true });
  }

  // Search-bar style pill for an example prompt.
  function promptBar(s, runs, y, { h = 0.5, size = 13.5, x = 0.6, w = 8.8 } = {}) {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: h / 2, fill: { color: 'FFFFFF', transparency: 92 }, line: { color: T.G, width: 1, transparency: 40 }, objectName: 'Prompt bar' });
    s.addText(runs, { x: x + 0.55, y, w: w - 1.3, h, margin: 0, valign: 'middle', fontSize: size, color: T.WHITE, isTextBox: true });
  }

  // Title / closing slide scaffold: wave background + large logo.
  function cover(s, { bg = 'hero', logo = { x: 0.75, y: 0.6, w: 1.5 } } = {}) {
    s.background = { path: `bg/${bg}.jpg` };
    s.addImage({ path: A('logo-white.png'), x: logo.x, y: logo.y, w: logo.w, h: logo.w * 40.94 / 139.19, objectName: 'Zebora logo' });
  }

  return { pres, T, Lu, A, icon, frame, title, card, badge, pill, arrowPill, eyebrow, callout, promptBar, cover };
}

module.exports = { create, T };
