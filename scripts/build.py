#!/usr/bin/env python3
"""Full Duplex static site build (Python 3 standard library only).

Sources: src/ (page bodies with a JSON <!--meta ... --> header), src/site.json, data/tracker.json.
Run from anywhere:  python3 scripts/build.py   then commit the output.
GitHub Pages serves the committed files from main; there is no CI step.

Generates: every HTML page, articles/index.html, tracker.html, tracker/<country>/index.html,
tracker/changes/index.html, search.html, 404.html, data/tracker.csv, data/tracker-changes.json,
search-index.json, sitemap.xml, robots.txt, feed.xml, launches/index.html (+ launches/cal/*.ics)
from data/launches.json (scripts/fetch_launches.py) and data/constellations.json.

The tracker change log is rebuilt from the git history of data/tracker.json when git is
available, and otherwise read back from data/tracker-changes.json.

IMAGES (approved by Sam, 9 Nov 2026): logo A (assets/logo.svg, inlined as LOGO_MARK), favicon A, home hero, article header plate,
tracker backdrop, sponsor plate and per-page OG share cards. Responsive files come from scripts/images.py (Pillow);
OG cards (assets/og/*.jpg) are generated here at build time when Pillow is installed, and kept as committed otherwise.
New artwork still needs Sam's approval of a preview before it goes on the site.
"""
import csv, html, io, json, math, pathlib, re, subprocess, sys, urllib.parse
from datetime import date, timedelta
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import satviz  # satellite illustrations + payload-card animations (preview, needs Sam's approval)
try:
    import images as IMGS  # needs Pillow; optional
except ImportError:
    IMGS = None

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'
SITE = json.loads((SRC / 'site.json').read_text())
BASE = SITE['base_url']
X = SITE['x_handle']
SUB = SITE['subscribe_url']
FORM = SITE['beehiiv_form']
MON = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split()
MONL = 'January February March April May June July August September October November December'.split()

def esc(t): return html.escape(str(t), quote=True)
def strip_tags(s): return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', re.sub(r'<(style|script)\b.*?</\1>', ' ', s, flags=re.S)))).strip()
def human(iso, long=True):
    y, m, d = map(int, iso.split('-')); return f"{d} {(MONL if long else MON)[m-1]} {y}"
def parse_human(t):
    d, m, y = t.split(); m = m[:3]; return f"{y}-{MON.index(m)+1:02d}-{int(d):02d}"
def rfc822(iso):
    y, m, d = map(int, iso.split('-')); return date(y, m, d).strftime('%a, ') + f"{d:02d} {MON[m-1]} {y} 08:00:00 +0000"
def slugify(t): return re.sub(r'[^a-z0-9]+', '-', t.lower()).strip('-')

def read_src(path):
    t = path.read_text()
    m = re.match(r'<!--meta\n(.*?)\n-->\n', t, re.S)
    meta = json.loads(m.group(1)); body = t[m.end():]
    scripts = ''
    if '<!--SCRIPTS-->' in body: body, scripts = body.split('<!--SCRIPTS-->', 1)
    return meta, body.strip(), scripts.strip()

def sub_url(surface):
    return SUB + '?' + urllib.parse.urlencode({'utm_source': 'fullduplex-site', 'utm_medium': surface, 'utm_campaign': 'signal'})
def share_url(text, url):
    return 'https://x.com/intent/post?' + urllib.parse.urlencode({'text': text, 'url': url, 'via': X})
def share_btn(text, url, label='Share on X'):
    return f'<a class="btn ghost" href="{esc(share_url(text, url))}" target=_blank rel=noopener>{label}</a>'
def follow_btn(cls='btn ghost'):
    return f'<a class="{cls}" href="https://x.com/{X}" target=_blank rel="noopener me">Follow @{X}</a>'

# ---------------------------------------------------------------- Signal blocks
def issues_list():
    li = ''.join(f'<li><a href="{esc(i["url"])}"><span class=ino>#{i["no"]}</span><span>{esc(i["title"])}</span></a></li>' for i in SITE['issues'][:3])
    return f'<ul class=issues aria-label="Recent issues of Signal">{li}</ul>'

def signal_block(root, surface, variant='full', heading_level=2, heading=None, intro=None):
    """The beehiiv embed loads lazily (assets/site.js) when the block nears the viewport;
    the button always works without it."""
    h = f'h{heading_level}'
    privacy = f'<p class=fine>Free. Your email is managed by beehiiv and used only to send Signal. Unsubscribe any time. <a href="{root}privacy.html">Privacy notice</a>.</p>'
    embed = f'<div class=bh-slot data-form="{FORM}" data-surface="{surface}"></div>'
    if variant == 'mid':
        return (f'<aside class="signal mid" aria-label="Subscribe to Signal"><p class=kicker>Signal · free weekly briefing</p>'
                f'<{h} class=signal-h>{heading or "Signal: the weekly direct-to-cell briefing from a mobile network insider with over 13 years in GSM"}</{h}>'
                f'{embed}<p class=signal-cta><a class=btn href="{esc(sub_url(surface))}">Send me Signal</a></p>{privacy}</aside>')
    return (f'<section class=signal aria-label="Subscribe to Signal"><div class=signal-copy><p class=kicker>Signal · free weekly briefing</p>'
            f'<{h} class=signal-h>{heading or "Get Signal: what changed in satellite-to-phone this week"}</{h}>'
            f'<p>{intro or "One email a week on direct-to-cell, mobile networks and what it means for you, from a mobile network insider with over 13 years in GSM."}</p>'
            f'<p class=issues-h>Recent issues</p>{issues_list()}</div><div class=signal-form>{embed}<p class=signal-cta><a class=btn href="{esc(sub_url(surface))}">Send me Signal</a> '
            f'<a class=more href="{esc(SITE["archive_url"])}">Read past issues</a></p>{privacy}</div></section>')

# ---------------------------------------------------------------- chrome
NAV = [('index.html', 'Home'), ('articles/index.html', 'Articles'), ('tracker.html', 'Tracker'), ('launches/index.html', 'Launches'), ('satellites/index.html', 'Satellites'), ('search.html', 'Search'), ('about.html', 'About'), ('sponsor.html', 'Sponsor')]

LOGO_MARK = ('<svg class=mark viewBox="254 250 516 516" width="44" height="44" aria-hidden="true" focusable="false">'
             '<g fill="none" stroke-width="32" stroke-linecap="round"><path d="M279 505A233 233 0 0 1 644.3 313.2" stroke="#00cfff"/><path d="M744.9 511.9A233 233 0 0 1 383.7 699.5" stroke="#fff"/></g><circle cx="423" cy="432" r="10" fill="#00cfff"/><path transform="translate(426 517.5) rotate(-15)" fill="#00cfff" fill-rule="evenodd" d="M-23.5 -57.5h47a5 5 0 0 1 5 5v105a5 5 0 0 1 -5 5h-47a5 5 0 0 1 -5 -5v-105a5 5 0 0 1 5 -5zM-8.5 -48h17.0a5.5 5.5 0 0 1 5.5 5.5v0.0a5.5 5.5 0 0 1 -5.5 5.5h-17.0a5.5 5.5 0 0 1 -5.5 -5.5v-0.0a5.5 5.5 0 0 1 5.5 -5.5z"/><g fill="#fff"><path d="M583 488h21l33 32-22 22-32-32z"/><path d="M620 492l20-21 15 14-21 22z"/><path d="M567 545l21-21 14 14-20 20z"/><circle cx="635" cy="541" r="8"/></g>' + '</svg>')  # logo A, approved by Sam 9 Nov 2026 (same as assets/logo.svg)

def header(root, current):
    links = ''.join(f'<a href="{root}{h}"{" aria-current=page" if h == current else ""}>{t}</a>' for h, t in NAV)
    return (f'<a class=skip href="#main">Skip to content</a><header class=site><div class=wrap><a class=logo href="{root}index.html">{LOGO_MARK}Full<span>Duplex</span></a>'
            f'<nav aria-label="Main">{links}</nav><div class=hdr-cta><a class=xlink href="https://x.com/{X}" target=_blank rel="noopener me">Follow @{X}</a>'
            f'<a class="btn pill" href="{esc(sub_url("header"))}">Subscribe</a></div></div></header>')

def footer(root, sticky=True):
    bar = (f'<div class=stickybar hidden role=region aria-label="Subscribe to Signal"><p><strong>Signal</strong> · the weekly direct-to-cell briefing</p>'
           f'<a class="btn pill" href="{esc(sub_url("sticky-bar"))}">Subscribe free</a><button class=x type=button aria-label="Dismiss">×</button></div>') if sticky else ''
    return (f'<footer class=site><div class=wrap><div><a class=logo href="{root}index.html">{LOGO_MARK}Full<span>Duplex</span></a><p>Independent analysis of satellite-to-phone and mobile networks. Made in the UK.</p>'
            f'<p class=copy>© 2026 Full Duplex.</p></div>'
            f'<nav aria-label="Footer"><a href="{esc(sub_url("footer"))}">Subscribe to Signal</a><a href="https://x.com/{X}" target=_blank rel="noopener me">Follow @{X} on X</a>'
            f'<a href="{root}articles/index.html">Articles</a><a href="{root}tracker.html">Tracker</a><a href="{root}tracker/changes/">Tracker changes</a><a href="{root}launches/">Launches</a><a href="{root}journey/">What happens when you hit send</a><a href="{root}satellites/">Meet the satellites</a><a href="{root}check/">Can my phone connect?</a><a href="{root}glossary/">Glossary</a>'
            f'<a href="{root}play/constellation.html">Constellation</a><a href="{root}search.html">Search</a><a href="{root}feed.xml">RSS</a>'
            f'<a href="{root}about.html">About</a><a href="{root}sponsor.html">Sponsor</a><a href="{root}privacy.html">Privacy</a></nav></div></footer>{bar}')

import hashlib
_AV = {}
def asset_v(rel):
    """Short content hash so browsers fetch new CSS/JS with new HTML (GitHub Pages caches for 10 minutes)."""
    # site.js lazy-loads assets/intro.js with its own ?v=, so its tag covers both files
    if rel not in _AV: _AV[rel] = hashlib.sha1(b''.join((ROOT / r).read_bytes() for r in ([rel, 'assets/intro.js'] if rel == 'assets/site.js' else [rel]) if (ROOT / r).exists())).hexdigest()[:8] if (ROOT / rel).exists() else '0'
    return _AV[rel]
# ---------------------------------------------------------------- hover/tap glossary (src/glossary.json; behaviour in assets/site.js)
GLOSS = json.loads((SRC / 'glossary.json').read_text())
GL_RX = [(t, re.compile('|'.join(t['match']))) for t in GLOSS['terms']]
GL_SKIP = {'a', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'button', 'script', 'style', 'svg', 'title', 'label', 'select', 'option', 'summary', 'code', 'abbr', 'dt', 'th', 'time', 'noscript', 'aside', 'nav', 'figcaption', 'blockquote'}
GL_VOID = {'br', 'img', 'input', 'meta', 'link', 'hr', 'source', 'wbr', 'col', 'area', 'path', 'circle', 'rect', 'line', 'ellipse', 'polygon', 'polyline', 'stop', 'use'}
_GLN = [0]
def gloss_tip(t, shown, root):
    _GLN[0] += 1; n = _GLN[0]
    return (f'<span class=gw><span class=gl role=button tabindex=0 aria-expanded=false aria-controls=gt{n} aria-describedby=gt{n}>{shown}</span>'
            f'<span class=gt id=gt{n}><b>{esc(t["term"])}</b> {esc(t["def"])} <a href="{root}glossary/#{t["id"]}">Glossary</a></span></span>')
def gloss_html(body, root, limit=14):
    """Wrap the first use of each glossary term in a tooltip, in running text only (never in links, headings, buttons, SVG or Signal blocks)."""
    used, out, stack = set(), [], []
    for tok in re.split(r'(<[^>]+>)', body):
        if tok.startswith('<'):
            m = re.match(r'<(/?)([a-zA-Z0-9]+)', tok)
            if m and not tok.startswith('<!'):
                name = m[2].lower(); closing = m[1] == '/'
                if closing:
                    while stack:
                        if stack.pop()[0] == name: break
                elif name not in GL_VOID and not tok.endswith('/>'):
                    skip = name in GL_SKIP or bool(re.search(r'class=["\']?(signal|sat-jump|row-cta|share-end|byline|crumbs|stats|kicker|sc-src|l-credit|pb-)', tok))
                    stack.append((name, skip))
            out.append(tok); continue
        if not tok.strip() or any(sk for _, sk in stack) or len(used) >= limit:
            out.append(tok); continue
        res, rest = '', tok
        while rest and len(used) < limit:
            best = None
            for t, rx in GL_RX:
                if t['id'] in used: continue
                mm = rx.search(rest)
                if mm and (best is None or mm.start() < best[1].start()): best = (t, mm)
            if not best: break
            t, mm = best; used.add(t['id'])
            res += rest[:mm.start()] + gloss_tip(t, mm[0], root); rest = rest[mm.end():]
        out.append(res + rest)
    return ''.join(out)

built = []  # (path, lastmod)
SEARCH = []

