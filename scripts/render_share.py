#!/usr/bin/env python3
"""Render the 1200x630 share cards for "Post to X" (PREVIEW, needs Sam's approval before it goes live).

Reads share/items.json (written by build.py), opens the real page in headless Chromium, screenshots the real
globe / infographic element, and adds logo A branding and a short caption with Pillow -> share/<slug>/card.jpg (JPEG q88, 4:4:4 chroma so text stays crisp).
Only renders cards that are missing or whose content key changed (share/manifest.json), so the refresh workflow
commits new images only when a launch is added or its details change. Stale cards are pruned by build.py.

  python3 scripts/render_share.py            render what's missing or changed
  python3 scripts/render_share.py --pending  exit 0 if anything needs rendering, 1 if not (stdlib only, no browser)
  python3 scripts/render_share.py --all      re-render everything
Needs: pip install playwright pillow && python -m playwright install --with-deps chromium
Then run scripts/build.py again so the share pages point at the new cards.
"""
import functools, http.server, io, json, pathlib, sys, threading

ROOT = pathlib.Path(__file__).resolve().parent.parent
SHARE = ROOT / 'share'
ITEMS = json.loads((SHARE / 'items.json').read_text())['items'] if (SHARE / 'items.json').exists() else []
MAN_P = SHARE / 'manifest.json'
MAN = json.loads(MAN_P.read_text()) if MAN_P.exists() else {}

def todo(force=False):
    return [it for it in ITEMS if force or MAN.get(it['slug'], {}).get('key') != it['key'] or not (SHARE / it['slug'] / 'card.jpg').exists()]

HIDE = ('header.site,.stickybar,.welcome,.shr,.skip,.gw .gt,#fl-hud .fl-ctl,#fl-hud .fl-fine,#fl-hud .fl-status{display:none!important}'
        '*{scroll-behavior:auto!important}'
        '.scale-row,.alt-chart{padding:22px 26px!important;background:#0b1424;border-radius:14px;box-sizing:border-box}.alt-chart{max-width:900px}.scale-row{flex-wrap:nowrap!important}')

def serve():
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT))
    class Q(h.func):
        def log_message(self, *a): pass
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Q, directory=str(ROOT)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f'http://127.0.0.1:{srv.server_address[1]}/'

def grab(page, base, it):
    page.goto(base + it['page'], wait_until='load')
    page.add_style_tag(content=HIDE)
    page.evaluate('document.fonts.ready')
    el = page.locator(it['sel']).first
    el.scroll_into_view_if_needed()
    if it['kind'] == 'flight':  # scrub to just after the satellites are let go (or the last event), so the whole climb is drawn
        page.evaluate("""() => { const evs=[...document.querySelectorAll('#fl-events .fe')]; const r=document.getElementById('fl-range');
            const pay=evs.find(e=>/deploy|separat/i.test(e.textContent)&&/payload|satellite|deploy/i.test(e.textContent)) || evs[evs.length-1];
            // fl-range is 0..1000 over the profile; walk it until the clock passes the chosen event
            const T=+pay.dataset.t; let lo=0, hi=1000;
            for(let k=0;k<14;k++){ const m=(lo+hi)/2; r.value=m; r.dispatchEvent(new Event('input')); const c=document.getElementById('fl-clock').textContent;
              const mm=c.match(/T\\+\\s*(\\d+):(\\d+):(\\d+)/); const t=mm? (+mm[1])*3600+(+mm[2])*60+(+mm[3]) : -1; if(t<T+20) lo=m; else hi=m; }
            r.value=lo; r.dispatchEvent(new Event('input')); }""")
        page.wait_for_timeout(400)
    elif it['kind'] == 'canvas':
        page.wait_for_function(f"() => {{ const c=document.querySelector({json.dumps(it['sel'] + ' canvas')}); return c && c.width>0 && (!c.parentNode.classList.contains('ov-globe') || c.parentNode.classList.contains('ready') || {json.dumps(it['sel'])}=='#orbitview'); }}", timeout=20000)
        page.wait_for_timeout(2500)
    else:
        page.wait_for_timeout(600)
    return el.screenshot(animations='disabled' if it['kind'] == 'dom' and 'sc-art' not in it['sel'] else 'allow')

