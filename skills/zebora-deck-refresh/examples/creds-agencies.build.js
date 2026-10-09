// REFERENCE ONLY — the first deck built with this process (agencies creds deck, 13 slides, Oct 2026).
// Written before scripts/lib.js existed, so helpers are inline, and it expects images lifted from that
// master deck (img/, assets/) which are not in this repo. Read it for layouts: light slides, case studies,
// logo strip + quote, steps + image, and how hand edits from the live deck were mirrored (slide 11).

// Zebora creds deck for agencies — brand-aligned redesign.
// Copy is taken verbatim from the master deck; only layout, styling and imagery change.
const pptxgen = require('pptxgenjs');
const sharp = require('sharp');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const Lu = require('react-icons/lu');

const G = '00EB5B', TEAL = '008A5C', DEEP = '081514', INK = '050D0C';
const WHITE = 'F8FAFC', BODY = 'C5D1CE', MUTED = '8A9E9A';
const CARD = '0E1E1C', CARD_LINE = '21403A', HI_FILL = '0B2A1C';
const L_TEXT = '0B1A18', L_BODY = '475569', L_LINE = 'E2E8F0';
const HEAD = 'Inter', MONO = 'Roboto Mono';

const pres = new pptxgen();
pres.layout = 'LAYOUT_16x9'; // 10 x 5.625, same canvas as the master
pres.title = 'Zebora creds deck for agencies';
pres.theme = { headFontFace: HEAD, bodyFontFace: HEAD };

async function icon(Comp, color = '#00EB5B', size = 256) {
  const svg = renderToStaticMarkup(React.createElement(Comp, { color, size, strokeWidth: 1.75 }));
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return 'image/png;base64,' + buf.toString('base64');
}

const A = (f) => `assets/${f}`;
const I = (f) => `img/${f}`;

// ---------- shared furniture ----------
function frame(slide, n, { light = false, bg = 'dark' } = {}) {
  slide.background = { path: `bg/${bg}.jpg` };
  slide.addImage({ path: A(light ? 'logo-dark.png' : 'logo-white.png'), x: 8.55, y: 5.1, w: 0.85, h: 0.25, objectName: 'Zebora logo' });
  slide.addText(String(n).padStart(2, '0') + ' / 13', {
    x: 0.6, y: 5.1, w: 1.2, h: 0.25, margin: 0, fontFace: MONO, fontSize: 8, color: light ? '94A3B8' : MUTED, charSpacing: 1, isTextBox: true,
  });
}
function title(slide, runs, { y = 0.42, h = 0.6, size = 24, light = false, w = 8.8 } = {}) {
  const arr = typeof runs === 'string' ? [{ text: runs }] : runs;
  slide.addText(arr.map((r) => ({ text: r.text, options: { bold: true, color: r.color || (light ? L_TEXT : WHITE), breakLine: r.breakLine } })), {
    x: 0.6, y, w, h, margin: 0, fontFace: HEAD, fontSize: size, valign: 'top', isTextBox: true, objectName: 'Title',
  });
}
function card(slide, x, y, w, h, { hi = false, light = false, name = 'Card' } = {}) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x, y, w, h, rectRadius: 0.08, objectName: name,
    fill: { color: light ? 'FFFFFF' : hi ? HI_FILL : CARD, transparency: light ? 0 : 8 },
    line: { color: light ? L_LINE : hi ? G : CARD_LINE, width: hi ? 1.25 : 0.75 },
    shadow: light ? { type: 'outer', color: '0F172A', opacity: 0.08, blur: 10, offset: 2, angle: 90 } : undefined,
  });
}
function eyebrow(slide, text, x, y, w) {
  slide.addText(text, { x, y, w, h: 0.25, margin: 0, fontFace: MONO, fontSize: 9, bold: true, color: G, charSpacing: 1, isTextBox: true });
}
function pill(slide, text, cx, cy, d = 0.42) {
  slide.addShape(pres.shapes.OVAL, { x: cx - d / 2, y: cy - d / 2, w: d, h: d, fill: { color: DEEP }, line: { color: G, width: 1 } });
  slide.addText(text, { x: cx - d / 2, y: cy - d / 2, w: d, h: d, margin: 0, align: 'center', valign: 'middle', fontSize: 15, bold: true, color: G, isTextBox: true });
}
async function iconBadge(slide, Comp, x, y, d, { light = false } = {}) {
  slide.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: light ? 'DCFCE7' : HI_FILL }, line: { color: light ? 'BBF7D0' : '1F5A3A', width: 0.75 } });
  const p = d * 0.26;
  slide.addImage({ data: await icon(Comp, light ? '#008A5C' : '#00EB5B'), x: x + p, y: y + p, w: d - 2 * p, h: d - 2 * p });
}

