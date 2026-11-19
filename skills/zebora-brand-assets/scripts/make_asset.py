#!/usr/bin/env python3
"""Render an on-brand Zebora image (social post, header, share image, blog header, slide, cover).

Pillow only, so it runs in Claude Code and in the claude.ai / Claude desktop code sandbox.
Fonts (Inter, Roboto Mono) and the supplied logo artwork ship in ../assets.

  make_asset.py --format linkedin-post --headline "Know why you are winning" \\
      --accent "winning" --eyebrow "AI visibility" --sub "One line of support." --out post.png

  make_asset.py --format blog-header --layout split --image tilted-dashboard.png \\
      --headline "Measure. Diagnose. Act." --accent "Act." --out header.png

  make_asset.py --list            # formats and their sizes

--accent is a phrase inside --headline that is set in Signal Green (the one focal point).
--image is a screenshot or a transparent PNG (e.g. from zebora-deck-refresh image_recipes.py tilt).
--bg is a finished background (e.g. from the Brand Asset Studio); a scrim keeps the text side calm.
Copy is checked before anything is drawn: em dashes and baked-in hype words stop the render.
"""
import argparse
import math
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "assets" / "fonts"
LOGOS = ROOT / "assets" / "logo"

DEEP = (8, 21, 20)
TRUE_DARK = (0, 11, 2)
GREEN = (0, 235, 91)
TEAL = (0, 138, 92)
SLATE_WHITE = (248, 250, 252)
SIGNAL_GREY = (148, 163, 184)
LIGHT_TEXT = (11, 26, 24)
LIGHT_BODY = (71, 85, 105)

# layout: centre = centred thesis (zebora.io share images); left = left thesis, waves to the right;
# split = text left, image right; header = LinkedIn cover (lower-left avatar area kept clear).
FORMATS = {
    "linkedin-post": {"size": (1080, 1080), "layout": "centre", "use": "LinkedIn / Instagram feed post"},
    "linkedin-header": {"size": (1584, 396), "layout": "header", "use": "LinkedIn profile or company cover"},
    "social-share": {"size": (1200, 630), "layout": "centre", "use": "Open Graph / link preview image"},
    "blog-header": {"size": (1600, 900), "layout": "left", "use": "Guide or article hero (16:9)"},
    "slide": {"size": (1920, 1080), "layout": "left", "use": "Single 16:9 slide image or title card"},
    "story": {"size": (1080, 1920), "layout": "centre", "use": "Vertical story / reel cover"},
    "doc-cover": {"size": (1240, 1754), "layout": "left", "use": "A4 report or one-pager cover"},
    "email-header": {"size": (1200, 400), "layout": "left", "use": "Email or newsletter banner"},
}

BANNED = ["revolutionary", "game-changing", "game changing", "cutting-edge", "unleash", "supercharge"]


def font(name, px):
    return ImageFont.truetype(str(FONTS / name), max(8, int(px)))


def check_copy(fields):
    problems = []
    for label, text in fields.items():
        if not text:
            continue
        if "—" in text:
            problems.append(f"{label}: contains an em dash; use a comma, colon or full stop")
        for word in BANNED:
            if word in text.lower():
                problems.append(f"{label}: '{word}' is on the brand's avoid list")
    return problems


# ---------------------------------------------------------------- background
def radial(size, centre, radius, colour, opacity):
    w, h = size
    layer = Image.new("RGBA", size, colour + (0,))
    mask = Image.radial_gradient("L").resize((int(radius * 2), int(radius * 2)))
    mask = mask.point(lambda v: int(255 * opacity * max(0.0, 1 - v / 240) ** 2))  # reaches 0 inside the square
    full = Image.new("L", size, 0)
    full.paste(mask, (int(centre[0] - radius), int(centre[1] - radius)))
    layer.putalpha(full)
    return layer


