#!/usr/bin/env python3
"""Image recipes for deck slides. All output transparent PNGs sized for a slot on a 10in-wide slide
(render at ~500px per inch), plus a *_prev.png on the dark canvas for showing the user first.

  tilt     A screenshot laid back at the website's angle, with chosen cards cut out and floating above it.
  collage  Several screenshots (or crops) as browser-style windows, flat or tilted, layered with shadows.
  cutout   Lift a four-cornered region (e.g. a tilted browser window in an ad) out of a larger image.

Examples
  # Dashboard tilted like /what-we-do/platform, two cards lifted and tipped towards the viewer
  image_recipes.py tilt overview.png out.png --card 63,229,478,465 --card 520,551,935,787 \\
      --scale 1.12 --origin 400,215 --card-rx 28

  # Four windows, tilted. Each --win is  file[@x0,y0,x1,y1]:width:x:y   (crop optional; later = on top)
  image_recipes.py collage out.png --size 2555x1843 --tilt \\
      --win table.png:1800:730:20 --win breakdown.png:1330:20:506 \\
      --win detail.png@0,0,1986,732:1380:40:1086 --win detail.png@1011,748,1976,1276:1512:1023:955

  # Cut a tilted browser window out of artwork (corners clockwise from top-left)
  image_recipes.py cutout ad.png out.png --quad 1790,815 3480,685 3535,2005 1782,1970 --radius 30

Needs: Pillow, numpy.
"""
import argparse, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

CANVAS_BG = (14, 30, 28, 255)   # card colour on the dark slides, for previews


def rounded_mask(size, r):
    m = Image.new('L', (size[0] * 3, size[1] * 3), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, m.width - 1, m.height - 1], r * 3, fill=255)
    return m.resize(size, Image.LANCZOS)


def warp(im, quad, size):
    """Projectively map `im` so its corners (TL, TR, BR, BL) land on `quad` inside an image of `size`."""
    w, h = im.size; s = [(0, 0), (w, 0), (w, h), (0, h)]; A = []; B = []
    for (x, y), (u, v) in zip(quad, s):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); B += [u, v]
    c = np.linalg.solve(np.array(A, float), np.array(B, float))
    return im.transform(size, Image.PERSPECTIVE, list(c), Image.BICUBIC)


