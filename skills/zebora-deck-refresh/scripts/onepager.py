#!/usr/bin/env python3
"""Branded one-page documents (A4) from a content JSON. Three outputs from the same content:

  pdf   <content.json> <out.pdf>            dark, full-bleed designed PDF (HTML rendered by headless Chrome)
  docx  <content.json> <out.docx> [--dark]  simple editable version; upload to Drive, then
                                            File > Save as Google Docs to get a native Google Doc
  check <content.json> <file.pdf>           word-for-word copy check of any rendered output

Run from a working folder that has ./bg and ./assets (scripts/brand_assets.js).
Content schema: see examples/onepager.content.json. Copy goes in verbatim; nothing is rewritten.

Needs: python-docx, PyMuPDF, Pillow; Google Chrome for `pdf`.
"""
import argparse, html, json, os, re, subprocess, sys
from collections import Counter

CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
E = html.escape

# ------------------------------------------------------------------ PDF (designed)
CSS = """
@page { size: A4; margin: 0; }
:root { --green:#00EB5B; --deep:#081514; --line:#21403A; --hi:#0B2A1C; --white:#F8FAFC; --body:#C5D1CE; }
* { box-sizing:border-box; margin:0; padding:0; }
html, body { width:210mm; height:297mm; }
body { font-family:Inter,Arial,sans-serif; color:var(--body); background:var(--deep); -webkit-print-color-adjust:exact; print-color-adjust:exact; }
.page { position:relative; width:210mm; height:297mm; overflow:hidden; isolation:isolate; background:var(--deep) url(bg/dark.jpg) center/cover no-repeat; }
.mono { font-family:'Roboto Mono',monospace; letter-spacing:.14em; text-transform:uppercase; }
header { position:relative; padding:11mm 14mm 9mm; }
header::before { content:""; position:absolute; inset:0 0 -14mm 0; z-index:-1; background:url(bg/hero.jpg) 70% 40%/cover no-repeat;
  -webkit-mask-image:linear-gradient(to bottom,#000 62%,transparent); mask-image:linear-gradient(to bottom,#000 62%,transparent); }
header > * { position:relative; }
.logo { height:7.5mm; display:block; }
.meta { display:inline-block; margin-top:8mm; padding:1.6mm 3.4mm; border:.3mm solid rgba(0,235,91,.55); border-radius:99px;
  font-size:6.6pt; font-weight:500; color:var(--green); background:rgba(0,235,91,.07); }
h1 { margin-top:5mm; font-size:26pt; line-height:1.06; font-weight:700; color:var(--white); letter-spacing:-.025em; }
.sub { margin-top:3.5mm; font-size:12pt; font-weight:600; color:var(--green); }
main { position:relative; z-index:1; padding:0 14mm; }
h2 { font-size:7.6pt; font-weight:700; color:var(--green); margin-bottom:3mm; }
p { font-size:8.4pt; line-height:1.45; } p + p { margin-top:1.8mm; }
section { margin-top:5.5mm; }
.opp { display:grid; grid-template-columns:1fr 63mm; gap:7mm; align-items:start; }
.question { border:.35mm solid var(--green); background:var(--hi); border-radius:3mm; padding:4.5mm 5mm; font-size:9.6pt; line-height:1.42;
  font-weight:600; color:var(--white); position:relative; }
.question::before { content:"\\201C"; position:absolute; top:-4.5mm; left:4mm; font:700 30pt Georgia,serif; color:var(--green); }
.grid { display:grid; grid-template-columns:1fr 1fr; gap:3.2mm; }
.card { background:rgba(14,30,28,.92); border:.25mm solid var(--line); border-radius:3mm; padding:3.6mm 4.4mm; }
.card.hi { border-color:var(--green); background:var(--hi); }
.num { font-size:7pt; font-weight:700; color:var(--green); }
.card h3 { margin-top:1.6mm; font-size:10pt; line-height:1.25; font-weight:700; color:var(--white); }
.card p { margin-top:1.8mm; font-size:7.9pt; line-height:1.45; }
ul { list-style:none; margin-top:1.8mm; } li { position:relative; padding-left:4mm; font-size:7.9pt; line-height:1.42; } li + li { margin-top:1.2mm; }
.card li::before { content:"\\25B8"; position:absolute; left:0; color:var(--green); font-size:7pt; top:.2mm; }
.take { background:rgba(14,30,28,.92); border:.25mm solid var(--line); border-radius:3mm; padding:4.5mm 5mm; display:grid; grid-template-columns:38mm 1fr; gap:5mm; }
.take .lead { font-size:10pt; font-weight:700; color:var(--white); line-height:1.3; }
.take ul { margin:0; display:grid; grid-template-columns:1fr 1fr; gap:2.4mm 6mm; } .take li { padding-left:6mm; font-size:8pt; } .take li + li { margin-top:0; }
.take li::before { content:""; position:absolute; left:0; top:.5mm; width:3.6mm; height:3.6mm; border-radius:50%;
  background:var(--green) url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23081514' stroke-width='3.5' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M5 12l5 5L20 7'/%3E%3C/svg%3E") center/2.4mm no-repeat; }
footer { position:absolute; left:0; right:0; bottom:0; padding:0 14mm 9mm; }
footer h2 { border-top:.3mm solid rgba(255,255,255,.14); padding-top:4.5mm; }
.about { display:grid; grid-template-columns:1fr 34mm; gap:8mm; align-items:end; } .about p { font-size:7.9pt; } .about img { height:6mm; justify-self:end; }
"""


