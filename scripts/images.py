#!/usr/bin/env python3
"""Full Duplex image pipeline (needs Pillow: pip install pillow).

Approved by Sam on 9 Nov 2026. Sources live in src/img/ (originals from the approved previews).
  python3 scripts/images.py          -> responsive WebP/JPEG in assets/img/ and PNG icons in assets/
build.py calls og_card() for the per-page 1200x630 share cards in assets/og/ when Pillow is installed.
Outputs are only rewritten when their bytes change, so rebuilding does not create noisy diffs.
"""
import io, math, pathlib, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / 'src' / 'img'
IMG = ROOT / 'assets' / 'img'
FONTS = ROOT / 'assets' / 'fonts'
CYAN, WHITE, BG = (94, 200, 255), (255, 255, 255), (7, 11, 20)

def save(im, path, fmt, **kw):
    buf = io.BytesIO(); im.save(buf, fmt, **kw); data = buf.getvalue()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_bytes() != data:
        path.write_bytes(data); return True
    return False

def fit(im, w, h, cy=.5, cx=.5):
    """Scale to cover w x h, then crop around (cx, cy) as fractions."""
    s = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x = round((im.width - w) * cx); y = round((im.height - h) * cy)
    return im.crop((x, y, x + w, y + h))

# ------------------------------------------------------------------ logo mark (same geometry as assets/favicon.svg)
def draw_mark(size, bg=True, rounded=True, pad=0.0):
    k = 8; S = size * k; im = Image.new('RGBA', (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    u = S / 64
    if bg:
        if rounded: d.rounded_rectangle((0, 0, S - 1, S - 1), radius=14 * u, fill=BG + (255,))
        else: d.rectangle((0, 0, S, S), fill=BG + (255,))
    sc = 1 - pad * 2; off = pad * S
    P = lambda x, y: (off + x * u * sc, off + y * u * sc)
    cx, cy = P(32, 32); r = 19 * u * sc; w = 7.5 * u * sc
    for a0, a1, col in ((165.3, 310.6, CYAN), (345.3, 490.6, WHITE)):
        R = r + w / 2; d.arc((cx - R, cy - R, cx + R, cy + R), a0, a1, fill=col + (255,), width=round(w))
        for a in (a0, a1):  # round caps (stroke centre on radius r)
            rr = r; x = cx + rr * math.cos(math.radians(a)); y = cy + rr * math.sin(math.radians(a))
            d.ellipse((x - w / 2, y - w / 2, x + w / 2, y + w / 2), fill=col + (255,))
    dr = 5.5 * u * sc; d.ellipse((cx - dr, cy - dr, cx + dr, cy + dr), fill=CYAN + (255,))
    return im.resize((size, size), Image.LANCZOS)

# ------------------------------------------------------------------ OG cards
_plate = None
def font(name, size): return ImageFont.truetype(str(FONTS / name), size)
def wrap(d, text, f, width):
    lines, cur = [], ''
    for wd in text.split():
        t = (cur + ' ' + wd).strip()
        if d.textlength(t, font=f) <= width or not cur: cur = t
        else: lines.append(cur); cur = wd
    return lines + [cur] if cur else lines

def og_card(out, kicker, title, foot='signalcraft-studio.github.io/full-duplex  ·  @FullDuplexHQ'):
    global _plate
    if _plate is None: _plate = fit(Image.open(SRC / 'og-plate.jpg').convert('RGB'), 1200, 630)
    im = _plate.copy(); d = ImageDraw.Draw(im)
    im.paste(m := draw_mark(56, bg=False), (72, 60), m)
    fh = font('InterTight-600.woff2', 40)
    d.text((140, 66), 'Full', font=fh, fill=WHITE); d.text((140 + d.textlength('Full', font=fh), 66), 'Duplex', font=fh, fill=CYAN)
    d.text((72, 200), kicker.upper(), font=font('JetBrainsMono-500.woff2', 26), fill=CYAN)
    for size in (76, 68, 60, 52):
        ft = font('InterTight-600.woff2', size); lines = wrap(d, title, ft, 1000)
        if len(lines) <= 3: break
    lines = lines[:3]; y = 250
    for ln in lines: d.text((72, y), ln, font=ft, fill=WHITE); y += round(size * 1.12)
    d.text((72, 548), foot, font=font('JetBrainsMono-500.woff2', 22), fill=(160, 176, 200))
    return save(im, out, 'JPEG', quality=84, optimize=True, progressive=True)

# ------------------------------------------------------------------ responsive assets + icons
def build():
    ch = []
    hero = Image.open(SRC / 'home-hero.jpg').convert('RGB')
    for w in (960, 1600): ch.append(save(hero.resize((w, round(w * hero.height / hero.width)), Image.LANCZOS), IMG / f'home-hero-{w}.webp', 'WEBP', quality=62, method=6))
    plate = fit(Image.open(SRC / 'article-plate.jpg').convert('RGB'), 1280, 512, cy=.55)
    for w in (640, 960, 1280): ch.append(save(plate.resize((w, w * 2 // 5), Image.LANCZOS), IMG / f'article-plate-{w}.webp', 'WEBP', quality=66, method=6))
    tr = Image.open(SRC / 'tracker-map.jpg').convert('RGB')
    for w in (640, 1280): ch.append(save(tr.resize((w, w * 9 // 16), Image.LANCZOS), IMG / f'tracker-map-{w}.webp', 'WEBP', quality=48, method=6))
    sp = Image.open(SRC / 'sponsor-plate.jpg').convert('RGB')
    ch.append(save(sp.resize((960, 540), Image.LANCZOS), IMG / 'sponsor-plate-960.webp', 'WEBP', quality=60, method=6))
    A = ROOT / 'assets'
    ch.append(save(draw_mark(32), A / 'favicon-32.png', 'PNG', optimize=True))
    ch.append(save(draw_mark(180, rounded=False, pad=.1).convert('RGB'), A / 'apple-touch-icon.png', 'PNG', optimize=True))
    for s in (192, 512): ch.append(save(draw_mark(s, rounded=False, pad=.1).convert('RGB'), A / f'icon-{s}.png', 'PNG', optimize=True))
    return sum(ch)

if __name__ == '__main__':
    print('changed', build(), 'files')