def page(*, path, title, description, body, root='', current='', og_type='website', jsonld=None, head_extra='', scripts='',
         viewport='width=device-width,initial-scale=1', sticky=True, full_title=None, lastmod=None, search=True, cls='', index=True, search_text=None, og=None, gloss=False):
    url = BASE + (path[:-len('index.html')] if path.endswith('index.html') else path)
    ft = full_title or f'{title} | Full Duplex'
    slug = 'home' if path == 'index.html' else re.sub(r'(/index)?\.html$', '', path).replace('/', '-')
    kicker, og_title, *og_more = og or ('Full Duplex', title)
    if not index: slug = 'home'
    elif IMGS: IMGS.og_card(ROOT / 'assets' / 'og' / f'{slug}.jpg', kicker, og_title, chips=og_more[0] if og_more else None)
    raw_body = body
    if gloss: body = gloss_html(body, root)
    og_img = f'{BASE}assets/og/{slug}.jpg'
    if index and not (ROOT / 'assets' / 'og' / f'{slug}.jpg').exists(): print('WARNING: missing OG card', slug, '(pip install pillow)')
    ld = ''.join(f'<script type="application/ld+json">{json.dumps(j, ensure_ascii=False)}</script>' for j in (jsonld or []))
    head = (f'<!doctype html><html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="{viewport}">'
            f'<title>{esc(ft)}</title><meta name="description" content="{esc(description)}"><link rel="canonical" href="{url}">'
            + ('' if index else '<meta name="robots" content="noindex">') +
            f'<link rel="icon" href="{root}assets/favicon-32.png" sizes="32x32" type="image/png"><link rel="icon" href="{root}assets/favicon.svg" sizes="any" type="image/svg+xml">'
            f'<link rel="apple-touch-icon" href="{root}assets/apple-touch-icon.png"><link rel="manifest" href="{root}site.webmanifest">'
            f'<link rel="preload" href="{root}assets/fonts/InterTight-600.woff2" as="font" type="font/woff2" crossorigin>'
            f'<link rel="preload" href="{root}assets/fonts/Newsreader-400.woff2" as="font" type="font/woff2" crossorigin><meta name="theme-color" content="#070b14"><meta name="color-scheme" content="dark">'
            f'<meta property="og:site_name" content="Full Duplex"><meta property="og:locale" content="en_GB"><meta property="og:type" content="{og_type}">'
            f'<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(description)}"><meta property="og:url" content="{url}">'
            f'<meta property="og:image" content="{og_img}"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">'
            f'<meta property="og:image:alt" content="{esc(og_title)} (Full Duplex)">'
            f'<meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="{og_img}"><meta name="twitter:image:alt" content="{esc(og_title)} (Full Duplex)"><meta name="twitter:site" content="@{X}"><meta name="twitter:title" content="{esc(title)}"><meta name="twitter:description" content="{esc(description)}">'
            f'<link rel="alternate" type="application/rss+xml" title="Full Duplex" href="{BASE}feed.xml">'
            f'<link rel="stylesheet" href="{root}style.css">'
            f'{head_extra}{ld}</head><body{" class=" + cls if cls else ""}>')
    out = (head + header(root, current) + f'<main id=main>{body}</main>' + footer(root, sticky)
           + f'<script src="{root}assets/site.js" defer></script>{scripts}</body></html>\n')
    out = re.sub(r'((?:href|src)="((?:\.\./)*)(style\.css|assets/[\w.-]+\.js))"', lambda m: f'{m[1]}?v={asset_v(m[3])}"', out)
    (ROOT / path).parent.mkdir(parents=True, exist_ok=True)
    (ROOT / path).write_text(out)
    if index: built.append((path, lastmod))
    if search: SEARCH.append({'t': title, 'u': path[:-len('index.html')] if path.endswith('index.html') else path, 'd': description, 'x': (search_text if search_text is not None else strip_tags(re.sub(r'<(aside|section) class=["]?signal.*?</\1>', ' ', raw_body, flags=re.S)))[:6000]})
    return url

PUBLISHER = {'@type': 'Organization', 'name': 'Full Duplex', 'url': BASE, 'sameAs': [f'https://x.com/{X}']}
AUTHOR = {'@type': 'Person', 'name': SITE['author'], 'url': BASE + 'about.html'}
def crumbs(items):
    return {'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
        {'@type': 'ListItem', 'position': i + 1, 'name': n, 'item': BASE + u} for i, (n, u) in enumerate(items)]}

# ---------------------------------------------------------------- tracker data
TRACK = json.loads((ROOT / 'data/tracker.json').read_text())
ROWS = TRACK['rows']
CLS = {'live': 'live', 'trial': 'trial', 'announced': 'ann'}
LABEL = {'live': 'Live', 'trial': 'Trial', 'announced': 'Announced'}
RANK = {'live': 3, 'trial': 2, 'announced': 1}
REGION = SITE['regions']
def provider(sat):
    for k, v in [('Starlink', 'Starlink'), ('AST', 'AST SpaceMobile'), ('Skylo', 'Skylo'), ('Lynk', 'Lynk / Elveo')]:
        if k in sat: return v
    return 'Other'
def region(r):
    if not r['iso_n3']: return 'Multi-country'
    if r['country'] not in REGION: print('WARNING: no region for', r['country'], '- add it to src/site.json regions')
    return REGION.get(r['country'], 'Other')
def country_slug(c): return slugify(c)
def the(c): return ('the ' + c) if c in ('United Kingdom', 'United States', 'Philippines') else c
COUNTRIES = {}
for r in ROWS:
    if r['iso_n3']: COUNTRIES.setdefault(r['country'], []).append(r)
def best(rows): return max((r['status'] for r in rows), key=lambda s: RANK[s])

def counts():
    c = {'live': 0, 'trial': 0, 'announced': 0}
    for r in ROWS: c[r['status']] += 1
    return c, len({r['country'] for r in ROWS if r['status'] == 'live' and r['iso_n3']}), len(COUNTRIES)
C, NLIVE_C, NCOUNTRIES = counts()

def pill(status): return f'<span class="spill s-{CLS[status]}">{LABEL[status]}</span>'
def sources_html(r): return ' · '.join(f"<a href='{s['url']}'>{s['label']}</a>" for s in r['sources'])

def stats_strip(root='', compact=False):
    items = [(C['live'], 'live services', 'live'), (NLIVE_C, 'countries with live service', 'live'), (C['trial'], 'trials', 'trial'), (C['announced'], 'announced', 'ann')]
    li = ''.join(f'<li class=s-{k}><b>{n}</b><span>{t}</span></li>' for n, t, k in items)
    return (f'<div class=stats><ul aria-label="Tracker totals">{li}</ul><p class=checked>From the <a href="{root}tracker.html">Full Duplex tracker</a>, last checked '
            f'<time datetime="{parse_human(TRACK["last_checked"])}">{TRACK["last_checked"]}</time>.</p></div>')

def tracker_table(root=''):
    head = "<thead><tr><th scope=col>Country</th><th scope=col>Operator partner</th><th scope=col>Satellite provider</th><th scope=col>Status</th><th scope=col>Services</th><th scope=col>Source</th><th scope=col>Last checked</th></tr></thead>"
    rows = []
    for r in ROWS:
        c = (f"<a href='{root}tracker/{country_slug(r['country'])}/'>{r['country']}</a>" if r['iso_n3'] else r['country'])
        rows.append(f"<tr data-status='{r['status']}' data-provider='{esc(provider(r['satellite']))}' data-region='{esc(region(r))}' data-checked='{parse_human(r['checked'])}' data-country='{esc(r['country'])}'>"
                    f"<td data-label='Country'>{c}</td><td data-label='Operator partner'>{r['operator']}</td>"
                    f"<td data-label='Satellite provider'>{r['satellite']}</td><td data-label='Status' class={CLS[r['status']]}>{r['status']}</td>"
                    f"<td data-label='Services'>{r['services']}</td><td data-label='Source'>{sources_html(r)}</td><td data-label='Last checked'>{r['checked']}</td></tr>")
    return ("<!-- TRACKER-TABLE:START (generated from data/tracker.json by scripts/build.py; do not edit by hand) -->"
            "<table id=tracker-table><caption class=sr>Direct-to-cell services by country</caption>" + head + '<tbody>' + ''.join(rows) + "</tbody></table><!-- TRACKER-TABLE:END -->")

# home globe dots (precomputed so the home page needs no map libraries)
sys.dont_write_bytecode = True; sys.path.insert(0, str(ROOT / 'scripts')); import globe_dots; globe_dots.build(ROOT)

# CSV
buf = io.StringIO(); w = csv.writer(buf, lineterminator='\n')
w.writerow(['country', 'iso_n3', 'region', 'operator', 'satellite_provider', 'provider_group', 'status', 'services', 'sources', 'last_checked'])
for r in ROWS:
    w.writerow([r['country'], r['iso_n3'] or '', region(r), r['operator'], r['satellite'], provider(r['satellite']), r['status'], r['services'],
                ' | '.join(s['url'] for s in r['sources']), parse_human(r['checked'])])
(ROOT / 'data/tracker.csv').write_text(buf.getvalue())

# change log from git history of data/tracker.json
def git(*a):
    return subprocess.run(['git', '-C', str(ROOT), *a], capture_output=True, text=True, check=True).stdout
def build_changes():
    try:
        log = [l.split() for l in git('log', '--reverse', '--format=%H %cI', '--', 'data/tracker.json').splitlines() if l.strip()]
    except Exception:
        return None
    versions = [(h, d[:10], json.loads(git('show', f'{h}:data/tracker.json'))['rows']) for h, d in log]
    try:
        cur = json.loads((ROOT / 'data/tracker.json').read_text())['rows']
        if not versions or cur != versions[-1][2]: versions.append(('working-tree', date.today().isoformat(), cur))
    except Exception: pass
    key = lambda r: (r['country'], r['operator'], r['satellite'])
    out = []; prev = None
    for h, d, rows in versions:
        k = {key(r): r for r in rows}
        if prev is None:
            out.append({'date': d, 'commit': h, 'items': [{'type': 'baseline', 'text': f'Tracker published with {len(rows)} entries.'}]})
        else:
            items = []
            for x in k:
                r = k[x]; label = f"{r['country']}: {r['operator']} + {r['satellite']}"
                if x not in prev: items.append({'type': 'added', 'status': r['status'], 'country': r['country'], 'text': f"Added {label} ({r['status']})."})
                elif prev[x]['status'] != r['status']: items.append({'type': 'status', 'status': r['status'], 'country': r['country'], 'text': f"{label}: {prev[x]['status']} → {r['status']}."})
                elif {a: b for a, b in prev[x].items() if a != 'checked'} != {a: b for a, b in r.items() if a != 'checked'}:
                    items.append({'type': 'updated', 'status': r['status'], 'country': r['country'], 'text': f"Updated details for {label}."})
            for x in prev:
                if x not in k: r = prev[x]; items.append({'type': 'removed', 'status': r['status'], 'country': r['country'], 'text': f"Removed {r['country']}: {r['operator']} + {r['satellite']}."})
            if items: out.append({'date': d, 'commit': h, 'items': items})
        prev = k
    return list(reversed(out))
CH_PATH = ROOT / 'data/tracker-changes.json'
CHANGES = build_changes()
if CHANGES is None: CHANGES = json.loads(CH_PATH.read_text()) if CH_PATH.exists() else []
else: CH_PATH.write_text(json.dumps(CHANGES, ensure_ascii=False, indent=1) + '\n')

def change_list(entries, root='', limit=None):
    out = []; n = 0
    for e in entries:
        lis = ''
        for it in e['items']:
            if limit and n >= limit: break
            tag = {'added': 'Added', 'status': 'Status', 'updated': 'Updated', 'removed': 'Removed', 'baseline': 'Launch'}[it['type']]
            c = it.get('country')
            txt = esc(it['text'])
            if c in COUNTRIES: txt = txt.replace(esc(c), f'<a href="{root}tracker/{country_slug(c)}/">{esc(c)}</a>', 1)
            lis += f'<li><span class="tag t-{it["type"]}">{tag}</span> {txt}</li>'; n += 1
        if lis: out.append(f'<li class=chg><time datetime="{e["date"]}">{human(e["date"], False)}</time><ul>{lis}</ul></li>')
        if limit and n >= limit: break
    return f'<ol class=changes>{"".join(out)}</ol>'


# ---------------------------------------------------------------- quick wins (13 Nov 2026 preview): race leaderboard, phone checker, glossary page
OGC = {'live': '#6ee79a', 'trial': '#f5c26b', 'announced': '#7f93a8', 'cyan': '#5ec8ff', 'muted': '#9fb0c3'}
def short_op(o): return re.split(r'\s*[(;]', o)[0].strip()
def status_chips(rs, n=4): return [(f'{short_op(r["operator"])} · {LABEL[r["status"]]}', OGC[r['status']]) for r in sorted(rs, key=lambda r: -RANK[r['status']])[:n]]
_J = {}
def jdata(rel):
    if rel not in _J: _J[rel] = json.loads((ROOT / rel).read_text()) if (ROOT / rel).exists() else None
    return _J[rel]
BOARD = [  # (label, tracker provider, constellations.json id, race.json series id, colour)
    ('Starlink Direct to Cell', 'Starlink', 'starlink-dtc', 'starlink-dtc', '#00cfff'),
    ('AST SpaceMobile', 'AST SpaceMobile', 'ast', 'ast', '#ff9a3c'),
    ('Skylo', 'Skylo', 'skylo', None, '#8fdbff'),
    ('Lynk / Elveo', 'Lynk / Elveo', 'lynk', 'lynk', '#6ee79a'),
    ('Globalstar (Apple)', None, 'globalstar', 'globalstar', '#b58cff')]
def board_rows():
    const = jdata('data/constellations.json'); race = jdata('data/race.json')
    ci = {i['id']: i for i in const['direct_to_device'] + const['broadband_only']}
    fr = race['frames'] if race else []
    prev = next((f for f in reversed(fr) if not f.get('final')), None); last = fr[-1] if fr else None
    week = (BUILD_DAY - timedelta(days=7)).isoformat()
    out = []
    for label, prov, cid, rid, col in BOARD:
        rs = [r for r in ROWS if prov and provider(r['satellite']) == prov]
        n = {st: sum(1 for r in rs if r['status'] == st) for st in RANK}
        live_c = sorted({r['country'] for r in rs if r['status'] == 'live' and r['iso_n3']})
        multi = [r for r in rs if not r['iso_n3'] and r['status'] == 'live']
        multi_n = sum(int(m[1]) for r in multi for m in [re.match(r'(\d+)', r['country'])] if m)
        ch = sum(1 for e in CHANGES if e['date'] >= week for it in e['items'] if prov and provider(it['text']) == prov)
        c = ci.get(cid); d = None
        if rid and prev and last and rid in last['v'] and rid in prev['v']: d = (last['v'][rid] - prev['v'][rid], prev['d'])
        out.append({'label': label, 'prov': prov, 'col': col, 'n': n, 'live_c': live_c, 'multi_n': multi_n, 'changes': ch, 'const': c, 'delta': d,
                    'key': (n['live'], len(live_c) + multi_n, n['trial'], n['announced'], (c or {}).get('count') or 0)})
    out.sort(key=lambda x: x['key'], reverse=True)
    return out
def country_board(k=6):
    sc = sorted(COUNTRIES.items(), key=lambda kv: (-sum(r['status'] == 'live' for r in kv[1]), -sum(r['status'] == 'trial' for r in kv[1]), -len(kv[1]), kv[0]))
    return sc[:k]