def vertical_gradient(size, top, bottom, start=0.55):
    w, h = size
    img = Image.new("RGB", size, top)
    d = ImageDraw.Draw(img)
    for y in range(int(h * start), h):
        t = (y - h * start) / max(1, h * (1 - start))
        d.line([(0, y), (w, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(top, bottom)))
    return img.convert("RGBA")


def grid(size, step, colour, opacity, fade_to_bottom=True):
    w, h = size
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    a = int(255 * opacity)
    for x in range(0, w + 1, step):
        d.line([(x, 0), (x, h)], fill=colour + (a,), width=1)
    for y in range(0, h + 1, step):
        d.line([(0, y), (w, y)], fill=colour + (a,), width=1)
    if fade_to_bottom:
        fade = Image.linear_gradient("L").resize(size).point(lambda v: 255 - int(v * 0.85))
        layer.putalpha(Image.composite(layer.getchannel("A"), Image.new("L", size, 0), fade))
    return layer


def waves(size, band, scale, n=26, amp=46, seed=0.0, fade="none"):
    """The zebora.io signal field: fine lines, every third one Signal Green."""
    w, h = size
    ss = 2
    layer = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    y0, y1 = band
    for i in range(n):
        pts = []
        for x in range(-40, w + 41, 8):
            y = (y0 + (y1 - y0) * i / max(1, n - 1)
                 + math.sin(x / (190 * scale) + i * 0.16 + seed) * amp * scale * math.sin(x / (640 * scale) + 0.6)
                 + math.sin(x / (90 * scale) + i * 0.3) * 6 * scale)
            pts.append((x * ss, y * ss))
        green = i % 3 == 0
        colour = GREEN + (int(255 * (0.30 if green else 0.09)),) if green else SLATE_WHITE + (int(255 * 0.09),)
        d.line(pts, fill=colour, width=max(2, int(1.3 * ss * scale)))
    layer = layer.resize(size, Image.LANCZOS)
    if fade != "none":
        g = Image.linear_gradient("L").rotate(90 if fade == "right" else -90, expand=True).resize(size)
        layer.putalpha(Image.composite(layer.getchannel("A"), Image.new("L", size, 0), g))
    return layer


def rings(size, centre, radii, opacity, scale):
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for i, r in enumerate(radii):
        a = int(255 * opacity * (1 - i * 0.3))
        d.ellipse([centre[0] - r, centre[1] - r, centre[0] + r, centre[1] + r], outline=GREEN + (a,), width=max(1, int(1.5 * scale)))
    return layer


def registration_mark(d, x, y, s, colour):
    r = 9 * s
    d.line([(x - r, y), (x + r, y)], fill=colour, width=max(1, int(1.2 * s)))
    d.line([(x, y - r), (x, y + r)], fill=colour, width=max(1, int(1.2 * s)))
    d.ellipse([x - r * 0.45, y - r * 0.45, x + r * 0.45, y + r * 0.45], outline=colour, width=max(1, int(1.2 * s)))


def background(size, layout, theme, scale, bg_path=None):
    w, h = size
    if theme == "light":
        canvas = Image.new("RGBA", size, SLATE_WHITE + (255,))
        canvas.alpha_composite(grid(size, int(60 * scale), (15, 23, 42), 0.06, fade_to_bottom=False))
        canvas.alpha_composite(radial(size, (w * 0.95, 0), max(w, h) * 0.55, GREEN, 0.10))
        return canvas
    canvas = vertical_gradient(size, DEEP, TRUE_DARK)
    if bg_path:
        art = Image.open(bg_path).convert("RGBA")
        ratio = max(w / art.width, h / art.height)
        art = art.resize((math.ceil(art.width * ratio), math.ceil(art.height * ratio)), Image.LANCZOS)
        left, top = (art.width - w) // 2, (art.height - h) // 2
        canvas.alpha_composite(art.crop((left, top, left + w, top + h)))
        scrim = Image.linear_gradient("L").rotate(90, expand=True).resize(size)  # dark on the left
        if layout in ("centre",):
            scrim = Image.new("L", size, 150)
        dark = Image.new("RGBA", size, DEEP + (0,))
        dark.putalpha(scrim.point(lambda v: int(v * 0.85)))
        canvas.alpha_composite(dark)
        return canvas
    if layout == "centre":
        canvas.alpha_composite(radial(size, (w * 0.5, h * 0.08), max(w, h) * 0.44, GREEN, 0.22))
        canvas.alpha_composite(radial(size, (w * 0.86, h * 0.78), max(w, h) * 0.34, TEAL, 0.16))
    else:
        canvas.alpha_composite(radial(size, (w * 0.78, h * 0.18), max(w, h) * 0.42, GREEN, 0.20))
        canvas.alpha_composite(radial(size, (w * 0.12, h * 0.96), max(w, h) * 0.38, TEAL, 0.16))
    g = grid(size, int(60 * scale), SIGNAL_GREY, 0.09 * 0.6)
    canvas.alpha_composite(g)
    if layout == "centre":
        r = min(w, h) * 0.53
        canvas.alpha_composite(rings(size, (w / 2, h * 0.11 + r), [r], 0.16, scale))
        canvas.alpha_composite(waves(size, (h - 180 * scale, h - 20 * scale), scale))
    elif layout == "header":
        canvas.alpha_composite(waves(size, (h * 0.15, h * 0.95), scale, n=30, amp=60, fade="right"))
    elif layout == "left":
        canvas.alpha_composite(rings(size, (w * 0.78, h * 0.5), [h * 0.42, h * 0.3], 0.12, scale))
        canvas.alpha_composite(waves(size, (h * 0.42, h * 0.78), scale, n=34, amp=70, fade="right"))
    return canvas


# ---------------------------------------------------------------- text
def tokens(headline, accent):
    """Split the headline into (word, is_accent) pairs; '\\n' forces a line break."""
    out = []
    start = headline.find(accent) if accent else -1
    if accent and start < 0:
        sys.exit(f"--accent '{accent}' does not appear in the headline")
    for m in re.finditer(r"\S+|\n", headline):
        hit = start >= 0 and m.start() >= start and m.end() <= start + len(accent)
        out.append((m.group(), hit))
    return out


def wrap(words, f, width):
    lines, line = [], []
    for word, hit in words:
        if word == "\n":
            lines.append(line)
            line = []
            continue
        trial = " ".join(w for w, _ in line + [(word, hit)])
        if line and f.getlength(trial) > width:
            lines.append(line)
            line = []
        line.append((word, hit))
    if line:
        lines.append(line)
    return lines


def fit_headline(words, max_px, min_px, width, max_lines):
    px = max_px
    while px > min_px:
        f = font("Inter-Medium.ttf", px)
        lines = wrap(words, f, width)
        if len(lines) <= max_lines and all(f.getlength(" ".join(w for w, _ in ln)) <= width for ln in lines):
            return f, lines
        px -= 2
    f = font("Inter-Medium.ttf", min_px)
    return f, wrap(words, f, width)


def paragraph(text, f, width):
    return [" ".join(w for w, _ in ln) for ln in wrap([(t, False) for t in text.split()], f, width)]


def draw_eyebrow(canvas, text, x, y, scale, align, theme):
    d = ImageDraw.Draw(canvas)
    f = font("RobotoMono-SemiBold.ttf", 14 * scale)
    label = text.upper()
    spacing = 0.2 * f.size
    tw = sum(f.getlength(c) + spacing for c in label) - spacing
    pad_x, pad_y, dot = 14 * scale, 9 * scale, 7 * scale
    bw, bh = tw + pad_x * 2 + dot + 10 * scale, f.size + pad_y * 2
    if align == "centre":
        x -= bw / 2
    pill = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    pd = ImageDraw.Draw(pill)
    pd.rounded_rectangle([x, y, x + bw, y + bh], radius=bh / 2, fill=GREEN + (26,), outline=GREEN + (90,), width=max(1, int(scale)))
    canvas.alpha_composite(pill)
    colour = TEAL if theme == "light" else GREEN
    cy = y + bh / 2
    d.ellipse([x + pad_x, cy - dot / 2, x + pad_x + dot, cy + dot / 2], fill=colour)
    cx = x + pad_x + dot + 10 * scale
    for c in label:
        d.text((cx, cy), c, font=f, fill=colour, anchor="lm")
        cx += f.getlength(c) + spacing
    return bh


def layout_text(spec, width, max_lines, max_px, scale, align, max_height):
    """Largest headline size whose whole block (eyebrow, headline, sub) fits width and height."""
    words = tokens(spec.headline, spec.accent)
    eyebrow_h = (14 * scale + 18 * scale + 26 * scale) if spec.eyebrow else 0
    px = max_px
    while True:
        f, lines = fit_headline(words, px, 22 * scale, width, max_lines)
        fs = font("Inter-Regular.ttf", max(17 * scale, f.size * 0.38))
        sub = paragraph(spec.sub, fs, width * (0.82 if align == "centre" else 0.9)) if spec.sub else []
        height = eyebrow_h + len(lines) * f.size * 1.06 + (22 * scale + len(sub) * fs.size * 1.4 if sub else 0)
        if height <= max_height or f.size <= 22 * scale:
            return f, lines, fs, sub
        px = f.size - 2


def draw_text_block(canvas, spec, box, align, theme, scale, max_bottom=None):
    """Eyebrow, headline (accent in green), sub. Returns the bottom y."""
    x0, y0, width, max_lines, max_px = box
    d = ImageDraw.Draw(canvas)
    head_colour = LIGHT_TEXT if theme == "light" else SLATE_WHITE
    accent_colour = TEAL if theme == "light" else GREEN
    sub_colour = LIGHT_BODY if theme == "light" else SIGNAL_GREY
    bottom = max_bottom if max_bottom is not None else canvas.height - 48 * scale
    f, lines, fs, sub = layout_text(spec, width, max_lines, max_px, scale, align, bottom - y0)
    cx = x0 + width / 2
    y = y0
    if spec.eyebrow:
        y += draw_eyebrow(canvas, spec.eyebrow, cx if align == "centre" else x0, y, scale, align, theme) + 26 * scale
    lh = f.size * 1.06
    space = f.getlength(" ")
    for ln in lines:
        lw = f.getlength(" ".join(w for w, _ in ln))
        x = cx - lw / 2 if align == "centre" else x0
        for word, hit in ln:
            d.text((x, y), word, font=f, fill=accent_colour if hit else head_colour)
            x += f.getlength(word) + space
        y += lh
    if sub:
        y += 22 * scale
        for line in sub:
            lw = fs.getlength(line)
            d.text((cx - lw / 2 if align == "centre" else x0, y), line, font=fs, fill=sub_colour)
            y += fs.size * 1.4
    if y > bottom + 1:
        print(f"warning: text runs {int(y - bottom)} px past the safe area; shorten the copy", file=sys.stderr)
    return y


# ---------------------------------------------------------------- images
def rounded(im, r):
    m = Image.new("L", (im.width * 3, im.height * 3), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, m.width - 1, m.height - 1], r * 3, fill=255)
    out = im.convert("RGBA")
    out.putalpha(Image.composite(out.getchannel("A"), Image.new("L", out.size, 0), m.resize(out.size, Image.LANCZOS)))
    return out