def compose(shot, it):
    from PIL import Image, ImageDraw, ImageFilter
    sys.path.insert(0, str(ROOT / 'scripts')); import images as I
    W, H = 1200, 630
    im = I.fit(Image.open(ROOT / 'src/img/og-plate.jpg').convert('RGB'), W, H)
    im = Image.blend(im, Image.new('RGB', (W, H), I.BG), 0.55)
    d = ImageDraw.Draw(im)
    g = Image.open(io.BytesIO(shot)).convert('RGB')
    logo = Image.open(ROOT / 'src/img/logo-a-512.png').convert('RGBA').resize((58, 58), Image.LANCZOS)
    im.paste(logo, (52, 40), logo)
    fh = I.font('InterTight-600.woff2', 32)
    d.text((122, 52), 'Full', font=fh, fill=I.WHITE); d.text((122 + d.textlength('Full', font=fh), 52), 'Duplex', font=fh, fill=I.CYAN)
    mono = lambda s: I.font('JetBrainsMono-500.woff2', s)
    foot = 'signalcraft-studio.github.io/full-duplex  ·  @FullDuplexHQ'
    def place(box):
        x0, y0, x1, y1 = box; bw, bh = x1 - x0, y1 - y0
        s = min(bw / g.width, bh / g.height); gg = g.resize((max(1, round(g.width * s)), max(1, round(g.height * s))), Image.LANCZOS)
        px, py = x0 + (bw - gg.width) // 2, y0 + (bh - gg.height) // 2
        m = Image.new('L', gg.size, 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, gg.width - 1, gg.height - 1), radius=18, fill=255)
        sh = Image.new('L', (W, H), 0); ImageDraw.Draw(sh).rounded_rectangle((px - 2, py + 6, px + gg.width + 2, py + gg.height + 10), radius=20, fill=150)
        im.paste(Image.new('RGB', (W, H), (0, 0, 0)), (0, 0), sh.filter(ImageFilter.GaussianBlur(14)))
        im.paste(gg, (px, py), m)
        ImageDraw.Draw(im).rounded_rectangle((px, py, px + gg.width - 1, py + gg.height - 1), radius=18, outline=(40, 64, 96), width=2)
    def title_lines(text, width, sizes, maxl):
        for size in sizes:
            ft = I.font('InterTight-600.woff2', size); ln = I.wrap(d, text, ft, width)
            if len(ln) <= maxl: return ft, size, ln
        return ft, size, ln[:maxl]
    if it['layout'] == 'square':
        place((640, 40, 1160, 590))
        d = ImageDraw.Draw(im)
        d.text((56, 180), it['kicker'].upper(), font=mono(21), fill=I.CYAN)
        ft, size, ln = title_lines(it['title'], 540, (58, 52, 46, 40), 3); y = 222
        for t in ln: d.text((56, y), t, font=ft, fill=I.WHITE); y += round(size * 1.14)
        y += 14
        for t in I.wrap(d, it.get('sub', ''), mono(22), 540)[:2]: d.text((56, y), t, font=mono(22), fill=(176, 192, 214)); y += 32
        if it.get('chips'):
            I.chip_row(d, [(t, I.hexrgb(c)) for t, c in it['chips'][:4]], 56, y + 14, maxw=560)
        d.text((W - 56 - d.textlength(foot, font=mono(17)), 598), foot, font=mono(17), fill=(150, 166, 190))  # right: X overlays the title bottom-left
    else:
        d.text((W - 52 - d.textlength(it['kicker'].upper(), font=mono(20)), 60), it['kicker'].upper(), font=mono(20), fill=I.CYAN)
        ft, size, ln = title_lines(it['title'], 1090, (50, 44, 40, 36), 1)
        d.text((56, 118), ln[0], font=ft, fill=I.WHITE)
        if it.get('sub'): d.text((56, 118 + round(size * 1.2)), it['sub'], font=mono(21), fill=(176, 192, 214))
        place((56, 218, W - 56, 580))
        d = ImageDraw.Draw(im)
        d.text((W - 56 - d.textlength(foot, font=mono(17)), 594), foot, font=mono(17), fill=(150, 166, 190))
    out = io.BytesIO()
    im.save(out, 'JPEG', quality=88, subsampling=0, optimize=True, progressive=True)
    return out.getvalue()

def main():
    force = '--all' in sys.argv
    work = todo(force)
    if '--pending' in sys.argv:
        print(f'{len(work)} share card(s) to render'); sys.exit(0 if work else 1)
    if not work: print('share cards up to date'); return
    from playwright.sync_api import sync_playwright
    srv, base = serve(); done = 0
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            ctx = b.new_context(viewport={'width': 1440, 'height': 1000}, device_scale_factor=2, reduced_motion='reduce', color_scheme='dark')
            for it in work:
                page = ctx.new_page(); errs = []
                page.on('pageerror', lambda e: errs.append(str(e)))
                try:
                    png = compose(grab(page, base, it), it)
                    (SHARE / it['slug']).mkdir(exist_ok=True); (SHARE / it['slug'] / 'card.jpg').write_bytes(png)
                    MAN[it['slug']] = {'key': it['key']}; done += 1
                    print(f'rendered {it["slug"]} ({len(png) // 1024} KB)' + (f' page errors: {errs}' if errs else ''))
                except Exception as e:
                    print(f'WARNING: could not render {it["slug"]}: {e}')
                finally:
                    page.close()
            b.close()
    finally:
        srv.shutdown()
    live = {it['slug'] for it in ITEMS}
    MAN_P.write_text(json.dumps({k: v for k, v in sorted(MAN.items()) if k in live}, indent=1) + '\n')
    print(f'{done}/{len(work)} share cards rendered')

if __name__ == '__main__':
    main()