def race_board(root, compact=False):
    """'This week in the race': ranked from data/tracker.json, data/constellations.json, data/race.json and the tracker change log. No numbers of our own."""
    rows = board_rows(); const = jdata('data/constellations.json')
    tr = []
    for i, x in enumerate(rows, 1):
        c = x['const']
        if c and c.get('count') is not None:
            sat = (f'<b>{c["count"]:,}</b><a class=lb-src href="{esc(c["source"]["url"])}" title="{esc(c["source"]["label"])}, as of {human(c["as_of"])}">source</a>')
            if x['delta'] and not compact:
                dv, dd = x['delta']; sat += f'<span class="lb-d{" up" if dv > 0 else " dn" if dv < 0 else ""}">{"+" if dv > 0 else ""}{dv} since {human(dd, False)}</span>'
        else:
            sat = f'<span class=lb-na>{"Not disclosed" if c else "n/a"}</span>' + (f'<a class=lb-src href="{esc(c["source"]["url"])}">source</a>' if c and c.get('source') else '')
        if x['prov']:
            cn = f'<b>{len(x["live_c"])}</b>' + (f'<span class=lb-m>+{x["multi_n"]} via partners</span>' if x['multi_n'] else '')
            live = f'<b>{x["n"]["live"]}</b>'; tri = f'{x["n"]["trial"]}'; ann = f'{x["n"]["announced"]}'
            wk = f'{x["changes"]} update{"s" if x["changes"] != 1 else ""}' if x['changes'] else '<span class=lb-na>None</span>'
        else:
            cn = live = tri = ann = '<span class=lb-na>n/a</span>'; wk = '<span class=lb-na>Apple only</span>'
        cells = (f'<td data-l="Live services">{live}</td><td data-l="Countries live">{cn}</td>'
                 + ('' if compact else f'<td data-l="Trials">{tri}</td><td data-l="Announced">{ann}</td>')
                 + f'<td data-l="Phone satellites in orbit">{sat}</td>' + ('' if compact else f'<td data-l="Tracker updates, last 7 days">{wk}</td>'))
        tr.append(f'<tr style="--c:{x["col"]}"><td class=lb-rank>{i}</td><th scope=row><i aria-hidden=true></i>{esc(x["label"])}</th>{cells}</tr>')
    head = ('<tr><th scope=col><span class=sr>Rank</span>#</th><th scope=col>Provider</th><th scope=col>Live services</th><th scope=col>Countries live</th>'
            + ('' if compact else '<th scope=col>Trials</th><th scope=col>Announced</th>') + '<th scope=col>Phone satellites in orbit</th>'
            + ('' if compact else '<th scope=col>Tracker updates, last 7 days</th>') + '</tr>')
    cb = ''.join(f'<li><a href="{root}tracker/{country_slug(c)}/"><span class=lb-cn>{esc(c)}</span><span class=lb-ops>'
                 + ' '.join(f'<span class="spill s-{CLS[r["status"]]}" title="{esc(r["operator"])} with {esc(r["satellite"])}">{esc(short_op(r["operator"]))}</span>' for r in sorted(rs, key=lambda r: -RANK[r['status']]))
                 + '</span></a></li>' for c, rs in country_board(4 if compact else 6))
    note = ('Ranked by live services, then countries with a live service, trials, announced deals and satellites in orbit. '
            f'Services and countries come from our <a href="{root}tracker.html">tracker</a> (last checked {TRACK["last_checked"]}); satellite counts from the '
            f'<a href="{root}launches/#cnt-h">launch tracker</a> (checked {human(const["last_checked"])}), each linked to its source. '
            'Skylo’s “via partners” figure is the 41-country row in the tracker. Globalstar works through Apple’s own iPhone features rather than operator deals, so it has no tracker rows.')
    if compact: note = (f'Ranked by live services, then countries live. From our <a href="{root}tracker.html">tracker</a> ({TRACK["last_checked"]}) and the '
                        f'<a href="{root}launches/#cnt-h">launch tracker</a> ({human(const["last_checked"])}), sources linked. <a href="{root}tracker.html#lb-h">Full leaderboard</a>.')
    return (f'<section class="lboard{" compact" if compact else ""}" aria-labelledby=lb-h><div class=lb-top><div><p class=kicker>This week in the race · as of {human(BUILD_DAY.isoformat())}</p>'
            f'<h2 id=lb-h>{"Who’s winning satellite-to-phone" if compact else "The race leaderboard"}</h2></div>'
            + ('' if compact else share_btn('Who’s winning satellite-to-phone this week? The Full Duplex race leaderboard, with sources.', BASE + 'tracker.html#lb-h'))
            + f'</div><div class=lb-grid><div class="tablewrap lbwrap"><table class=lb-table><thead>{head}</thead><tbody>{"".join(tr)}</tbody></table></div>'
            f'<div class=lb-countries><h3>Most connected countries</h3><ol>{cb}</ol></div></div><p class=l-credit>{note}</p></section>')
BUILD_DAY = date.today()

# ---------------------------------------------------------------- articles
arts = []
for slug in SITE['article_order']:
    meta, body, _ = read_src(SRC / 'articles' / f'{slug}.html'); meta['body'] = body; arts.append(meta)
def reading_time(body): return max(1, math.ceil(len(strip_tags(body).split()) / 230))
def insert_mid(body, block):
    hs = [m.start() for m in re.finditer(r'<h2[ >]', body)]
    return body[:hs[1]] + block + body[hs[1]:] if len(hs) >= 2 else body + block
def art_meta(a):
    return f'<p class=meta><time datetime="{a["published"]}">{human(a["published"], False)}</time> · {reading_time(a["body"])} min read</p>'
def art_card(a, root='', level=3, cls='card'):
    inner = (f'<h{level}><a href="{root}articles/{a["slug"]}.html">{esc(a["title"])}</a></h{level}>'
             f'<p>{esc(a["summary"])}</p>{art_meta(a)}')
    if 'feature' not in cls.split():
        return f'<article class="{cls}">{inner}</article>'
    # Lead card: approved article plate as a cover background, with a dark fade so the type stays readable.
    href = f'{root}articles/{a["slug"]}.html'
    img = (f'<img class="feature-img" src="{root}assets/img/article-plate-1280.webp" '
           f'srcset="{root}assets/img/article-plate-640.webp 640w, {root}assets/img/article-plate-960.webp 960w, {root}assets/img/article-plate-1280.webp 1280w" '
           f'sizes="(min-width:900px) 50vw, 100vw" width="1280" height="512" alt="" decoding="async" loading="lazy">')
    copy = f'<h{level}>{esc(a["title"])}</h{level}><p>{esc(a["summary"])}</p>{art_meta(a)}'
    return f'<article class="{cls}"><a href="{href}">{img}<div class="feature-copy">{copy}</div></a></article>'
def mentions(a, country):
    alias = {'United Kingdom': r'\b(UK|United Kingdom|Britain)\b', 'United States': r'\b(US|USA|United States|America)\b'}
    return re.search(alias.get(country, r'\b' + re.escape(country) + r'\b'), strip_tags(a['body']))

for i, a in enumerate(arts):
    path = f"articles/{a['slug']}.html"; url = BASE + path; root = '../'
    dates = f"<time datetime=\"{a['published']}\">{human(a['published'])}</time>"
    if a.get('updated'): dates += f" · Updated <time datetime=\"{a['updated']}\">{human(a['updated'])}</time>"
    related = [b for b in arts if b is not a][:3] if i else arts[1:4]
    body = (f'<article class=post><header class=art-head><p class=kicker><a href="{root}articles/index.html">Analysis</a></p><h1>{esc(a["title"])}</h1>'
            f'<p class=dek>{esc(a["summary"])}</p>'
            f'<div class=byline><p>By <a href="{root}about.html">{esc(SITE["author"])}</a> · {dates} · {reading_time(a["body"])} min read</p>{share_btn(a["title"], url)}</div></header>'
            f'<figure class=art-plate><img src="{root}assets/img/article-plate-1280.webp" srcset="{root}assets/img/article-plate-640.webp 640w, {root}assets/img/article-plate-960.webp 960w, {root}assets/img/article-plate-1280.webp 1280w" sizes="(min-width:860px) 820px, 100vw" width="1280" height="512" alt="" decoding="async" fetchpriority="high"></figure>'
            f'<div class=prose>' + insert_mid(a['body'], signal_block(root, 'mid-article', 'mid')) + '</div>'
            f'<div class=share-end><p>Found this useful? Share it, or follow us for daily updates.</p>{share_btn(a["title"], url)}{follow_btn()}</div></article>'
            + signal_block(root, 'end-article')
            + f'<section class=related aria-labelledby=rel-h><h2 id=rel-h>Keep reading</h2><div class=grid3>{"".join(art_card(b, root) for b in related)}</div></section>')
    ld = [{'@context': 'https://schema.org', '@type': 'NewsArticle', 'headline': a['title'], 'description': a['description'],
           'datePublished': a['published'], 'dateModified': a.get('updated', a['published']), 'author': AUTHOR,
           'publisher': PUBLISHER, 'mainEntityOfPage': url, 'inLanguage': 'en-GB', 'image': [f"{BASE}assets/og/articles-{a['slug']}.jpg"]},
          crumbs([('Home', ''), ('Articles', 'articles/'), (a['title'], path)])]
    page(path=path, title=a['title'], description=a['description'], body=body, root=root, og_type='article', jsonld=ld, current='articles/index.html',
         full_title=f"{a['short_title']} | Full Duplex", lastmod=a.get('updated', a['published']), cls='is-article', search_text=strip_tags(a['body']), og=('Analysis', a['title'], [(f'By {SITE["author"]}', OGC['cyan']), (f'{reading_time(a["body"])} min read', OGC['muted'])]), gloss=True,
         head_extra=f'<meta property="article:published_time" content="{a["published"]}"><meta property="article:author" content="{esc(SITE["author"])}">')

# articles index
body = (f'<header class=page-head><p class=kicker>Analysis</p><h1>Articles</h1><p class=lede>Plain-English analysis of direct-to-cell, satellite-to-phone and mobile networks, from a mobile network insider with over 13 years in GSM.</p></header>'
        f'<div class=grid3>{"".join(art_card(a, "../", 2) for a in arts)}</div>' + signal_block('../', 'articles-index'))
page(og=('Analysis', 'All articles'), path='articles/index.html', title='Articles', description='All Full Duplex analysis: direct-to-cell, satellite-to-phone, 2G/3G switch-off, MVNOs and the future of mobile networks.',
     body=body, root='../', current='articles/index.html', lastmod=max(a.get('updated', a['published']) for a in arts), search=False)

# ---------------------------------------------------------------- simple pages
for p in ['about', 'sponsor', 'privacy']:
    meta, body, scripts = read_src(SRC / 'pages' / f'{p}.html')
    body = f'<div class=prose-page>{body}</div>'
    if p == 'about': body += f'<p class=follow-row>{follow_btn()}</p>' + signal_block('', 'about')
    if p == 'sponsor': body += signal_block('', 'sponsor', heading='See the newsletter sponsors would appear in')
    page(path=f'{p}.html', title=meta['title'], description=meta['description'], body=body, current=f'{p}.html', sticky=(p != 'privacy'), search_text=strip_tags(read_src(SRC / 'pages' / f'{p}.html')[1]))

meta, body, scripts = read_src(SRC / 'pages' / 'constellation.html')
body = body + f'<div class=share-end><p>Beat your score? Challenge someone.</p>{share_btn("I just played Constellation: deploy direct-to-cell satellites before time runs out.", BASE + "play/constellation.html", "Share the game on X")}{follow_btn()}</div>' + signal_block('../', 'game')
page(og=('Play', 'Constellation: deploy direct-to-cell satellites'), path='play/constellation.html', title=meta['title'], description=meta['description'], body=body, root='../', cls='is-game',
     head_extra=meta['head_extra'], scripts=scripts, viewport=meta['viewport'], full_title='Constellation — deploy D2C satellites | Full Duplex')

# ---------------------------------------------------------------- tracker
meta, tbody, tscripts = read_src(SRC / 'pages' / 'tracker.html')
provs = sorted({provider(r['satellite']) for r in ROWS}); regs = sorted({region(r) for r in ROWS})
opts = lambda xs: ''.join(f'<option>{esc(x)}</option>' for x in xs)
controls = (f'<div class=filters role=search aria-label="Filter the tracker"><div class=f-row><label class=f-search><span class=sr>Search countries and operators</span>'
            f'<input id=t-q type=search placeholder="Search a country or operator" autocomplete=off></label>'
            f'<div class=chips role=group aria-label="Status"><button type=button class=chip data-status=all aria-pressed=true>All</button>'
            f'<button type=button class="chip c-live" data-status=live aria-pressed=false>Live</button><button type=button class="chip c-trial" data-status=trial aria-pressed=false>Trial</button>'
            f'<button type=button class="chip c-ann" data-status=announced aria-pressed=false>Announced</button></div></div>'
            f'<div class=f-row><label>Provider <select id=t-prov><option value="">All</option>{opts(provs)}</select></label>'
            f'<label>Region <select id=t-reg><option value="">All</option>{opts(regs)}</select></label>'
            f'<label>Sort <select id=t-sort><option value=default>Tracker order</option><option value=country>Country A–Z</option><option value=checked>Last checked</option><option value=status>Status</option></select></label>'
            f'<p id=t-count class=t-count role=status aria-live=polite>{len(ROWS)} entries</p></div></div>')
country_links = ''.join(f'<a class="cc s-{CLS[best(rs)]}" href="tracker/{country_slug(c)}/">{esc(c)}</a>' for c, rs in sorted(COUNTRIES.items()))
tools = (f'<div class=t-tools><a class="btn ghost" href="data/tracker.csv" download>Download CSV</a><a class="btn ghost" href="data/tracker.json">JSON</a>'
         + share_btn(f"Direct-to-cell tracker: {C['live']} live services, {C['trial']} trials, {C['announced']} announced. Country by country, with sources.", BASE + 'tracker.html') +
         f'</div><p class=cite><strong>Cite this tracker:</strong> Full Duplex, “Direct-to-cell tracker”, last checked {TRACK["last_checked"]}, {BASE}tracker.html</p>')