def build_html(c):
    i, g, t, a = c['intro'], c['grid'], c['takeaways'], c['about']
    cards = []
    for k, it in enumerate(g['items']):
        hi = ' hi' if it.get('highlight') else ''
        body = ''.join(f'<p>{E(x)}</p>' for x in it.get('body', []))
        bul = ('<ul>' + ''.join(f'<li>{E(x)}</li>' for x in it['bullets']) + '</ul>') if it.get('bullets') else ''
        cards.append(f'<div class="card{hi}"><div class="num mono">{E(it["num"])}</div><h3>{E(it["title"])}</h3>{body}{bul}</div>')
    return f"""<!doctype html><html lang="en-GB"><head><meta charset="utf-8"><title>{E(c['title'])}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Roboto+Mono:wght@500;700&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body><div class="page">
<header><img class="logo" src="assets/logo-white.png" alt="Zebora"><div class="meta mono">{E(c['meta'])}</div>
<h1 style="white-space:{'nowrap' if len(c['title']) <= 40 else 'normal'}">{E(c['title'])}</h1><div class="sub">{E(c['subtitle'])}</div></header>
<main><section style="margin-top:0"><h2 class="mono">{E(i['label'])}</h2><div class="opp"><div>{''.join(f'<p>{E(x)}</p>' for x in i['paras'])}</div>
<div class="question">{E(i['quote'])}</div></div></section>
<section><h2 class="mono">{E(g['label'])}</h2><div class="grid">{''.join(cards)}</div></section>
<section><h2 class="mono">{E(t['label'])}</h2><div class="take"><div class="lead">{E(t['lead'])}</div><ul>{''.join(f'<li>{E(x)}</li>' for x in t['items'])}</ul></div></section></main>
<footer><h2 class="mono">{E(a['label'])}</h2><div class="about"><div>{''.join(f'<p>{E(x)}</p>' for x in a['paras'])}</div>
<img src="assets/logo-white.png" alt="Zebora"></div></footer></div></body></html>"""


def cmd_pdf(a):
    c = json.load(open(a.content))
    with open('_onepager.html', 'w') as f:
        f.write(build_html(c))
    subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--no-pdf-header-footer', '--virtual-time-budget=8000',
                    f'--print-to-pdf={a.out}', 'file://' + os.path.abspath('_onepager.html')], check=True, capture_output=True)
    import fitz
    d = fitz.open(a.out); d[0].get_pixmap(dpi=110).save(a.out.rsplit('.', 1)[0] + '_preview.png')
    print('wrote', a.out, f'({d.page_count} page{"s" if d.page_count > 1 else ""}) — if more than 1, the copy is too long for this layout')


