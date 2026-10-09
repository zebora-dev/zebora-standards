// Worked example: "Vitruvian Oct 9th GEO presentation" (10 slides, mostly text in the master).
// Shows the patterns in references/patterns.md built with scripts/lib.js. Copy is verbatim from the master.
// Run from a working folder that has ./bg, ./assets (brand_assets.js) and ./img (deck_tools.py dump --images img).
const path = require('path');
const SKILL = process.env.ZEBORA_DECK_SKILL || path.join(__dirname, '..');
const { create } = require(path.join(SKILL, 'scripts', 'lib.js'));

const z = create({ title: 'Vitruvian Oct 9th GEO presentation', total: 10 });
const { pres, T, Lu, A, icon, frame, title, card, badge, arrowPill } = z;
const { G, DEEP, WHITE, BODY, MUTED, CARD, CARD_LINE, HI_FILL, HI_LINE, MONO } = T;
const I = (f) => `img/${f}`;   // images lifted from the master deck

(async () => {
  // ===== 1. Title =====
  {
    const s = pres.addSlide(); s.background = { path: 'bg/hero.jpg' };
    s.addImage({ path: A('logo-white.png'), x: 0.75, y: 0.6, w: 1.5, h: 1.5 * 40.94 / 139.19, objectName: 'Zebora logo' });
    s.addText([
      { text: 'Zebora + Vitruvian', options: { color: WHITE, breakLine: true } },
      { text: 'GEO: The current state of play', options: { color: G } },
    ], { x: 0.75, y: 1.85, w: 7.5, h: 1.4, margin: 0, fontSize: 34, bold: true, valign: 'top', isTextBox: true });
    s.addText('Prepared by Zebora | 09 October 2026', { x: 0.75, y: 3.55, w: 6, h: 0.3, margin: 0, fontFace: MONO, fontSize: 11, color: BODY, charSpacing: 1, isTextBox: true });
  }

  // ===== 2. GEO is splitting into 3 layers =====
  {
    const s = pres.addSlide(); frame(s, 2, 'darkAlt');
    title(s, 'GEO is splitting into 3 layers');
    const cols = [
      ['1. Monitoring & measurement', [{ text: 'Where do we appear? What is our visibility? Sentiment? Who is beating us?' }], Lu.LuActivity],
      ['2. Diagnosis & strategy', [{ text: 'Why', hi: true }, { text: ' are we winning or losing? Which gaps actually matter? What is causing them? ' }, { text: 'What should we do?', hi: true }], Lu.LuScanSearch],
      ['3. Execution', [{ text: 'PR, brand, content, SEO, web, product and commerce?' }], Lu.LuRocket],
    ];
    for (let i = 0; i < 3; i++) {
      const [t, body, Ic] = cols[i]; const x = 0.6 + i * 3.025, y = 1.35, w = 2.75, h = 3.2, hi = i === 1;
      card(s, x, y, w, h, { hi, name: `Layer ${i + 1}` });
      await badge(s, Ic, x + 0.25, y + 0.28, 0.6);
      s.addText(t, { x: x + 0.25, y: y + 1.1, w: w - 0.5, h: 0.65, margin: 0, fontSize: 16, bold: true, color: hi ? G : WHITE, valign: 'top', isTextBox: true });
      s.addShape(pres.shapes.LINE, { x: x + 0.25, y: y + 1.82, w: w - 0.5, h: 0, line: { color: hi ? HI_LINE : CARD_LINE, width: 0.75 } });
      s.addText(body.map((r) => ({ text: r.text, options: { bold: !!r.hi, color: r.hi ? G : BODY } })), { x: x + 0.25, y: y + 1.95, w: w - 0.5, h: 1.1, margin: 0, fontSize: 12, valign: 'top', isTextBox: true });
    }
  }

  // ===== 3. Second phase =====
  {
    const s = pres.addSlide(); frame(s, 3, 'dark');
    title(s, 'And so we’re starting to see the GEO move into its second phase', { h: 0.9, size: 24 });
    card(s, 0.6, 1.55, 4.9, 3.2, { name: 'First phase' });
    s.addText([{ text: 'The first phase was about ', options: { color: BODY } }, { text: 'measuring visibility', options: { bold: true, color: WHITE } }],
      { x: 0.85, y: 1.72, w: 4.4, h: 0.35, margin: 0, fontSize: 15, valign: 'top', isTextBox: true });
    // Platform overview tilted as on /what-we-do/platform, with two cards lifted off the plane (see tilt3.py)
    s.addImage({ path: A('slide3_tilt.png'), x: 0.68, y: 2.2, w: 4.74, h: 2.37, objectName: 'Platform overview' });
    await arrowPill(s, 5.75, 3.15);
    card(s, 6.0, 1.55, 3.4, 3.2, { hi: true, name: 'Next phase' });
    await badge(s, Lu.LuLightbulb, 6.25, 1.8, 0.6);
    s.addText([{ text: 'The next phase is about ', options: { color: BODY } }, { text: 'understanding why brands win or lose, and what to do about it.', options: { bold: true, color: G } }],
      { x: 6.25, y: 2.65, w: 2.9, h: 1.95, margin: 0, fontSize: 16, valign: 'top', isTextBox: true });
  }

  // ===== 4. Measurement is harder than it looks =====
  {
    const s = pres.addSlide(); frame(s, 4, 'darkAlt');
    title(s, 'Measurement is harder than it looks');
    s.addText('LLM measurement is fundamentally a measurement-design problem.', { x: 0.6, y: 1.15, w: 8.8, h: 0.35, margin: 0, fontSize: 16, bold: true, color: G, isTextBox: true });
    s.addText([
      { text: 'There are almost unlimited ways in which someone prompts an LLM', options: { color: BODY, breakLine: true } },
      { text: 'You can’t measure every interaction', options: { bold: true, color: WHITE, paraSpaceBefore: 4 } },
    ], { x: 0.6, y: 1.58, w: 8.8, h: 0.6, margin: 0, fontSize: 12.5, valign: 'top', isTextBox: true });
    card(s, 0.6, 2.35, 3.9, 1.35, { quiet: true, name: 'Less' });
    s.addText('Therefore its less:', { x: 0.85, y: 2.48, w: 3.4, h: 0.25, margin: 0, fontFace: MONO, fontSize: 9, color: MUTED, charSpacing: 1, isTextBox: true });
    s.addText('“Do we appear for this prompt?”', { x: 0.85, y: 2.8, w: 3.4, h: 0.75, margin: 0, fontSize: 14, color: BODY, valign: 'top', isTextBox: true });
    await arrowPill(s, 4.8, 3.03);
    card(s, 5.1, 2.35, 4.3, 1.35, { hi: true, name: 'More' });
    s.addText('And more:', { x: 5.35, y: 2.48, w: 3.8, h: 0.25, margin: 0, fontFace: MONO, fontSize: 9, bold: true, color: G, charSpacing: 1, isTextBox: true });
    s.addText('Does AI sufficiently understand my brand to recommend us in the situations that matter?', { x: 5.35, y: 2.8, w: 3.8, h: 0.8, margin: 0, fontSize: 14, bold: true, color: WHITE, valign: 'top', isTextBox: true });
    s.addText('This needs a structured approach that starts with the business:', { x: 0.6, y: 3.92, w: 8.8, h: 0.28, margin: 0, fontSize: 12, color: BODY, isTextBox: true });
    const steps = ['Business', 'Customer situations', 'Taxonomy', 'Prompts', 'Measurement'];
    const ws = [1.25, 2.1, 1.3, 1.2, 1.55], gap = 0.35; let x = 0.6;
    steps.forEach((t, i) => {
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 4.3, w: ws[i], h: 0.46, rectRadius: 0.08, fill: { color: i === 4 ? HI_FILL : CARD }, line: { color: i === 4 ? G : CARD_LINE, width: i === 4 ? 1.25 : 0.75 } });
      s.addText(t, { x, y: 4.3, w: ws[i], h: 0.46, margin: 0, align: 'center', valign: 'middle', fontSize: 12, bold: true, color: i === 4 ? G : WHITE, isTextBox: true });
      x += ws[i];
      if (i < 4) { s.addText('→', { x, y: 4.3, w: gap, h: 0.46, margin: 0, align: 'center', valign: 'middle', fontSize: 13, bold: true, color: G, isTextBox: true }); x += gap; }
    });
    s.addNotes('+ different histories, contexts and responses (and different LLMs and models)');
  }

  // ===== 5. Ecosystem of signals =====
  {
    const s = pres.addSlide(); frame(s, 5, 'dark');
    title(s, "AI doesn't form its view of your brand from your website alone", { h: 0.9, size: 24 });
    const cx = 5.0, cy = 3.02, rx = 3.3, ry = 1.25;
    const nodes = ['Publishers & editorial', 'Communities & social', 'OTHER!', 'Reference & expert sources', 'Retailers & marketplaces', 'Reviews & comparison sites', 'Your website'];
    const angs = [-90, -30, 15, 60, 120, 165, 210];
    const pts = angs.map((a) => [cx + rx * Math.cos(a * Math.PI / 180), cy + ry * Math.sin(a * Math.PI / 180)]);
    s.addShape(pres.shapes.OVAL, { x: cx - rx, y: cy - ry, w: rx * 2, h: ry * 2, fill: { type: 'none' }, line: { color: G, width: 0.75, transparency: 70, dashType: 'dash' } });
    pts.forEach(([px, py]) => s.addShape(pres.shapes.LINE, { x: Math.min(cx, px), y: Math.min(cy, py), w: Math.abs(px - cx), h: Math.abs(py - cy), flipH: (px < cx) !== (py < cy), line: { color: G, width: 0.75, transparency: 55 } }));
    s.addShape(pres.shapes.OVAL, { x: cx - 0.95, y: cy - 0.95, w: 1.9, h: 1.9, fill: { color: HI_FILL }, line: { color: G, width: 1.5 } });
    s.addText('What does AI believe about my brand?', { x: cx - 0.8, y: cy - 0.7, w: 1.6, h: 1.4, margin: 0, align: 'center', valign: 'middle', fontSize: 13, bold: true, color: WHITE, isTextBox: true });
    nodes.forEach((t, i) => {
      const w = 1.75, h = 0.55, [px, py] = pts[i], other = t === 'OTHER!';
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: px - w / 2, y: py - h / 2, w, h, rectRadius: 0.27, fill: { color: other ? DEEP : CARD }, line: { color: other ? MUTED : G, width: 0.75, transparency: other ? 0 : 40, dashType: other ? 'dash' : 'solid' } });
      s.addText(t, { x: px - w / 2, y: py - h / 2, w, h, margin: 0, align: 'center', valign: 'middle', fontSize: 10.5, bold: true, color: other ? MUTED : WHITE, isTextBox: true });
    });
    s.addText([{ text: 'There is an ', options: { color: BODY } }, { text: 'ecosystem', options: { color: G, bold: true } }, { text: ' of signals to manage', options: { color: BODY } }],
      { x: 0.6, y: 4.68, w: 6, h: 0.3, margin: 0, fontSize: 14, isTextBox: true });
  }

  // ===== 6. Three buckets =====
  {
    const s = pres.addSlide(); frame(s, 6, 'darkAlt');
    title(s, '3rd party influence splits into 3 key buckets');
    const cols = [
      [['Editorial'], 'PR, content & outreach', ['Media', 'Reviews', 'Listicles', 'Buying guides', 'Expert content'], Lu.LuNewspaper],
      [['Non editorial, ', 'can influence'], 'Bespoke action', ['Retailer product pages', 'Directories', 'Company desc (e.g Trustpilot)', 'Partner websites', 'Forums/communities', 'Reddit(?)', 'Youtube(?)', 'Facebook posts(?)', 'Wikipedia (?)'], Lu.LuWrench],
      [['Non editorial, ', 'can’t influence'], 'Can’t be influenced', ['Govt websites', 'Competitor websites', 'Regulators', 'Academic', 'Retailer listings'], Lu.LuLock],
    ];
    for (let i = 0; i < 3; i++) {
      const [head, sub, items, Ic] = cols[i]; const x = 0.6 + i * 3.025, y = 1.2, w = 2.75, h = 3.75, quiet = i === 2;
      card(s, x, y, w, h, { quiet, name: `Bucket ${i + 1}` });
      await badge(s, Ic, x + w - 0.72, y + 0.2, 0.5);
      s.addText(head.map((t, j) => ({ text: t, options: { breakLine: j < head.length - 1 } })), { x: x + 0.25, y: y + 0.2, w: w - 1.05, h: 0.55, margin: 0, fontSize: 14.5, bold: true, color: quiet ? BODY : WHITE, valign: 'middle', isTextBox: true });
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x + 0.25, y: y + 0.9, w: w - 0.5, h: 0.32, rectRadius: 0.16, fill: { color: quiet ? CARD : G, transparency: quiet ? 0 : 88 }, line: { color: quiet ? MUTED : G, width: 0.75, transparency: quiet ? 40 : 50 } });
      s.addText(sub, { x: x + 0.25, y: y + 0.9, w: w - 0.5, h: 0.32, margin: 0, align: 'center', valign: 'middle', fontSize: 10.5, italic: true, bold: true, color: quiet ? MUTED : G, isTextBox: true });
      s.addText(items.map((t, j) => ({ text: t, options: { breakLine: j < items.length - 1 } })), { x: x + 0.25, y: y + 1.38, w: w - 0.5, h: 2.25, margin: 0, fontSize: 11, color: quiet ? MUTED : BODY, valign: 'top', paraSpaceAfter: 2.5, isTextBox: true });
    }
  }

  // ===== 7. There isn't one GEO playbook =====
  {
    const s = pres.addSlide(); frame(s, 7, 'dark');
    title(s, 'There isn’t one GEO playbook');
    s.addText([{ text: 'Different AI platforms favour ' }, { text: 'different', options: { color: G, bold: true } }, { text: ' sources' }], { x: 0.6, y: 1.12, w: 8.8, h: 0.35, margin: 0, fontSize: 15, color: BODY, isTextBox: true });
    const cols = [
      ['Google AI overviews:', ['Reddit', 'Youtube', 'Facebook'], 'google.png'],
      ['ChatGPT:', ['Reviews & listicles', 'Retailer web pages and sources'], 'openai.png'],
    ];
    cols.forEach(([head, items, logo], i) => {
      const x = 0.6 + i * 4.5, y = 1.7, w = 4.3, h = 2.35;
      card(s, x, y, w, h, { name: head });
      s.addShape(pres.shapes.OVAL, { x: x + 0.25, y: y + 0.2, w: 0.46, h: 0.46, fill: { color: 'FFFFFF' }, line: { color: 'FFFFFF' } });
      s.addImage({ path: A(logo), x: x + 0.36, y: y + 0.31, w: 0.24, h: 0.24 });
      s.addText(head, { x: x + 0.85, y: y + 0.2, w: w - 1.1, h: 0.46, margin: 0, fontSize: 15, bold: true, color: WHITE, valign: 'middle', isTextBox: true });
      s.addShape(pres.shapes.LINE, { x: x + 0.25, y: y + 0.82, w: w - 0.5, h: 0, line: { color: CARD_LINE, width: 0.75 } });
      s.addText(items.map((t, j) => ({ text: t, options: { bullet: { code: '25B8', indent: 14 }, breakLine: j < items.length - 1 } })), { x: x + 0.25, y: y + 0.98, w: w - 0.5, h: 1.25, margin: 0, fontSize: 13, color: BODY, valign: 'top', paraSpaceAfter: 7, isTextBox: true });
    });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: 4.27, w: 8.8, h: 0.55, rectRadius: 0.08, fill: { color: G, transparency: 90 }, line: { color: G, width: 0.75, transparency: 60 } });
    s.addText('But there is a much bigger variance by sector and category', { x: 0.85, y: 4.27, w: 8.3, h: 0.55, margin: 0, valign: 'middle', fontSize: 13, bold: true, color: WHITE, isTextBox: true });
  }

  // ===== 8. Turning gaps into action =====
  {
    const s = pres.addSlide(); frame(s, 8, 'darkAlt');
    title(s, 'The real task is turning gaps into action');
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: 1.2, w: 8.8, h: 0.5, rectRadius: 0.25, fill: { color: 'FFFFFF', transparency: 92 }, line: { color: G, width: 1, transparency: 40 } });
    s.addText('“', { x: 0.8, y: 1.27, w: 0.3, h: 0.5, margin: 0, fontFace: 'Georgia', fontSize: 28, bold: true, color: G, valign: 'middle', isTextBox: true });
    s.addText('Example: ‘Best board games for a family?’', { x: 1.15, y: 1.2, w: 7.5, h: 0.5, margin: 0, valign: 'middle', fontSize: 13.5, color: WHITE, isTextBox: true });
    const rows = [
      ['Highest commercial gap', 'Family games'], ['Message', 'Easy, inclusive family fun'], ['Source types', 'Publishers, retailers, Youtube'],
      ['Content types', 'Reviews, best games, top 10 games for…'], ['Action', 'PR, retailer product page updates, Youtube influencer outreach'],
    ];
    rows.forEach(([l, v], i) => {
      const y = 1.92 + i * 0.62, hi = i === 4;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y, w: 2.6, h: 0.42, rectRadius: 0.08, fill: { color: hi ? HI_FILL : CARD }, line: { color: hi ? G : CARD_LINE, width: hi ? 1.25 : 0.75 } });
      s.addText(l, { x: 0.8, y, w: 2.3, h: 0.42, margin: 0, valign: 'middle', fontSize: 12, bold: true, color: hi ? G : WHITE, isTextBox: true });
      s.addShape(pres.shapes.LINE, { x: 3.2, y: y + 0.21, w: 0.4, h: 0, line: { color: hi ? G : CARD_LINE, width: 0.75 } });
      s.addText(v, { x: 3.75, y, w: 5.65, h: 0.42, margin: 0, valign: 'middle', fontSize: 12.5, italic: true, color: hi ? WHITE : BODY, isTextBox: true });
      if (i < 4) s.addText(' ↓', { x: 0.75, y: y + 0.42, w: 0.4, h: 0.2, margin: 0, valign: 'middle', fontSize: 10, bold: true, color: G, isTextBox: true });
    });
  }

  // ===== 9. Where this is all heading =====
  {
    const s = pres.addSlide(); frame(s, 9, 'dark');
    title(s, 'Where this is all heading');
    const items = [
      ['AI is becoming a major influence on purchase decisions', [{ text: 'LLMs are moving from information tools to recommendation engines. Being understood and recommended by AI will increasingly affect consideration and purchase.' }], Lu.LuShoppingCart],
      ['GEO is not an SEO problem', [{ text: 'It is an ecosystem and company alignment problem. AI is influenced by signals across PR, brand, content, product, ecommerce, reviews, retailers, communities and the website itself.' }], Lu.LuNetwork],
      ['Monitoring will become a given →Diagnosis and action are where the advantage lies.', [{ text: 'Most companies will soon know their visibility score. The harder and more valuable questions are ' }, { text: 'why', b: true }, { text: ' they are winning or losing, which signals are responsible and what to change.' }], Lu.LuTarget],
    ];
    for (let i = 0; i < 3; i++) {
      const [t, body, Ic] = items[i]; const x = 0.6 + i * 3.025, y = 1.25, w = 2.75, h = 3.6, hi = i === 2;
      card(s, x, y, w, h, { hi, name: `Point ${i + 1}` });
      await badge(s, Ic, x + 0.25, y + 0.25, 0.55);
      s.addText(t, { x: x + 0.25, y: y + 0.95, w: w - 0.5, h: 1.15, margin: 0, fontSize: 13.5, bold: true, color: hi ? G : WHITE, valign: 'top', isTextBox: true });
      s.addShape(pres.shapes.LINE, { x: x + 0.25, y: y + 2.15, w: w - 0.5, h: 0, line: { color: hi ? HI_LINE : CARD_LINE, width: 0.75 } });
      s.addText(body.map((r) => ({ text: r.text, options: { bold: !!r.b, color: r.b ? WHITE : BODY } })), { x: x + 0.25, y: y + 2.27, w: w - 0.5, h: 1.25, margin: 0, fontSize: 10, valign: 'top', isTextBox: true });
    }
  }

  // ===== 10. Closing =====
  {
    const s = pres.addSlide(); s.background = { path: 'bg/closing.jpg' };
    s.addImage({ path: A('logo-white.png'), x: 0.75, y: 1.75, w: 3.4, h: 1.0, objectName: 'Zebora logo' });
    s.addText([{ text: 'Own your Narrative. ', options: { color: WHITE } }, { text: 'Win in AI.', options: { color: G } }], { x: 0.75, y: 3.05, w: 6.5, h: 0.6, margin: 0, fontSize: 30, bold: true, isTextBox: true });
  }

  await pres.writeFile({ fileName: 'Vitruvian Oct 9th GEO presentation - brand refresh.pptx' });
  console.log('written');
})();