tbody = tbody.replace('<!--TRACKER-TABLE-->', tracker_table())
tbody = re.sub(r'<span id=tracker-checked>.*?</span>', f"<span id=tracker-checked>{TRACK['last_checked']}</span>", tbody)
# hero + stats before the intro; filters before the table; extras after
tbody = tbody.replace('<h1>Direct-to-cell around the world</h1>', '<header class=page-head><p class=kicker>Tracker</p><h1>Direct-to-cell around the world</h1></header>' + stats_strip() + race_board(''), 1)
tbody = tbody.replace('<div class=tablewrap>', f'<section aria-labelledby=tbl-h><h2 id=tbl-h>Every tracked service</h2>{controls}{tools}<div class=tablewrap>', 1)
tbody = tbody.replace('</div><p class=note>Spotted a change?', '</div></section><p class=note>Spotted a change?', 1)
tbody += (f'<section aria-labelledby=bc-h><h2 id=bc-h>Browse by country</h2><div class=cclist>{country_links}</div></section>'
          f'<p class=note>Next satellites going up: see the <a href="launches/">launch tracker</a> for upcoming SpaceX, AST SpaceMobile and other direct-to-cell launches, and how many phone-capable satellites each operator has in orbit.</p>'
          f'<section aria-labelledby=ch-h><h2 id=ch-h>What changed</h2>{change_list(CHANGES, "", 8)}<p><a href="tracker/changes/">Full change log</a></p></section>'
          + signal_block('', 'tracker', heading='Get tracker updates in Signal', intro='Every week, Signal covers what changed in the tracker: new launches, trials and status changes, with the sources.'))
ld = [{'@context': 'https://schema.org', '@type': 'Dataset', 'name': 'Full Duplex direct-to-cell tracker', 'description': meta['description'],
       'url': BASE + 'tracker.html', 'creator': PUBLISHER, 'isAccessibleForFree': True, 'inLanguage': 'en-GB', 'dateModified': parse_human(TRACK['last_checked']),
       'distribution': [{'@type': 'DataDownload', 'encodingFormat': 'text/csv', 'contentUrl': BASE + 'data/tracker.csv'},
                        {'@type': 'DataDownload', 'encodingFormat': 'application/json', 'contentUrl': BASE + 'data/tracker.json'}]}]
page(og=('Tracker', 'Direct-to-cell around the world', [(f"{C['live']} live", OGC['live']), (f"{C['trial']} trials", OGC['trial']), (f"{C['announced']} announced", OGC['announced']), (f'{NLIVE_C} countries live', OGC['cyan'])]), path='tracker.html', title=meta['title'], description=meta['description'], body=tbody, current='tracker.html', cls='is-tracker',
     head_extra=meta['head_extra'] + '<link rel="preload" as="image" href="assets/img/tracker-map-640.webp" media="(max-width:699px)"><link rel="preload" as="image" href="assets/img/tracker-map-1280.webp" media="(min-width:700px)">', scripts=tscripts + '<script defer src="assets/tracker-filters.js"></script>', jsonld=ld, lastmod=parse_human(TRACK['last_checked']),
     search_text=meta['description'] + ' ' + ' '.join(f"{r['country']} {r['operator']} {r['satellite']} {r['status']}. {strip_tags(r['services'])}." for r in ROWS))

# country pages
for c, rs in sorted(COUNTRIES.items()):
    slug = country_slug(c); path = f'tracker/{slug}/index.html'; root = '../../'
    b = best(rs); n = {s: sum(1 for r in rs if r['status'] == s) for s in RANK}
    parts = ', '.join(f"{n[s]} {s}" for s in ['live', 'trial', 'announced'] if n[s])
    checked = max(parse_human(r['checked']) for r in rs)
    ops = '; '.join(f"{r['operator']} with {r['satellite']} ({r['status']})" for r in rs)
    desc = f"Satellite-to-phone in {the(c)}: {ops}. Status, services and sources, last checked {human(checked)}."
    if len(desc) > 200: desc = f"Satellite-to-phone in {the(c)}: {len(rs)} direct-to-cell partnerships tracked ({parts}). Status, services and sources, last checked {human(checked)}."
    cards = ''.join(f'<article class="card op"><div class=op-head><h2>{r["operator"]} <span class=plus>+</span> {r["satellite"]}</h2>{pill(r["status"])}</div>'
                    f'<p>{r["services"]}</p><p class=meta>Source: {sources_html(r)} · Last checked {r["checked"]}</p></article>' for r in rs)
    rel = [a for a in arts if mentions(a, c)][:3]
    relh = f'<section aria-labelledby=rel-h><h2 id=rel-h>Related analysis</h2><div class=grid3>{"".join(art_card(a, root) for a in rel)}</div></section>' if rel else ''
    chg = [{'date': e['date'], 'items': [it for it in e['items'] if it.get('country') == c]} for e in CHANGES]
    chg = [e for e in chg if e['items']]
    chh = f'<section aria-labelledby=ch-h><h2 id=ch-h>Changes for {esc(c)}</h2>{change_list(chg, root)}</section>' if chg else ''
    body = (f'<nav class=crumbs aria-label=Breadcrumb><a href="{root}tracker.html">Tracker</a> <span aria-hidden=true>/</span> <span aria-current=page>{esc(c)}</span></nav>'
            f'<header class=page-head><p class=kicker>{esc(REGION.get(c, ""))} · {pill(b)}</p><h1>Satellite-to-phone in {esc(the(c))}</h1>'
            f'<p class=lede>{len(rs)} direct-to-cell partnership{"s" if len(rs) > 1 else ""} tracked in {esc(the(c))}: {parts}. Last checked {human(checked)}.</p>'
            f'<p class=row-cta>{share_btn(f"Satellite-to-phone in {the(c)}: who is live, trialling or announced, with sources.", BASE + path[:-10])}<a class="btn ghost" href="{root}tracker.html">All countries</a></p></header>'
            f'{cards}<p class=note>Status reflects what the source says on the date checked. Multi-country services such as Skylo are listed on the <a href="{root}tracker.html">main tracker</a>.</p>'
            f'{chh}{relh}' + signal_block(root, 'tracker-country', heading=f'Get {esc(the(c))} updates in Signal', intro='Signal covers new launches, trials and status changes every week, with the sources.'))
    ld = [crumbs([('Tracker', 'tracker.html'), (c, path[:-10])])]
    page(og=('Tracker', f'Satellite-to-phone in {the(c)}', status_chips(rs)), path=path, title=f'Satellite-to-phone in {the(c)}', description=desc, body=body, root=root, current='tracker.html', jsonld=ld, lastmod=checked,
         search_text=' '.join(f"{r['operator']} with {r['satellite']}: {r['status']}. {strip_tags(r['services'])}." for r in rs))

# change log page
body = (f'<nav class=crumbs aria-label=Breadcrumb><a href="../../tracker.html">Tracker</a> <span aria-hidden=true>/</span> <span aria-current=page>Changes</span></nav>'
        f'<header class=page-head><p class=kicker>Tracker</p><h1>Tracker change log</h1><p class=lede>Every change to the direct-to-cell tracker, newest first. Generated from the tracker data’s history.</p></header>'
        + change_list(CHANGES, '../../') + signal_block('../../', 'tracker-changes', heading='Get tracker changes in Signal', intro='Signal rounds up what changed in the tracker every week.'))
page(og=('Tracker', 'Tracker change log'), path='tracker/changes/index.html', title='Tracker change log', description='Every change to the Full Duplex direct-to-cell tracker: new launches, trials and status changes, newest first.',
     body=body, root='../../', current='tracker.html', lastmod=CHANGES[0]['date'] if CHANGES else None,
     search_text=' '.join(it['text'] for e in CHANGES for it in e['items']))

# ---------------------------------------------------------------- launches (data/launches.json from scripts/fetch_launches.py)
from datetime import datetime, timezone, timedelta
LDATA = json.loads((ROOT / 'data/launches.json').read_text()) if (ROOT / 'data/launches.json').exists() else {'fetched_at': None, 'launches': []}
CONST = json.loads((ROOT / 'data/constellations.json').read_text())
SATS = json.loads((SRC / 'satellites.json').read_text())  # /satellites/ content + payload-card stats
LTAGS = json.loads((ROOT / 'data/launch-tags.json').read_text()).get('overrides', {}) if (ROOT / 'data/launch-tags.json').exists() else {}
def iso_dt(s): return datetime.fromisoformat(s.replace('Z', '+00:00'))
BUILD_NOW = datetime.now(timezone.utc)
TAG = {  # label, css class, why it matters for your phone (plain English, no hype)
    'starlink-dtc': ('Starlink Direct to Cell', 'dtc', 'Adds satellites that talk straight to ordinary phones through partner networks such as T-Mobile and One NZ. More of them means more frequent passes overhead and fewer gaps for texts and app data where there’s no signal.'),
    'starlink': ('Starlink', 'sl', 'These serve Starlink dishes, not phones directly. More of them mainly adds broadband capacity, including links some mobile networks use to connect remote masts.'),
    'ast': ('AST SpaceMobile', 'ast', 'Each BlueBird adds coverage for AST’s partner networks, such as AT&T, Verizon and Vodafone. AST says it needs about 45 in orbit before service moves beyond intermittent coverage.'),
    'amazon-leo': ('Amazon Leo · broadband', 'leo', 'Amazon Leo is broadband for dishes, not phones. It matters to telcos as a rival to Starlink for backhaul and business links, not as a phone-to-satellite service.'),
    'd2d-other': ('Other direct-to-device', 'd2d', 'Another phone-to-satellite network. Whether your phone can use it depends on your handset and your mobile operator’s deals.'),
    'other': ('Other', 'oth', 'Not a phone-satellite launch. Listed so you can see everything SpaceX and its rivals are flying.'),
}
WHO = [('all', 'All'), ('phone', 'Phone satellites'), ('spacex', 'SpaceX'), ('ast', 'AST SpaceMobile'), ('amazon-leo', 'Amazon Leo'), ('lynk', 'Lynk / Elveo'), ('others', 'Others')]
EMPTY = {'lynk': 'No Lynk or Elveo launches are listed right now. Elveo says it will start launching its new satellites in Q4 2027.'}
def ltext(l): return ' '.join(str(l.get(k) or '') for k in ('name', 'mission', 'mission_description'))
def classify(l):
    if l['id'] in LTAGS: return LTAGS[l['id']]['tag']
    t = ltext(l)
    if re.search(r'BlueBird|AST SpaceMobile', t): return 'ast'
    if re.search(r'Amazon Leo|Kuiper', t): return 'amazon-leo'
    if re.search(r'\bLynk\b|Elveo|Omnispace|Globalstar', t): return 'd2d-other'
    if re.search(r'Starlink', l['name'] + ' ' + (l.get('mission') or '')):
        # Direct to Cell only when the source text says so (or a sourced override in data/launch-tags.json)
        return 'starlink-dtc' if re.search(r'direct[- ]to[- ]cell|\bDTC\b|direct[- ]to[- ]cell', t, re.I) else 'starlink'
    return 'other'
def who(l, tag):
    w = []
    if l.get('provider') == 'SpaceX' or tag in ('starlink', 'starlink-dtc'): w.append('spacex')
    if tag == 'ast': w.append('ast')
    if tag == 'amazon-leo': w.append('amazon-leo')
    if re.search(r'\bLynk\b|Elveo|Omnispace', ltext(l)): w.append('lynk')
    if tag in ('starlink-dtc', 'ast', 'd2d-other'): w.append('phone')
    if (tag == 'd2d-other' and 'lynk' not in w) or (tag == 'other' and l.get('provider') != 'SpaceX'): w.append('others')
    return w
PRECISE = ('Second', 'Minute', 'Hour')
def when_text(l):
    p = l['precision']; d = iso_dt(l['net'])
    if p in ('Second', 'Minute'): return d.strftime('%a %-d %b %Y, %H:%M UTC')
    if p == 'Hour': return d.strftime('%a %-d %b %Y, about %H:00 UTC')
    if p == 'Day': return d.strftime('%a %-d %b %Y') + ' · time not set'
    if p == 'Month': return d.strftime('%B %Y') + ' · date not set'
    if p == 'Week': return 'Week of ' + d.strftime('%-d %b %Y')
    m = re.match(r'Quarter (\d)', p)
    if m: return f'Q{m.group(1)} {d.year} · date not set'
    m = re.match(r'Half (\d)', p)
    if m: return f'H{m.group(1)} {d.year} · date not set'
    if p.startswith('Year'): return f'{d.year} · date not set'
    return 'No earlier than ' + d.strftime('%-d %b %Y')
def ics_name(l): return f"{(l.get('slug') or slugify(l['name']))[:70]}-{l['id'][:8]}.ics"
def ics(l, tag):
    d = iso_dt(l['net']); stamp = (LDATA.get('fetched_at') or BUILD_NOW.strftime('%Y-%m-%dT%H:%M:%SZ')).replace('-', '').replace(':', '')
    why = TAG[tag][2]
    lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Full Duplex//Launch tracker//EN', 'CALSCALE:GREGORIAN', 'METHOD:PUBLISH', 'BEGIN:VEVENT',
             f"UID:{l['id']}@fullduplex", f'DTSTAMP:{stamp}']
    if l['precision'] in PRECISE:
        end = iso_dt(l['window_end']) if l.get('window_end') and iso_dt(l['window_end']) > d else d + timedelta(hours=1)
        lines += [f"DTSTART:{d.strftime('%Y%m%dT%H%M%SZ')}", f"DTEND:{end.strftime('%Y%m%dT%H%M%SZ')}"]
    else:
        lines += [f"DTSTART;VALUE=DATE:{d.strftime('%Y%m%d')}", f"DTEND;VALUE=DATE:{(d + timedelta(days=1)).strftime('%Y%m%d')}"]
    def ical_esc(s): return s.replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,').replace('\n', '\\n')
    desc = f"{l.get('rocket')} from {l.get('pad')}, {l.get('location')}. {TAG[tag][0]}: {why} Launch times move: check {BASE}launches/ before you watch."
    lines += ['SUMMARY:' + ical_esc(f"Launch: {l.get('mission') or l['name']} ({l.get('rocket')})"), 'DESCRIPTION:' + ical_esc(desc),
              'LOCATION:' + ical_esc(f"{l.get('pad')}, {l.get('location')}"), f'URL:{BASE}launches/', 'END:VEVENT', 'END:VCALENDAR']
    out = []
    for ln in lines:  # fold at 75 octets
        b = ln.encode()
        while len(b) > 74:
            cut = 74
            while (b[cut] & 0xC0) == 0x80: cut -= 1
            out.append(b[:cut].decode()); b = b' ' + b[cut:]
        out.append(b.decode())
    return '\r\n'.join(out) + '\r\n'

