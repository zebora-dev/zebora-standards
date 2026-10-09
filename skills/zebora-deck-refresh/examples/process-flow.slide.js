// Worked example: a single slide rebuilt as a horizontal process flow (track + icon nodes + cards).
// Standalone on purpose, so it can be pasted into a live deck as one slide. Run from a folder with ./bg and ./assets.
const pptxgen = require(require('path').join(__dirname, '..', 'node_modules', 'pptxgenjs'));
const sharp = require(require('path').join(__dirname, '..', 'node_modules', 'sharp'));
const React = require(require('path').join(__dirname, '..', 'node_modules', 'react'));
const { renderToStaticMarkup } = require(require('path').join(__dirname, '..', 'node_modules', 'react-dom', 'server'));
const Lu = require(require('path').join(__dirname, '..', 'node_modules', 'react-icons', 'lu'));
const G = '00EB5B', DEEP = '081514', WHITE = 'F8FAFC', BODY = 'C5D1CE', MUTED = '8A9E9A';
const CARD = '0E1E1C', CARD_LINE = '21403A', HI_FILL = '0B2A1C', HI_LINE = '1F6B45', MONO = 'Roboto Mono';
const pres = new pptxgen(); pres.layout = 'LAYOUT_16x9'; pres.theme = { headFontFace: 'Inter', bodyFontFace: 'Inter' };
async function icon(Comp, color = '#00EB5B') {
  const svg = renderToStaticMarkup(React.createElement(Comp, { color, size: 256, strokeWidth: 1.75 }));
  return 'image/png;base64,' + (await sharp(Buffer.from(svg)).png().toBuffer()).toString('base64');
}
(async () => {
  const s = pres.addSlide();
  s.background = { path: 'bg/darkAlt.jpg' };
  s.addImage({ path: 'assets/logo-white.png', x: 8.55, y: 5.1, w: 0.85, h: 0.25 });
  s.addText('08 / 10', { x: 0.6, y: 5.1, w: 1.2, h: 0.25, margin: 0, fontFace: MONO, fontSize: 8, color: MUTED, charSpacing: 1, isTextBox: true });
  s.addText('The real task is turning gaps into action', { x: 0.6, y: 0.42, w: 8.8, h: 0.6, margin: 0, fontSize: 26, bold: true, color: WHITE, valign: 'top', isTextBox: true });

  // The trigger: the example prompt
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: 1.18, w: 8.8, h: 0.5, rectRadius: 0.25, fill: { color: 'FFFFFF', transparency: 92 }, line: { color: G, width: 1, transparency: 40 } });
  s.addText('“', { x: 0.8, y: 1.25, w: 0.3, h: 0.5, margin: 0, fontFace: 'Georgia', fontSize: 28, bold: true, color: G, valign: 'middle', isTextBox: true });
  s.addText('Example: ‘Best board games for a family?’', { x: 1.15, y: 1.18, w: 7.5, h: 0.5, margin: 0, valign: 'middle', fontSize: 13.5, color: WHITE, isTextBox: true });

  const steps = [
    ['Highest commercial gap', 'Family games', Lu.LuChartNoAxesColumn],
    ['Message', 'Easy, inclusive family fun', Lu.LuMessageSquare],
    ['Source types', 'Publishers, retailers, Youtube', Lu.LuGlobe],
    ['Content types', 'Reviews, best games, top 10 games for…', Lu.LuFileText],
    ['Action', 'PR, retailer product page updates, Youtube influencer outreach', Lu.LuRocket],
  ];
  const w = 1.64, gap = 0.15, x0 = 0.6, trackY = 2.3, d = 0.64, cardY = 2.82, cardH = 2.08;
  const cx = (i) => x0 + i * (w + gap) + w / 2;
  // drop from the prompt into the first step, then the track through all five
  s.addShape(pres.shapes.LINE, { x: cx(0), y: 1.68, w: 0, h: trackY - 1.68, line: { color: G, width: 1.25, transparency: 30 } });
  s.addShape(pres.shapes.LINE, { x: cx(0), y: trackY, w: cx(4) - cx(0), h: 0, line: { color: G, width: 1.25, transparency: 30 } });
  for (let i = 0; i < 5; i++) {
    const [label, value, Ic] = steps[i], hi = i === 4, x = x0 + i * (w + gap);
    if (i < 4) {
      const mx = (cx(i) + cx(i + 1)) / 2;
      s.addShape(pres.shapes.OVAL, { x: mx - 0.12, y: trackY - 0.12, w: 0.24, h: 0.24, fill: { color: DEEP }, line: { color: DEEP } });
      s.addImage({ data: await icon(Lu.LuChevronRight), x: mx - 0.11, y: trackY - 0.11, w: 0.22, h: 0.22 });
    }
    // node
    s.addShape(pres.shapes.OVAL, { x: cx(i) - d / 2, y: trackY - d / 2, w: d, h: d, fill: { color: hi ? G : HI_FILL }, line: { color: G, width: hi ? 0 : 1.25 } });
    const p = d * 0.27;
    s.addImage({ data: await icon(Ic, hi ? '#081514' : '#00EB5B'), x: cx(i) - d / 2 + p, y: trackY - d / 2 + p, w: d - 2 * p, h: d - 2 * p });
    // stem + card
    s.addShape(pres.shapes.LINE, { x: cx(i), y: trackY + d / 2, w: 0, h: cardY - trackY - d / 2, line: { color: G, width: 1, transparency: hi ? 0 : 50 } });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: cardY, w, h: cardH, rectRadius: 0.08, fill: { color: hi ? HI_FILL : CARD, transparency: 8 }, line: { color: hi ? G : CARD_LINE, width: hi ? 1.25 : 0.75 } });
    s.addText(label, { x: x + 0.16, y: cardY + 0.16, w: w - 0.32, h: 0.5, margin: 0, fontSize: 12, bold: true, color: hi ? G : WHITE, valign: 'top', isTextBox: true });
    s.addShape(pres.shapes.LINE, { x: x + 0.16, y: cardY + 0.74, w: w - 0.32, h: 0, line: { color: hi ? HI_LINE : CARD_LINE, width: 0.75 } });
    s.addText(value, { x: x + 0.16, y: cardY + 0.86, w: w - 0.32, h: cardH - 1.0, margin: 0, fontSize: 11, italic: true, color: hi ? WHITE : BODY, valign: 'top', isTextBox: true });
  }
  await pres.writeFile({ fileName: 'Slide 8 flow - temp.pptx' });
  console.log('ok');
})();