def place_image(canvas, path, box, scale):
    """Opaque screenshots get a browser-window frame and shadow; transparent PNGs are placed as they are."""
    x, y, bw, bh = box
    im = Image.open(path).convert("RGBA")
    has_alpha = im.getchannel("A").getextrema()[0] < 250
    ratio = min(bw / im.width, bh / im.height)
    im = im.resize((int(im.width * ratio), int(im.height * ratio)), Image.LANCZOS)
    if not has_alpha:
        bar = int(max(18, im.width * 0.03))
        framed = Image.new("RGBA", (im.width, im.height + bar), (28, 30, 30, 255))
        framed.paste(im, (0, bar))
        fd = ImageDraw.Draw(framed)
        for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
            ccx, r = bar * (0.7 + i * 0.62), bar * 0.2
            fd.ellipse([ccx - r, bar / 2 - r, ccx + r, bar / 2 + r], fill=c)
        im = rounded(framed, int(14 * scale))
        ImageDraw.Draw(im).rounded_rectangle([0, 0, im.width - 1, im.height - 1], int(14 * scale), outline=(255, 255, 255, 36), width=max(1, int(scale)))
        shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        blk = Image.new("RGBA", im.size, (0, 0, 0, 170))
        blk.putalpha(im.getchannel("A").point(lambda v: v * 170 // 255))
        px, py = int(x + (bw - im.width) / 2), int(y + (bh - im.height) / 2)
        shadow.alpha_composite(blk, (px, py + int(24 * scale)))
        canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(30 * scale)))
        canvas.alpha_composite(im, (px, py))
        return
    canvas.alpha_composite(im, (int(x + (bw - im.width) / 2), int(y + (bh - im.height) / 2)))


