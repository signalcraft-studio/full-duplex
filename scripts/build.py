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
from datetime import date
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
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
                f'<{h} class=signal-h>{heading or "Signal: the weekly direct-to-cell briefing from an 11-year network insider"}</{h}>'
                f'{embed}<p class=signal-cta><a class=btn href="{esc(sub_url(surface))}">Send me Signal</a></p>{privacy}</aside>')
    return (f'<section class=signal aria-label="Subscribe to Signal"><div class=signal-copy><p class=kicker>Signal · free weekly briefing</p>'
            f'<{h} class=signal-h>{heading or "Get Signal: what changed in satellite-to-phone this week"}</{h}>'
            f'<p>{intro or "One email a week on direct-to-cell, mobile networks and what it means for you, from an 11-year mobile network insider."}</p>'
            f'<p class=issues-h>Recent issues</p>{issues_list()}</div><div class=signal-form>{embed}<p class=signal-cta><a class=btn href="{esc(sub_url(surface))}">Send me Signal</a> '
            f'<a class=more href="{esc(SITE["archive_url"])}">Read past issues</a></p>{privacy}</div></section>')

# ---------------------------------------------------------------- chrome
NAV = [('index.html', 'Home'), ('articles/index.html', 'Articles'), ('tracker.html', 'Tracker'), ('launches/index.html', 'Launches'), ('search.html', 'Search'), ('about.html', 'About'), ('sponsor.html', 'Sponsor')]

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
            f'<a href="{root}articles/index.html">Articles</a><a href="{root}tracker.html">Tracker</a><a href="{root}tracker/changes/">Tracker changes</a><a href="{root}launches/">Launches</a>'
            f'<a href="{root}play/constellation.html">Constellation</a><a href="{root}search.html">Search</a><a href="{root}feed.xml">RSS</a>'
            f'<a href="{root}about.html">About</a><a href="{root}sponsor.html">Sponsor</a><a href="{root}privacy.html">Privacy</a></nav></div></footer>{bar}')

built = []  # (path, lastmod)
SEARCH = []

def page(*, path, title, description, body, root='', current='', og_type='website', jsonld=None, head_extra='', scripts='',
         viewport='width=device-width,initial-scale=1', sticky=True, full_title=None, lastmod=None, search=True, cls='', index=True, search_text=None, og=None):
    url = BASE + (path[:-len('index.html')] if path.endswith('index.html') else path)
    ft = full_title or f'{title} | Full Duplex'
    slug = 'home' if path == 'index.html' else re.sub(r'(/index)?\.html$', '', path).replace('/', '-')
    kicker, og_title = og or ('Full Duplex', title)
    if not index: slug = 'home'
    elif IMGS: IMGS.og_card(ROOT / 'assets' / 'og' / f'{slug}.jpg', kicker, og_title)
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
    (ROOT / path).parent.mkdir(parents=True, exist_ok=True)
    (ROOT / path).write_text(out)
    if index: built.append((path, lastmod))
    if search: SEARCH.append({'t': title, 'u': path[:-len('index.html')] if path.endswith('index.html') else path, 'd': description, 'x': (search_text if search_text is not None else strip_tags(re.sub(r'<(aside|section) class=["]?signal.*?</\1>', ' ', body, flags=re.S)))[:6000]})
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
         full_title=f"{a['short_title']} | Full Duplex", lastmod=a.get('updated', a['published']), cls='is-article', search_text=strip_tags(a['body']), og=('Analysis', a['title']),
         head_extra=f'<meta property="article:published_time" content="{a["published"]}"><meta property="article:author" content="{esc(SITE["author"])}">')

