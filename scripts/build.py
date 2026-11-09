#!/usr/bin/env python3
"""Full Duplex static site build (Python 3 standard library only).

Sources: src/ (page bodies with a JSON <!--meta ... --> header), src/site.json, data/tracker.json.
Run from anywhere:  python3 scripts/build.py   then commit the output.
GitHub Pages serves the committed files from main; there is no CI step.

Generates: every HTML page, articles/index.html, tracker.html, tracker/<country>/index.html,
tracker/changes/index.html, search.html, 404.html, data/tracker.csv, data/tracker-changes.json,
search-index.json, sitemap.xml, robots.txt, feed.xml.

The tracker change log is rebuilt from the git history of data/tracker.json when git is
available, and otherwise read back from data/tracker-changes.json.

IMAGES: no image is referenced anywhere yet. Every place an approved image will go is
marked "TODO(image-approval)". Do not add one until Sam approves a preview.
"""
import csv, html, io, json, math, pathlib, re, subprocess, sys, urllib.parse
from datetime import date

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
NAV = [('index.html', 'Home'), ('articles/index.html', 'Articles'), ('tracker.html', 'Tracker'), ('search.html', 'Search'), ('about.html', 'About'), ('sponsor.html', 'Sponsor')]

def header(root, current):
    links = ''.join(f'<a href="{root}{h}"{" aria-current=page" if h == current else ""}>{t}</a>' for h, t in NAV)
    return (f'<a class=skip href="#main">Skip to content</a><header class=site><div class=wrap><a class=logo href="{root}index.html">Full<span>Duplex</span></a>'
            f'<nav aria-label="Main">{links}</nav><div class=hdr-cta><a class=xlink href="https://x.com/{X}" target=_blank rel="noopener me">Follow @{X}</a>'
            f'<a class="btn pill" href="{esc(sub_url("header"))}">Subscribe</a></div></div></header>')

def footer(root, sticky=True):
    bar = (f'<div class=stickybar hidden role=region aria-label="Subscribe to Signal"><p><strong>Signal</strong> · the weekly direct-to-cell briefing</p>'
           f'<a class="btn pill" href="{esc(sub_url("sticky-bar"))}">Subscribe free</a><button class=x type=button aria-label="Dismiss">×</button></div>') if sticky else ''
    return (f'<footer class=site><div class=wrap><div><a class=logo href="{root}index.html">Full<span>Duplex</span></a><p>Independent analysis of satellite-to-phone and mobile networks. Made in the UK.</p>'
            f'<p class=copy>© 2026 Full Duplex.</p></div>'
            f'<nav aria-label="Footer"><a href="{esc(sub_url("footer"))}">Subscribe to Signal</a><a href="https://x.com/{X}" target=_blank rel="noopener me">Follow @{X} on X</a>'
            f'<a href="{root}articles/index.html">Articles</a><a href="{root}tracker.html">Tracker</a><a href="{root}tracker/changes/">Tracker changes</a>'
            f'<a href="{root}play/constellation.html">Constellation</a><a href="{root}search.html">Search</a><a href="{root}feed.xml">RSS</a>'
            f'<a href="{root}about.html">About</a><a href="{root}sponsor.html">Sponsor</a><a href="{root}privacy.html">Privacy</a></nav></div></footer>{bar}')

built = []  # (path, lastmod)
SEARCH = []