# ------------------------------------------------------------------ DOCX (simple, editable)
def cmd_docx(a):
    from docx import Document
    from docx.shared import Pt, Mm, RGBColor
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    from PIL import Image
    c = json.load(open(a.content))
    hexrgb = lambda h: RGBColor.from_string(h)
    if a.dark:   # website palette: Deep Field page, slate-white headings, Signal Green accents
        INK, BODY, TEAL = hexrgb('F8FAFC'), hexrgb('C5D1CE'), hexrgb('00EB5B')
        TINT, GREY, LINE, ACC, PAGE, LOGO = '0B2A1C', '0E1E1C', '21403A', '00EB5B', '081514', 'assets/logo-white.png'
    else:
        INK, BODY, TEAL = hexrgb('081514'), hexrgb('3F4B48'), hexrgb('008A5C')
        TINT, GREY, LINE, ACC, PAGE, LOGO = 'EEF8F2', 'F5F7F6', 'D5E3DD', '008A5C', None, 'assets/logo-dark.png'
    small = '_logo_small.png'; im = Image.open(LOGO); im.thumbnail((600, 200)); im.save(small)
    F = 'Inter'
    d = Document(); s = d.sections[0]
    s.page_width, s.page_height = Mm(210), Mm(297)
    s.left_margin = s.right_margin = Mm(16); s.top_margin = Mm(13); s.bottom_margin = Mm(12)
    st = d.styles['Normal']; st.font.name = F; st.font.size = Pt(9.5); st.font.color.rgb = BODY
    st.element.rPr.rFonts.set(qn('w:eastAsia'), F); st.paragraph_format.space_after = Pt(4); st.paragraph_format.line_spacing = 1.2
    if PAGE:   # page colour (Docs keeps it: File > Page setup > Page colour)
        bg = OxmlElement('w:background'); bg.set(qn('w:color'), PAGE); d.element.insert(0, bg)
        d.settings.element.insert(0, OxmlElement('w:displayBackgroundShape'))

    def run(p, text, size=9.5, bold=False, italic=False, color=BODY, spacing=None):
        r = p.add_run(text); r.font.size = Pt(size); r.bold = bold; r.italic = italic; r.font.color.rgb = color; r.font.name = F
        if spacing:
            sp = OxmlElement('w:spacing'); sp.set(qn('w:val'), str(spacing)); r._element.get_or_add_rPr().append(sp)
        return r

    def para(text='', after=4, before=0, p=None, **k):
        p = p if p is not None else d.add_paragraph()
        p.paragraph_format.space_after = Pt(after); p.paragraph_format.space_before = Pt(before)
        if text: run(p, text, **k)
        return p

    def shade(cell, fill, border):
        pr = cell._element.get_or_add_tcPr()
        sh = OxmlElement('w:shd'); sh.set(qn('w:val'), 'clear'); sh.set(qn('w:color'), 'auto'); sh.set(qn('w:fill'), fill); pr.append(sh)
        b = OxmlElement('w:tcBorders')
        for side in ('top', 'left', 'bottom', 'right'):
            e = OxmlElement(f'w:{side}'); e.set(qn('w:val'), 'single'); e.set(qn('w:sz'), '8'); e.set(qn('w:color'), border); b.append(e)
        pr.append(b)
        m = OxmlElement('w:tcMar')
        for side, v in (('top', 150), ('bottom', 120), ('left', 200), ('right', 200)):
            e = OxmlElement(f'w:{side}'); e.set(qn('w:w'), str(v)); e.set(qn('w:type'), 'dxa'); m.append(e)
        pr.append(m)

    eyebrow = lambda t: para(t.upper(), size=8, bold=True, color=TEAL, before=12, after=5, spacing=30)
    p = d.add_paragraph(); p.add_run().add_picture(small, width=Mm(30)); p.paragraph_format.space_after = Pt(10)
    para(c['meta'], size=8.5, bold=True, italic=True, color=TEAL, after=5)
    h = d.add_heading(level=1); h.paragraph_format.space_before = Pt(0); h.paragraph_format.space_after = Pt(3)
    run(h, c['title'], size=24, bold=True, color=INK)
    para(c['subtitle'], size=12.5, bold=True, color=TEAL, after=2)

    i = c['intro']; split = i.get('quote_after', len(i['paras']))
    eyebrow(i['label'])
    for k, x in enumerate(i['paras'][:split]): para(x, after=6 if k == split - 1 else 4)
    t = d.add_table(rows=1, cols=1); cell = t.cell(0, 0); shade(cell, TINT, ACC)
    para(i['quote'], size=10.5, bold=True, color=INK, after=0, p=cell.paragraphs[0]); para('', after=2)
    for x in i['paras'][split:]: para(x)

    g = c['grid']; eyebrow(g['label'])
    rows = (len(g['items']) + 1) // 2
    t = d.add_table(rows=rows, cols=2); t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for k, it in enumerate(g['items']):
        cell = t.cell(k // 2, k % 2); hi = it.get('highlight')
        shade(cell, TINT if hi else GREY, ACC if hi else LINE)
        para(it['num'], size=8, bold=True, color=TEAL, after=1, p=cell.paragraphs[0])
        para(it['title'], size=10.5, bold=True, color=INK, after=3, p=cell.add_paragraph())
        for x in it.get('body', []): para(x, size=8.8, after=3, p=cell.add_paragraph())
        for x in it.get('bullets', []):
            q = cell.add_paragraph(); q.paragraph_format.space_after = Pt(2); run(q, '▸  ', size=8.8, bold=True, color=TEAL); run(q, x, size=8.8)

    tk = c['takeaways']; eyebrow(tk['label']); para(tk['lead'], bold=True, color=INK, after=3)
    for x in tk['items']:
        q = d.add_paragraph(); q.paragraph_format.space_after = Pt(2); run(q, '✓  ', bold=True, color=TEAL); run(q, x)
    ab = c['about']; eyebrow(ab['label'])
    for x in ab['paras']: para(x)
    d.save(a.out); os.remove(small)
    print('wrote', a.out, '— upload into the Drive folder, open it, File > Save as Google Docs, then bin the .docx')


# ------------------------------------------------------------------ copy check
def words_of_content(c):
    out = [c['meta'], c['title'], c['subtitle'], c['intro']['label'], *c['intro']['paras'], c['intro']['quote'], c['grid']['label']]
    for it in c['grid']['items']: out += [it['num'], it['title'], *it.get('body', []), *it.get('bullets', [])]
    out += [c['takeaways']['label'], c['takeaways']['lead'], *c['takeaways']['items'], c['about']['label'], *c['about']['paras']]
    return Counter(' '.join(out).replace('’', "'").lower().split())


def cmd_check(a):
    import fitz
    src = words_of_content(json.load(open(a.content)))
    got = Counter(' '.join(p.get_text() for p in fitz.open(a.file)).replace('’', "'").lower().split())
    miss, extra = src - got, got - src
    extra = {k: v for k, v in extra.items() if k not in ('“', '▸', '✓')}
    print('missing', dict(miss)); print('extra', extra)
    print('IDENTICAL' if not miss and not extra else 'DIFF — "missing" must be empty')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    s = ap.add_subparsers(dest='cmd', required=True)
    x = s.add_parser('pdf'); x.add_argument('content'); x.add_argument('out'); x.set_defaults(fn=cmd_pdf)
    x = s.add_parser('docx'); x.add_argument('content'); x.add_argument('out'); x.add_argument('--dark', action='store_true'); x.set_defaults(fn=cmd_docx)
    x = s.add_parser('check'); x.add_argument('content'); x.add_argument('file'); x.set_defaults(fn=cmd_check)
    a = ap.parse_args(); a.fn(a)


if __name__ == '__main__':
    main()
