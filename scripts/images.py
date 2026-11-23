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

def chip_row(d, chips, x, y, maxw=1056):
    """Data chips under the title: [(text, (r,g,b)), ...]. Pills wrap to a second row; anything that won't fit is dropped."""
    f = font('JetBrainsMono-500.woff2', 25); h = 50; x0 = x
    for text, col in chips:
        w = round(d.textlength(text, font=f)) + 44
        if x + w > x0 + maxw:
            x = x0; y += h + 14
            if y > 500: break
        d.rounded_rectangle((x, y, x + w, y + h), radius=25, fill=tuple(round(c * .16 + b * .84) for c, b in zip(col, BG)), outline=col, width=2)
        d.ellipse((x + 16, y + h // 2 - 5, x + 26, y + h // 2 + 5), fill=col)
        d.text((x + 34, y + 11), text, font=f, fill=WHITE)
        x += w + 14

def hexrgb(h): h = h.lstrip('#'); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

def og_card(out, kicker, title, foot='fullduplexhq.com  ·  @FullDuplexHQ', chips=None):
    global _plate
    if _plate is None: _plate = fit(Image.open(SRC / 'og-plate.jpg').convert('RGB'), 1200, 630)
    im = _plate.copy(); d = ImageDraw.Draw(im)
    logo = Image.open(SRC / 'logo-a-512.png').convert('RGBA').resize((76, 76), Image.LANCZOS)  # logo A (rendered from assets/logo.svg)
    im.paste(logo, (64, 50), logo)
    fh = font('InterTight-600.woff2', 40)
    d.text((148, 66), 'Full', font=fh, fill=WHITE); d.text((148 + d.textlength('Full', font=fh), 66), 'Duplex', font=fh, fill=CYAN)
    d.text((72, 200), kicker.upper(), font=font('JetBrainsMono-500.woff2', 26), fill=CYAN)
    maxl = 2 if chips else 3
    for size in ((68, 60, 54, 48) if chips else (76, 68, 60, 52)):
        ft = font('InterTight-600.woff2', size); lines = wrap(d, title, ft, 1000)
        if len(lines) <= maxl: break
    lines = lines[:maxl]; y = 250
    for ln in lines: d.text((72, y), ln, font=ft, fill=WHITE); y += round(size * 1.12)
    if chips: chip_row(d, [(t, hexrgb(c) if isinstance(c, str) else c) for t, c in chips], 72, y + 30)
    d.text((72, 548), foot, font=font('JetBrainsMono-500.woff2', 22), fill=(160, 176, 200))
    return save(im, out, 'JPEG', quality=84, optimize=True, progressive=True)


def og_card_art(out, kicker, title, art, sub=None, foot='fullduplexhq.com  ·  @FullDuplexHQ'):
    """1200x630 share card: brand plate, title, and a hero still in a rounded frame.
    Same typography and footer as og_card / render_share.py, with artwork in the lower band."""
    W, H = 1200, 630
    global _plate
    if _plate is None:
        _plate = fit(Image.open(SRC / 'og-plate.jpg').convert('RGB'), W, H)
    im = Image.blend(_plate.copy(), Image.new('RGB', (W, H), BG), 0.45)
    d = ImageDraw.Draw(im)
    logo = Image.open(SRC / 'logo-a-512.png').convert('RGBA').resize((64, 64), Image.LANCZOS)
    im.paste(logo, (52, 36), logo)
    fh = font('InterTight-600.woff2', 34)
    d.text((128, 48), 'Full', font=fh, fill=WHITE)
    d.text((128 + d.textlength('Full', font=fh), 48), 'Duplex', font=fh, fill=CYAN)
    mono_k = font('JetBrainsMono-500.woff2', 20)
    kw = d.textlength(kicker.upper(), font=mono_k)
    d.text((W - 52 - kw, 54), kicker.upper(), font=mono_k, fill=CYAN)
    for size in (48, 42, 38, 34):
        ft = font('InterTight-600.woff2', size)
        lines = wrap(d, title, ft, 1090)
        if len(lines) <= 2:
            break
    y = 112
    for ln in lines[:2]:
        d.text((56, y), ln, font=ft, fill=WHITE)
        y += round(size * 1.14)
    if sub:
        ms = font('JetBrainsMono-500.woff2', 20)
        d.text((56, y + 4), sub, font=ms, fill=(176, 192, 214))
        y += 32
    # hero still in the remaining band
    art_im = Image.open(art).convert('RGB')
    box = (56, y + 18, W - 56, 572)
    bw, bh = box[2] - box[0], box[3] - box[1]
    s = max(bw / art_im.width, bh / art_im.height)
    gg = art_im.resize((max(1, round(art_im.width * s)), max(1, round(art_im.height * s))), Image.LANCZOS)
    ax = box[0] + (bw - gg.width) // 2
    ay = box[1] + (bh - gg.height) // 2
    gg = gg.crop((max(0, -ax), max(0, -ay), max(0, -ax) + bw, max(0, -ay) + bh))
    ax, ay = box[0], box[1]
    m = Image.new('L', gg.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, gg.width - 1, gg.height - 1), radius=18, fill=255)
    sh = Image.new('L', (W, H), 0)
    ImageDraw.Draw(sh).rounded_rectangle((ax - 2, ay + 6, ax + gg.width + 2, ay + gg.height + 10), radius=20, fill=150)
    im.paste(Image.new('RGB', (W, H), (0, 0, 0)), (0, 0), sh.filter(ImageFilter.GaussianBlur(14)))
    im.paste(gg, (ax, ay), m)
    ImageDraw.Draw(im).rounded_rectangle((ax, ay, ax + gg.width - 1, ay + gg.height - 1), radius=18, outline=(40, 64, 96), width=2)
    d = ImageDraw.Draw(im)
    mf = font('JetBrainsMono-500.woff2', 18)
    d.text((W - 56 - d.textlength(foot, font=mf), 588), foot, font=mf, fill=(150, 166, 190))
    return save(im, out, 'JPEG', quality=88, subsampling=0, optimize=True, progressive=True)

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