# articles index
body = (f'<header class=page-head><p class=kicker>Analysis</p><h1>Articles</h1><p class=lede>Plain-English analysis of direct-to-cell, satellite-to-phone and mobile networks, from an 11-year network insider.</p></header>'
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
tbody = tbody.replace('<h1>Direct-to-cell around the world</h1>', '<header class=page-head><p class=kicker>Tracker</p><h1>Direct-to-cell around the world</h1></header>' + stats_strip(), 1)
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
page(og=('Tracker', 'Direct-to-cell around the world: who is live, trialling or announced'), path='tracker.html', title=meta['title'], description=meta['description'], body=tbody, current='tracker.html', cls='is-tracker',
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
    page(og=('Tracker', f'Satellite-to-phone in {the(c)}'), path=path, title=f'Satellite-to-phone in {the(c)}', description=desc, body=body, root=root, current='tracker.html', jsonld=ld, lastmod=checked,
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
def launch_item(l, root):
    cd = f'<p class=lcd data-countdown="{l["net"]}" aria-hidden=true></p>' if l['precision'] in PRECISE else ''
    status = l.get('status') or ''
    st = f'<span class="lst{" go" if (l.get("status_abbrev") == "Go") else ""}">{esc(status)}</span>' if status else ''
    return (f'<li class="launch t-{TAG[l["tag"]][1]}" data-who="{" ".join(l["who"])}"><div class=l-when>{local_time(l)}{cd}</div>'
            f'<div class=l-body><div class=l-top>{tag_pill(l["tag"])}{st}</div><h3>{esc(l.get("mission") or l["name"])}</h3>'
            f'<p class=l-meta>{esc(l.get("rocket") or "")} · {esc(l.get("provider") or "")} · {esc(l.get("location") or "")}</p>'
            f'<p class=l-why><strong>Why it matters for your phone:</strong> {esc(TAG[l["tag"]][2])}</p>'
            f'<div class=l-act>{cal_btn(l, root)}</div></div></li>')
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
            + next_card(root) + glance(root) +
            f'<section aria-labelledby=up-h><h2 id=up-h>Upcoming launches</h2>'
            f'<p class=l-intro>{len(UPCOMING)} upcoming launches from SpaceX, AST SpaceMobile, Amazon Leo and other satellite-to-phone players, {n_phone} of them carrying phone-capable satellites. Each one is tagged by what it means for mobile.</p>'
            f'<div class=filters role=search aria-label="Filter launches"><div class=f-row><div class=chips role=group aria-label="Show launches for">{chips}</div>'
            f'<p id=l-count class=t-count role=status aria-live=polite>{len(UPCOMING)} launches</p></div></div>'
            f'<div id=launch-list><ol class=launches>{items}</ol>{more}</div><p id=l-empty class=l-empty hidden{empty} data-empty="No upcoming launches match this filter right now.">No upcoming launches match this filter right now.</p>'
            f'<p class=l-credit>{upd} Times are shown in UTC, or your local time where your browser allows. Launch dates slip often, so check again on the day. We tag a Starlink launch as Direct to Cell only when the launch data or a reliable source says it carries direct-to-cell satellites.</p></section>'
            f'<section aria-labelledby=cnt-h class=countsec><h2 id=cnt-h>Phone satellites in orbit: who has how many</h2>'
            f'<p class=l-intro>Satellites that can connect to ordinary phones, by operator. Every number has a source and a date. If a company doesn’t publish a figure and we can’t find a reliable independent one, we say so rather than guess.</p>'
            + count_rows(CONST['direct_to_device'], root) +
            f'<h3 class=bb-h>Broadband-only constellations (not phone-capable)</h3><p class=l-intro>For scale: these networks serve dishes and terminals, not phones directly.</p>'
            + count_rows(CONST['broadband_only'], root) +
            f'<p class=l-credit>Counts last checked {human(CONST["last_checked"])}. Satellite totals change with every launch and re-entry. Data: <a href="{root}data/constellations.json">constellations.json</a> · <a href="{root}data/launches.json">launches.json</a></p></section>'
            f'<section class="card tlink" aria-labelledby=tl-h><p class=kicker>From the tracker</p><h2 id=tl-h><a href="{root}tracker.html">Where these satellites already reach phones</a></h2>'
            f'<p>{C["live"]} live direct-to-cell services in {NLIVE_C} countries, plus {C["trial"]} trials and {C["announced"]} announced. See who’s live, country by country, with sources.</p>'
            f'<p class=row-cta><a class="btn ghost" href="{root}tracker.html">Open the tracker</a><a class="btn ghost" href="{root}articles/why-starship-is-a-telco-story.html">Why Starship is a telco story</a></p></section>'
            + signal_block(root, 'launches', heading='Get launch alerts in Signal', intro='Signal is our free weekly direct-to-cell briefing. Subscribe for the launches that matter for your phone and what changed in the tracker, in one email a week.'))
    ld = [crumbs([('Home', ''), ('Launches', 'launches/')]),
          {'@context': 'https://schema.org', '@type': 'Dataset', 'name': 'Full Duplex: phone-capable satellites in orbit by operator', 'description': 'Direct-to-device satellite counts by operator, each with a source and an as-of date, kept separate from broadband-only constellations.',
           'url': BASE + 'launches/', 'creator': PUBLISHER, 'isAccessibleForFree': True, 'dateModified': CONST['last_checked'],
           'distribution': [{'@type': 'DataDownload', 'encodingFormat': 'application/json', 'contentUrl': BASE + 'data/constellations.json'}]}]
    page(og=('Launches', 'Launch tracker: what’s going up, and what it means for your phone'), path='launches/index.html', title='Launch tracker',
         full_title='Launch tracker: SpaceX, AST SpaceMobile and phone-satellite launches | Full Duplex',
         description='Upcoming SpaceX, AST SpaceMobile, Amazon Leo and direct-to-cell launches, tagged by what they mean for your phone, plus a sourced count of phone-capable satellites in orbit.',
         body=body, root=root, current='launches/index.html', jsonld=ld, cls='is-launches', lastmod=(fetched or BUILD_NOW.isoformat())[:10],
         scripts=f'<script defer src="{root}assets/launches.js"></script>',
         search_text='Launch tracker. ' + ' '.join(f"{l.get('mission')} {l.get('rocket')} {TAG[l['tag']][0]}." for l in UPCOMING) + ' ' + ' '.join(f"{i['network']} {i['operator']} {i['note']}" for i in CONST['direct_to_device'] + CONST['broadband_only']))
launches_page()

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
        f'<p class=byl>By <a href="about.html">{esc(SITE["author"])}</a>, an 11-year mobile network insider · {follow_btn("xinline")}</p></div>'
        f'<figure class=globe-wrap><div id=globe class=globe role=img aria-label="Rotating globe: {NLIVE_C} countries with live direct-to-cell service in green, countries with trials in amber. Full data in the tracker."></div>'
        f'<figcaption><span class=k-live>Live</span><span class=k-trial>Trial</span><span class=k-ann>Announced</span> <a href="tracker.html">Open the map</a></figcaption></figure>'
        f'</section>'
        + stats_strip()
        + next_card('')
        + f'<section aria-labelledby=latest class=front><h2 id=latest class=sec>Latest analysis</h2><div class=front-grid>{art_card(feat, "", 3, "card feature")}'
          f'<div class=grid3>{"".join(art_card(a) for a in rest[:3])}</div></div></section>'
        + signal_block('', 'home')
        + f'<section aria-labelledby=ft-h class=from-tracker><h2 id=ft-h class=sec>From the tracker</h2><div class=two><div>{change_list(CHANGES, "", 5)}<p><a href="tracker/changes/">All tracker changes</a></p></div>'
          f'<div class="card"><h3><a href="tracker.html">Direct-to-cell tracker</a></h3><p>Who’s live, who’s trialling and who’s announced, country by country, with sources. Filter by status, provider and region, or download the CSV.</p>'
          f'<div class=cclist>{"".join(f"<a class=\"cc s-{CLS[best(rs)]}\" href=\"tracker/{country_slug(c)}/\">{esc(c)}</a>" for c, rs in sorted(COUNTRIES.items(), key=lambda kv: -RANK[best(kv[1])])[:8])}</div></div></div></section>'
        + f'<section aria-labelledby=more-h><h2 id=more-h class=sec>More analysis</h2><div class=list>{"".join(art_card(a, "", 3, "row") for a in rest[3:])}</div><p><a href="articles/index.html">All articles</a></p></section>'
        + '<section aria-labelledby=play-h class="card play"><p class=kicker>Play</p><h2 id=play-h><a href="play/constellation.html">Constellation</a></h2><p>Deploy direct-to-cell satellites into orbit. A 75-second browser game: hit the slots before time runs out.</p></section>'
        + '<aside class=sponsor-card aria-label="Sponsorship"><p class=kicker>Presented by · slot available</p><h2>Put your brand in front of the people building satellite-to-phone</h2>'
          '<p>Engineers, operator teams, investors and early adopters read Full Duplex. One sponsor at a time, always clearly labelled.</p>'
          '<p><a class="btn ghost" href="sponsor.html">See sponsor options</a></p></aside>')
ld = [{'@context': 'https://schema.org', '@type': 'WebSite', 'name': 'Full Duplex', 'url': BASE, 'inLanguage': 'en-GB', 'publisher': PUBLISHER,
       'potentialAction': {'@type': 'SearchAction', 'target': BASE + 'search.html?q={q}', 'query-input': 'required name=q'}}]
page(og=('Full Duplex', 'Your phone is about to talk to space.'), path='index.html', title='Satellite-to-phone and the future of mobile', full_title='Satellite-to-phone and the future of mobile | Full Duplex',
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