# keep launches that haven't happened yet at build time (allow 3 h for a launch window in progress)
UPCOMING = []
for l in LDATA['launches']:
    if iso_dt(l['net']) < BUILD_NOW - timedelta(hours=3) and l['precision'] in PRECISE + ('Day',): continue
    tag = classify(l); UPCOMING.append(dict(l, tag=tag, who=who(l, tag)))
CAL = ROOT / 'launches' / 'cal'; CAL.mkdir(parents=True, exist_ok=True)
for f in CAL.glob('*.ics'): f.unlink()
for l in UPCOMING:
    if l['precision'] in PRECISE + ('Day',): (CAL / ics_name(l)).write_bytes(ics(l, l['tag']).encode())
def tag_pill(tag): return f'<span class="ltag l-{TAG[tag][1]}">{TAG[tag][0]}</span>'
def local_time(l):
    d = iso_dt(l['net'])
    if l['precision'] in PRECISE: return f'<time datetime="{l["net"]}" data-local>{esc(when_text(l))}</time>'
    return f'<time datetime="{d.date().isoformat()}">{esc(when_text(l))}</time>'
def cal_btn(l, root):
    if l['precision'] not in PRECISE + ('Day',): return ''
    return f'<a class="btn ghost sm" href="{root}launches/cal/{ics_name(l)}" download>Add to calendar<span class=sr> ({esc(l.get("mission") or l["name"])})</span></a>'
# ---- "What's on board" (card back). Only what Launch Library 2's mission text says, or a sourced fact below.
BB2_AREA = {'text': 'Each Block 2 BlueBird’s antenna array is about 2,400 sq ft (223 m²) when unfolded.',
            'src': ('Space.com, 5 Aug 2026', 'https://www.space.com/space-exploration/launches-spacecraft/spacex-launches-ast-spacemobile-11-13-direct-to-cell-satellites')}
def first_sentence(t, n=220):
    t = re.sub(r'\s+', ' ', (t or '')).strip()
    if not t: return ''
    m = re.match(r'(.+?[.!?])(\s|$)', t); t = m.group(1) if m else t
    return t if len(t) <= n else t[:n].rsplit(' ', 1)[0] + '…'
def payload(l):
    """-> (headline, detail, extra_fact_or_None). Never guesses a number."""
    name = l.get('mission') or l['name']; desc = l.get('mission_description') or ''; mt = l.get('mission_type') or ''
    m = re.search(r'BlueBirds? (\d+)\s*[-–]\s*(\d+)', name)
    if m and 'Block 2' in name:
        a, b = int(m[1]), int(m[2])
        return f'{b - a + 1} BlueBird Block 2 satellites (BlueBirds {a}–{b})', 'AST SpaceMobile phone-capable satellites, built to give 4G and 5G phones broadband from space.', BB2_AREA
    if re.search(r'BlueBird', name):
        return 'BlueBird Block 2 satellites · number not disclosed yet', 'AST SpaceMobile phone-capable satellites.', BB2_AREA
    m = re.search(r'\(x\s*(\d+)\)', name)
    if m and 'Globalstar' in name:
        return f'{m[1]} Globalstar replacement satellites', 'They top up the network behind satellite messaging on recent iPhones.', None
    m = re.search(r'\bbatch of (\d+) satellites for the (Starlink|OneWeb)', desc) or re.match(r'(\d+) satellites for (Rivada)', desc)
    if m:
        kind = {'Starlink': 'Starlink broadband', 'OneWeb': 'OneWeb broadband', 'Rivada': 'Rivada'}[m[2]]
        return f'{m[1]} {kind} satellites', first_sentence(desc), None
    if 'Starlink' in name:
        return 'Starlink satellites · number not disclosed', first_sentence(desc), None
    if 'Amazon Leo' in name:
        return 'Amazon Leo broadband satellites · number not disclosed in the launch data', 'Broadband for dishes and terminals, not phones.', None
    if mt == 'Government/Top Secret':
        return 'Classified payload', first_sentence(desc) or 'Details not disclosed.', None
    s = first_sentence(desc)
    if not s: return 'Payload not disclosed', '', None
    return (f'{mt} mission' if mt and mt != 'Unknown' else 'Mission'), s, None
def payload_html(l):
    h, d, fact = payload(l)
    fx = (f'<p class=pb-fact>{esc(fact["text"])} <a href="{esc(fact["src"][1])}">{esc(fact["src"][0])}</a></p>') if fact else ''
    src = f'<a href="{esc(l["ll2_url"])}">Launch Library 2</a>' if l.get('ll2_url') else 'Launch Library 2'
    orbit = {'LEO': 'low Earth orbit', 'PO': 'polar orbit', 'SSO': 'sun-synchronous orbit', 'GTO': 'geostationary transfer orbit', 'Direct-GEO': 'geostationary orbit', 'LO': 'lunar orbit'}.get(l.get('orbit') or '', '')
    k = satviz.kind_of(l['tag'], ltext(l), l.get('who', []))
    sat = sat_box(k) if k else ''
    return (f'<p class=kicker>What’s on board</p><p class=pb-h>{esc(h)}</p>' + (f'<p class=pb-d>{esc(d)}</p>' if d else '') + fx + sat +
            f'<p class=pb-meta>{("Heading to " + orbit + " · ") if orbit else ""}Source: {src}</p>')
def sat_box(k):
    """Static picture of the satellite type + basic stats (src/satellites.json 'card'), linking to /satellites/. No motion here."""
    f = next(x for x in SATS['families'] if x['anim'] == k)
    stats = ''.join(f'<div><dt>{esc(x["k"])}</dt><dd>{esc(x["v"])}</dd></div>' for x in f['card'])
    return (f'<div class=pb-sat style="--c:{f["color"]}"><figure class=pb-pic>{satviz.scene(k, "still")}</figure><div class=pb-info>'
            f'<p class=pb-name>{esc(f["name"])}</p><dl class=pb-stats>{stats}</dl>'
            f'<p class=pb-more><a href="../satellites/#{f["id"]}">How it works →<span class=sr> ({esc(f["name"])}, sources and animation)</span></a></p></div></div>')
SAT_ANCHOR = {'starlink-dtc': 'starlink-dtc', 'bluebird': 'bluebird', 'amazon-leo': 'amazon-leo', 'lynk': 'lynk', 'globalstar': 'globalstar'}
SAT_NAME = {'starlink-dtc': 'a Starlink Direct to Cell satellite', 'bluebird': 'a BlueBird', 'amazon-leo': 'an Amazon Leo satellite', 'lynk': 'a Lynk satellite', 'globalstar': 'a Globalstar satellite'}

# Launch sites for the orbit view's launch moment (lat, lon; public pad coordinates, rounded) and an illustrative ascent heading.
PADS = {'Cape Canaveral SFS, FL, USA': (28.56, -80.58, 45), 'Kennedy Space Center, FL, USA': (28.61, -80.60, 45),
        'Vandenberg SFB, CA, USA': (34.63, -120.61, 190), 'SpaceX Starbase, TX, USA': (26.0, -97.16, 95),
        'Guiana Space Centre, French Guiana': (5.24, -52.77, 85)}
def pad_of(l):
    if l.get('pad_lat') is not None: return (l['pad_lat'], l['pad_lon'], PADS.get(l.get('location'), (0, 0, 60))[2])
    return PADS.get(l.get('location'))
def liftoff(l):
    """Data for the launch-moment animation: where it goes up from, how many satellites to drop (if known) and whose."""
    pd = pad_of(l)
    if not pd: return None
    h = payload(l)[0]; m = re.match(r'(\d+) ', h); n = int(m[1]) if m else 0
    who = {'starlink-dtc': 'starlink-dtc', 'ast': 'ast'}.get(l['tag']) or ('globalstar' if 'Globalstar' in (l.get('mission') or '') else 'lynk' if 'lynk' in l['who'] else 'other')
    return {'m': l.get('mission') or l['name'], 'r': l.get('rocket'), 'p': l.get('location'), 'lat': pd[0], 'lon': pd[1], 'az': pd[2], 'n': min(n, 30), 'c': who, 'net': l['net']}

def launch_item(l, root):
    cd = f'<p class=lcd data-countdown="{l["net"]}" aria-hidden=true></p>' if l['precision'] in PRECISE else ''
    status = l.get('status') or ''
    st = f'<span class="lst{" go" if (l.get("status_abbrev") == "Go") else ""}">{esc(status)}</span>' if status else ''
    return (f'<li class="launch t-{TAG[l["tag"]][1]}" data-who="{" ".join(l["who"])}"><div class=l-when>{local_time(l)}{cd}</div>'
            f'<div class=l-body><div class=flip><div class="face front"><div class=l-top>{tag_pill(l["tag"])}{st}</div><h3>{esc(l.get("mission") or l["name"])}</h3>'
            f'<p class=l-meta>{esc(l.get("rocket") or "")} · {esc(l.get("provider") or "")} · {esc(l.get("location") or "")}</p>'
            f'<p class=l-why><strong>Why it matters for your phone:</strong> {esc(TAG[l["tag"]][2])}</p>'
            f'<div class=l-act><button type=button class="btn ghost sm flipbtn" aria-expanded=false>What’s on board<span class=sr> {esc(l.get("mission") or l["name"])}</span></button>{cal_btn(l, root)}</div></div>'
            f'<div class="face back" id="pb-{l["id"][:8]}">{payload_html(l)}<p class=l-act><button type=button class="btn ghost sm flipback">Back to launch<span class=sr> details</span></button></p></div></div></div></li>')
def human_dt(iso):
    d = iso_dt(iso); return d.strftime('%-d %b %Y, %H:%M UTC')
def next_launches(n=6):
    return [l for l in UPCOMING if l['precision'] in PRECISE and iso_dt(l['net']) > BUILD_NOW - timedelta(hours=3)][:n]
def window_text(l):
    if not (l.get('window_start') and l.get('window_end')): return ''
    a, b = iso_dt(l['window_start']), iso_dt(l['window_end'])
    if a == b: return 'Instantaneous window (one exact time)'
    return f"Window {a.strftime('%H:%M')}–{b.strftime('%H:%M')} UTC" + (' (ends next day)' if b.date() > a.date() else '')
def next_card(root=''):
    q = next_launches()
    if not q: return ''
    l = q[0]
    queue = json.dumps([{'n': x['net'], 'm': x.get('mission') or x['name'], 'r': x.get('rocket'), 'p': x.get('location'), 'w': window_text(x), 't': TAG[x['tag']][0], 'c': TAG[x['tag']][1]} for x in q], ensure_ascii=False, separators=(',', ':'))
    ph = next((x for x in UPCOMING if x['tag'] in ('starlink-dtc', 'ast', 'd2d-other')), None)
    phone = (f'<p class=nl-phone>Next phone-satellite launch: <strong>{esc(ph.get("mission") or ph["name"])}</strong> · {esc(when_text(ph))}</p>') if ph else ''
    return (f'<section class=nextlaunch aria-labelledby=nl-h data-queue="{esc(queue)}"><div class=nl-main><p class=kicker>Next launch <span class=nl-tag>{tag_pill(l["tag"])}</span></p>'
            f'<h2 id=nl-h class=nl-title>{esc(l.get("mission") or l["name"])}</h2>'
            f'<p class=nl-meta><span class=nl-rocket>{esc(l.get("rocket") or "")}</span> · <span class=nl-pad>{esc(l.get("location") or "")}</span></p>'
            f'<p class=nl-when>{local_time(l)}</p><p class=nl-window>{esc(window_text(l))}</p></div>'
            f'<div class=nl-side><p class=nl-cd data-countdown="{l["net"]}" role=timer aria-live=off>T− <span>--d --h --m --s</span></p>'
            f'<p class=nl-links><a class=btn href="{root}launches/">All launches</a>{cal_btn(l, root)}</p></div>{phone}</section>')
def count_rows(items, root):
    top = max([i['count'] for i in items if i['count']] or [1])
    out = []
    for i in items:
        n = i['count']
        num = f'{n:,}' if n is not None else esc(i.get('count_display') or 'Not disclosed')
        bar = (f'<span class=cbar aria-hidden=true><i style="width:{max(1.2, 100 * n / top):.1f}%"></i></span>') if n else '<span class="cbar none" aria-hidden=true></span>'
        srcs = [i['source']] + i.get('extra_sources', [])
        src = ' · '.join(f'<a href="{esc(s["url"])}">{esc(s["label"])}</a>' for s in srcs)
        plan = f'<p class=cplan><strong>Plan:</strong> {esc(i["planned"]["text"])}. <a href="{esc(i["planned"]["source"]["url"])}">Source</a></p>' if i.get('planned') else ''
        out.append(f'<li class="crow f-{i["filter"]}"><div class=chead><div><h3>{esc(i["network"])}</h3><p class=cop>{esc(i["operator"])}</p></div>'
                   f'<p class=cnum><b{" class=nd" if n is None else ""}>{num}</b><span>{esc(i["count_label"])}</span></p></div>{bar}'
                   f'<p class=cnote>{esc(i["note"])}</p>{plan}<p class=csrc>As of <time datetime="{i["as_of"]}">{human(i["as_of"])}</time> · Source: {src}</p></li>')
    return '<ul class=counts>' + ''.join(out) + '</ul>'

def glance(root):
    items = [i for i in CONST['direct_to_device'] if i['count'] is not None]
    li = ''.join(f'<li class="g-{i["filter"]}"><b>{i["count"]:,}</b><span>{esc(i["short"])}</span></li>' for i in items)
    asof = max(i['as_of'] for i in items)
    return (f'<div class="stats glance"><p class=kicker>Phone-capable satellites in orbit</p><ul aria-label="Phone-capable satellites in orbit by network">{li}</ul>'
            f'<p class=checked>As of {human(asof)}, with sources. <a href="#cnt-h">Compare them, plus broadband-only networks</a>.</p></div>')