(async () => {
  // ===== 1. Title =====
  {
    const s = pres.addSlide();
    s.background = { path: 'bg/hero.jpg' };
    s.addImage({ path: A('logo-white.png'), x: 0.75, y: 1.45, w: 3.4, h: 1.0, objectName: 'Zebora logo' });
    s.addText([
      { text: 'Own your Narrative. ', options: { color: WHITE } },
      { text: 'Win in AI.', options: { color: G } },
    ], { x: 0.75, y: 2.75, w: 6.5, h: 0.6, margin: 0, fontSize: 30, bold: true, isTextBox: true });
    s.addText('Helping agencies understand and improve how brands are represented and recommended by AI.', {
      x: 0.75, y: 3.5, w: 5.0, h: 0.75, margin: 0, fontSize: 15, color: BODY, valign: 'top', isTextBox: true,
    });
  }

  // ===== 2. AI is where your clients' customers discover =====
  {
    const s = pres.addSlide(); frame(s, 2, { bg: 'dark' });
    title(s, [
      { text: 'AI is where your clients’ customers ' }, { text: 'discover, ', color: G, breakLine: true },
      { text: 'shortlist & choose', color: G },
    ], { h: 0.9, size: 26 });
    // Prompt bar
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: 1.55, w: 8.8, h: 0.58, rectRadius: 0.29, fill: { color: 'FFFFFF', transparency: 92 }, line: { color: G, width: 1, transparency: 40 }, objectName: 'Prompt bar' });
    s.addImage({ data: await icon(Lu.LuSparkles, '#8A9E9A'), x: 0.82, y: 1.71, w: 0.26, h: 0.26 });
    s.addText([
      { text: 'Compare the top [' }, { text: 'your category', options: { bold: true, color: G } }, { text: '] brands - which should I choose?' },
    ], { x: 1.2, y: 1.55, w: 7.4, h: 0.58, margin: 0, valign: 'middle', fontSize: 14, color: WHITE, isTextBox: true });
    s.addShape(pres.shapes.OVAL, { x: 8.86, y: 1.64, w: 0.4, h: 0.4, fill: { color: G }, line: { color: G } });
    s.addImage({ data: await icon(Lu.LuArrowRight, '#081514'), x: 8.95, y: 1.73, w: 0.22, h: 0.22 });
    // LLM logo card
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: 2.45, w: 2.7, h: 2.4, rectRadius: 0.08, fill: { color: 'FFFFFF' }, line: { color: 'FFFFFF' }, objectName: 'LLM logos' });
    const logos = [['chatgpt', 416, 121], ['gemini', 369, 130], ['perplexity', 458, 110], ['claude', 200, 44]];
    logos.forEach(([f, w, h], i) => {
      const bh = 0.3, bw = Math.min(1.6, (w / h) * bh), hh = bw * (h / w);
      s.addImage({ path: A(f + '.png'), x: 0.6 + (2.7 - bw) / 2, y: 2.62 + i * 0.55 + (0.36 - hh) / 2, w: bw, h: hh });
    });
    s.addText([
      { text: 'LLMs decide ', options: { bold: true, color: WHITE } },
      { text: "who's mentioned, how they're framed and who gets endorsed.", options: { color: WHITE, breakLine: true } },
      { text: 'For agencies, it creates a new opportunity:', options: { bold: true, color: G, fontSize: 14, paraSpaceBefore: 16, breakLine: true } },
      { text: "Help clients understand how they're represented in AI, improve the signals shaping that representation and influence who gets recommended.", options: { color: BODY, fontSize: 14, paraSpaceBefore: 6 } },
    ], { x: 3.75, y: 2.45, w: 5.65, h: 2.4, margin: 0, fontSize: 18, valign: 'top', lineSpacingMultiple: 1.1, isTextBox: true });
  }

  // ===== 3. Enterprise brands don't lose because they're invisible =====
  {
    const s = pres.addSlide(); frame(s, 3, { bg: 'orbit' });
    title(s, [{ text: 'Enterprise brands ', breakLine: true }, { text: 'don’t lose in AI because they’re invisible.' }], { y: 0.5, h: 1.25, size: 24, w: 4.9 });
    s.addText([
      { text: 'They lose because they’re ', options: { color: G } },
      { text: 'misunderstood', options: { color: G, bold: true } },
    ], { x: 0.6, y: 1.85, w: 4.9, h: 0.45, margin: 0, fontSize: 20, isTextBox: true });
    s.addText('Here’s why', { x: 0.6, y: 2.55, w: 4.9, h: 0.3, margin: 0, fontSize: 12, bold: true, color: WHITE, isTextBox: true });
    const why = ['Multiple products and services', 'Diverse customer segments', 'Overlapping and nuanced use cases', 'Fragmented competitors across categories', 'Legacy content designed for humans, not LLMs ', 'Commercial realities that AI doesn’t get'];
    s.addText(why.flatMap((t, i) => [
      { text: '→ ', options: { color: G, bold: true } },
      { text: t, options: { color: BODY, breakLine: i < why.length - 1 } },
    ]), { x: 0.6, y: 2.9, w: 4.9, h: 2.0, margin: 0, fontSize: 12, valign: 'top', paraSpaceAfter: 6, isTextBox: true });
    // Target at the orbit centre
    const cx = 7.87, cy = 2.81;
    s.addShape(pres.shapes.OVAL, { x: cx - 0.5, y: cy - 0.5, w: 1.0, h: 1.0, fill: { color: '0A2A1A' }, line: { color: G, width: 1, transparency: 50 } });
    s.addShape(pres.shapes.OVAL, { x: cx - 0.3, y: cy - 0.3, w: 0.6, h: 0.6, fill: { type: 'none' }, line: { color: G, width: 2.5 } });
    s.addShape(pres.shapes.OVAL, { x: cx - 0.12, y: cy - 0.12, w: 0.24, h: 0.24, fill: { color: G }, line: { color: G } });
    const orbit = [ // [file, w(in), x, y] relative to the master's placement, re-centred
      ['o_chatgpt', 1.6, 7.95, 1.12], ['o_google', 1.35, 6.05, 1.7], ['o_copilot', 0.9, 8.85, 2.3],
      ['o_perplexity', 1.0, 6.2, 3.1], ['o_claude', 0.75, 8.6, 3.5], ['o_gemini', 1.05, 6.95, 4.0],
    ];
    const dims = { o_chatgpt: [1024, 226], o_google: [1015, 230], o_copilot: [1024, 266], o_perplexity: [1024, 244], o_claude: [1024, 221], o_gemini: [1024, 231] };
    orbit.forEach(([f, w, x, y]) => s.addImage({ path: A(f + '.png'), x, y, w, h: w * dims[f][1] / dims[f][0] }));
  }

  // ===== 4. GEO is starting to split into 3 layers =====
  {
    const s = pres.addSlide(); frame(s, 4, { bg: 'darkAlt' });
    title(s, 'GEO is starting to split into 3 layers', { size: 26 });
    const cols = [
      ['01 / MONITORING', 'Tools & monitoring', "What's happening? Visibility, rankings, mentions, citations", 'Profound, Peec, Semrush etc', Lu.LuActivity],
      ['02 / STRATEGY', 'Diagnosis & strategy', 'Why is it happening, what matters and what should we do?', 'Zebora + Your agency', Lu.LuScanSearch],
      ['03 /EXECUTION', 'Execution & action', 'PR, earned media, content, messaging, brand, campaigns', 'Your agency', Lu.LuRocket],
    ];
    for (let i = 0; i < 3; i++) {
      const [eb, t, d, who, Ic] = cols[i];
      const x = 0.6 + i * 3.025, y = 1.3, w = 2.75, h = 2.75, hi = i === 1;
      card(s, x, y, w, h, { hi, name: `Layer ${i + 1}` });
      await iconBadge(s, Ic, x + w - 0.68, y + 0.22, 0.46);
      eyebrow(s, eb, x + 0.25, y + 0.3, 1.9);
      s.addText(t, { x: x + 0.25, y: y + 0.8, w: w - 0.5, h: 0.35, margin: 0, fontSize: 15, bold: true, color: WHITE, isTextBox: true });
      s.addText(d, { x: x + 0.25, y: y + 1.22, w: w - 0.5, h: 0.75, margin: 0, fontSize: 11.5, color: BODY, valign: 'top', isTextBox: true });
      s.addShape(pres.shapes.LINE, { x: x + 0.25, y: y + 2.08, w: w - 0.5, h: 0, line: { color: hi ? '1F6B45' : CARD_LINE, width: 0.75 } });
      s.addText(who, { x: x + 0.25, y: y + 2.2, w: w - 0.5, h: 0.35, margin: 0, fontSize: 12, bold: true, color: hi ? G : WHITE, isTextBox: true });
    }
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: 4.3, w: 8.8, h: 0.55, rectRadius: 0.08, fill: { color: G, transparency: 90 }, line: { color: G, width: 0.75, transparency: 60 } });
    s.addText([
      { text: 'Tools tell you what happened. ' }, { text: 'Zebora', options: { bold: true, color: G } },
      { text: ' tells you why and where to focus. ' }, { text: 'Your agency', options: { bold: true, color: WHITE } },
      { text: ' decides what to do and executes it.' },
    ], { x: 0.85, y: 4.3, w: 8.4, h: 0.55, margin: 0, valign: 'middle', fontSize: 11.5, color: BODY, isTextBox: true });
  }

  // ===== 5. Zebora gives your team the intelligence =====
  {
    const s = pres.addSlide(); frame(s, 5, { bg: 'dark' });
    title(s, 'Zebora gives your team the intelligence to lead GEO strategy', { size: 21, h: 0.75 });
    const cols = [
      ['01 / INPUT', 'Custom setup', 'Build each client’s intelligence model ', ['Bespoke prompt taxonomy (600-800 prompts)', 'Commercial weighting by business priority', 'Custom configured to your client’s products, services & competitors']],
      ['02 / INTELLIGENCE', 'Zebora Platform', 'Diagnose the opportunity', ['Visibility & recommendations', 'Brand perception & competitive gaps', 'Citations & signals', 'Clearly identified PR & content opportunities']],
      ['03 / ACTION', 'Your agency', 'Strategy & execution', ['PR strategies', 'Content strategies', 'Narrative & messaging', 'Source & media targeting', 'Campaign activation', 'Ongoing optimisation']],
    ];
    cols.forEach(([eb, t, sub, items], i) => {
      const x = 0.6 + i * 3.05, y = 1.3, w = 2.7, h = 3.25, hi = i === 1;
      card(s, x, y, w, h, { hi, name: `Step ${i + 1}` });
      eyebrow(s, eb, x + 0.25, y + 0.25, 2.2);
      s.addText(t, { x: x + 0.25, y: y + 0.55, w: w - 0.5, h: 0.35, margin: 0, fontSize: 17, bold: true, color: WHITE, isTextBox: true });
      s.addText(sub, { x: x + 0.25, y: y + 0.92, w: w - 0.5, h: 0.42, margin: 0, fontSize: 11, color: hi ? G : BODY, valign: 'top', isTextBox: true });
      s.addShape(pres.shapes.LINE, { x: x + 0.25, y: y + 1.4, w: w - 0.5, h: 0, line: { color: hi ? '1F6B45' : CARD_LINE, width: 0.75 } });
      s.addText(items.map((it, j) => ({ text: it, options: { bullet: { code: '25B8', indent: 12 }, breakLine: j < items.length - 1 } })), {
        x: x + 0.2, y: y + 1.52, w: w - 0.4, h: 1.7, margin: 0, fontSize: 10.5, color: WHITE, valign: 'top', paraSpaceAfter: 4, isTextBox: true,
      });
    });
    pill(s, '+', 3.475, 2.925); pill(s, '+', 6.525, 2.925);
    s.addText('You retain the client relationship. Zebora supports where needed.', { x: 0.6, y: 4.68, w: 7.5, h: 0.3, margin: 0, fontSize: 12, color: BODY, isTextBox: true });
  }

  // ===== 6. From AI visibility gap to PR action =====
  {
    const s = pres.addSlide(); frame(s, 6, { bg: 'darkAlt' });
    title(s, 'From AI visibility gap to PR action', { size: 24, h: 0.45 });
    s.addText('One example of how the intelligence translates into action', { x: 0.6, y: 0.92, w: 5, h: 0.3, margin: 0, fontSize: 12, color: MUTED, isTextBox: true });
    const steps = [
      ["1. Where you're losing", 'Which commercially important messages and topics competitors are winning'],
      ["2. Why you're losing", 'Which publishers, pages and third-party signals are influencing the AI answer'],
      ['3. Where to act', 'Which publications, messages and content opportunities have the greatest potential impact'],
      ['4. Agency execution', 'Outreach, earned media, messaging, campaigns and content'],
    ];
    steps.forEach(([t, d], i) => {
      const y = 1.35 + i * 0.9, hi = i === 3;
      card(s, 0.6, y, 3.65, 0.78, { hi, name: `Step ${i + 1}` });
      s.addText([
        { text: t, options: { bold: true, color: hi ? G : WHITE, fontSize: 12.5, breakLine: true } },
        { text: d, options: { color: hi ? 'CBD5E1' : '94A3B8', fontSize: 10 } },
      ], { x: 0.8, y, w: 3.3, h: 0.78, margin: 0, valign: 'middle', paraSpaceAfter: 2, isTextBox: true });
    });
    // Composed from focused crops of the three platform screenshots (see compose6.py)
    const pw = 5.05;
    s.addImage({ path: A('slide6.png'), x: 4.4, y: 1.27, w: pw, h: pw * 1843 / 2555, objectName: 'Platform intelligence' });
  }

  // ===== 7. Why Zebora for agencies? (light) =====
  {
    const s = pres.addSlide(); frame(s, 7, { light: true, bg: 'light' });
    title(s, 'Why Zebora for agencies?', { size: 26, light: true });
    const items = [
      ['1. Differentiate your agency', ['Build a distinctive GEO capability, not just another agency offering the same monitoring tool.', 'Use Zebora behind the scenes, collaboratively or white-labelled.'], Lu.LuAward],
      ['2. Deeper, bespoke intelligence ', ['600-800 commercially weighted prompts built around each client’s actual business.', 'Products, audiences, use cases, competitors and priorities.'], Lu.LuLayers],
      ['3. Deeper diagnosis', ['Understand why clients are winning or losing, not simply where they rank.', 'What matters, what’s driving it and where to focus.'], Lu.LuScanSearch],
      ['4. Client-ready strategic intelligence', ['A CMO-friendly platform built for decision-making, not another data dashboard.', 'Clear enough for senior client conversations, with the depth to inform strategy and action.'], Lu.LuPresentation],
    ];
    for (let i = 0; i < 4; i++) {
      const [t, body, Ic] = items[i];
      const x = 0.6 + (i % 2) * 4.5, y = 1.2 + Math.floor(i / 2) * 1.9, w = 4.3, h = 1.75;
      card(s, x, y, w, h, { light: true, name: `Reason ${i + 1}` });
      await iconBadge(s, Ic, x + 0.25, y + 0.25, 0.5, { light: true });
      s.addText([
        { text: t, options: { bold: true, color: L_TEXT, fontSize: 13.5, breakLine: true } },
        { text: body[0], options: { breakLine: true, paraSpaceBefore: 5 } },
        { text: body[1] },
      ], { x: x + 0.95, y: y + 0.22, w: w - 1.17, h: h - 0.35, margin: 0, fontSize: 10, color: L_BODY, valign: 'top', paraSpaceAfter: 3, isTextBox: true });
    }
  }

  // ===== 8. Range Rover case study =====
  {
    const s = pres.addSlide(); frame(s, 8, { bg: 'dark' });
    title(s, 'What this looks like in practice', { size: 26 });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: 1.25, w: 2.45, h: 3.7, rectRadius: 0.08, fill: { color: 'FFFFFF' }, line: { color: CARD_LINE, width: 0.75 } });
    s.addImage({ path: I('s08_rId3.png'), x: 0.68, y: 1.33, w: 2.29, h: 3.54, sizing: { type: 'contain', w: 2.29, h: 3.54 }, objectName: 'Range Rover range' });
    card(s, 3.3, 1.25, 6.1, 3.7, { name: 'Case study' });
    s.addImage({ path: A('rr-white.png'), x: 3.6, y: 1.5, w: 2.6, h: 2.6 * 168 / 3125, objectName: 'Range Rover logo' });
    s.addText('Range Rover case study', { x: 3.6, y: 1.75, w: 5.5, h: 0.4, margin: 0, fontSize: 17, bold: true, color: WHITE, isTextBox: true });
    const blocks = [
      ['Challenge', 'Strong visibility, but inconsistent representation across the Range Rover portfolio.'],
      ['Diagnosis', 'AI frequently recommended Range Rover but struggled to differentiate individual models, customer segments and use cases.'],
      ['Strategic Framework', 'Range-specific messaging, segmentation and use-case ownership.'],
      ['Outcome', 'A shared strategic roadmap enabling Brand, PR, SEO and Product teams to strengthen AI representation across the portfolio.'],
    ];
    blocks.forEach(([l, t], i) => {
      const x = 3.6 + (i % 2) * 2.85, y = 2.35 + Math.floor(i / 2) * 1.25;
      s.addShape(pres.shapes.LINE, { x, y, w: 2.6, h: 0, line: { color: CARD_LINE, width: 0.75 } });
      s.addText([
        { text: l, options: { bold: true, color: G, fontSize: 11.5, breakLine: true } },
        { text: t, options: { color: BODY, fontSize: 10.5 } },
      ], { x, y: y + 0.1, w: 2.6, h: 1.05, margin: 0, valign: 'top', paraSpaceAfter: 3, isTextBox: true });
    });
  }

  // ===== 9. Sykes Cottages & Voltarol =====
  {
    const s = pres.addSlide(); frame(s, 9, { bg: 'darkAlt' });
    title(s, 'And when AI knows your brand, but still recommends someone else.', { size: 22, h: 0.85, w: 8.2 });
    const cs = [
      ['Sykes Cottages', 'sykes-photo.png', [
        ['Challenge: ', 'High visibility, but usually the 3rd or 4th recommendation.'],
        ['Diagnosis: ', 'AI saw Sykes as one of several good options, not the obvious choice.'],
        ['Framework: ', 'Canonical messaging and proof-led differentiation.'],
        ['Outcome: ', 'Improved recommendation performance within three months.']]],
      ['Voltarol', 'voltarol-photo.png', [
        ['Challenge: ', 'Strong awareness, but increasing competition from generic alternatives.'],
        ['Diagnosis: ', 'AI often grouped Voltarol alongside ibuprofen, paracetamol and own-label.'],
        ['Framework: ', 'Differentiation strategy focused on targeted relief and category ownership.'],
        ['Outcome: ', 'Moving from generic alternative to category leader for targeted muscle relief']]],
    ];
    cs.forEach(([name, img, rows], i) => {
      const x = 0.6 + i * 4.5, y = 1.45, w = 4.3, h = 3.5;
      card(s, x, y, w, h, { name });
      s.addImage({ path: A(img), x: x + 0.12, y: y + 0.12, w: w - 0.24, h: 1.25, objectName: name + ' image' });
      s.addText(name, { x: x + 0.25, y: y + 1.5, w: w - 0.5, h: 0.32, margin: 0, fontSize: 15, bold: true, color: G, isTextBox: true });
      s.addText(rows.flatMap(([l, t], j) => [
        { text: l, options: { bold: true, color: WHITE } },
        { text: t, options: { color: BODY, breakLine: j < rows.length - 1 } },
      ]), { x: x + 0.25, y: y + 1.88, w: w - 0.5, h: 1.55, margin: 0, fontSize: 9.5, valign: 'top', paraSpaceAfter: 4, isTextBox: true });
    });
  }

  // ===== 10. How agencies partner with Zebora =====
  {
    const s = pres.addSlide(); frame(s, 10, { bg: 'dark' });
    title(s, 'How agencies partner with Zebora', { size: 26 });
    const cols = [
      [[{ text: 'Zebora intelligence platform ' }], ['Bespoke client setup', 'AI measurement & diagnosis', 'Competitive benchmarking', 'Citation and PR opportunity analysis'], Lu.LuLayoutDashboard],
      [[{ text: 'Your agency ' }], ['Owns the client', 'Builds the strategy', 'Executes PR / content / campaigns', 'Creates an ongoing GEO revenue stream'], Lu.LuBriefcase],
      [[{ text: 'Zebora support' }, { text: ' (optional, as needed)', italic: true, size: 11 }], ['Specialist GEO expertise', 'Strategy support where required', 'Client sessions if wanted', 'Ongoing re-calibration and measurement'], Lu.LuUsers],
    ];
    for (let i = 0; i < 3; i++) {
      const [head, items, Ic] = cols[i];
      const x = 0.6 + i * 3.075, y = 1.25, w = 2.65, h = 3.6, hi = i === 1;
      card(s, x, y, w, h, { hi, name: `Partner ${i + 1}` });
      await iconBadge(s, Ic, x + 0.25, y + 0.25, 0.6);
      s.addText(head.map((r) => ({ text: r.text, options: { italic: !!r.italic, fontSize: r.size || 14, breakLine: false } })), {
        x: x + 0.25, y: y + 1.0, w: w - 0.5, h: 0.6, margin: 0, bold: true, color: G, valign: 'top', isTextBox: true,
      });
      s.addShape(pres.shapes.LINE, { x: x + 0.25, y: y + 1.68, w: w - 0.5, h: 0, line: { color: hi ? '1F6B45' : CARD_LINE, width: 0.75 } });
      s.addText(items.map((t, j) => ({ text: t, options: { breakLine: j < items.length - 1 } })), {
        x: x + 0.25, y: y + 1.8, w: w - 0.5, h: 1.65, margin: 0, fontSize: 11.5, color: WHITE, valign: 'top', paraSpaceAfter: 7, isTextBox: true,
      });
    }
    pill(s, '→', 3.4375, 3.05); pill(s, '+', 6.5125, 3.05);
  }

  // ===== 11. Build GEO into your agency offering =====
  {
    const s = pres.addSlide(); frame(s, 11, { bg: 'darkAlt' });
    title(s, 'Build GEO into your agency offering', { size: 26 });
    // Left: what the agency gets. Right: the white-labelled platform, large.
    s.addText([{ text: 'Everything you need ', options: { softBreakBefore: false } }, { text: 'to take to market', options: { softBreakBefore: true } }], { x: 0.6, y: 1.3, w: 2.238, h: 0.55, margin: 0, fontSize: 14, bold: true, color: WHITE, valign: 'top', isTextBox: true });
    const list = ['Sales narrative (what GEO is, why now)', 'Pitch deck templates', 'Case-study examples', 'Objection handling', 'Pricing guidance (positioning and markup)'];
    s.addText(list.map((t, j) => ({ text: t, options: { bullet: { code: '25B8', indent: 14 }, breakLine: j < list.length - 1 } })), {
      x: 0.6, y: 1.95, w: 3.3, h: 2.15, margin: 0, fontSize: 12, color: BODY, valign: 'top', paraSpaceAfter: 8, isTextBox: true,
    });
    s.addText('Your brand. Your clients. Fully owned by your team.', { x: 0.6, y: 4.2, w: 3.3, h: 0.6, margin: 0, fontSize: 14, bold: true, color: G, valign: 'top', isTextBox: true });
    const cx0 = 4.4, cw = 5.0;
    card(s, cx0, 1.2, cw, 3.75, { name: 'White label' });
    pill(s, '+', 4.15, 3.075);
    // Positions below mirror Grant's hand edits in the live Google Slides deck — keep them when rebuilding
    s.addText('White-label option available ', { x: 4.881, y: 0.9, w: 4.5, h: 0.3, margin: 0, align: 'right', valign: 'middle', fontSize: 10, bold: true, color: WHITE, isTextBox: true });
    // White-labelled platform in a browser window (from the Pimento brochure artwork) with annotations
    s.addImage({ path: A('browser.png'), x: 4.785, y: 1.379, w: 4.283, h: 3.26, objectName: 'White-label platform' });
    const note = (text, x, y, w, { bold = false } = {}) => s.addText(text, { x, y, w, h: 0.22, margin: 0, valign: 'middle', fontFace: MONO, fontSize: 8.5, bold, color: G, isTextBox: true });
    note('Your Logo', 5.328, 1.389, 1.0);
    note('Your Brand Colors', 6.435, 1.389, 1.8);
    note('Invite your clients onto (Your) platform', 5.168, 4.609, 3.9, { bold: true });
    s.addShape(pres.shapes.LINE, { x: 5.221, y: 4.4, w: 0, h: 0.26, line: { color: G, width: 1 } });
  }

  // ===== 12. Trusted by leading brands (light) =====
  {
    const s = pres.addSlide(); frame(s, 12, { light: true, bg: 'light' });
    title(s, 'Trusted by leading brands', { size: 26, light: true });
    card(s, 0.6, 1.2, 8.8, 0.95, { light: true, name: 'Client logos' });
    const L = [['jlr', 239, 211], ['sykes', 327, 71], ['sage', 1280, 720], ['gatsby', 336, 134], ['haleon', 1029, 161]];
    const slotW = 8.8 / 5;
    L.forEach(([f, w, h], i) => {
      const maxW = 1.3, maxH = 0.5; let bw = maxW, bh = bw * h / w; if (bh > maxH) { bh = maxH; bw = bh * w / h; }
      s.addImage({ path: A(f + '.png'), x: 0.6 + i * slotW + (slotW - bw) / 2, y: 1.2 + (0.95 - bh) / 2, w: bw, h: bh });
    });
    s.addText('“', { x: 0.55, y: 2.3, w: 0.7, h: 0.9, margin: 0, fontFace: 'Georgia', fontSize: 80, color: G, isTextBox: true });
    s.addText('‘Zebora helped us understand why LLMs present our brands the way they do and the impact on consumer behaviour. In such a nascent space, working with impartial subject matter experts to build strong foundations is crucial.’', {
      x: 1.3, y: 2.45, w: 7.9, h: 1.05, margin: 0, fontSize: 15, italic: true, color: '1E293B', valign: 'top', lineSpacingMultiple: 1.1, isTextBox: true,
    });
    s.addText([
      { text: '-', options: { color: L_BODY } },
      { text: ' Phil Jackson, Global Digital Marketing Effectiveness Innovation Director, Haleon', options: { bold: true, color: L_TEXT } },
    ], { x: 1.3, y: 3.6, w: 7.9, h: 0.3, margin: 0, fontSize: 11, isTextBox: true });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: 4.25, w: 8.8, h: 0.55, rectRadius: 0.08, fill: { color: 'DCFCE7', transparency: 30 }, line: { color: 'BBF7D0', width: 0.75 } });
    s.addText([
      { text: 'Agency partners include: ', options: { bold: true, color: L_TEXT } },
      { text: 'VCCP, Frank PR, Kindred, MESH Experience', options: { color: L_BODY } },
    ], { x: 0.85, y: 4.25, w: 8.4, h: 0.55, margin: 0, valign: 'middle', fontSize: 12, isTextBox: true });
  }

  // ===== 13. Closing =====
  {
    const s = pres.addSlide();
    s.background = { path: 'bg/closing.jpg' };
    s.addText('Build a differentiated GEO capability for your clients.', { x: 0.75, y: 0.95, w: 7.0, h: 1.1, margin: 0, fontSize: 30, bold: true, color: WHITE, valign: 'top', isTextBox: true });
    s.addText("We'll show you the platform, the intelligence and how agencies are using it with clients.", { x: 0.75, y: 2.2, w: 6.4, h: 0.75, margin: 0, fontSize: 17, color: G, valign: 'top', isTextBox: true });
    s.addText('Book a discovery call to find out more ', { x: 0.75, y: 3.15, w: 6, h: 0.3, margin: 0, fontSize: 14, color: WHITE, isTextBox: true });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.75, y: 3.55, w: 2.1, h: 0.46, rectRadius: 0.23, fill: { color: G }, line: { color: G } });
    s.addText([{ text: 'liam@zebora.io', options: { hyperlink: { url: 'mailto:liam@zebora.io' } } }], { x: 0.75, y: 3.55, w: 2.1, h: 0.46, margin: 0, align: 'center', valign: 'middle', fontSize: 13, bold: true, color: DEEP, isTextBox: true });
    s.addImage({ path: A('logo-white.png'), x: 0.75, y: 4.45, w: 1.5, h: 1.5 * 40.94 / 139.19, objectName: 'Zebora logo' });
    s.addText([
      { text: 'Own your Narrative. ', options: { color: WHITE } }, { text: 'Win in AI.', options: { color: G } },
    ], { x: 2.45, y: 4.45, w: 4.5, h: 0.44, margin: 0, valign: 'middle', fontSize: 14, isTextBox: true });
  }

  await pres.writeFile({ fileName: 'Zebora-creds-agencies-brand.pptx' });
  console.log('written');
})();