def drop(canvas, im, x, y, blur=26, alpha=170, dy=16):
    """Composite `im` at (x, y) with a soft shadow underneath."""
    sh = Image.new('RGBA', canvas.size, (0, 0, 0, 0))
    blk = Image.new('RGBA', im.size, (0, 0, 0, 255)); blk.putalpha(im.getchannel('A').point(lambda v: v * alpha // 255))
    sh.alpha_composite(blk, (max(x, 0), max(y + dy, 0)))
    canvas.alpha_composite(sh.filter(ImageFilter.GaussianBlur(blur))); canvas.alpha_composite(im, (x, y))


def window(im, w, bar=True, radius=24, border=(40, 78, 70, 255), bw=3):
    """A screenshot scaled to width `w` in a rounded browser-style frame."""
    im = im.convert('RGB'); im = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
    bh = round(w * 0.024) if bar else 0
    out = Image.new('RGB', (w, im.height + bh), (28, 30, 30)); out.paste(im, (0, bh))
    if bar:
        d = ImageDraw.Draw(out); r = bh * 0.2
        for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
            cx = bh * (0.7 + i * 0.62); d.ellipse([cx - r, bh / 2 - r, cx + r, bh / 2 + r], fill=c)
    out = out.convert('RGBA'); out.putalpha(rounded_mask(out.size, radius))
    ImageDraw.Draw(out).rounded_rectangle([0, 0, out.width - 1, out.height - 1], radius, outline=border, width=bw)
    return out


def save(canvas, out):
    canvas.save(out)
    bg = Image.new('RGBA', canvas.size, CANVAS_BG); bg.alpha_composite(canvas)
    prev = out.rsplit('.', 1)[0] + '_prev.png'
    bg.convert('RGB').resize((canvas.width // 2, canvas.height // 2), Image.LANCZOS).save(prev)
    print('wrote', out, 'and', prev, canvas.size)


# ---------------------------------------------------------------- tilt
def tilt(a):
    """CSS equivalent of the website's tilted platform cards: perspective 1600px; rotateX(50deg) rotateZ(-20deg)."""
    src = Image.open(a.src).convert('RGBA'); SW, SH = src.size
    CW, CH = map(int, a.size.split('x')); OX, OY = map(float, a.origin.split(','))
    RX, RZ, P, S = math.radians(a.rx), math.radians(a.rz), a.perspective, a.scale
    CRX, CRZ = math.radians(a.card_rx), math.radians(a.rz if a.card_rz is None else a.card_rz)
    cards = [tuple(map(int, c.split(','))) for c in a.card]

    def screen(x, y, z):
        k = P / (P - z)
        return (CW / 2 + (x + OX - CW / 2) * k, CH / 2 + (y + OY - CH / 2) * k)

    def plane_xyz(x, y, z=0.0):
        x, y, z = x * S, y * S, z * S
        x, y = x * math.cos(RZ) - y * math.sin(RZ), x * math.sin(RZ) + y * math.cos(RZ)
        return x, y * math.cos(RX) - z * math.sin(RX), y * math.sin(RX) + z * math.cos(RX)

    project = lambda x, y, z=0.0: screen(*plane_xyz(x, y, z))

    def card_pt(cx, cy, dx, dy):
        # Centre sits `lift` above the plane; the card itself uses its own (shallower) lean and spin.
        x, y, z = plane_xyz(cx, cy, a.lift)
        ox, oy = dx * S, dy * S
        ox, oy = ox * math.cos(CRZ) - oy * math.sin(CRZ), ox * math.sin(CRZ) + oy * math.cos(CRZ)
        return screen(x + ox, y + oy * math.cos(CRX), z + oy * math.sin(CRX))

    # Base plane: an empty slot and a cast shadow where each card has lifted off
    plane = src.copy(); shadow = Image.new('RGBA', plane.size, (0, 0, 0, 0)); d = ImageDraw.Draw(shadow)
    for (x0, y0, x1, y1) in cards:
        ImageDraw.Draw(plane).rounded_rectangle([x0, y0, x1, y1], a.card_radius, fill=(6, 15, 14, 255), outline=(30, 58, 53, 255), width=2)
        d.rounded_rectangle([x0 - 10, y0 + 30, x1 + 30, y1 + 70], 26, fill=(0, 0, 0, 200))
    plane.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(26)))
    plane.putalpha(rounded_mask(plane.size, 26))
    ImageDraw.Draw(plane).rounded_rectangle([0, 0, SW - 1, SH - 1], 26, outline=(255, 255, 255, 40), width=2)
    canvas = Image.new('RGBA', (CW, CH), (0, 0, 0, 0))
    canvas.alpha_composite(warp(plane, [project(0, 0), project(SW, 0), project(SW, SH), project(0, SH)], (CW, CH)))

    # Fade the plane out towards the canvas edges, as the website does
    fade = Image.new('L', (CW, CH), 255); fd = ImageDraw.Draw(fade)
    for i in range(160):
        fd.rectangle([i, i * CH // CW, CW - 1 - i, CH - 1 - i * CH // CW], outline=int(255 * (i / 160) ** 1.4))
    alpha = np.array(canvas.getchannel('A'), float) * np.array(fade.filter(ImageFilter.GaussianBlur(40)), float) / 255
    canvas.putalpha(Image.fromarray(alpha.astype('uint8')))

    for (x0, y0, x1, y1) in cards:
        card = src.crop((x0, y0, x1, y1)); card.putalpha(rounded_mask(card.size, a.card_radius))
        ImageDraw.Draw(card).rounded_rectangle([0, 0, card.width - 1, card.height - 1], a.card_radius, outline=(255, 255, 255, 70), width=2)
        cx, cy, hw, hh = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2 * a.grow, (y1 - y0) / 2 * a.grow
        quad = [card_pt(cx, cy, dx, dy) for dx, dy in ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh))]
        canvas.alpha_composite(warp(card.resize((card.width * 3, card.height * 3), Image.LANCZOS), quad, (CW, CH)))
    save(canvas, a.out)


# ---------------------------------------------------------------- collage
def collage(a):
    CW, CH = map(int, a.size.split('x')); canvas = Image.new('RGBA', (CW, CH), (0, 0, 0, 0))
    for spec in a.win:
        src, w, x, y = spec.rsplit(':', 3); crop = None
        if '@' in src:
            src, c = src.split('@'); crop = tuple(map(int, c.split(',')))
        im = Image.open(src).convert('RGB')
        if crop: im = im.crop(crop)
        win = window(im, int(w), bar=not a.no_bar)
        if a.tilt:   # gentle lean matching the brochure browser window
            W, H = win.size
            win = warp(win, [(0, H * 0.085), (W, 0), (W, H * 0.985), (W * 0.012, H * 0.93)], (W, H))
            drop(canvas, win, int(x), int(y), blur=34, alpha=190, dy=26)
        else:
            drop(canvas, win, int(x), int(y))
    save(canvas, a.out)


# ---------------------------------------------------------------- cutout
def cutout(a):
    src = Image.open(a.src).convert('RGBA')
    quad = [tuple(map(float, p.split(','))) for p in a.quad]
    xs, ys = [p[0] for p in quad], [p[1] for p in quad]
    box = (int(min(xs)) - 10, int(min(ys)) - 10, int(max(xs)) + 10, int(max(ys)) + 10)
    crop = src.crop(box); q = [(x - box[0], y - box[1]) for x, y in quad]; r = a.radius
    cx, cy = sum(p[0] for p in q) / 4, sum(p[1] for p in q) / 4

    def inset(p):
        dx, dy = cx - p[0], cy - p[1]; d = math.hypot(dx, dy); return (p[0] + dx / d * r * 1.5, p[1] + dy / d * r * 1.5)
    qi = [inset(p) for p in q]; SS = 3
    m = Image.new('L', (crop.width * SS, crop.height * SS), 0); d = ImageDraw.Draw(m)
    qs = [(x * SS, y * SS) for x, y in qi]
    d.polygon(qs, fill=255); d.line(qs + [qs[0], qs[1]], fill=255, width=int(r * 2 * SS), joint='curve')   # rounded corners
    crop.putalpha(m.resize(crop.size, Image.LANCZOS))
    save(crop, a.out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    t = sub.add_parser('tilt'); t.add_argument('src'); t.add_argument('out')
    t.add_argument('--card', action='append', default=[], help='x0,y0,x1,y1 of a card to lift (source pixels); repeatable')
    t.add_argument('--size', default='2180x1090'); t.add_argument('--scale', type=float, default=1.12)
    t.add_argument('--origin', default='400,215', help='where the plane\'s top-left sits on the canvas')
    t.add_argument('--rx', type=float, default=50); t.add_argument('--rz', type=float, default=-20); t.add_argument('--perspective', type=float, default=1600)
    t.add_argument('--lift', type=float, default=72); t.add_argument('--grow', type=float, default=1.16)
    t.add_argument('--card-rx', type=float, default=28, help='50 = flat on the plane, 28 = tipped forward (readable), 12 = nearly facing the viewer')
    t.add_argument('--card-rz', type=float, default=None, help='card spin; defaults to the plane\'s. Less negative = rotated clockwise')
    t.add_argument('--card-radius', type=int, default=18); t.set_defaults(fn=tilt)
    c = sub.add_parser('collage'); c.add_argument('out'); c.add_argument('--win', action='append', required=True)
    c.add_argument('--size', default='2555x1843'); c.add_argument('--tilt', action='store_true'); c.add_argument('--no-bar', action='store_true'); c.set_defaults(fn=collage)
    k = sub.add_parser('cutout'); k.add_argument('src'); k.add_argument('out'); k.add_argument('--quad', nargs=4, required=True); k.add_argument('--radius', type=int, default=30); k.set_defaults(fn=cutout)
    a = ap.parse_args(); a.fn(a)


if __name__ == '__main__':
    main()