# ---- orbit view (assets/orbits.js): one dot per phone-capable satellite, real totals from data/constellations.json
OCOL = {'starlink-dtc': '#00cfff', 'ast': '#ff9a3c', 'globalstar': '#b58cff', 'lynk': '#6ee79a', 'other': '#e8eef7'}
# Illustrative shells: inclination (deg) and height (km) from McDowell's catalogue/stats; split of Starlink DTC per data/constellations.json note.
OSHELLS = {'starlink-dtc': [(310 / 637, 53, 360, 24), (327 / 637, 43, 360, 24)], 'ast': [(1, 53, 520, 3)],
           'globalstar': [(1, 52, 1414, 8)], 'lynk': [(1, 97.5, 510, 4)]}
def orbit_panel(root):
    items = [i for i in CONST['direct_to_device'] if i['count'] and i['id'] in OSHELLS]
    cfg = [{'id': i['id'], 'n': i['count'], 'c': OCOL[i['id']], 's': [[round(f, 4), inc, alt, planes] for f, inc, alt, planes in OSHELLS[i['id']]]} for i in items]
    total = sum(i['count'] for i in items)
    li = ''.join(f'<li class="o-{i["id"]}"><i style="background:{OCOL[i["id"]]}" aria-hidden=true></i><b data-count="{i["count"]}">{i["count"]:,}</b><span>{esc(i["short"])}</span></li>' for i in items)
    asof = max(i['as_of'] for i in items)
    ups = [x for x in (liftoff(l) for l in UPCOMING) if x]
    demo = next((liftoff(l) for l in UPCOMING if l['tag'] in ('starlink-dtc', 'ast', 'd2d-other') and liftoff(l)), ups[0] if ups else None)
    queue = [x for x in (liftoff(l) for l in next_launches()) if x]
    desc = (f'Illustrative globe with {total:,} dots, one for each phone-capable satellite in orbit: '
            + ', '.join(f'{i["count"]:,} {i["short"]}' for i in items) + '. Dots circle the Earth on representative orbits.')
    return (f'<section class=orbit aria-labelledby=ov-h data-base="{root}" data-orbits="{esc(json.dumps(cfg, separators=(",", ":")))}"'
            f' data-demo="{esc(json.dumps(demo, ensure_ascii=False, separators=(",", ":")))}" data-queue="{esc(json.dumps(queue, ensure_ascii=False, separators=(",", ":")))}">'
            f'<div class=ov-copy><p class=kicker>Orbit view</p><h2 id=ov-h>Every phone-capable satellite, one dot each</h2>'
            f'<p class=ov-intro>{total:,} satellites can talk straight to ordinary phones today. Starlink has the numbers; AST’s BlueBirds are far fewer but each one is huge.</p>'
            f'<ul class=ov-legend aria-label="Phone-capable satellites in orbit by network">{li}</ul>'
            f'<p class=ov-scale><strong>1 dot = 1 satellite.</strong> Heights are to scale; the orbits are illustrative, not live positions.</p>'
            f'<p class=ov-act><button type=button class="btn sm" id=ov-launch>Watch a launch moment</button></p>'
            f'<p class=ov-status id=ov-status role=status aria-live=polite></p>'
            f'<p class=checked>Counts as of {human(asof)}, with sources <a href="#cnt-h">below</a>.</p></div>'
            f'<figure class=ov-fig><div id=orbitview class="globe ov-globe" role=img aria-label="{esc(desc)}"></div>'
            f'<figcaption>Illustrative. Real satellites fly in many more orbital planes. Drag to spin.</figcaption></figure></section>')

# ---- race chart (assets/race.js) from data/race.json (scripts/race_data.py)
RACE = json.loads((ROOT / 'data/race.json').read_text()) if (ROOT / 'data/race.json').exists() else None
def race_section(root):
    if not RACE: return ''
    R = RACE; fin = R['frames'][-1]; ser = {x['id']: x for x in R['series']}
    top = max(fin['v'].values()) * 1.12
    order = sorted(ser, key=lambda k: -fin['v'][k])
    rows = ''.join(f'<div class="rrow r-{k}" data-id="{k}" style="--c:{ser[k]["color"]};transform:translateY({i * 100}%)"><span class=rlab>{esc(ser[k]["label"])}</span>'
                   f'<span class=rbar><i style="width:{100 * fin["v"][k] / top:.2f}%"></i><b class=rval>{fin["v"][k]:,}</b></span></div>' for i, k in enumerate(order))
    t = R['target']
    tl = f'<div class=rtarget style="left:{100 * t["value"] / top:.2f}%"><span>{esc(t["label"])}</span></div>'
    q = [f for f in R['frames'] if f['d'][5:7] in ('03', '06', '09', '12') or f.get('final')]
    thead = '<tr><th scope=col>Date</th>' + ''.join(f'<th scope=col>{esc(ser[k]["label"])}</th>' for k in ser) + '</tr>'
    trows = ''.join(f'<tr><th scope=row>{human(f["d"], False)}{" (today, working)" if f.get("final") else ""}</th>' + ''.join(f'<td>{f["v"][k]:,}</td>' for k in ser) + '</tr>' for f in q)
    srcs = ''.join(f'<li><strong>{esc(x["label"])}:</strong> ' + ' · '.join(f'<a href="{esc(y["url"])}">{esc(y["label"])}</a>' for y in x['sources']) + (f'. {esc(x["note"])}' if x.get('note') else '') + '</li>' for x in R['series'])
    evs = ''.join(f'<li><time datetime="{e["d"]}">{human(e["d"], False)}</time> {esc(e["t"])} (<a href="{esc(e["src"]["url"])}">{esc(e["src"]["label"])}</a>)</li>' for e in R['events'])
    data = {'f': [[f['d'], [f['v'][k] for k in ser]] for f in R['frames']], 'k': list(ser), 't': t['value'], 'e': [[e['d'], e['t'], e['s']] for e in R['events']]}
    first = R['frames'][0]['d']
    summary = (f'From {human(first)} to {human(fin["d"])}: ' + ', '.join(f'{ser[k]["label"]} went from {R["frames"][0]["v"][k]:,} to {fin["v"][k]:,}' for k in ser) + f'. AST’s target is about {t["value"]} BlueBirds by mid-2027.')
    return (f'<section class=race aria-labelledby=race-h data-race="{esc(json.dumps(data, ensure_ascii=False, separators=(",", ":")))}">'
            f'<p class=kicker>The race so far</p><h2 id=race-h>Phone-capable satellites in orbit, month by month</h2>'
            f'<p class=l-intro>Starlink raced ahead in 2024 and has held about 640 direct-to-cell satellites since. AST is now launching three big BlueBirds at a time towards its target of about 45.</p>'
            f'<div class=race-chart aria-hidden=true><p class=race-date>{human(fin["d"], False)}</p><div class=race-plot>{rows}{tl}</div><p class=race-event>Today, working satellites</p></div>'
            f'<p class=sr>{esc(summary)}</p>'
            f'<div class=race-ctl><button type=button class="btn sm" id=race-play>Replay the race</button>'
            f'<button type=button class="btn ghost sm" id=race-zoom aria-pressed=false>Zoom in on the smaller networks</button>'
            f'<label class=race-scrub>Month <input id=race-range type=range min=0 max="{len(R["frames"]) - 1}" value="{len(R["frames"]) - 1}" step=1 aria-valuetext="{human(fin["d"], False)}"></label></div>'
            f'<details class=race-data><summary>Data and sources</summary><p class=l-credit>{esc(R["metric"])} Bars move smoothly between month ends for the animation only; every month-end value comes from the sources below.</p>'
            f'<div class=tablewrap><table><caption class=sr>Phone-capable satellites in orbit, by quarter</caption><thead>{thead}</thead><tbody>{trows}</tbody></table></div>'
            f'<p class=l-credit>Every month end is in <a href="{root}data/race.json">race.json</a>.</p><ul class=race-src>{srcs}</ul><h3 class=bb-h>Milestones</h3><ul class=race-src>{evs}</ul></details></section>')

def LAUNCH_CHIPS():
    nx = next_launches(1)
    out = [(f'Next: {nx[0]["name"].split("|")[-1].strip()[:30]} · {iso_dt(nx[0]["net"]).strftime("%-d %b")}', OGC['cyan'])] if nx else []
    return out + SAT_CHIPS()[:2]
def launches_page():
    root = '../'
    fetched = LDATA.get('fetched_at')
    chips = ''.join(f'<button type=button class=chip data-who={k} aria-pressed={"true" if k == "all" else "false"}>{t}</button>' for k, t in WHO)
    FIRST = 20
    items = ''.join(launch_item(l, root) for l in UPCOMING[:FIRST])
    rest = UPCOMING[FIRST:]
    more = (f'<details class=lmore id=launch-more><summary>Show {len(rest)} more launches</summary><ol class=launches start={FIRST + 1}>'
            + ''.join(launch_item(l, root) for l in rest) + '</ol></details>') if rest else ''
    n_phone = sum(1 for l in UPCOMING if 'phone' in l['who'])
    empty = ''.join(f' data-empty-{k}="{esc(v)}"' for k, v in EMPTY.items())
    upd = (f'Launch data from <a href="https://thespacedevs.com/llapi">The Space Devs Launch Library 2</a>, refreshed <time datetime="{fetched}">{human_dt(fetched)}</time>.' if fetched else 'Launch data from The Space Devs Launch Library 2.')
    body = (f'<header class=page-head><p class=kicker>Launches</p><h1>Launch tracker</h1>'
            f'<p class=lede>What SpaceX and its rivals are launching next, and what each launch means for the phone in your pocket.</p></header>'
            + next_card(root) + orbit_panel(root) +
            f'<section aria-labelledby=up-h><h2 id=up-h>Upcoming launches</h2>'
            f'<p class=l-intro>{len(UPCOMING)} upcoming launches from SpaceX, AST SpaceMobile, Amazon Leo and other satellite-to-phone players, {n_phone} of them carrying phone-capable satellites. Each one is tagged by what it means for mobile.</p>'
            f'<div class=filters role=search aria-label="Filter launches"><div class=f-row><div class=chips role=group aria-label="Show launches for">{chips}</div>'
            f'<p id=l-count class=t-count role=status aria-live=polite>{len(UPCOMING)} launches</p></div></div>'
            f'<div id=launch-list><ol class=launches>{items}</ol>{more}</div><p id=l-empty class=l-empty hidden{empty} data-empty="No upcoming launches match this filter right now.">No upcoming launches match this filter right now.</p>'
            f'<p class=l-credit>{upd} Times are shown in UTC, or your local time where your browser allows. Launch dates slip often, so check again on the day. We tag a Starlink launch as Direct to Cell only when the launch data or a reliable source says it carries direct-to-cell satellites.</p></section>'
            + race_section(root) +
            f'<section aria-labelledby=cnt-h class=countsec><h2 id=cnt-h>Phone satellites in orbit: who has how many</h2>'
            f'<p class=l-intro>Satellites that can connect to ordinary phones, by operator. Every number has a source and a date. If a company doesn’t publish a figure and we can’t find a reliable independent one, we say so rather than guess.</p>'
            + count_rows(CONST['direct_to_device'], root) +
            f'<h3 class=bb-h>Broadband-only constellations (not phone-capable)</h3><p class=l-intro>For scale: these networks serve dishes and terminals, not phones directly.</p>'
            + count_rows(CONST['broadband_only'], root) +
            f'<p class=l-credit>Counts last checked {human(CONST["last_checked"])}. Satellite totals change with every launch and re-entry. Data: <a href="{root}data/constellations.json">constellations.json</a> · <a href="{root}data/launches.json">launches.json</a></p></section>'
            f'<section class="card tlink" aria-labelledby=tl-h><p class=kicker>From the tracker</p><h2 id=tl-h><a href="{root}tracker.html">Where these satellites already reach phones</a></h2>'
            f'<p>{C["live"]} live direct-to-cell services in {NLIVE_C} countries, plus {C["trial"]} trials and {C["announced"]} announced. See who’s live, country by country, with sources.</p>'
            f'<p class=row-cta><a class="btn ghost" href="{root}tracker.html">Open the tracker</a><a class="btn ghost" href="{root}articles/why-starship-is-a-telco-story.html">Why Starship is a telco story</a></p></section>'
            + journey_card(root) + sats_card(root)
            + signal_block(root, 'launches', heading='Get launch alerts in Signal', intro='Signal is our free weekly direct-to-cell briefing. Subscribe for the launches that matter for your phone and what changed in the tracker, in one email a week.'))
    ld = [crumbs([('Home', ''), ('Launches', 'launches/')]),
          {'@context': 'https://schema.org', '@type': 'Dataset', 'name': 'Full Duplex: phone-capable satellites in orbit by operator', 'description': 'Direct-to-device satellite counts by operator, each with a source and an as-of date, kept separate from broadband-only constellations.',
           'url': BASE + 'launches/', 'creator': PUBLISHER, 'isAccessibleForFree': True, 'dateModified': CONST['last_checked'],
           'distribution': [{'@type': 'DataDownload', 'encodingFormat': 'application/json', 'contentUrl': BASE + 'data/constellations.json'}]}]
    page(og=('Launches', 'Launch tracker: what’s going up, and what it means for your phone', LAUNCH_CHIPS()), path='launches/index.html', title='Launch tracker',
         full_title='Launch tracker: SpaceX, AST SpaceMobile and phone-satellite launches | Full Duplex',
         description='Upcoming SpaceX, AST SpaceMobile, Amazon Leo and direct-to-cell launches, tagged by what they mean for your phone, plus a sourced count of phone-capable satellites in orbit.',
         body=body, root=root, current='launches/index.html', jsonld=ld, cls='is-launches', lastmod=(fetched or BUILD_NOW.isoformat())[:10],
         scripts=f'<script defer src="{root}assets/launches.js"></script><script defer src="{root}assets/orbits.js"></script><script defer src="{root}assets/race.js"></script>',
         search_text='Launch tracker. ' + ' '.join(f"{l.get('mission')} {l.get('rocket')} {TAG[l['tag']][0]}." for l in UPCOMING) + ' ' + ' '.join(f"{i['network']} {i['operator']} {i['note']}" for i in CONST['direct_to_device'] + CONST['broadband_only']))