def page(*, path, title, description, body, root='', current='', og_type='website', jsonld=None, head_extra='', scripts='',
         viewport='width=device-width,initial-scale=1', sticky=True, full_title=None, lastmod=None, search=True, cls='', index=True, search_text=None):
    url = BASE + (path[:-len('index.html')] if path.endswith('index.html') else path)
    ft = full_title or f'{title} | Full Duplex'
    ld = ''.join(f'<script type="application/ld+json">{json.dumps(j, ensure_ascii=False)}</script>' for j in (jsonld or []))
    head = (f'<!doctype html><html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="{viewport}">'
            f'<title>{esc(ft)}</title><meta name="description" content="{esc(description)}"><link rel="canonical" href="{url}">'
            + ('' if index else '<meta name="robots" content="noindex">') +
            f'<meta name="theme-color" content="#070b14"><meta name="color-scheme" content="dark">'
            f'<meta property="og:site_name" content="Full Duplex"><meta property="og:locale" content="en_GB"><meta property="og:type" content="{og_type}">'
            f'<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(description)}"><meta property="og:url" content="{url}">'
            f'<!-- TODO(image-approval): add og:image (1200x630) + og:image:alt and switch twitter:card to summary_large_image once Sam approves the OG card preview. -->'
            f'<meta name="twitter:card" content="summary"><meta name="twitter:site" content="@{X}"><meta name="twitter:title" content="{esc(title)}"><meta name="twitter:description" content="{esc(description)}">'
            f'<link rel="alternate" type="application/rss+xml" title="Full Duplex" href="{BASE}feed.xml">'
            f'<link rel="stylesheet" href="{root}style.css">'
            f'<link rel="stylesheet" href="{root}assets/fonts.css" media="print" onload="this.media=\'all\'"><noscript><link rel="stylesheet" href="{root}assets/fonts.css"></noscript>'
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
    return (f'<article class="{cls}"><h{level}><a href="{root}articles/{a["slug"]}.html">{esc(a["title"])}</a></h{level}><p>{esc(a["summary"])}</p>{art_meta(a)}</article>')
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
            f'<!-- TODO(image-approval): article header image goes here once Sam approves the header plate preview. -->'
            f'<div class=prose>' + insert_mid(a['body'], signal_block(root, 'mid-article', 'mid')) + '</div>'
            f'<div class=share-end><p>Found this useful? Share it, or follow us for daily updates.</p>{share_btn(a["title"], url)}{follow_btn()}</div></article>'
            + signal_block(root, 'end-article')
            + f'<section class=related aria-labelledby=rel-h><h2 id=rel-h>Keep reading</h2><div class=grid3>{"".join(art_card(b, root) for b in related)}</div></section>')
    ld = [{'@context': 'https://schema.org', '@type': 'NewsArticle', 'headline': a['title'], 'description': a['description'],
           'datePublished': a['published'], 'dateModified': a.get('updated', a['published']), 'author': AUTHOR,
           'publisher': PUBLISHER, 'mainEntityOfPage': url, 'inLanguage': 'en-GB'},  # TODO(image-approval): add "image"
          crumbs([('Home', ''), ('Articles', 'articles/'), (a['title'], path)])]
    page(path=path, title=a['title'], description=a['description'], body=body, root=root, og_type='article', jsonld=ld, current='articles/index.html',
         full_title=f"{a['short_title']} | Full Duplex", lastmod=a.get('updated', a['published']), cls='is-article', search_text=strip_tags(a['body']),
         head_extra=f'<meta property="article:published_time" content="{a["published"]}"><meta property="article:author" content="{esc(SITE["author"])}">')

# articles index
body = (f'<header class=page-head><p class=kicker>Analysis</p><h1>Articles</h1><p class=lede>Plain-English analysis of direct-to-cell, satellite-to-phone and mobile networks, from an 11-year network insider.</p></header>'
        f'<div class=grid3>{"".join(art_card(a, "../", 2) for a in arts)}</div>' + signal_block('../', 'articles-index'))