def place_logo(canvas, theme, x, y, height, align="left"):
    logo = Image.open(LOGOS / ("logo-on-light.png" if theme == "light" else "logo-on-dark.png")).convert("RGBA")
    w = int(logo.width * height / logo.height)
    logo = logo.resize((w, int(height)), Image.LANCZOS)
    if align == "right":
        x -= w
    canvas.alpha_composite(logo, (int(x), int(y)))


# ---------------------------------------------------------------- compose
def render(spec):
    fmt = FORMATS[spec.format]
    w, h = fmt["size"]
    layout = spec.layout or fmt["layout"]
    if layout == "split" and not spec.image:
        sys.exit("--layout split needs --image")
    scale = h / 396 if w / h >= 2.5 else min(w, h) / 630
    scale = max(0.6, min(scale, 2.4))
    canvas = background((w, h), layout, spec.theme, scale, spec.bg)
    margin = 64 * scale
    mark = (148, 163, 184, 110) if spec.theme == "dark" else (71, 85, 105, 110)

    if layout == "centre":
        place_logo(canvas, spec.theme, margin, 52 * scale, 46 * scale)
        top = h * 0.30 if h > w else 138 * scale
        width = w - 200 * scale
        if spec.image:
            img_h = h * 0.32
            place_image(canvas, spec.image, (margin, h - img_h - margin, w - 2 * margin, img_h), scale)
        bottom = h - (h * 0.32 + margin + 24 * scale if spec.image else 150 * scale)
        draw_text_block(canvas, spec, (100 * scale, top, width, 3, 84 * scale), "centre", spec.theme, scale, max_bottom=bottom)
    elif layout == "header":
        place_logo(canvas, spec.theme, w - 44 * scale, 38 * scale, 52 * scale, align="right")
        draw_text_block(canvas, spec, (w * 0.25, h * 0.26, w * 0.6, 2, 53 * scale), "left", spec.theme, scale,
                        max_bottom=h - 40 * scale)
        registration_mark(ImageDraw.Draw(canvas), w - 66 * scale, h - 66 * scale, scale, mark)
    elif layout == "left":
        tall, banner = h > w, w / h >= 2.5
        if banner:
            place_logo(canvas, spec.theme, w - margin * 0.7, margin * 0.6, 40 * scale, align="right")
        else:
            place_logo(canvas, spec.theme, margin, margin * 0.8, 46 * scale)
        width = (w - 2 * margin) * (0.86 if tall else 0.58)
        top = h * 0.36 if tall else h * (0.22 if banner else 0.30)
        if spec.image:
            place_image(canvas, spec.image, (w * 0.55, h * 0.18, w * 0.42, h * 0.64), scale)
            width = w * 0.46
        max_px = 88 * scale if tall else min(72 * scale, h * 0.13)
        draw_text_block(canvas, spec, (margin, top, width, 4 if tall else 3, max_px), "left", spec.theme, scale,
                        max_bottom=h - margin)
        registration_mark(ImageDraw.Draw(canvas), w - margin, h - margin, scale, mark)
    elif layout == "split":
        place_logo(canvas, spec.theme, margin, margin * 0.8, 46 * scale)
        place_image(canvas, spec.image, (w * 0.47, h * 0.12, w * 0.52, h * 0.80), scale)
        draw_text_block(canvas, spec, (margin, h * 0.26, w * 0.40, 4, min(72 * scale, h * 0.1)), "left", spec.theme, scale,
                        max_bottom=h - margin)

    out = canvas.convert("RGB")
    out.save(spec.out, quality=95) if spec.out.lower().endswith((".jpg", ".jpeg")) else out.save(spec.out)
    print(f"wrote {spec.out} {w}x{h} ({spec.format}, {layout}, {spec.theme})")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true", help="list formats and exit")
    ap.add_argument("--format", choices=sorted(FORMATS))
    ap.add_argument("--layout", choices=["centre", "left", "split", "header"])
    ap.add_argument("--theme", choices=["dark", "light"], default="dark")
    ap.add_argument("--headline")
    ap.add_argument("--accent", default="", help="phrase inside the headline to set in Signal Green")
    ap.add_argument("--eyebrow", default="")
    ap.add_argument("--sub", default="")
    ap.add_argument("--image", help="screenshot or transparent PNG to place")
    ap.add_argument("--bg", help="finished background image (e.g. from the Brand Asset Studio)")
    ap.add_argument("--out", default="zebora-asset.png")
    spec = ap.parse_args()
    if spec.list:
        for name, f in FORMATS.items():
            print(f"{name:16} {f['size'][0]}x{f['size'][1]:<6} {f['layout']:7} {f['use']}")
        return
    if not spec.format or not spec.headline:
        ap.error("--format and --headline are required")
    if spec.headline and "\\n" in spec.headline:
        spec.headline = spec.headline.replace("\\n", "\n")
    problems = check_copy({"headline": spec.headline, "eyebrow": spec.eyebrow, "sub": spec.sub})
    if problems:
        sys.exit("Copy check failed:\n  " + "\n  ".join(problems))
    render(spec)


if __name__ == "__main__":
    main()