# ---------------------------------------------------------------- journey explainer (src/pages/journey.html; animations in style.css + assets/journey.js)
JOURNEY_MINI = ('<svg viewBox="0 0 150 90" aria-hidden=true focusable=false><rect width=150 height=90 rx=12 fill="#0c1830"/><path d="M0 78C30 62 60 58 90 64S130 80 150 76V90H0z" fill="#16243d"/>'
                '<path d="M40 64L75 18 116 70" fill=none stroke="#00cfff" stroke-width=1.6 stroke-dasharray="3 4"/><rect x=64 y=12 width=22 height=10 rx=2 fill="#e8eef7"/><rect x=50 y=14 width=12 height=6 fill="#06324a" stroke="#00cfff"/><rect x=88 y=14 width=12 height=6 fill="#06324a" stroke="#00cfff"/>'
                '<rect x=34 y=56 width=10 height=17 rx=2 fill="#1b2840" stroke="#8fdbff"/><path d="M108 74h16M112 74l4-10 4 10" stroke="#7f93a8" stroke-width=1.6 fill="none"/></svg>')
def journey_card(root):
    return (f'<section class="card jcard" aria-labelledby=jc-h>{JOURNEY_MINI}<div><p class=kicker>Explainer</p><h2 id=jc-h><a href="{root}journey/">What happens when you hit send</a></h2>'
            f'<p>Follow one text from a hillside with no signal, up to a satellite, through the mobile network and on to the person you’re texting. Six short animated scenes.</p></div></section>')
def journey_page():
    meta, body, _ = read_src(SRC / 'pages' / 'journey.html'); root = '../'; url = BASE + 'journey/'
    share = share_btn('What happens when you hit send from a phone with no signal: one text message, via satellite, in six scenes.', url)
    body = body.replace('<!--SHARE-TOP-->', f'<p class=row-cta>{share}{follow_btn()}</p>')
    body += (f'<div class=share-end><p>Know someone who still thinks satellite phones need a brick-sized handset? Send them this.</p>{share}{follow_btn()}</div>'
             + signal_block(root, 'journey', heading='Get Signal: the weekly direct-to-cell briefing', intro='One email a week on satellite-to-phone, mobile networks and what it means for you, from a mobile network insider with over 13 years in GSM. Plain English, with sources.'))
    ld = [crumbs([('Home', ''), ('What happens when you hit send', 'journey/')]),
          {'@context': 'https://schema.org', '@type': 'Article', 'headline': meta['title'], 'description': meta['description'], 'author': AUTHOR, 'publisher': PUBLISHER,
           'mainEntityOfPage': url, 'inLanguage': 'en-GB', 'image': [f'{BASE}assets/og/journey.jpg'], 'datePublished': '2026-11-10'}]
    page(og=('Explainer', 'What happens when you hit send: one text, via satellite'), gloss=True, path='journey/index.html', title=meta['title'], description=meta['description'],
         body=body, root=root, current='', jsonld=ld, cls='is-journey', lastmod='2026-11-10', scripts=f'<script defer src="{root}assets/journey.js"></script>',
         full_title='What happens when you hit send: a text via satellite | Full Duplex')
# ---------------------------------------------------------------- satellites explainer (src/satellites.json; drawings in scripts/satviz.py)
def const_item(cid): return next((i for i in CONST['direct_to_device'] + CONST['broadband_only'] if i['id'] == cid), None)
def sats_card(root):
    return (f'<section class="card jcard scard" aria-labelledby=sc-h>{satviz.scene("bluebird")}<div><p class=kicker>Explainer · new</p><h2 id=sc-h><a href="{root}satellites/">Meet the satellites</a></h2>'
            f'<p>What a Starlink, a BlueBird, a Lynk and a Globalstar satellite look like, how high they fly and how they reach an ordinary phone. Plus why Amazon Leo isn’t a phone satellite (yet).</p></div></section>')
def SAT_CHIPS():
    out = []
    for cid, nm, col in (('starlink-dtc', 'Starlink DTC', '#00cfff'), ('ast', 'BlueBirds', '#ff9a3c'), ('globalstar', 'Globalstar', '#b58cff'), ('lynk', 'Lynk', '#6ee79a')):
        c = const_item(cid)
        if c and c.get('count') is not None: out.append((f'{c["count"]:,} {nm}', col))
    return out
def satellites_page():
    root = '../'; url = BASE + 'satellites/'; S = SATS['sources']
    def src(keys):
        if not keys: return ''
        return '<span class=sc-src>Source: ' + ' · '.join(f'<a href="{esc(S[k][1])}">{esc(S[k][0])}</a>' for k in keys) + '</span>'
    fams = SATS['families']
    jump = ''.join(f'<li><a href="#{f["id"]}" style="--c:{f["color"]}">{satviz.scene(f["anim"])}<span><i aria-hidden=true></i>{esc(f["short"])}</span></a></li>' for f in fams)
    # infographic 1: phone antennas to scale (sides in metres; BlueBird squares have the same area as the real array)
    scale = [('Lynk', 'whole satellite, about 1 m across', 1, 1, '#6ee79a', ['keeptrack-lynk']),
             ('Starlink DTC', 'phone antenna, about 2.7 × 2.3 m', 2.7, 2.3, '#00cfff', ['astrospace-dtc']),
             ('BlueBird Block 1', 'array about 64 m² (693 sq ft)', 8.02, 8.02, '#ff9a3c', ['keeptrack-ast']),
             ('BlueBird Block 2', 'array about 223 m² (2,400 sq ft)', 14.93, 14.93, '#ff9a3c', ['space-bb2'])]
    person = '<svg class=person viewBox="0 0 10 36" aria-hidden=true focusable=false><circle cx=5 cy=4 r=3.4 fill="#9fb0c3"/><path d="M1.5 10h7l-.6 12H7.2L6.8 35H3.2L2.8 22H2.1z" fill="#9fb0c3"/></svg>'
    sc_li = ''.join(f'<li style="--w:{w};--h:{h};--c:{c}"><span class=sqbox><span class=sq aria-hidden=true></span></span><b>{esc(n)}</b><span>{esc(t)}</span></li>' for n, t, w, h, c, _ in scale)
    sc_src = src(sorted({k for *_, ks in scale for k in ks}, key=list(S).index))
    scale_html = (f'<section class=sat-info aria-labelledby=scale-h><p class=kicker>To scale</p><h2 id=scale-h>How big is the bit that talks to your phone?</h2>'
                  f'<p class=l-intro>Bigger antennas can hear a phone’s weak signal from further away. Drawn to the same scale, next to a 1.8 m person. BlueBird squares have the same area as the real arrays.</p>'
                  f'<ul class=scale-row><li class=sp style="--h:1.8"><span class=sqbox>{person}</span><b>Person</b><span>1.8 m tall</span></li>{sc_li}</ul>'
                  f'<p class=l-credit>Globalstar’s antenna size: TBC. Amazon Leo isn’t shown because it doesn’t talk to phones. {sc_src}</p></section>')
    # infographic 2: how high they fly
    alts = [('Starlink DTC', 360, 'about 360 km', '#00cfff', ['keeptrack-dtc']), ('BlueBird', 520, 'about 520 km', '#ff9a3c', ['keeptrack-ast']),
            ('Amazon Leo', 630, '590 to 630 km', '#f5c26b', ['wiki-leo']), ('Globalstar', 1414, 'about 1,414 km', '#b58cff', ['gs-fcc-c3'])]
    al_li = ''.join(f'<li style="--c:{c}"><span class=al-n>{esc(n)}</span><span class=al-bar><i style="width:{100 * v / 1414:.1f}%"></i></span><span class=al-v>{esc(t)}</span></li>' for n, v, t, c, _ in alts)
    alt_html = (f'<section class=sat-info aria-labelledby=alt-h><p class=kicker>Height</p><h2 id=alt-h>How high they fly</h2>'
                f'<p class=l-intro>Lower satellites are closer to your phone, so the signal has less distance to cover, but each one passes overhead faster and you need more of them.</p>'
                f'<ul class=alt-chart>{al_li}<li style="--c:#6ee79a"><span class=al-n>Lynk</span><span class="al-bar tbc"></span><span class=al-v>low orbit, height TBC</span></li></ul>'
                f'<p class=l-credit>{src(["keeptrack-dtc", "keeptrack-ast", "wiki-leo", "gs-fcc-c3", "keeptrack-lynk"])}</p></section>')
    cards = []; rows = []
    for f in fams:
        ci = const_item(f['count_id'])
        if ci and ci['count'] is not None:
            cnt = (f'<p class=sc-count><b>{ci["count"]:,}</b><span>{esc(ci["count_label"])} · as of <time datetime="{ci["as_of"]}">{human(ci["as_of"])}</time> · '
                   f'Source: <a href="{esc(ci["source"]["url"])}">{esc(ci["source"]["label"])}</a></span></p>')
            cnt_s = f'{ci["count"]:,} ({human(ci["as_of"], False)})'
        else:
            cnt = '<p class=sc-count><b>TBC</b><span>No sourced count yet</span></p>'; cnt_s = 'TBC'
        facts = ''.join(f'<div><dt>{esc(x["k"])}</dt><dd>{esc(x["v"])} {src(x["s"])}</dd></div>' for x in f['facts'])
        nxt = f'<p class=sc-next><strong>What’s next:</strong> {esc(f["next"]["v"])} {src(f["next"]["s"])}</p>'
        badge = f'<span class="sc-badge{"" if f["phone"] else " no"}">{esc(f["badge"])}</span>'
        cards.append(f'<article class=satcard id="{f["id"]}" style="--c:{f["color"]}" aria-labelledby="h-{f["id"]}">'
                     f'<figure class=sc-art>{satviz.scene(f["anim"], "card")}<figcaption>Illustration drawn by Full Duplex from public descriptions. Not to scale.</figcaption></figure>'
                     f'<div class=sc-body><p class=kicker>{esc(f["operator"])}</p>{badge}<h2 id="h-{f["id"]}">{esc(f["name"])}</h2><p class=sc-lede>{esc(f["lede"])}</p>'
                     f'{cnt}<dl class=sc-facts>{facts}</dl>{nxt}</div></article>')
        rows.append(f'<tr><th scope=row><a href="#{f["id"]}">{esc(f["short"])}</a></th><td data-l="Ordinary phones?">{"Yes" if f["phone"] else "No, dishes only"}</td><td data-l="Frequencies">{esc(f["glance"]["spec"])}</td><td data-l="Today">{esc(f["glance"]["today"])}</td><td data-l="In orbit">{cnt_s}</td></tr>')
    glance = ('<section class=sat-info aria-labelledby=gl-h><p class=kicker>At a glance</p><h2 id=gl-h>Which is which</h2><div class=tablewrap><table class=sat-table>'
              '<thead><tr><th scope=col>Satellite</th><th scope=col>Talks to ordinary phones?</th><th scope=col>Whose frequencies</th><th scope=col>What works today</th><th scope=col>In orbit</th></tr></thead>'
              f'<tbody>{"".join(rows)}</tbody></table></div><p class=l-credit>Sources are listed with each satellite above. Satellite counts come from our <a href="{root}launches/#cnt-h">launch tracker</a> and change with every launch.</p></section>')
    share = share_btn('Meet the satellites that talk to your phone: what Starlink, AST’s BlueBird, Lynk and Globalstar look like and how they work.', url)
    body = (f'<header class="page-head sathead"><p class=kicker>Explainer · satellite to phone</p><h1>Meet the satellites</h1>'
            f'<p class=lede>The satellites that can talk to an ordinary phone, and one that can’t yet. What each looks like, how high it flies, how it reaches your phone and who it works with.</p>'
            f'<p class=jcred>Written by a mobile network insider with over 13 years in GSM, from IVR and SMS to call routing and thin and thick MVNOs.</p>'
            f'<p class=row-cta>{share}{follow_btn()}</p><ul class=sat-jump aria-label="Jump to a satellite">{jump}</ul></header>'
            + scale_html + alt_html + ''.join(cards) + glance
            + f'<p class=l-credit>Checked {human(SATS["checked"])}. Illustrations are drawn by Full Duplex from public descriptions and are not to scale. Where we couldn’t find a reliable figure we say TBC. Watch the next launches on our <a href="{root}launches/">launch tracker</a>.</p>'
            + f'<div class=share-end><p>Know someone who thinks every satellite is the same? Send them this.</p>{share}{follow_btn()}</div>'
            + signal_block(root, 'satellites', heading='Get Signal: the weekly direct-to-cell briefing', intro='One email a week on satellite-to-phone, mobile networks and what it means for you, from a mobile network insider with over 13 years in GSM. Plain English, with sources.'))
    ld = [crumbs([('Home', ''), ('Meet the satellites', 'satellites/')]),
          {'@context': 'https://schema.org', '@type': 'Article', 'headline': 'Meet the satellites', 'description': 'What Starlink Direct to Cell, AST SpaceMobile BlueBird, Amazon Leo, Lynk and Globalstar satellites look like, how high they fly and how they reach an ordinary phone.',
           'author': AUTHOR, 'publisher': PUBLISHER, 'mainEntityOfPage': url, 'inLanguage': 'en-GB', 'image': [f'{BASE}assets/og/satellites.jpg'], 'datePublished': SATS['checked']}]
    page(og=('Explainer', 'Meet the satellites that talk to your phone', SAT_CHIPS()), gloss=True, path='satellites/index.html', title='Meet the satellites',
         full_title='Meet the satellites: Starlink, BlueBird, Lynk, Globalstar and Amazon Leo explained | Full Duplex',
         description='What Starlink Direct to Cell, AST SpaceMobile BlueBird, Amazon Leo, Lynk and Globalstar satellites look like, how high they fly and how they reach an ordinary phone. Plain English, with sources.',
         body=body, root=root, current='satellites/index.html', jsonld=ld, cls='is-sats', lastmod=SATS['checked'])
launches_page()
journey_page()
satellites_page()


# ---------------------------------------------------------------- "Can my phone connect?" checker (src/phones.json + data/tracker.json; logic in assets/check.js)
PHONES = json.loads((SRC / 'phones.json').read_text())
def check_data():
    rows = [{'c': r['country'], 'cs': country_slug(r['country']) if r['iso_n3'] else '', 'o': r['operator'], 'os': slugify(short_op(r['operator'])),
             'p': provider(r['satellite']), 'sat': r['satellite'], 'st': r['status'], 'sv': strip_tags(r['services']),
             'src': [[x['label'], x['url']] for x in r['sources']], 'chk': r['checked']} for r in ROWS]
    return {'rows': rows, 'phones': PHONES, 'checked': TRACK['last_checked'], 'base': BASE}
def check_ops():
    ops = {}
    for r in ROWS:
        if r['iso_n3']: ops.setdefault(country_slug(r['country']), []).append([slugify(short_op(r['operator'])), r['operator']])
    return json.dumps(ops, ensure_ascii=False, separators=(',', ':'))
