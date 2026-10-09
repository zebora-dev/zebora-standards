// Generates the Zebora deck brand kit into ./bg and ./assets of the current working directory:
//   bg/hero.jpg, closing.jpg   signal-wave field (title / closing slides)
//   bg/dark.jpg, darkAlt.jpg   gridded Deep Field canvas (content slides; alternate them)
//   bg/light.jpg               slate-white gridded canvas (the website's light sections)
//   bg/orbit.jpg               dark canvas with a right-hand ring panel
//   assets/logo-white.png, logo-dark.png, google.png, openai.png
// Usage: node <skill>/scripts/brand_assets.js   (run from the deck's working folder)
const sharp = require('sharp');
const fs = require('fs');
const path = require('path');

const SKILL_ASSETS = path.join(__dirname, '..', 'assets');
const W = 1920, H = 1080, DEEP = '#081514', GREEN = '#00EB5B', TEAL = '#008A5C';

function grid(color, op, step = 64) {
  let s = `<g stroke="${color}" stroke-opacity="${op}" stroke-width="1">`;
  for (let x = 0; x <= W; x += step) s += `<line x1="${x}" y1="0" x2="${x}" y2="${H}"/>`;
  for (let y = 0; y <= H; y += step) s += `<line x1="0" y1="${y}" x2="${W}" y2="${y}"/>`;
  return s + '</g>';
}
// Ribbon of flowing lines, like the zebora.io hero signal field
function waves({ n = 60, cy = 560, amp = 120, spread = 220, op = 0.35, x0 = -100, x1 = W + 100, seed = 1 }) {
  let s = '';
  for (let i = 0; i < n; i++) {
    const t = i / (n - 1), pts = [];
    for (let x = x0; x <= x1; x += 12) {
      const u = (x - x0) / (x1 - x0);
      const env = 0.55 + 0.45 * Math.sin(Math.PI * u * 1.3 + seed);
      const y = cy + (t - 0.5) * spread * env + amp * Math.sin(u * 4.6 + seed + t * 2.4) +
        0.55 * amp * Math.sin(u * 9.5 - t * 3.2 + seed * 2) * env + 0.18 * amp * Math.sin(u * 23 + t * 7);
      pts.push(`${x.toFixed(1)},${y.toFixed(1)}`);
    }
    const o = (op * (0.35 + 0.65 * Math.sin(Math.PI * t))).toFixed(3);
    s += `<polyline points="${pts.join(' ')}" fill="none" stroke="${GREEN}" stroke-opacity="${o}" stroke-width="1.3"/>`;
  }
  return s;
}
const glow = (id, cx, cy, r, color, op) =>
  `<radialGradient id="${id}" cx="${cx}" cy="${cy}" r="${r}" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="${color}" stop-opacity="${op}"/><stop offset="1" stop-color="${color}" stop-opacity="0"/></radialGradient>`;
// Waves fade in from the left so text sits on a clean area
const fadeMask = (id) =>
  `<linearGradient id="${id}" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset="0.45" stop-color="#fff" stop-opacity="0.15"/><stop offset="1" stop-color="#fff" stop-opacity="1"/></linearGradient><mask id="m${id}"><rect width="${W}" height="${H}" fill="url(#${id})"/></mask>`;
const fill = (id) => `<rect width="${W}" height="${H}" fill="${id}"/>`;