page(path='articles/index.html', title='Articles', description='All Full Duplex analysis: direct-to-cell, satellite-to-phone, 2G/3G switch-off, MVNOs and the future of mobile networks.',
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
page(path='play/constellation.html', title=meta['title'], description=meta['description'], body=body, root='../', cls='is-game',
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
          f'<section aria-labelledby=ch-h><h2 id=ch-h>What changed</h2>{change_list(CHANGES, "", 8)}<p><a href="tracker/changes/">Full change log</a></p></section>'
          + signal_block('', 'tracker', heading='Get tracker updates in Signal', intro='Every week, Signal covers what changed in the tracker: new launches, trials and status changes, with the sources.'))
ld = [{'@context': 'https://schema.org', '@type': 'Dataset', 'name': 'Full Duplex direct-to-cell tracker', 'description': meta['description'],
       'url': BASE + 'tracker.html', 'creator': PUBLISHER, 'isAccessibleForFree': True, 'inLanguage': 'en-GB', 'dateModified': parse_human(TRACK['last_checked']),
       'distribution': [{'@type': 'DataDownload', 'encodingFormat': 'text/csv', 'contentUrl': BASE + 'data/tracker.csv'},
                        {'@type': 'DataDownload', 'encodingFormat': 'application/json', 'contentUrl': BASE + 'data/tracker.json'}]}]
page(path='tracker.html', title=meta['title'], description=meta['description'], body=tbody, current='tracker.html', cls='is-tracker',
     head_extra=meta['head_extra'], scripts=tscripts + '<script defer src="assets/tracker-filters.js"></script>', jsonld=ld, lastmod=parse_human(TRACK['last_checked']),
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
    page(path=path, title=f'Satellite-to-phone in {the(c)}', description=desc, body=body, root=root, current='tracker.html', jsonld=ld, lastmod=checked,
         search_text=' '.join(f"{r['operator']} with {r['satellite']}: {r['status']}. {strip_tags(r['services'])}." for r in rs))

# change log page
body = (f'<nav class=crumbs aria-label=Breadcrumb><a href="../../tracker.html">Tracker</a> <span aria-hidden=true>/</span> <span aria-current=page>Changes</span></nav>'
        f'<header class=page-head><p class=kicker>Tracker</p><h1>Tracker change log</h1><p class=lede>Every change to the direct-to-cell tracker, newest first. Generated from the tracker data’s history.</p></header>'
        + change_list(CHANGES, '../../') + signal_block('../../', 'tracker-changes', heading='Get tracker changes in Signal', intro='Signal rounds up what changed in the tracker every week.'))
page(path='tracker/changes/index.html', title='Tracker change log', description='Every change to the Full Duplex direct-to-cell tracker: new launches, trials and status changes, newest first.',
     body=body, root='../../', current='tracker.html', lastmod=CHANGES[0]['date'] if CHANGES else None,
     search_text=' '.join(it['text'] for e in CHANGES for it in e['items']))

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
home = (f'<section class=hero><div class=hero-copy><p class=kicker>Both directions, all at once</p><h1>Your phone is about to talk to space.</h1>'
        f'<p class=lede>Full Duplex explains direct-to-cell satellites, GSM and the shake-up coming to the mobile industry.</p>'
        f'<p class=hero-cta><a class=btn href="{esc(sub_url("home-hero"))}">Send me Signal</a><a class="btn ghost" href="tracker.html">Explore the tracker</a></p>'
        f'<p class=byl>By <a href="about.html">{esc(SITE["author"])}</a>, an 11-year mobile network insider · {follow_btn("xinline")}</p></div>'
        f'<figure class=globe-wrap><div id=globe class=globe role=img aria-label="Rotating globe: {NLIVE_C} countries with live direct-to-cell service in green, countries with trials in amber. Full data in the tracker."></div>'
        f'<figcaption><span class=k-live>Live</span><span class=k-trial>Trial</span><span class=k-ann>Announced</span> <a href="tracker.html">Open the map</a></figcaption></figure>'
        f'<!-- TODO(image-approval): home hero key art can sit behind the globe once Sam approves the hero preview. --></section>'
        + stats_strip()
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
          '<p><a class="btn ghost" href="sponsor.html">See sponsor options</a></p><!-- TODO(image-approval): sponsor plate background --></aside>')
ld = [{'@context': 'https://schema.org', '@type': 'WebSite', 'name': 'Full Duplex', 'url': BASE, 'inLanguage': 'en-GB', 'publisher': PUBLISHER,
       'potentialAction': {'@type': 'SearchAction', 'target': BASE + 'search.html?q={q}', 'query-input': 'required name=q'}}]
page(path='index.html', title='Satellite-to-phone and the future of mobile', full_title='Satellite-to-phone and the future of mobile | Full Duplex',
     description=SITE['home_description'], body=home, current='index.html', jsonld=ld, cls='is-home',
     scripts='<script defer src="assets/globe.js"></script>', lastmod=max(a.get('updated', a['published']) for a in arts), search=False)

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