def check_selects(idp, countries, models, op_hint=True):
    copt = ''.join(f'<option value="{country_slug(c)}">{esc(c)}</option>' for c in countries)
    groups = {}
    for mid, lab, brand in models: groups.setdefault(brand, []).append(f'<option value="{mid}">{esc(lab)}</option>')
    popt = ''.join(f'<optgroup label="{esc(b)}">{"".join(o)}</optgroup>' for b, o in groups.items())
    return (f'<label><span>Country</span><select id={idp}-c name=c required><option value="">Pick a country</option>{copt}<option value=other>Somewhere else</option></select></label>'
            f'<label><span>Network</span><select id={idp}-o name=o><option value="">Pick a network</option></select></label>'
            f'<label><span>Phone</span><select id={idp}-p name=p><option value="">Pick a phone</option>{popt}</select></label>')
def check_box(root):
    """Compact entry box for the home page: a plain GET form to /check/, so it works without JavaScript too."""
    return (f'<section class="card chkbox" aria-labelledby=ck-h><div class=ck-copy><p class=kicker>New · 3 taps, no sign-up</p><h2 id=ck-h><a href="{root}check/">Can my phone connect to a satellite?</a></h2>'
            f'<p>Pick your country, network and phone. We’ll tell you what’s live, what’s on trial and how to check your handset, with sources. No IMEI needed.</p></div>'
            f'<form class=ck-form action="{root}check/" method=get data-chk data-ops="{esc(check_ops())}">{check_selects("hk", sorted(COUNTRIES), PHONES["models"])}<button class=btn type=submit>Check</button></form></section>')
def check_page():
    root = '../'; url = BASE + 'check/'
    data = json.dumps(check_data(), ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    srcs = sorted({(v['label'], v['url']) for v in PHONES['lists'].values() if v.get('url')} | {(PHONES[k]['label'], PHONES[k]['url']) for k in ('apple_carrier', 'apple_sos', 'pixel_sos')} | {(h['src'][0], h['src'][1]) for h in PHONES['howto']})
    body = (f'<header class=page-head><p class=kicker>Checker · satellite to phone</p><h1>Can my phone connect?</h1>'
            f'<p class=lede>Pick your country, your network and your phone. You’ll get a plain-English answer from our tracker: what’s live, what’s only on trial, what it does, and whether your phone is on the official list.</p>'
            f'<p class=jcred>Built by a mobile network insider with over 13 years in GSM. We never ask for your IMEI and nothing you pick leaves your browser.</p></header>'
            f'<form id=chk class="card ck-form big" action="./" method=get data-chk data-ops="{esc(check_ops())}">{check_selects("ck", sorted(COUNTRIES), PHONES["models"])}<button class=btn type=submit>Check</button></form>'
            f'<div id=chk-out class=ck-out aria-live=polite></div>'
            f'<noscript><p class=note>The checker needs JavaScript. Every service is listed in the <a href="{root}tracker.html">tracker</a>, with sources.</p></noscript>'
            f'<section class=ck-about aria-labelledby=ca-h><h2 id=ca-h>How the checker works</h2><ul>'
            f'<li>Network answers come straight from the <a href="{root}tracker.html">Full Duplex tracker</a> (last checked {TRACK["last_checked"]}): {len(ROWS)} services in {NCOUNTRIES} countries.</li>'
            f'<li>Phone answers only use official compatibility lists from networks, Apple and Google. If we don’t have one for your network and phone, we say so and show you how to check on the phone itself.</li>'
            f'<li>Lists change often. Always confirm on your network’s own page before you pay for anything.</li></ul>'
            f'<p class=l-credit>Phone lists used (checked {human(PHONES["checked"])}): ' + ' · '.join(f'<a href="{esc(u)}">{esc(l)}</a>' for l, u in srcs) + '. Orange and Telstra details come from the tracker’s own sources.</p></section>'
            f'<script type=application/json id=chk-data>{data}</script>'
            + signal_block(root, 'checker', heading='Get told when your network goes live', intro='Signal covers new launches, trials and status changes every week, country by country, with the sources.'))
    page(og=('Checker', 'Can my phone connect to a satellite?', [(f'{len(ROWS)} services', OGC['cyan']), (f'{NCOUNTRIES} countries', OGC['live']), ('No IMEI needed', OGC['muted'])]),
         path='check/index.html', title='Can my phone connect?', full_title='Can my phone connect to a satellite? Check by country, network and phone | Full Duplex',
         description='Check whether satellite-to-phone works on your network and phone: pick your country, network and handset for a plain-English answer with sources. No IMEI needed.',
         body=body, root=root, cls='is-check', scripts='<script defer src="../assets/check.js"></script>', lastmod=parse_human(TRACK['last_checked']),
         search_text='Can my phone connect to a satellite? Phone checker by country, network and phone model. ' + ' '.join(f"{r['country']} {r['operator']}" for r in ROWS))

def glossary_page():
    root = '../'; terms = sorted(GLOSS['terms'], key=lambda t: t['term'].lower())
    jump = ''.join(f'<a href="#{t["id"]}">{esc(t["term"])}</a>' for t in terms)
    items = ''.join(f'<div class=gl-item id="{t["id"]}"><dt>{esc(t["term"])}</dt><dd><p>{esc(t["def"])}</p><p class=gl-src>Source: '
                    + ' · '.join(f'<a href="{esc(u)}">{esc(l)}</a>' for l, u in t['src']) + '</p></dd></div>' for t in terms)
    body = (f'<header class=page-head><p class=kicker>Glossary</p><h1>Satellite-to-phone jargon, in plain English</h1>'
            f'<p class=lede>The terms you’ll meet in our articles and explainers. Tap or hover a dotted word anywhere on the site to see its meaning without leaving the page.</p>'
            f'<p class=jcred>Definitions by a mobile network insider with over 13 years in GSM. Checked {human(GLOSS["checked"])}.</p></header>'
            f'<nav class=gl-jump aria-label="Jump to a term">{jump}</nav><dl class=gl-list>{items}</dl>'
            + signal_block(root, 'glossary'))
    page(og=('Glossary', 'Satellite-to-phone jargon, in plain English', [(f'{len(terms)} terms', OGC['cyan']), ('D2D · NTN · LEO · MVNO', OGC['muted'])]),
         path='glossary/index.html', title='Glossary', full_title='Satellite-to-phone glossary: D2D, NTN, LEO, MVNO and more | Full Duplex',
         description='Plain-English definitions of satellite-to-phone and mobile network jargon: D2D, NTN, LEO, MVNO, spectrum, eNodeB, bent pipe and more, with sources.',
         body=body, root=root, lastmod=GLOSS['checked'])
check_page()
glossary_page()

# ---------------------------------------------------------------- search + 404
body = ('<header class=page-head><p class=kicker>Search</p><h1>Search Full Duplex</h1></header>'
        '<form class=searchbox role=search action="search.html" method=get><label for=q class=sr>Search articles, countries and operators</label>'
        '<input id=q name=q type=search placeholder="Try Starlink, Japan or 2G" autocomplete=off><button type=submit class=btn>Search</button></form>'
        '<p id=s-status class=t-count role=status aria-live=polite></p><ol id=s-results class=results></ol>'
        '<noscript><p>Search needs JavaScript. Browse the <a href="articles/index.html">articles</a> or the <a href="tracker.html">tracker</a>.</p></noscript>')
page(path='search.html', title='Search', description='Search Full Duplex articles, tracker countries and operators.', body=body, current='search.html',
     scripts='<script defer src="assets/search.js"></script>', search=False, index=True)
body = ('<header class=page-head><p class=kicker>404</p><h1>Lost signal</h1><p class=lede>That page isn’t here. It may have moved.</p></header>'
        f'<p class=row-cta><a class=btn href="{BASE}">Go to the home page</a><a class="btn ghost" href="{BASE}search.html">Search the site</a><a class="btn ghost" href="{BASE}tracker.html">Open the tracker</a></p>')
# 404 is served at any depth, so it uses absolute URLs
page(path='404.html', title='Page not found', description='Page not found.', body=body, root=BASE, search=False, index=False, sticky=False)

# ---------------------------------------------------------------- home
feat, rest = arts[0], arts[1:]
home = (f'<section class=hero><div class=hero-art aria-hidden=true><img src="assets/img/home-hero-1600.webp" srcset="assets/img/home-hero-960.webp 960w, assets/img/home-hero-1600.webp 1600w" sizes="100vw" width="1600" height="687" alt="" decoding="async" fetchpriority="high"></div><div class=hero-copy><p class=kicker>Both directions, all at once</p><h1>Your phone is about to talk to space.</h1>'
        f'<p class=lede>Full Duplex explains direct-to-cell satellites, GSM and the shake-up coming to the mobile industry.</p>'
        f'<p class=hero-cta><a class=btn href="{esc(sub_url("home-hero"))}">Send me Signal</a><a class="btn ghost" href="tracker.html">Explore the tracker</a></p>'
        f'<p class=byl>By <a href="about.html">{esc(SITE["author"])}</a>, a mobile network insider with over 13 years in GSM · {follow_btn("xinline")}</p></div>'
        f'<figure class=globe-wrap><div id=globe class=globe role=img aria-label="Rotating globe: {NLIVE_C} countries with live direct-to-cell service in green, countries with trials in amber. Full data in the tracker."></div>'
        f'<figcaption><span class=k-live>Live</span><span class=k-trial>Trial</span><span class=k-ann>Announced</span> <a href="tracker.html">Open the map</a></figcaption></figure>'
        f'</section>'
        + stats_strip()
        + check_box('')
        + race_board('', compact=True)
        + next_card('')
        + f'<section aria-labelledby=latest class=front><h2 id=latest class=sec>Latest analysis</h2><div class=front-grid>{art_card(feat, "", 3, "card feature")}'
          f'<div class=grid3>{"".join(art_card(a) for a in rest[:3])}</div></div></section>'
        + signal_block('', 'home')
        + f'<section aria-labelledby=ft-h class=from-tracker><h2 id=ft-h class=sec>From the tracker</h2><div class=two><div>{change_list(CHANGES, "", 5)}<p><a href="tracker/changes/">All tracker changes</a></p></div>'
          f'<div class="card"><h3><a href="tracker.html">Direct-to-cell tracker</a></h3><p>Who’s live, who’s trialling and who’s announced, country by country, with sources. Filter by status, provider and region, or download the CSV.</p>'
          f'<div class=cclist>{"".join(f"<a class=\"cc s-{CLS[best(rs)]}\" href=\"tracker/{country_slug(c)}/\">{esc(c)}</a>" for c, rs in sorted(COUNTRIES.items(), key=lambda kv: -RANK[best(kv[1])])[:8])}</div></div></div></section>'
        + f'<section aria-labelledby=more-h><h2 id=more-h class=sec>More analysis</h2><div class=list>{"".join(art_card(a, "", 3, "row") for a in rest[3:])}</div><p><a href="articles/index.html">All articles</a></p></section>'
        + '<section aria-labelledby=play-h class="card play"><p class=kicker>Play</p><h2 id=play-h><a href="play/constellation.html">Constellation</a></h2><p>Deploy direct-to-cell satellites into orbit. A 75-second browser game: hit the slots before time runs out.</p></section>'
        + journey_card('')
        + '<aside class=sponsor-card aria-label="Sponsorship"><p class=kicker>Presented by · slot available</p><h2>Put your brand in front of the people building satellite-to-phone</h2>'
          '<p>Engineers, operator teams, investors and early adopters read Full Duplex. One sponsor at a time, always clearly labelled.</p>'
          '<p><a class="btn ghost" href="sponsor.html">See sponsor options</a></p></aside>')
ld = [{'@context': 'https://schema.org', '@type': 'WebSite', 'name': 'Full Duplex', 'url': BASE, 'inLanguage': 'en-GB', 'publisher': PUBLISHER,
       'potentialAction': {'@type': 'SearchAction', 'target': BASE + 'search.html?q={q}', 'query-input': 'required name=q'}}]
page(og=('Full Duplex', 'Your phone is about to talk to space.', [(f"{C['live']} live services", OGC['live']), (f'{NLIVE_C} countries', OGC['cyan']), ('Weekly briefing: Signal', OGC['muted'])]), path='index.html', title='Satellite-to-phone and the future of mobile', full_title='Satellite-to-phone and the future of mobile | Full Duplex',
     description=SITE['home_description'], body=home, current='index.html', jsonld=ld, cls='is-home',
     scripts='<script defer src="assets/globe.js"></script><script defer src="assets/launches.js"></script>', lastmod=max(a.get('updated', a['published']) for a in arts), search=False)

# ---------------------------------------------------------------- feeds, sitemap, search index
sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
for p, lm in sorted(built):
    loc = BASE + (p[:-len('index.html')] if p.endswith('index.html') else p)
    sm.append(f'<url><loc>{loc}</loc>' + (f'<lastmod>{lm}</lastmod>' if lm else '') + '</url>')
sm.append('</urlset>')
(ROOT / 'sitemap.xml').write_text('\n'.join(sm) + '\n')
(ROOT / 'robots.txt').write_text(f'User-agent: *\nAllow: /\n\nSitemap: {BASE}sitemap.xml\n')
latest = max(a.get('updated', a['published']) for a in arts)
items = ''.join(f'<item><title>{esc(a["title"])}</title><link>{BASE}articles/{a["slug"]}.html</link><guid>{BASE}articles/{a["slug"]}.html</guid>'
                f'<pubDate>{rfc822(a["published"])}</pubDate><description>{esc(a["description"])}</description></item>'
                for a in sorted(arts, key=lambda a: a['published'], reverse=True))
(ROOT / 'feed.xml').write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel><title>Full Duplex</title><link>{BASE}</link>'
                               f'<atom:link href="{BASE}feed.xml" rel="self" type="application/rss+xml"/><description>{esc(SITE["home_description"])}</description><language>en-gb</language>'
                               f'<lastBuildDate>{rfc822(latest)}</lastBuildDate>{items}</channel></rss>\n')
(ROOT / 'search-index.json').write_text(json.dumps(SEARCH, ensure_ascii=False, separators=(',', ':')) + '\n')
print(f'built {len(built)} indexed pages (+404), {len(COUNTRIES)} country pages, {sum(len(e["items"]) for e in CHANGES)} change-log items; tracker rows: {len(ROWS)}')