const bgs = {
  hero: `<defs>${glow('g1', 1350, 520, 900, GREEN, 0.16)}${glow('g2', 200, 1100, 700, TEAL, 0.18)}${fadeMask('f1')}</defs>${fill(DEEP)}${fill('url(#g1)')}${fill('url(#g2)')}<g opacity="0.5">${grid('#FFFFFF', 0.035)}</g><circle cx="1380" cy="540" r="430" fill="none" stroke="${GREEN}" stroke-opacity="0.10" stroke-width="1.5"/><circle cx="1380" cy="540" r="300" fill="none" stroke="${GREEN}" stroke-opacity="0.06" stroke-width="1.5"/><g mask="url(#mf1)">${waves({ n: 90, cy: 600, amp: 95, spread: 520, op: 0.5, seed: 0.6 })}</g>`,
  closing: `<defs>${glow('g1', 1500, 300, 900, GREEN, 0.14)}${glow('g2', 300, 1000, 800, TEAL, 0.16)}${fadeMask('f1')}</defs>${fill(DEEP)}${fill('url(#g1)')}${fill('url(#g2)')}<g opacity="0.5">${grid('#FFFFFF', 0.035)}</g><g mask="url(#mf1)">${waves({ n: 90, cy: 560, amp: 110, spread: 560, op: 0.45, seed: 2.2 })}</g>`,
  dark: `<defs>${glow('g1', 1750, -80, 900, GREEN, 0.10)}${glow('g2', 0, 1080, 700, TEAL, 0.10)}</defs>${fill(DEEP)}${fill('url(#g1)')}${fill('url(#g2)')}${grid('#FFFFFF', 0.028)}<g opacity="0.45">${waves({ n: 40, cy: 1030, amp: 34, spread: 150, op: 0.28, seed: 1.4 })}</g>`,
  darkAlt: `<defs>${glow('g1', 0, -60, 900, GREEN, 0.09)}${glow('g2', 1920, 1080, 800, TEAL, 0.12)}</defs>${fill(DEEP)}${fill('url(#g1)')}${fill('url(#g2)')}${grid('#FFFFFF', 0.028)}<g opacity="0.45">${waves({ n: 40, cy: 1035, amp: 30, spread: 140, op: 0.28, seed: 3.1 })}</g>`,
  light: `<defs>${glow('g1', 1800, 0, 800, GREEN, 0.10)}${glow('g2', 0, 1080, 700, TEAL, 0.06)}</defs>${fill('#F8FAFC')}${grid('#0F172A', 0.06)}${fill('url(#g1)')}${fill('url(#g2)')}`,
  // Right-hand panel starts at x=1102px (5.74in on a 10in slide); ring centre is (1511, 540) = (7.87in, 2.81in)
  orbit: `<defs>${glow('g1', 1440, 540, 560, GREEN, 0.22)}${glow('g2', 0, 1080, 700, TEAL, 0.10)}</defs>${fill(DEEP)}${fill('url(#g2)')}${grid('#FFFFFF', 0.028)}<rect x="1102" y="0" width="${W - 1102}" height="${H}" fill="#050D0C"/><rect x="1102" y="0" width="${W - 1102}" height="${H}" fill="url(#g1)"/><line x1="1102" y1="0" x2="1102" y2="${H}" stroke="${GREEN}" stroke-opacity="0.18"/>${[150, 260, 390].map((r) => `<circle cx="1511" cy="540" r="${r}" fill="none" stroke="${GREEN}" stroke-opacity="${(0.42 - r / 1400).toFixed(2)}" stroke-width="1.6"/>`).join('')}`,
};

const sized = (svg) => svg.replace('height="1em"', 'height="256"').replace('width="1em"', 'width="256"');

(async () => {
  fs.mkdirSync('bg', { recursive: true });
  fs.mkdirSync('assets', { recursive: true });
  for (const [k, body] of Object.entries(bgs)) {
    await sharp(Buffer.from(`<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">${body}</svg>`)).jpeg({ quality: 90 }).toFile(`bg/${k}.jpg`);
  }
  // Website logo: white wordmark + green mark. The dark variant recolours the wordmark for light slides.
  const logo = fs.readFileSync(path.join(SKILL_ASSETS, 'zebora-logo.svg'), 'utf8');
  await sharp(Buffer.from(logo), { density: 1200 }).png().toFile('assets/logo-white.png');
  await sharp(Buffer.from(logo.replace('fill: #fff', 'fill: #081514')), { density: 1200 }).png().toFile('assets/logo-dark.png');
  await sharp(Buffer.from(sized(fs.readFileSync(path.join(SKILL_ASSETS, 'google.svg'), 'utf8')))).png().toFile('assets/google.png');
  await sharp(Buffer.from(sized(fs.readFileSync(path.join(SKILL_ASSETS, 'openai.svg'), 'utf8')).replace('currentColor', '#0B1A18'))).png().toFile('assets/openai.png');
  console.log('brand kit written to ./bg and ./assets');
})();
