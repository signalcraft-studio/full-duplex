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
from urllib.parse import urlsplit as _urlsplit
BASE_PATH = _urlsplit(BASE).path or '/'  # '/' on the custom domain
# GitHub Pages custom domain: keep CNAME in step with base_url (the Deploy Pages workflow ships it).
if not _urlsplit(BASE).hostname.endswith('github.io'):
    (ROOT / 'CNAME').write_text(_urlsplit(BASE).hostname + '\n')
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

def sub_url(surface, source='fullduplex-site', content=None):
    q = {'utm_source': source, 'utm_medium': surface, 'utm_campaign': 'signal'}
    if content: q['utm_content'] = content
    return SUB + '?' + urllib.parse.urlencode(q)

def git_lastmod(*rels):
    """YYYY-MM-DD of the latest commit touching any of these repo-relative paths.
    Uncommitted or untracked changes count as today, so a preview build stays honest."""
    paths = []
    for r in rels:
        if not r: continue
        pth = pathlib.Path(r)
        pth = pth if pth.is_absolute() else (ROOT / r)
        if not pth.exists(): continue
        try: paths.append(str(pth.resolve().relative_to(ROOT)))
        except ValueError: continue
    if not paths: return None
    dates = []
    try:
        out = subprocess.check_output(['git', 'log', '-1', '--format=%cs', '--'] + paths, cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
        if out: dates.append(out)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    try:
        st = subprocess.check_output(['git', 'status', '--porcelain', '-uall', '--'] + paths, cwd=ROOT, text=True, stderr=subprocess.DEVNULL)
        if st.strip(): dates.append(date.today().isoformat())
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return max(dates) if dates else None

def inferred_sources(path):
    """Source files that usually feed a built page, used to date the sitemap."""
    rels = []
    if path.endswith('/index.html'):
        slug = path[:-len('/index.html')]
        for cand in (SRC / 'pages' / f'{slug}.html', SRC / f'{slug}.json'):
            if cand.exists(): rels.append(str(cand.relative_to(ROOT)))
    elif path.endswith('.html'):
        cand = SRC / 'pages' / path
        if cand.exists(): rels.append(str(cand.relative_to(ROOT)))
        base = pathlib.Path(path).name
        cand2 = SRC / 'pages' / base
        if cand2.exists() and str(cand2.relative_to(ROOT)) not in rels:
            rels.append(str(cand2.relative_to(ROOT)))
        if path.startswith('articles/') and path != 'articles/index.html':
            art = SRC / 'articles' / path.split('/', 1)[1]
            if art.exists(): rels.append(str(art.relative_to(ROOT)))
    return rels

def merge_lastmod(explicit, sources):
    dates = []
    if explicit: dates.append(str(explicit)[:10])
    g = git_lastmod(*(sources or []))
    if g: dates.append(g)
    return max(dates) if dates else None
def share_url(text, url):
    return 'https://x.com/intent/post?' + urllib.parse.urlencode({'text': text, 'url': url, 'via': X})
def share_btn(text, url, label='Share on X'):
    return f'<a class="btn ghost" href="{esc(share_url(text, url))}" target=_blank rel=noopener>{label}</a>'
def follow_btn(cls='btn ghost'):
    return f'<a class="{cls}" href="https://x.com/{X}" target=_blank rel="noopener me">Follow @{X}</a>'

# ---------------------------------------------------------------- Signal blocks
ISSUES_SHOWN = 5  # newest first; to add a new issue, put it at the top of "issues" in src/site.json and rebuild
def issues_list():
    li = ''.join(f'<li><a href="{esc(i["url"])}"><span class=ino>#{i["no"]}</span><span>{esc(i["title"])}</span></a></li>' for i in SITE['issues'][:ISSUES_SHOWN])
    return f'<ul class=issues aria-label="Recent issues of Signal">{li}</ul>'

def signal_block(root, surface, variant='full', heading_level=2, heading=None, intro=None, content='', source='fullduplex-site', label=None):
    """One on-brand call to action. Signing up is a link to beehiiv's hosted page, not an embed: an iframe would
    load third-party cookies and scripts before anyone chose to subscribe, which would make the privacy notice untrue.
    The first iframe was removed in the 14 Nov 2026 UAT for that reason and because the form theme squashed on phones."""
    h = f'h{heading_level}'
    privacy = f'<p class=fine>Free, one email a week. Opens beehiiv’s sign-up page; your email is used only to send Signal. Unsubscribe any time. <a href="{root}privacy.html">Privacy notice</a>.</p>'
    btn = f'<a class="btn signal-btn" href="{esc(sub_url(surface, source, content or None))}">Get Signal free <span aria-hidden=true>→</span></a>'
    aria = f' aria-label="{esc(label or "Subscribe to Signal")}"'
    intro_h = f'<p>{intro}</p>' if intro else ''
    if variant == 'mid':
        return (f'<aside class="signal mid"{aria}><p class=kicker>Signal · free weekly briefing</p>'
                f'<{h} class=signal-h>{heading or "Signal: the weekly direct-to-cell briefing from a mobile network insider with over 13 years in GSM"}</{h}>'
                f'{intro_h}<p class=signal-cta>{btn}</p>{privacy}</aside>')
    return (f'<section class=signal{aria}><div class=signal-copy><p class=kicker>Signal · free weekly briefing</p>'
            f'<{h} class=signal-h>{heading or "Get Signal: what changed in satellite-to-phone this week"}</{h}>'
            f'<p>{intro or "One email a week on direct-to-cell, mobile networks and what it means for you, from a mobile network insider with over 13 years in GSM."}</p></div>'
            f'<div class=signal-form><p class=issues-h>Recent issues</p>{issues_list()}<p class=signal-cta>{btn}'
            f'<a class=more href="{esc(SITE["archive_url"])}">Read past issues</a></p>{privacy}</div></section>')

# ---------------------------------------------------------------- chrome
NAV = [('index.html', 'Home'), ('articles/index.html', 'Articles'), ('tracker.html', 'Tracker'), ('launches/index.html', 'Launches'), ('explainers/index.html', 'Explainers'), ('inner-signal/index.html', 'Inner Signal'), ('satellites/index.html', 'Satellites'), ('check/index.html', 'Check my phone'), ('search.html', 'Search'), ('about.html', 'About')]  # Inner Signal added for launch prep (22 Nov 2026); Sponsor stays footer-only so the bar can stay on one desktop row

LOGO_MARK = ('<svg class=mark viewBox="254 250 516 516" width="44" height="44" aria-hidden="true" focusable="false">'
             '<g fill="none" stroke-width="32" stroke-linecap="round"><path d="M279 505A233 233 0 0 1 644.3 313.2" stroke="#00cfff"/><path d="M744.9 511.9A233 233 0 0 1 383.7 699.5" stroke="#fff"/></g><circle cx="423" cy="432" r="10" fill="#00cfff"/><path transform="translate(426 517.5) rotate(-15)" fill="#00cfff" fill-rule="evenodd" d="M-23.5 -57.5h47a5 5 0 0 1 5 5v105a5 5 0 0 1 -5 5h-47a5 5 0 0 1 -5 -5v-105a5 5 0 0 1 5 -5zM-8.5 -48h17.0a5.5 5.5 0 0 1 5.5 5.5v0.0a5.5 5.5 0 0 1 -5.5 5.5h-17.0a5.5 5.5 0 0 1 -5.5 -5.5v-0.0a5.5 5.5 0 0 1 5.5 -5.5z"/><g fill="#fff"><path d="M583 488h21l33 32-22 22-32-32z"/><path d="M620 492l20-21 15 14-21 22z"/><path d="M567 545l21-21 14 14-20 20z"/><circle cx="635" cy="541" r="8"/></g>' + '</svg>')  # logo A, approved by Sam 9 Nov 2026 (same as assets/logo.svg)

def header(root, current):
    # "Search" is an icon on desktop and "Follow" an X mark, so the nav (now with "Check my phone") stays on one row from 861px up
    lab = lambda h, t: (f'<svg class=nav-ico viewBox="0 0 24 24" width=18 height=18 aria-hidden=true focusable=false><circle cx=10.5 cy=10.5 r=6.5 fill=none stroke=currentColor stroke-width=2.2 /><path d="M15.5 15.5l5 5" stroke=currentColor stroke-width=2.2 stroke-linecap=round /></svg><span class=nav-t>{t}</span>' if h == 'search.html' else t)
    links = ''.join(f'<a href="{root}{h}"{" class=nav-search" if h == "search.html" else ""}{" aria-current=page" if h == current else ""}>{lab(h, t)}</a>' for h, t in NAV)
    return (f'<a class=skip href="#main">Skip to content</a><header class=site><div class=wrap><a class=logo href="{root}index.html">{LOGO_MARK}Full<span>Duplex</span></a>'
            f'<nav aria-label="Main">{links}</nav><div class=hdr-cta><a class=xlink href="https://x.com/{X}" target=_blank rel="noopener me" title="Follow @{X} on X"><svg class=x-ico viewBox="0 0 24 24" width=17 height=17 aria-hidden=true focusable=false><path fill=currentColor d="M17.75 3h3.07l-6.7 7.66L22 21h-6.17l-4.83-6.32L5.47 21H2.4l7.17-8.2L2 3h6.33l4.37 5.78L17.75 3zm-1.08 16.17h1.7L7.4 4.74H5.58l11.09 14.43z"/></svg><span class=xl-t>Follow</span><span class=sr> @{X} on X</span></a>'
            f'<a class="btn pill" href="{esc(sub_url("header"))}">Subscribe</a></div></div></header>')

def footer(root, sticky=True):
    bar = (f'<div class=stickybar hidden role=region aria-label="Subscribe to Signal"><p><strong>Signal</strong> · the weekly direct-to-cell briefing</p>'
           f'<a class="btn pill" href="{esc(sub_url("sticky-bar"))}">Subscribe free</a><button class=x type=button aria-label="Dismiss">×</button></div>') if sticky else ''
    return (f'<footer class=site><div class=wrap><div><a class=logo href="{root}index.html">{LOGO_MARK}Full<span>Duplex</span></a><p>Independent analysis of satellite-to-phone and mobile networks. Made in the UK.</p>'
            f'<p class=copy>© 2026 Full Duplex.</p></div>'
            f'<nav aria-label="Footer"><a href="{esc(sub_url("footer"))}">Subscribe to Signal</a><a href="https://x.com/{X}" target=_blank rel="noopener me">Follow @{X} on X</a>'
            f'<a href="{root}start/">Start here</a><a href="{root}articles/index.html">Articles</a><a href="{root}tracker.html">Tracker</a><a href="{root}tracker/changes/">Tracker changes</a><a href="{root}launches/">Launches</a><a href="{root}explainers/">Starship explainers</a><a href="{root}journey/">What happens when you hit send</a><a href="{root}inner-signal/">Inner Signal</a><a href="{root}satellites/">Meet the satellites</a><a href="{root}check/">Can my phone connect?</a><a href="{root}glossary/">Glossary</a>'
            f'<a href="{root}play/constellation.html">Constellation</a><a href="{root}search.html">Search</a><a href="{root}feed.xml">RSS</a>'
            f'<a href="{root}resources/">Resources</a><a href="{root}about.html">About</a><a href="{root}sponsor.html">Sponsor</a><a href="{root}privacy.html">Privacy</a><a href="{root}disclosure/">Disclosure</a></nav></div></footer>{bar}')

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
SEO = json.loads((SRC / 'seo.json').read_text())['pages']
CRUMB = {'tracker.html': [('Tracker', 'tracker.html')], 'tracker/changes/index.html': [('Tracker', 'tracker.html'), ('Change log', 'tracker/changes/')],
         'articles/index.html': [('Articles', 'articles/')], 'about.html': [('About', 'about.html')], 'sponsor.html': [('Sponsor', 'sponsor.html')],
         'privacy.html': [('Privacy', 'privacy.html')], 'search.html': [('Search', 'search.html')], 'check/index.html': [('Phone checker', 'check/')],
         'glossary/index.html': [('Glossary', 'glossary/')], 'explainers/index.html': [('Launches', 'launches/'), ('Explainers', 'explainers/')], 'inner-signal/index.html': [('Inner Signal', 'inner-signal/')], 'resources/index.html': [('Resources', 'resources/')], 'play/constellation.html': [('Constellation', 'play/constellation.html')], 'start/index.html': [('Start here', 'start/')]}
# ---------------------------------------------------------------- outbound links: /resources/ and the "Sources and further reading" boxes (src/resources.json)
RES = json.loads((SRC / 'resources.json').read_text())
def ext_link(l, label=None):
    """Plain text link to another organisation's own page: new tab, no referrer-opener, no logos, no partnership wording."""
    return f'<a href="{esc(l["url"])}" target=_blank rel="noopener">{esc(label or l["label"])}<span class=sr> (opens in a new tab)</span></a>'
def sources_box(root, key):
    """Compact box at the foot of a content page: 3-6 official links plus a pointer to /resources/."""
    ids = RES['boxes'].get(key)
    if not ids: return ''
    li = ''.join(f'<li>{ext_link(RES["links"][i])}</li>' for i in ids)
    return (f'<aside class=srcbox aria-labelledby=src-h><h2 id=src-h>Sources and further reading</h2><ul>{li}</ul>'
            f'<p class=src-more>More on the <a href="{root}resources/">Resources page</a>. Independent site, not affiliated with any company listed. Links open in a new tab.</p></aside>')

SEARCH = []

def blank_external(h):
    """Every link to another site opens in a new tab with rel=noopener (approved by Sam, 16 Nov 2026). Links to this site and links that already set a target are left alone."""
    def fix(m):
        tag = m[0]
        if re.search(r'\starget=', tag) or BASE.rstrip('/') in m[1] or 'beehiiv.com' in m[1]: return tag
        tag = re.sub(r'\srel=("[^"]*"|\S+)', lambda r: ' rel="' + ' '.join(dict.fromkeys(r[1].strip('"').split() + ['noopener'])) + '"', tag) if re.search(r'\srel=', tag) else tag[:-1] + ' rel="noopener">'
        return tag[:-1] + ' target=_blank>'
    return re.sub(r'<a\s[^>]*?href="(https?://[^"]+)"[^>]*>', fix, h)

def page(*, path, title, description, body, root='', current='', og_type='website', jsonld=None, head_extra='', scripts='',
         viewport='width=device-width,initial-scale=1', sticky=True, full_title=None, lastmod=None, sources=None, search=True, cls='', index=True, search_text=None, og=None, gloss=False, og_art=None, og_sub=None):
    url = BASE + (path[:-len('index.html')] if path.endswith('index.html') else path)
    lastmod = merge_lastmod(lastmod, list(sources or []) + inferred_sources(path))
    ft = full_title or f'{title} | Full Duplex'
    o = SEO.get(path, {})
    if o.get('title'): ft = o['title']
    if o.get('description'):
        old, description = description, o['description']
        for j in jsonld or []:
            if j.get('description') == old: j['description'] = description
    if index and path != 'index.html' and not any(j.get('@type') == 'BreadcrumbList' for j in jsonld or []):
        jsonld = (jsonld or []) + [crumbs([('Home', '')] + CRUMB.get(path, [(title, path)]))]
    if index and (len(ft) > 60 or not 70 <= len(description) <= 160): print(f'WARNING: SEO limits {path}: title {len(ft)}, description {len(description)}')
    slug = 'home' if path == 'index.html' else re.sub(r'(/index)?\.html$', '', path).replace('/', '-')
    kicker, og_title, *og_more = og or ('Full Duplex', title)
    if not index: slug = 'home'
    elif IMGS:
        dest = ROOT / 'assets' / 'og' / f'{slug}.jpg'
        if og_art:
            IMGS.og_card_art(dest, kicker, og_title, og_art, sub=og_sub)
        else:
            IMGS.og_card(dest, kicker, og_title, chips=og_more[0] if og_more else None)
    raw_body = body
    if gloss: body = gloss_html(body, root)
    og_img = f'{BASE}assets/og/{slug}.jpg'
    if index and not (ROOT / 'assets' / 'og' / f'{slug}.jpg').exists(): print('WARNING: missing OG card', slug, '(pip install pillow)')
    ld = ''.join(f'<script type="application/ld+json">{json.dumps(j, ensure_ascii=False)}</script>' for j in (jsonld or []))
    verify = (f'<meta name="google-site-verification" content="{esc(SITE["google_site_verification"])}" />'
              if SITE.get("google_site_verification") else '')
    head = (f'<!doctype html><html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="{viewport}">'
            f'<title>{esc(ft)}</title><meta name="description" content="{esc(description)}"><link rel="canonical" href="{url}">'
            + verify + ('' if index else '<meta name="robots" content="noindex">') +
            f'<link rel="icon" href="{root}assets/favicon-32.png" sizes="32x32" type="image/png"><link rel="icon" href="{root}assets/favicon.svg" sizes="any" type="image/svg+xml">'
            f'<link rel="apple-touch-icon" href="{root}assets/apple-touch-icon.png"><link rel="manifest" href="{root}site.webmanifest">'
            f'<link rel="preload" href="{root}assets/fonts/InterTight-600.woff2" as="font" type="font/woff2" crossorigin>'
            f'<link rel="preload" href="{root}assets/fonts/Newsreader-400.woff2" as="font" type="font/woff2" crossorigin><meta name="theme-color" content="#070b14"><meta name="color-scheme" content="dark">'
            f'<meta property="og:site_name" content="Full Duplex"><meta property="og:locale" content="en_GB"><meta property="og:type" content="{og_type}">'
            f'<meta property="og:title" content="{esc(ft)}"><meta property="og:description" content="{esc(description)}"><meta property="og:url" content="{url}">'
            f'<meta property="og:image" content="{og_img}"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">'
            f'<meta property="og:image:alt" content="{esc(og_title)} (Full Duplex)">'
            f'<meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="{og_img}"><meta name="twitter:image:alt" content="{esc(og_title)} (Full Duplex)"><meta name="twitter:site" content="@{X}"><meta name="twitter:title" content="{esc(ft)}"><meta name="twitter:description" content="{esc(description)}">'
            f'<link rel="alternate" type="application/rss+xml" title="Full Duplex" href="{BASE}feed.xml">'
            f'<link rel="stylesheet" href="{root}style.css">'
            f'{head_extra}{ld}</head><body{" class=" + cls if cls else ""}>')
    out = (head + header(root, current) + f'<main id=main>{body}</main>' + footer(root, sticky)
           + f'<script src="{root}assets/site.js" defer></script>{scripts}</body></html>\n')
    out = blank_external(out)
    out = re.sub(r'((?:href|src)="((?:\.\./)*)(style\.css|assets/[\w.-]+\.js))"', lambda m: f'{m[1]}?v={asset_v(m[3])}"', out)
    (ROOT / path).parent.mkdir(parents=True, exist_ok=True)
    (ROOT / path).write_text(out)
    if index: built.append((path, lastmod))
    if search: SEARCH.append({'t': title, 'u': path[:-len('index.html')] if path.endswith('index.html') else path, 'd': description, 'x': (search_text if search_text is not None else strip_tags(re.sub(r'<(aside|section) class=["]?signal.*?</\1>', ' ', raw_body, flags=re.S)))[:6000]})
    return url

LOGO = {'@type': 'ImageObject', 'url': BASE + 'assets/logo.svg', 'width': 516, 'height': 516}  # logo A
PUBLISHER = {'@type': 'Organization', '@id': BASE + '#organization', 'name': 'Full Duplex', 'url': BASE, 'logo': LOGO, 'sameAs': [f'https://x.com/{X}']}
AUTHOR = {'@type': 'Person', '@id': BASE + 'about.html#sam', 'name': SITE['author'], 'url': BASE + 'about.html'}
ORG = {'@context': 'https://schema.org', **PUBLISHER, 'description': 'Independent analysis of satellite-to-phone and mobile networks.',
       'founder': AUTHOR}
PERSON = {'@context': 'https://schema.org', **AUTHOR, 'description': 'Mobile network insider with over 13 years in GSM, writing Full Duplex.',
          'knowsAbout': ['GSM', 'Mobile networks', 'MVNOs', 'Satellite-to-phone', 'Direct-to-cell'], 'worksFor': {'@id': PUBLISHER['@id']}}
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
    return (f'<section class="lboard{" compact" if compact else ""}" aria-labelledby=lb-h><div class=lb-top><div><p class=kicker>This week in the race · data checked {human(CHECK_DAY)}</p>'
            f'<h2 id=lb-h>{"Who’s winning satellite-to-phone" if compact else "The race leaderboard"}</h2></div>'
            + ('' if compact else share_btn('Who’s winning satellite-to-phone this week? The Full Duplex race leaderboard, with sources.', BASE + 'tracker.html#lb-h'))
            + f'</div><div class=lb-grid><div class="tablewrap lbwrap"><table class=lb-table><thead>{head}</thead><tbody>{"".join(tr)}</tbody></table></div>'
            f'<div class=lb-countries><h3>Most connected countries</h3><ol>{cb}</ol></div></div><p class=l-credit>{note}</p></section>')
BUILD_DAY = date.today()
# One shared "data checked" stamp, written by scripts/daily_refresh.py (daily-refresh.yml). Falls back to the build day.
REFRESH = json.loads((ROOT / 'data/refresh.json').read_text()) if (ROOT / 'data/refresh.json').exists() else {}
CHECK_DAY = REFRESH.get('date') or BUILD_DAY.isoformat()

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
            + sources_box(root, path)
            + signal_block(root, 'end-article')
            + f'<section class=related aria-labelledby=rel-h><h2 id=rel-h>Keep reading</h2><div class=grid3>{"".join(art_card(b, root) for b in related)}</div></section>')
    ld = [{'@context': 'https://schema.org', '@type': 'NewsArticle', 'headline': a['title'], 'description': a['description'],
           'datePublished': a['published'], 'dateModified': a.get('updated', a['published']), 'author': AUTHOR,
           'publisher': PUBLISHER, 'mainEntityOfPage': url, 'inLanguage': 'en-GB', 'image': [f"{BASE}assets/og/articles-{a['slug']}.jpg"]},
          crumbs([('Home', ''), ('Articles', 'articles/'), (a['short_title'], path)])]
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
    ld = [{'@context': 'https://schema.org', '@type': 'AboutPage', 'url': BASE + 'about.html', 'name': 'About Full Duplex', 'about': {'@id': PUBLISHER['@id']}, 'mainEntity': {'@id': AUTHOR['@id']}}, PERSON, ORG] if p == 'about' else None
    page(path=f'{p}.html', title=meta['title'], description=meta['description'], body=body, current=f'{p}.html', jsonld=ld, sticky=(p != 'privacy'), search_text=strip_tags(read_src(SRC / 'pages' / f'{p}.html')[1]))

meta, body, scripts = read_src(SRC / 'pages' / 'disclosure.html')
page(path='disclosure/index.html', title=meta['title'], description=meta['description'], body=f'<div class=prose-page>{body}</div>', root='../', current='disclosure/index.html', search_text=strip_tags(body))

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
         f'</div><p class=cite><strong>Cite this tracker:</strong> Full Duplex, “Direct-to-cell tracker”, last checked {TRACK["last_checked"]}, {BASE}tracker.html</p>'
         f'<p class=cite>Tracker data: <a href="{SITE["data_license"]}" rel="license">CC BY 4.0</a>, credit Full Duplex.</p>')
tbody = tbody.replace('<!--TRACKER-TABLE-->', tracker_table())
tbody = re.sub(r'<span id=tracker-checked>.*?</span>', f"<span id=tracker-checked>{TRACK['last_checked']}</span>", tbody)
# hero + stats before the intro; filters before the table; extras after
tbody = tbody.replace('<h1>Direct-to-cell around the world</h1>', '<header class=page-head><p class=kicker>Tracker</p><h1>Direct-to-cell around the world</h1></header>' + stats_strip() + race_board(''), 1)
tbody = tbody.replace('<div class=tablewrap>', f'<section aria-labelledby=tbl-h><h2 id=tbl-h>Every tracked service</h2>{controls}{tools}<div class="tablewrap trackwrap">', 1)
tbody = tbody.replace('</div><p class=note>Spotted a change?', '</div></section><p class=note>Spotted a change?', 1)
# Signal sign-up directly under the map (22 Nov 2026), replacing the generic block that sat at the end of the page
tbody = tbody.replace('</section><section aria-labelledby=tbl-h>', '</section>' + signal_block('', 'tracker', heading='Get told when this map changes',
    intro=f"{C['live']} live services, {NLIVE_C} countries, last checked {TRACK['last_checked']}. Signal is the Friday email when those numbers move.", label='Get told when this map changes') + '<section aria-labelledby=tbl-h>', 1)
assert 'utm_medium=tracker' in tbody, 'tracker: map section not found for the Signal block'
tbody += (f'<section aria-labelledby=bc-h><h2 id=bc-h>Browse by country</h2><div class=cclist>{country_links}</div></section>'
          f'<p class=note>Next satellites going up: see the <a href="launches/">launch tracker</a> for upcoming SpaceX, AST SpaceMobile and other direct-to-cell launches, and how many phone-capable satellites each operator has in orbit.</p>'
          f'<section aria-labelledby=ch-h><h2 id=ch-h>What changed</h2>{change_list(CHANGES, "", 8)}<p><a href="tracker/changes/">Full change log</a></p></section>')
ld = [{'@context': 'https://schema.org', '@type': 'Dataset', 'name': 'Full Duplex direct-to-cell tracker', 'description': meta['description'],
       'url': BASE + 'tracker.html', 'creator': PUBLISHER, 'license': SITE['data_license'], 'isAccessibleForFree': True, 'inLanguage': 'en-GB', 'dateModified': parse_human(TRACK['last_checked']),
       'distribution': [{'@type': 'DataDownload', 'encodingFormat': 'text/csv', 'contentUrl': BASE + 'data/tracker.csv'},
                        {'@type': 'DataDownload', 'encodingFormat': 'application/json', 'contentUrl': BASE + 'data/tracker.json'}]}]
page(og=('Tracker', 'Direct-to-cell around the world', [(f"{C['live']} live", OGC['live']), (f"{C['trial']} trials", OGC['trial']), (f"{C['announced']} announced", OGC['announced']), (f'{NLIVE_C} countries live', OGC['cyan'])]), path='tracker.html', title=meta['title'], description=meta['description'], body=tbody, current='tracker.html', cls='is-tracker',
     head_extra=meta['head_extra'] + '<link rel="preload" as="image" href="assets/img/tracker-map-640.webp" media="(max-width:699px)"><link rel="preload" as="image" href="assets/img/tracker-map-1280.webp" media="(min-width:700px)">', scripts=tscripts + '<script defer src="assets/tracker-filters.js"></script>', jsonld=ld, lastmod=parse_human(TRACK['last_checked']), sources=['src/pages/tracker.html', 'data/tracker.json'],
     search_text=meta['description'] + ' ' + ' '.join(f"{r['country']} {r['operator']} {r['satellite']} {r['status']}. {strip_tags(r['services'])}." for r in ROWS))

# country pages
for c, rs in sorted(COUNTRIES.items()):
    slug = country_slug(c); path = f'tracker/{slug}/index.html'; root = '../../'
    b = best(rs); n = {s: sum(1 for r in rs if r['status'] == s) for s in RANK}
    parts = ', '.join(f"{n[s]} {s}" for s in ['live', 'trial', 'announced'] if n[s])
    checked = max(parse_human(r['checked']) for r in rs)
    ops = '; '.join(f"{r['operator']} with {r['satellite']} ({r['status']})" for r in rs)
    desc = f"Satellite-to-phone in {the(c)}: {ops}. Status, services and sources, last checked {human(checked)}."
    if len(desc) > 160: desc = f"Satellite-to-phone in {the(c)}: {len(rs)} direct-to-cell partnerships tracked ({parts}). Status, services and sources, last checked {human(checked)}."
    cards = ''.join(f'<article class="card op"><div class=op-head><h2>{r["operator"]} <span class=plus>+</span> {r["satellite"]}</h2>{pill(r["status"])}</div>'
                    f'<p>{r["services"]}</p><p class=meta>Source: {sources_html(r)} · Last checked {r["checked"]}</p></article>' for r in rs)
    rel = sorted((a for a in arts if mentions(a, c)), key=lambda a: not (c == 'United Kingdom' and a['slug'] == 'o2-satellite-uk'))[:3]  # UK: lead with the O2 Satellite explainer
    relh = f'<section aria-labelledby=rel-h><h2 id=rel-h>Related analysis</h2><div class=grid3>{"".join(art_card(a, root) for a in rel)}</div></section>' if rel else ''
    chg = [{'date': e['date'], 'items': [it for it in e['items'] if it.get('country') == c]} for e in CHANGES]
    chg = [e for e in chg if e['items']]
    chh = f'<section aria-labelledby=ch-h><h2 id=ch-h>Changes for {esc(c)}</h2>{change_list(chg, root)}</section>' if chg else ''
    body = (f'<nav class=crumbs aria-label=Breadcrumb><a href="{root}tracker.html">Tracker</a> <span aria-hidden=true>/</span> <span aria-current=page>{esc(c)}</span></nav>'
            f'<header class=page-head><p class=kicker>{esc(REGION.get(c, ""))} · {pill(b)}</p><h1>Satellite-to-phone in {esc(the(c))}</h1>'
            f'<p class=lede>{len(rs)} direct-to-cell partnership{"s" if len(rs) > 1 else ""} tracked in {esc(the(c))}: {parts}. Last checked {human(checked)}.</p>'
            f'<p class=row-cta>{share_btn(f"Satellite-to-phone in {the(c)}: who is live, trialling or announced, with sources.", BASE + path[:-10])}<a class="btn ghost" href="{root}tracker.html">All countries</a></p></header>'
            f'{cards}<p class=note>Status reflects what the source says on the date checked. Multi-country services such as Skylo are listed on the <a href="{root}tracker.html">main tracker</a>.</p>'
            + signal_block(root, 'tracker-country', heading=f'Get told when {esc(the(c))} changes', content=slug, label=f'Get told when {the(c)} changes',
                           intro=f'Live, trial and announced satellite-to-phone services in {esc(the(c))}, with the sources. One email a week, when the row moves.')
            + f'{chh}{relh}')
    ld = [crumbs([('Home', ''), ('Tracker', 'tracker.html'), (c, path[:-10])])]
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
sys.path.insert(0, str(ROOT / 'scripts')); import launch_overrides
launch_overrides.apply(LDATA['launches'])  # sourced corrections over Launch Library 2 (data/launch-overrides.json)
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
# ---- launch times (BB-2). Every time on a launch card comes from ONE UTC instant in data/launches.json
# (net / window_start / window_end, all ISO with Z). We print it three ways: UTC, UK time (GMT or BST from the
# Europe/London rules, never a fixed offset) and the launch site's local time (IANA zone per site).
from zoneinfo import ZoneInfo
UTC_Z = ZoneInfo('UTC'); UK_Z = ZoneInfo('Europe/London')
# Launch site -> IANA zone. Launch Library 2's own location.timezone_name (l['tz'], stored by fetch_launches.py) wins;
# this list covers older cached data and any site LL2 leaves blank. Unknown site = no local line (never a guess).
SITE_TZ = [(r'\bFL, USA|Florida|Cape Canaveral|Kennedy Space', 'America/New_York'), (r'\bCA, USA|California|Vandenberg', 'America/Los_Angeles'),
           (r'\bTX, USA|Texas|Starbase|Boca Chica', 'America/Chicago'), (r'\bVA, USA|Wallops', 'America/New_York'), (r'\bAK, USA|Kodiak|Alaska', 'America/Anchorage'),
           (r'\bNM, USA|Spaceport America', 'America/Denver'), (r'Kwajalein|Marshall Islands', 'Pacific/Kwajalein'), (r'French Guiana|Kourou|Guiana Space', 'America/Cayenne'),
           (r'New Zealand|Mahia|Rocket Lab LC-1', 'Pacific/Auckland'), (r'Baikonur|Kazakhstan', 'Asia/Almaty'), (r'Plesetsk|Russian Federation|Russia', 'Europe/Moscow'),
           (r'Vostochny', 'Asia/Yakutsk'), (r'Jiuquan|Xichang|Taiyuan|Wenchang|Haiyang|China|Yellow Sea', 'Asia/Shanghai'), (r'Tanegashima|Uchinoura|Japan|Taiki', 'Asia/Tokyo'),
           (r'Satish Dhawan|Sriharikota|India', 'Asia/Kolkata'), (r'Naro|South Korea|Republic of Korea', 'Asia/Seoul'), (r'Palmachim|Israel', 'Asia/Jerusalem'),
           (r'Semnan|Shahroud|Iran', 'Asia/Tehran'), (r'SaxaVord|Shetland|Sutherland|Cornwall|United Kingdom', 'Europe/London'), (r'And(ø|o)ya|Norway', 'Europe/Oslo'),
           (r'Esrange|Sweden', 'Europe/Stockholm'), (r'Woomera|Bowen|Australia', 'Australia/Adelaide'), (r'Alc[aâ]ntara|Brazil', 'America/Sao_Paulo')]
# Abbreviations that clash or that tzdata only gives as a number.
TZ_ABBR = {'Asia/Shanghai': 'CST China', 'Asia/Kolkata': 'IST India', 'Asia/Jerusalem': None}
def site_zone(l):
    if l.get('tz'):
        try: return ZoneInfo(l['tz'])
        except Exception: pass
    t = f"{l.get('location') or ''} {l.get('pad') or ''}"
    for pat, z in SITE_TZ:
        if re.search(pat, t, re.I): return ZoneInfo(z)
    return None
def zabbr(dt, z):
    key = getattr(z, 'key', '')
    if TZ_ABBR.get(key): return TZ_ABBR[key]
    a = dt.tzname() or ''
    if a[:1] in '+-' or not a:  # tzdata has no letters for this zone: show the offset, e.g. UTC-3
        off = dt.utcoffset(); m = int(off.total_seconds() // 60); sg = '+' if m >= 0 else '−'; m = abs(m)
        return f'UTC{sg}{m // 60}' + (f':{m % 60:02d}' if m % 60 else '')
    return a
def long_day(d): return d.strftime('%a, %-d %b %Y')
def time_lines(l):
    """-> one-line launch time text for a precise launch, all from the same UTC instants:
    'Sun, 29 Nov 2026 · LW 04:39–08:39 (UTC) · 04:39–08:39 (GMT) · 20:39–00:39 (PST) Sat, 28 Nov 2026'
    or 'Sun, 29 Nov 2026 · T-0 15:47 (UTC) · 15:47 (GMT) · 10:47 (EST)'. LW = launch window.
    The UK and launch-site parts add their own date only when it differs from the UTC date."""
    net = iso_dt(l['net']); ws, we = l.get('window_start'), l.get('window_end')
    a = iso_dt(ws) if ws else None; b = iso_dt(we) if we else None
    win = bool(a and b and b > a) and l['precision'] != 'Hour'
    start = a if win else net
    day = start.astimezone(UTC_Z).date()
    def part(z, label):
        x = start.astimezone(z)
        if win: t = f'{x:%H:%M}–{b.astimezone(z):%H:%M} ({label})'
        elif l['precision'] == 'Hour': t = f'{x:%H}:00 ({label})'
        else: t = f'{x:%H:%M} ({label})'
        return t + (f' {long_day(x)}' if x.date() != day else '')
    lead = 'LW ' if win else ('About ' if l['precision'] == 'Hour' else 'T-0 ')
    out = [long_day(start.astimezone(UTC_Z)), lead + part(UTC_Z, 'UTC'), part(UK_Z, start.astimezone(UK_Z).tzname())]
    z = site_zone(l)
    if z and getattr(z, 'key', '') not in ('Europe/London', 'UTC'): out.append(part(z, zabbr(start.astimezone(z), z)))
    return ' · '.join(out)
def when_text(l):
    p = l['precision']; d = iso_dt(l['net'])
    if p in ('Second', 'Minute'): return long_day(d) + f', {d:%H:%M} (UTC)'
    if p == 'Hour': return long_day(d) + f', about {d:%H}:00 (UTC)'
    if p == 'Day': return d.strftime('%a %-d %b %Y') + ' · time not set'
    if p == 'Month': return d.strftime('%B %Y') + ' · date not set'
    if p == 'Week': return 'Week of ' + d.strftime('%-d %b %Y')
    m = re.match(r'Quarter (\d)', p)
    if m: return f'Q{m.group(1)} {d.year} · date not set'
    m = re.match(r'Half (\d)', p)
    if m: return f'H{m.group(1)} {d.year} · date not set'
    if p.startswith('Year'): return f'{d.year} · date not set'
    return 'No earlier than ' + d.strftime('%-d %b %Y')
def net_text3(l):
    """Flight view's 'Planned liftoff' text: the same one-line format as the launch cards."""
    return time_lines(l) if l['precision'] in PRECISE else when_text(l)
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
LW_ABBR = '<abbr title="Launch window">LW</abbr>'
def local_time(l):
    d = iso_dt(l['net'])
    if l['precision'] in PRECISE:
        # each part stays on one line; the line wraps only between parts
        parts = [f'<span>{esc(x)}</span>'.replace('<span>LW ', f'<span>{LW_ABBR} ', 1).replace(') ', ')</span> <span>', 1) for x in time_lines(l).split(' · ')]
        return f'<time datetime="{l["net"]}" class=tz1>' + ' · '.join(parts) + '</time>'
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
        if l.get('payload_count') and l.get('override_source'):
            o = l['override_source']
            return f'{l["payload_count"]} Amazon Leo broadband satellites', 'Broadband for dishes and terminals, not phones.', {'text': 'Satellite count from', 'src': (o['label'], o['url'])}
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
    return {'m': l.get('mission') or l['name'], 'r': l.get('rocket'), 'p': l.get('location'), 'lat': pd[0], 'lon': pd[1], 'az': pd[2], 'n': min(n, 30), 'nt': n, 'c': who, 'net': l['net']}

# ---- share to X (PREVIEW for Sam's approval, 16 Nov 2026). "Post to X" is a plain x.com web intent link: no X scripts on the site.
# Each shareable infographic gets a static share page share/<slug>/index.html with its own og:image (X's crawler runs no JS and
# ignores query strings), which sends people on to the deep link with UTM tags. The 1200x630 JPEG cards (share/<slug>/card.jpg)
# are screenshots of the real globe/infographic made by scripts/render_share.py (headless Chromium + Pillow); build.py only
# writes share/items.json (what to render) and the share pages, and prunes share pages for launches that have gone.
SHARE_UTM = 'utm_source=x&utm_medium=share&utm_campaign=infographic'
SHARE_DIR = ROOT / 'share'
SHARE_MAN = json.loads((SHARE_DIR / 'manifest.json').read_text()) if (SHARE_DIR / 'manifest.json').exists() else {}
SHARE = {}  # slug -> item
SHARE_LAUNCH_IMAGES = 16  # pre-rendered cards for this many upcoming launches (phone first, then broadband; never military); the rest share the flight view's card
SHORT_WHY = {'starlink-dtc': 'More satellites that talk straight to ordinary phones means fewer gaps with no signal.',
             'starlink': 'These serve dishes, not phones, but add capacity some mobile masts rely on.',
             'ast': 'Each BlueBird adds space coverage for ordinary phones on AT&T, Verizon and Vodafone.',
             'amazon-leo': 'Broadband for dishes, not phones: Amazon’s Starlink rival for telco backhaul.',
             'd2d-other': 'Another network built to reach ordinary phones from space.',
             'other': ''}
VIA = f' via @{X}'
def share_deep(path, anchor=''): return BASE + path + ('&' if '?' in path else '?') + SHARE_UTM + (f'#{anchor}' if anchor else '')
def share_fit(text):
    """X counts any URL as 23 characters; keep text + space + URL + ' via @FullDuplexHQ' within 280."""
    room = 280 - 24 - len(VIA)
    if len(text) <= room: return text
    return text[:room - 1].rsplit(' ', 1)[0].rstrip(',;:') + '…'
def share_item(slug, *, text, title, desc, path, anchor='', alt, render=None, img=None):
    # img: a static 1200x630 card (path from the site root) for items that have no rendered card, e.g. the explainer videos
    it = {'slug': slug, 'text': share_fit(text), 'title': title, 'desc': desc, 'target': share_deep(path, anchor), 'alt': alt, 'render': render, 'img': img}
    if render: it['key'] = hashlib.sha1(json.dumps([render, title, 'jpg'], sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:10]
    SHARE[slug] = it; return it
def share_has_png(it): return bool(it.get('render')) and (SHARE_DIR / it['slug'] / 'card.jpg').exists()
def share_png(it, root): return f'{root}share/{it["slug"]}/card.jpg' if share_has_png(it) else ''
def share_link(it): return f'{BASE}share/{it["slug"]}/'
X_ICO = ('<svg class=shr-ico viewBox="0 0 24 24" width=15 height=15 aria-hidden=true focusable=false><path fill=currentColor d="M17.75 3h3.07l-6.7 7.66L22 21h-6.17l-4.83-6.32L5.47 21H2.4l7.17-8.2L2 3h6.33l4.37 5.78L17.75 3zm-1.08 16.17h1.7L7.4 4.74H5.58l11.09 14.43z"/></svg>')
DL_ICO = ('<svg class=shr-ico viewBox="0 0 24 24" width=15 height=15 aria-hidden=true focusable=false><path d="M12 4v11m0 0l-4.5-4.5M12 15l4.5-4.5M5 19.5h14" fill=none stroke=currentColor stroke-width=2.2 stroke-linecap=round stroke-linejoin=round /></svg>')
def share_bar(it, root, what, canvas=None, tag='div', extra='', keep_save=False):
    """'Post to X' + 'Save image' for one infographic. canvas: CSS selector of a live <canvas> to save (with a watermark) instead of the card."""
    png = share_png(it, root)
    save = ''
    if png or canvas or keep_save:  # keep_save: flight view swaps launches in JS, so keep a (hidden) link to fill in
        dl = f'full-duplex-{it["slug"]}.{"jpg" if png else "png"}'  # share.js saves live globes as PNG
        save = (f'<a class="btn ghost sm shr-save" href="{png or "#"}" download="{dl}"' + (f' data-canvas="{esc(canvas)}"' if canvas else '') +
                f'{"" if png else " hidden"}>{DL_ICO}<span class=shr-t>Save image</span><span class=sr> of {esc(what)}</span></a>')
    return (f'<{tag} class="shr{(" " + extra) if extra else ""}"><a class="btn ghost sm shr-x" href="{esc(share_url(it["text"], share_link(it)))}" target=_blank rel=noopener>{X_ICO}'
            f'<span class=shr-t>Post to X</span><span class=sr> about {esc(what)} (opens X in a new tab)</span></a>{save}</{tag}>')
def share_launch(l):
    """Share item for one launch: the flight view of that launch (deep link ?l=<slug>)."""
    if not l.get('slug'): return None
    s = 'l-' + l['slug'][:80]
    if s in SHARE: return SHARE[s]
    m = l.get('mission') or l['name']; r = re.sub(r'\s+Block 5$', '', l.get('rocket') or 'its rocket')
    d = iso_dt(l['net'])
    when = d.strftime('%a %-d %b') if l['precision'] in PRECISE else d.strftime('%-d %b') if l['precision'] == 'Day' else when_text(l).split(' · ')[0]
    h = payload(l)[0]; h = re.sub(r'\s*\(.*?\)', '', h)
    cnt = h if re.match(r'\d+ ', h) else ''
    lead = f'{m}: {cnt} go up on {r}, {when}.' if cnt else f'{m} goes up on {r}, {when}.'
    why = SHORT_WHY.get(l['tag'], '')
    text = ' '.join(x for x in (lead, why, 'Follow the flight stage by stage:') if x)
    pick = l['slug'] in SHARE_PICK
    return share_item(s, text=text, title=f'{m}: {r} launch, {when}', path=f'launches/flight/?l={l["slug"]}',
                      desc=(f'{cnt[:1].upper() + cnt[1:]}. ' if cnt else '') + (why or 'Follow the launch stage by stage: ascent profile, stage events and mission clock.'),
                      alt=f'Flight view infographic for {m} on {r}',
                      render={'kind': 'flight', 'page': f'launches/flight/?l={l["slug"]}&nowelcome', 'sel': '#fl-hud', 'layout': 'wide',
                              'kicker': f'Launch · {when}', 'title': m, 'sub': f'{r}' + (f' · {cnt}' if cnt else ''), 'tag': l['tag']} if pick else None)
MILITARY = re.compile(r'\b(USSF|NROL|SDA|Tranche|SICRAL|Victus|Space Force|Reconnaissance|Space Development Agency)\b', re.I)
def share_tier(l):
    """Who gets the 16 pre-rendered launch cards (Sam, 16 Nov 2026): phone/direct-to-cell first, then Starlink/Amazon Leo/OneWeb
    broadband, then other commercial communications launches. Military/NRO launches never get one (they keep the generic card)."""
    ag = ' '.join(a.get('name', '') if isinstance(a, dict) else str(a) for a in (l.get('mission_agencies') or []))
    if l.get('mission_type') == 'Government/Top Secret' or MILITARY.search(ltext(l) + ' ' + ag): return None
    if l['tag'] in ('starlink-dtc', 'ast', 'd2d-other') or 'phone' in l['who']: return 0
    if l['tag'] in ('starlink', 'amazon-leo') or re.search(r'OneWeb', ltext(l)): return 1
    if l.get('mission_type') == 'Communications': return 2
    return None
def share_pick():
    ls = [(share_tier(l), i, l) for i, l in enumerate(UPCOMING) if l.get('slug')]
    out, seen = [], {}
    for t, i, l in sorted((t, i, l) for t, i, l in ls if t is not None):
        series = re.sub(r'[\s\-#]*\d+$', '', l.get('mission') or l['name'])  # e.g. Rivada 1..12: at most 3 near-identical cards
        if t == 2 and seen.get(series, 0) >= 3: continue
        seen[series] = seen.get(series, 0) + 1; out.append(l['slug'])
    return out[:SHARE_LAUNCH_IMAGES]
SHARE_PICK = share_pick()

def launch_share(l, root):
    it = share_launch(l)
    return share_bar(it, root, f'{l.get("mission") or l["name"]}', tag='span', extra='shr-in') if it else ''
def explainer_btn(l, root):
    """Starship launches get a link to the 30-second Starship explainers (hot staging, satellite release, tower catch)."""
    if 'Starship' not in (l.get('rocket') or '') + ' ' + l['name']: return ''
    return f'<a class="btn ghost sm" href="{root}explainers/">Watch the explainer<span class=sr>s: how Starship launches, releases satellites and is caught</span></a>'
def launch_item(l, root):
    cd = f'<p class=lcd data-countdown="{l["net"]}" aria-hidden=true></p>' if l['precision'] in PRECISE else ''
    status = l.get('status') or ''
    st = f'<span class="lst{" go" if (l.get("status_abbrev") == "Go") else ""}">{esc(status)}</span>' if status else ''
    return (f'<li class="launch t-{TAG[l["tag"]][1]}" data-who="{" ".join(l["who"])}"><div class=l-when>{local_time(l)}{cd}</div>'
            f'<div class=l-body><div class=flip><div class="face front"><div class=l-top>{tag_pill(l["tag"])}{st}</div><h3>{esc(l.get("mission") or l["name"])}</h3>'
            f'<p class=l-meta>{esc(l.get("rocket") or "")} · {esc(l.get("provider") or "")} · {esc(l.get("location") or "")}</p>'
            f'<p class=l-why><strong>Why it matters for your phone:</strong> {esc(TAG[l["tag"]][2])}</p>'
            f'<div class=l-act><button type=button class="btn ghost sm flipbtn" aria-expanded=false>What’s on board<span class=sr> {esc(l.get("mission") or l["name"])}</span></button><a class="btn ghost sm" href="{flight_url(l, root)}">Flight view<span class=sr> for {esc(l.get("mission") or l["name"])}</span></a>{explainer_btn(l, root)}{cal_btn(l, root)}{launch_share(l, root)}</div></div>'
            f'<div class="face back" id="pb-{l["id"][:8]}">{payload_html(l)}<p class=l-act><button type=button class="btn ghost sm flipback">Back to launch<span class=sr> details</span></button></p></div></div></div></li>')
def human_dt(iso):
    d = iso_dt(iso); return d.strftime('%-d %b %Y, %H:%M UTC')
def next_launches(n=6):
    return [l for l in UPCOMING if l['precision'] in PRECISE and iso_dt(l['net']) > BUILD_NOW - timedelta(hours=3)][:n]
def next_card(root=''):
    q = next_launches()
    if not q: return ''
    l = q[0]
    queue = json.dumps([{'n': x['net'], 'm': x.get('mission') or x['name'], 'r': x.get('rocket'), 'p': x.get('location'), 'tl': time_lines(x), 't': TAG[x['tag']][0], 'c': TAG[x['tag']][1]} for x in q], ensure_ascii=False, separators=(',', ':'))
    ph = next((x for x in UPCOMING if x['tag'] in ('starlink-dtc', 'ast', 'd2d-other')), None)
    phone = (f'<p class=nl-phone>Next phone-satellite launch: <strong>{esc(ph.get("mission") or ph["name"])}</strong> · {esc(when_text(ph))}</p>') if ph else ''
    return (f'<section class=nextlaunch aria-labelledby=nl-h data-queue="{esc(queue)}"><div class=nl-main><p class=kicker>Next launch <span class=nl-tag>{tag_pill(l["tag"])}</span></p>'
            f'<h2 id=nl-h class=nl-title>{esc(l.get("mission") or l["name"])}</h2>'
            f'<p class=nl-meta><span class=nl-rocket>{esc(l.get("rocket") or "")}</span> · <span class=nl-pad>{esc(l.get("location") or "")}</span></p>'
            f'<p class=nl-when>{local_time(l)}</p></div>'
            f'<div class=nl-side><p class=nl-cd data-countdown="{l["net"]}" role=timer aria-live=off>T− <span>--d --h --m --s</span></p>'
            f'<p class=nl-links><a class=btn href="{root}launches/">All launches</a><a class="btn ghost" href="{flight_url(l, root)}">Flight view</a>{cal_btn(l, root)}</p></div>{phone}</section>')
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
                   f'<p class=cnote>{esc(i["note"])}</p>'
                   + (f'<p class=cnote>{esc(i["count_note"])}</p>' if i.get("count_note") else '')
                   + f'{plan}<p class=csrc>As of <time datetime="{i["as_of"]}">{human(i["as_of"])}</time> · Source: {src}</p></li>')
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
OSHORT = {'starlink-dtc': 'Starlink DTC', 'ast': 'BlueBirds', 'globalstar': 'Globalstar', 'lynk': 'Lynk'}
def orbit_panel(root):
    items = [i for i in CONST['direct_to_device'] if i['count'] and i['id'] in OSHELLS]
    cfg = [{'id': i['id'], 'n': i['count'], 'c': OCOL[i['id']], 's': [[round(f, 4), inc, alt, planes] for f, inc, alt, planes in OSHELLS[i['id']]]} for i in items]
    total = sum(i['count'] for i in items)
    li = ''.join(f'<li class="o-{i["id"]}"><i style="background:{OCOL[i["id"]]}" aria-hidden=true></i><b data-count="{i["count"]}">{i["count"]:,}</b><span>{esc(i["short"])}</span></li>' for i in items)
    asof = max(i['as_of'] for i in items)
    ups = [x for x in (liftoff(l) for l in UPCOMING) if x]
    demo = next((liftoff(l) for l in UPCOMING if l['tag'] in ('starlink-dtc', 'ast', 'd2d-other') and liftoff(l)), ups[0] if ups else None)
    queue = [x for x in (liftoff(l) for l in next_launches()) if x]
    big = sorted(items, key=lambda i: -i['count'])
    chip_order = sorted(items, key=lambda i: list(OSHORT).index(i['id']) if i['id'] in OSHORT else 9)
    osh = share_item('orbit-view', text=f'Every satellite that can talk to an ordinary phone, one dot each: {total:,} in orbit today. '
                     f'{big[0]["short"]} has {big[0]["count"]:,} of them; AST’s BlueBirds are far fewer but each one is huge.',
                     title=f'{total:,} phone-capable satellites, one dot each', path='launches/', anchor='ov-h',
                     desc='Every satellite that can talk straight to an ordinary phone, on one globe: ' + ', '.join(f'{i["count"]:,} {i["short"]}' for i in items) + '.',
                     alt=f'Globe with {total:,} dots, one per phone-capable satellite in orbit',
                     render={'kind': 'canvas', 'page': 'launches/?nowelcome', 'sel': '#orbitview', 'layout': 'square', 'kicker': f'Orbit view · {human(asof, False)}',
                             'title': f'{total:,} satellites that can talk to your phone', 'sub': 'One dot = one satellite',
                             'chips': [[f'{i["count"]:,} {OSHORT.get(i["id"], i["short"])}', OCOL[i['id']]] for i in chip_order]})
    desc = (f'Illustrative globe with {total:,} dots, one for each phone-capable satellite in orbit: '
            + ', '.join(f'{i["count"]:,} {i["short"]}' for i in items) + '. Dots circle the Earth on representative orbits.')
    return (f'<section class=orbit aria-labelledby=ov-h data-base="{root}" data-orbits="{esc(json.dumps(cfg, separators=(",", ":")))}"'
            f' data-demo="{esc(json.dumps(demo, ensure_ascii=False, separators=(",", ":")))}" data-queue="{esc(json.dumps(queue, ensure_ascii=False, separators=(",", ":")))}">'
            f'<div class=ov-copy><p class=kicker>Orbit view</p><h2 id=ov-h>Every phone-capable satellite, one dot each</h2>'
            f'<p class=ov-intro>{total:,} satellites can talk straight to ordinary phones today. Starlink has the numbers; AST’s BlueBirds are far fewer but each one is huge.</p>'
            f'<ul class=ov-legend aria-label="Phone-capable satellites in orbit by network">{li}</ul>'
            f'<p class=ov-scale><strong>1 dot = 1 satellite.</strong> Heights are to scale; the orbits are illustrative, not live positions.</p>'
            f'<p class=ov-act><button type=button class="btn sm" id=ov-launch>Watch a launch moment</button>{share_bar(osh, root, "the orbit view globe", canvas="#orbitview canvas", tag="span", extra="shr-in")}</p>'
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
    rsh = share_item('race', text=f'The race for satellites that talk to your phone, month by month since {human(first, False)[-4:]}: '
                     + ', '.join(f'{ser[k]["label"]} {fin["v"][k]:,}' for k in order[:3]) + f'. AST is aiming for about {t["value"]} BlueBirds.',
                     title='Phone-capable satellites in orbit, month by month', path='launches/', anchor='race-h',
                     desc=f'Starlink, AST SpaceMobile and the rest: phone-capable satellites in orbit from {human(first, False)} to today, with sources.',
                     alt='Bar chart race of phone-capable satellites in orbit by network',
                     render={'kind': 'dom', 'page': 'launches/?nowelcome', 'sel': '.race-chart', 'layout': 'wide', 'kicker': f'The race so far · {human(fin["d"], False)}',
                             'title': 'Satellites that can talk to your phone', 'sub': 'Working satellites in orbit, by network'})
    summary = (f'From {human(first)} to {human(fin["d"])}: ' + ', '.join(f'{ser[k]["label"]} went from {R["frames"][0]["v"][k]:,} to {fin["v"][k]:,}' for k in ser) + f'. AST’s target is about {t["value"]} BlueBirds by mid-2027.')
    return (f'<section class=race aria-labelledby=race-h data-race="{esc(json.dumps(data, ensure_ascii=False, separators=(",", ":")))}">'
            f'<p class=kicker>The race so far</p><h2 id=race-h>Phone-capable satellites in orbit, month by month</h2>'
            f'<p class=l-intro>Starlink raced ahead in 2024 and has held about 640 direct-to-cell satellites since. AST is now launching three big BlueBirds at a time towards its target of about 45.</p>'
            f'<div class=race-chart aria-hidden=true><p class=race-date>{human(fin["d"], False)}</p><div class=race-plot>{rows}{tl}</div><p class=race-event>Today, working satellites</p></div>'
            f'<p class=sr>{esc(summary)}</p>'
            f'<div class=race-ctl><button type=button class="btn sm" id=race-play>Replay the race</button>'
            f'<button type=button class="btn ghost sm" id=race-zoom aria-pressed=false>Zoom in on the smaller networks</button>{share_bar(rsh, root, "the satellite race chart", tag="span", extra="shr-in")}'
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
    chips = ''.join(f'<button type=button class=chip data-who={k} aria-pressed={"true" if k == "phone" else "false"}>{t}</button>' for k, t in WHO)
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
            f'<div id=launch-list><ol class=launches>{items}</ol>{more}</div><p class=l-allrow><button type=button class="btn ghost sm" id=l-all hidden>Show all {len(UPCOMING)} launches</button></p><p id=l-empty class=l-empty hidden{empty} data-empty="No upcoming launches match this filter right now.">No upcoming launches match this filter right now.</p>'
            f'<p class=l-credit>{upd} Times are shown in UTC, then UK time (GMT or BST), then local time at the launch site, with that day’s date if it differs. Key: LW = launch window; T-0 = planned liftoff time. Launch dates slip often, so check again on the day. We tag a Starlink launch as Direct to Cell only when the launch data or a reliable source says it carries direct-to-cell satellites.</p></section>'
            + race_section(root) +
            f'<section aria-labelledby=cnt-h class=countsec><h2 id=cnt-h>Phone satellites in orbit: who has how many</h2>'
            f'<p class=l-intro>Satellites that can connect to ordinary phones, by operator. Every number has a source and a date. If a company doesn’t publish a figure and we can’t find a reliable independent one, we say so rather than guess.</p>'
            + count_rows(CONST['direct_to_device'], root) +
            f'<h3 class=bb-h>Broadband-only constellations (not phone-capable)</h3><p class=l-intro>For scale: these networks serve dishes and terminals, not phones directly.</p>'
            + count_rows(CONST['broadband_only'], root) +
            f'<p class=l-credit>Counts last checked {human(CONST["last_checked"])}' + (f' (daily check, last run <time datetime="{REFRESH["updated"]}">{human_dt(REFRESH["updated"])}</time>; a count only gets a new date when its source confirms it)' if REFRESH.get('updated') else '') + f'. Satellite totals change with every launch and re-entry. Data: <a href="{root}data/constellations.json">constellations.json</a> · <a href="{root}data/launches.json">launches.json</a></p></section>'
            f'<section class="card tlink" aria-labelledby=tl-h><p class=kicker>From the tracker</p><h2 id=tl-h><a href="{root}tracker.html">Where these satellites already reach phones</a></h2>'
            f'<p>{C["live"]} live direct-to-cell services in {NLIVE_C} countries, plus {C["trial"]} trials and {C["announced"]} announced. See who’s live, country by country, with sources.</p>'
            f'<p class=row-cta><a class="btn ghost" href="{root}tracker.html">Open the tracker</a><a class="btn ghost" href="{root}articles/why-starship-is-a-telco-story.html">Why Starship is a telco story</a></p></section>'
            + explainers_card(root) + inner_signal_card(root) + journey_card(root) + sats_card(root)
            + sources_box(root, 'launches/index.html')
            + signal_block(root, 'launches', heading='Get launch alerts in Signal', intro='Signal is our free weekly direct-to-cell briefing. Subscribe for the launches that matter for your phone and what changed in the tracker, in one email a week.'))
    ld = [crumbs([('Home', ''), ('Launches', 'launches/')]),
          {'@context': 'https://schema.org', '@type': 'Dataset', 'name': 'Full Duplex: phone-capable satellites in orbit by operator', 'description': 'Direct-to-device satellite counts by operator, each with a source and an as-of date, kept separate from broadband-only constellations.',
           'url': BASE + 'launches/', 'creator': PUBLISHER, 'isAccessibleForFree': True, 'dateModified': CONST['last_checked'],
           'distribution': [{'@type': 'DataDownload', 'encodingFormat': 'application/json', 'contentUrl': BASE + 'data/constellations.json'}]}]
    page(og=('Launches', 'Launch tracker: what’s going up, and what it means for your phone', LAUNCH_CHIPS()), path='launches/index.html', title='Launch tracker',
         full_title='Launch tracker: SpaceX, AST SpaceMobile and phone-satellite launches | Full Duplex',
         description='Upcoming SpaceX, AST SpaceMobile, Amazon Leo and direct-to-cell launches, tagged by what they mean for your phone, plus a sourced count of phone-capable satellites in orbit.',
         body=body, root=root, current='launches/index.html', jsonld=ld, cls='is-launches', lastmod=(fetched or BUILD_NOW.isoformat())[:10],
         scripts=f'<script defer src="{root}assets/launches.js"></script><script defer src="{root}assets/orbits.js"></script><script defer src="{root}assets/race.js"></script><script defer src="{root}assets/share.js"></script>',
         search_text='Launch tracker. ' + ' '.join(f"{l.get('mission')} {l.get('rocket')} {TAG[l['tag']][0]}." for l in UPCOMING) + ' ' + ' '.join(f"{i['network']} {i['operator']} {i['note']}" for i in CONST['direct_to_device'] + CONST['broadband_only']))
# ---------------------------------------------------------------- flight view (/launches/flight/; assets/flight.js + lazy assets/flight-globe.js)
FLIGHT = json.loads((SRC / 'flight-profiles.json').read_text())['profiles']
GPR = json.loads((ROOT / 'data/gp-recent.json').read_text()) if (ROOT / 'data/gp-recent.json').exists() else None
def flight_profile(l):
    slug, rocket, text = l.get('slug') or '', l.get('rocket') or '', ltext(l)
    for p in FLIGHT:
        if p.get('match_slug') and p['match_slug'] in slug: return p
    for p in FLIGHT:
        if p.get('match_slug') or not p.get('match_rocket'): continue
        if p['match_rocket'] in rocket and (not p.get('match_text') or p['match_text'] in text): return p
    return FLIGHT[-1]
FL_NET = {'starlink-dtc': 'starlink', 'starlink': 'starlink', 'ast': 'ast', 'amazon-leo': 'amazon-leo'}
def fl_net(l):
    t = ltext(l)
    if 'Globalstar' in t: return 'globalstar'
    if 'OneWeb' in t: return 'oneweb'
    if re.search(r'\bLynk\b', t): return 'lynk'
    return FL_NET.get(l['tag'])
def flight_url(l, root): return f'{root}launches/flight/?l={l.get("slug") or l["id"]}'
def flight_events_html(p):
    return ''.join(f'<li class="fe fe-{k}" data-t="{t}"><span class=fe-t>T+{int(t) // 3600:d}:{int(t) % 3600 // 60:02d}:{int(t) % 60:02d}</span><span class=fe-b><b>{esc(lab)}</b> {esc(d)}</span></li>' for t, k, lab, d in p['events'])
def flight_page():
    root = '../../'
    ls = [l for l in UPCOMING if l.get('slug')]
    if not ls: return
    data = [{'id': l['id'], 's': l['slug'], 'm': l.get('mission') or l['name'], 'r': l.get('rocket') or '', 'pv': l.get('provider') or '', 'n': l['net'], 'pr': l['precision'],
             'w': net_text3(l), 'loc': l.get('location') or '', 'st': l.get('status') or '', 'tag': TAG[l['tag']][0], 'tc': TAG[l['tag']][1], 'why': TAG[l['tag']][2],
             'p': flight_profile(l)['id'], 'net': fl_net(l), 'ph': 'phone' in l['who'],
             'x': share_launch(l)['text'], 'sh': share_launch(l)['slug'], 'pg': int(share_has_png(share_launch(l)))} for l in ls]
    profs = {p['id']: {k: p[k] for k in ('title', 'vehicle', 'events', 'keypoints', 'booster') if k in p} | {'src': p.get('source'), 'basis': p.get('basis', ''), 'pay': p.get('payload_note', ''), 'gen': bool(p.get('generic'))} for p in FLIGHT}
    d0 = ls[0]; p0 = flight_profile(d0)
    quick = [l for l in ls if l['tag'] != 'other'][:6]
    if d0 not in quick: quick = [d0] + quick[:5]
    opts = ''.join(f'<option value="{esc(l["slug"])}"{" selected" if l is d0 else ""}>{esc(iso_dt(l["net"]).strftime("%-d %b %Y") if l["precision"] in PRECISE + ("Day",) else when_text(l).split(" · ")[0])} · {esc(l.get("mission") or l["name"])} · {esc(l.get("rocket") or "")}</option>' for l in ls)
    chips = ''.join(f'<a class=chip href="?l={esc(l["slug"])}" data-l="{esc(l["slug"])}"{" aria-current=true" if l is d0 else ""}>{esc(l.get("mission") or l["name"])}</a>' for l in quick)
    src0 = p0.get('source')
    gp_note = ''
    if GPR:
        n_sat = sum(g['n'] for g in GPR['groups']); n_l = len(GPR['groups'])
        gp_note = f'{n_sat} satellites from {n_l} recent broadband and phone-network launches'
    gsh = share_item('flight-globe', text=f'Where the newest broadband and phone satellites are right now'
                     + (f': {GPR and sum(g["n"] for g in GPR["groups"])} satellites from the last 30 days of launches' if GPR else '')
                     + ', placed on their real orbits. Fresh batches fly as a tight “train”, then spread out.',
                     title='Where the newest satellites are right now', path='launches/flight/', anchor='gl-h',
                     desc='Real orbits of satellites launched in the last 30 days for broadband and phone networks, computed from CelesTrak data.',
                     alt='Globe of recently launched broadband and phone satellites at their computed positions',
                     render={'kind': 'canvas', 'page': 'launches/flight/?nowelcome', 'sel': '#glview', 'layout': 'square', 'kicker': 'After deployment · real orbits',
                             'title': 'Where the newest satellites are right now', 'sub': gp_note[:1].upper() + gp_note[1:] if gp_note else 'From CelesTrak orbit data'})
    body = (f'<header class=page-head><p class=kicker><a href="{root}launches/">Launches</a> · Flight view</p><h1>Flight view: follow a launch, stage by stage</h1>'
            f'<p class=lede>See a launch the way the webcasts show it: the climb, each stage event and the moment the satellites are let go. Then see where the newest satellites are right now.</p>'
            f'<p class=fl-expl><a class="btn ghost sm" href="{root}explainers/">Watch the explainer</a><span>Starship Flight 15 in three 30-second animations: hot staging, satellite release and the tower catch.</span></p></header>'
            f'<section class=fl aria-labelledby=fl-h data-base="{root}"><h2 id=fl-h class=sr>Launch infographic</h2>'
            f'<div class=fl-pick><label for=fl-sel class=kicker>Choose a launch</label><select id=fl-sel>{opts}</select>'
            f'<div class=fl-quick role=group aria-label="Quick picks: phone and broadband launches">{chips}</div></div>'
            f'<div class=fl-hud id=fl-hud><div class=fl-top><div><p class=fl-mission id=fl-mission>{esc(d0.get("mission") or d0["name"])}</p>'
            f'<p class=fl-veh id=fl-veh>{esc(d0.get("rocket") or "")} · {esc(d0.get("location") or "")}</p></div>'
            f'<p class=fl-badge>Planned profile · not live telemetry</p></div>'
            f'<div class=fl-plot><svg id=fl-svg viewBox="0 0 1000 340" role=img aria-label="Ascent profile: planned altitude against time, with stage events marked" preserveAspectRatio="xMidYMid meet"></svg></div>'
            f'<div class=fl-bar><div class=fl-g><svg viewBox="0 0 120 120" aria-hidden=true><circle class=fl-gt cx=60 cy=60 r=50 pathLength=100 /><circle class=fl-gv id=fl-spd-arc cx=60 cy=60 r=50 pathLength=100 /></svg>'
            f'<p><b id=fl-spd>0</b><span>km/h</span><small>Speed (est.)</small></p></div>'
            f'<div class=fl-clockbox><p class=fl-clock id=fl-clock role=timer aria-live=off>T− --:--:--:--</p><p class=fl-next id=fl-next></p></div>'
            f'<div class=fl-g><svg viewBox="0 0 120 120" aria-hidden=true><circle class=fl-gt cx=60 cy=60 r=50 pathLength=100 /><circle class="fl-gv alt" id=fl-alt-arc cx=60 cy=60 r=50 pathLength=100 /></svg>'
            f'<p><b id=fl-alt>0</b><span>km</span><small>Altitude (est.)</small></p></div></div>'
            f'<div class=fl-ctl><div class=fl-btns role=group aria-label="Clock mode"><button type=button class="btn sm" id=fl-live aria-pressed=true>Live clock</button>'
            f'<button type=button class="btn ghost sm" id=fl-replay aria-pressed=false>Replay the flight</button></div>'
            f'<label class=fl-scrub>Scrub through the flight <input id=fl-range type=range min=0 max=1000 value=0 step=1></label></div>'
            + share_bar(share_launch(d0), root, 'this launch', extra='fl-share" id="fl-share', keep_save=True) +
            f'<p class=fl-status id=fl-status role=status aria-live=polite></p>'
            f'<p class=fl-fine id=fl-note>The clock counts to the launch time in our launch data, refreshed every hour, and every 15 minutes in the six hours before a launch. Speed and altitude follow the planned profile as if the rocket flies exactly on time and on plan. They’re our estimates, not readings from the rocket.</p></div>'
            f'<div class=fl-cols><div><h2 id=fe-h>What happens, step by step</h2><ol class=fl-events id=fl-events aria-labelledby=fe-h>{flight_events_html(p0)}</ol></div>'
            f'<aside class="card fl-side"><p class=kicker>Why it matters for your phone</p><p id=fl-why>{esc(TAG[d0["tag"]][2])}</p>'
            f'<p class=fl-pay id=fl-pay>{esc(p0.get("payload_note", ""))}</p>'
            f'<p class=kicker>Where the timeline comes from</p><p class=fl-src id=fl-src>'
            + (f'Event times: <a href="{esc(src0["url"])}">{esc(src0["label"])}</a>, checked {human(src0["checked"])}. ' if src0 else '')
            + f'{esc(p0.get("basis", ""))} Speed and altitude between events are Full Duplex estimates.</p>'
            f'<p class=fl-fine>Launch times: <a href="https://thespacedevs.com/llapi">The Space Devs Launch Library 2</a>. Times slip often; check on the day.</p></aside></div></section>'
            f'<section class="orbit flg" aria-labelledby=gl-h data-base="{root}">'
            f'<div class=ov-copy><p class=kicker>After deployment</p><h2 id=gl-h>Where the newest satellites are right now</h2>'
            f'<p class=ov-intro>Each dot is a real satellite launched in the last 30 days for a broadband or phone network, placed using its latest published orbit. A fresh batch flies as a tight “train”, then spreads out around the orbit over the following weeks.</p>'
            f'<p class=gl-sel id=gl-sel role=status aria-live=polite></p>'
            f'<div class=gl-chips id=gl-chips role=group aria-label="Highlight a launch"></div>'
            f'<p class=gl-sum id=gl-sum></p><p class=gl-time id=gl-time></p>'
            + (share_bar(gsh, root, 'the live satellite globe', canvas='#glview canvas') if GPR else '') +
            f'<div class=gl-speed role=group aria-label="Playback speed"><button type=button class="chip" data-x=1 aria-pressed=true>Real time</button><button type=button class=chip data-x=60 aria-pressed=false>×60</button><button type=button class=chip data-x=600 aria-pressed=false>×600</button></div>'
            f'<p class=checked id=gl-credit>Orbits: <a href="https://celestrak.org/">CelesTrak</a> GP data'
            + (f', fetched <time datetime="{GPR["fetched_at"]}">{human_dt(GPR["fetched_at"])}</time> ({gp_note})' if GPR else '')
            + '. Positions are computed in your browser with <a href="https://github.com/shashwatak/satellite-js">satellite.js</a> (SGP4). They’re typically within a few kilometres near the data’s date, and drift if a satellite fires its thrusters.</p></div>'
            f'<figure class=ov-fig><div id=glview class="globe ov-globe" role=img aria-label="Globe showing recently launched broadband and phone-network satellites at their computed current positions"></div>'
            f'<figcaption>Real orbits, computed in your browser. Heights to scale; dots enlarged. Drag to spin.</figcaption></figure></section>'
            f'<section class="card fl-why" aria-labelledby=sp-h><h2 id=sp-h>Why new satellites spread out</h2>'
            f'<p>Rockets drop a whole batch of satellites in one place. To cover the planet, each satellite needs its own slot, so over the following weeks they use small thrusters to climb to slightly different heights. Lower satellites go round faster than higher ones, so the batch slowly stretches into a line, then a ring.</p>'
            f'<p><strong>Why it matters for your phone:</strong> a satellite only helps your phone when it’s overhead. Until a new batch has spread out and reached its working height, it adds little coverage. That’s why a launch today usually means better gaps-in-signal coverage weeks later, not tonight.</p></section>'
            + sources_box(root, 'launches/flight/index.html')
            + signal_block(root, 'flight', heading='Get launch alerts in Signal', intro='Signal is our free weekly direct-to-cell briefing: the launches that matter for your phone, in one email a week.'))
    fdata = json.dumps({'l': data, 'p': profs}, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    body += f'<script type="application/json" id=fl-data>{fdata}</script>'
    ld = [crumbs([('Home', ''), ('Launches', 'launches/'), ('Flight view', 'launches/flight/')])]
    page(og=('Launches', 'Flight view: follow a launch, stage by stage'), path='launches/flight/index.html', title='Flight view: follow a launch, stage by stage',
         description='A webcast-style infographic for upcoming launches: ascent profile, stage events and mission clock, plus a live globe of newly launched broadband and phone satellites.',
         body=body, root=root, current='launches/index.html', jsonld=ld, cls='is-flight', lastmod=BUILD_NOW.isoformat()[:10],
         scripts=f'<script defer src="{root}assets/flight-globe.js"></script><script defer src="{root}assets/flight.js"></script><script defer src="{root}assets/share.js"></script>',
         search_text='Flight view. Launch infographic: ascent profile, Max-Q, MECO, stage separation, fairing, booster landing, SECO, payload deployment. Globe of new Starlink, Amazon Leo and phone satellites.')
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
# ---------------------------------------------------------------- Inner Signal explainer (src/pages/inner-signal.html; scroll animation in assets/inner-signal.js + .css)
def inner_signal_card(root):
    return (f'<section class="card jcard" aria-labelledby=is-h>'
            f'<img class=is-thumb src="{root}assets/img/inner-signal/p-sat.webp" width="400" height="400" alt="" decoding="async">'
            f'<div><p class=kicker>Explainer · new</p><h2 id=is-h><a href="{root}inner-signal/">Inner Signal: the life of a phone call</a></h2>'
            f'<p>Ride a phone call from a mobile in Warminster to a hiker with no mast, via satellite, then on to the bill. Fourteen animated chapters, in plain English.</p></div></section>')
def inner_signal_page():
    meta, body, _ = read_src(SRC / 'pages' / 'inner-signal.html'); root = '../'; url = BASE + 'inner-signal/'
    share = share_btn('Inner Signal: follow one phone call from a mobile in Warminster to a hiker with no mast, via satellite, all the way to the bill.', url)
    body = body.replace('<!--SHARE-TOP-->', f'<p class=row-cta>{share}{follow_btn()}</p>').replace('<!--SHARE-END-->',
        f'<div class=share-end><p>Know someone who has always wondered what happens between dialling and ringing? Send them this.</p>{share}{follow_btn()}</div>')
    mid = signal_block(root, 'inner-signal-mid', variant='mid', source='site', heading='Get the next chapter in your inbox',
                       intro='The chapters below stay here. Signal is the Friday briefing on satellite-to-phone, from a mobile network insider with over 13 years in GSM.',
                       label='Get the next chapter in your inbox')
    if '<!--MID-SIGNAL-->' not in body:
        raise SystemExit('inner-signal: missing <!--MID-SIGNAL--> placeholder after chapter 7')
    body = body.replace('<!--MID-SIGNAL-->', mid)
    body += signal_block(root, 'inner-signal', source='site', heading='Get Signal: the weekly direct-to-cell briefing', intro='One email a week on satellite-to-phone, mobile networks and what it means for you, from a mobile network insider with over 13 years in GSM. Plain English, with sources.')
    css = f'<link rel="stylesheet" href="{root}assets/inner-signal.css?v={asset_v("assets/inner-signal.css")}">'
    ld = [crumbs([('Home', ''), ('Inner Signal', 'inner-signal/')]),
          {'@context': 'https://schema.org', '@type': 'Article', 'headline': meta['title'], 'description': meta['description'], 'author': AUTHOR, 'publisher': PUBLISHER,
           'mainEntityOfPage': url, 'inLanguage': 'en-GB', 'image': [f'{BASE}assets/og/inner-signal.jpg'], 'datePublished': '2026-11-22'}]
    page(og=('Explainer', 'Inner Signal: the life of a phone call'), gloss=True, path='inner-signal/index.html', title=meta['title'], description=meta['description'],
         body=body, root=root, current='inner-signal/index.html', cls='is-inner', index=True, search=True, lastmod='2026-11-22', sources=['src/pages/inner-signal.html', 'scripts/gen_inner_signal.py'], jsonld=ld, head_extra=css,
         og_art=ROOT / 'assets' / 'img' / 'inner-signal' / 'satellite-beam.webp', og_sub='Fourteen chapters. One phone call. Via satellite.',
         scripts=f'<script defer src="{root}assets/inner-signal.js"></script>')
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
def sat_share(f, ci):
    n = ci['count'] if ci and ci.get('count') is not None else None
    lede = first_sentence(f['lede'], 150)
    if lede.split(' ', 1)[0] in ('A', 'An', 'The', 'Few'): lede = lede[:1].lower() + lede[1:]
    cnt = f' {n:,} in orbit today.' if n else ''
    return share_item(f'sat-{f["id"]}', text=f'Meet {f["short"] if f["short"] != f["name"] else f["name"]}: {lede}{cnt}{" What it looks like and how it reaches your phone:" if f["phone"] else " Why it doesn’t talk to your phone (yet):"}',
                      title=f'Meet the satellites: {f["name"]}', path='satellites/', anchor=f['id'], desc=f['lede'][:157] + ('…' if len(f['lede']) > 157 else ''),
                      alt=f'Illustration of {SAT_NAME.get(f["anim"], f["name"])} by Full Duplex',
                      render={'kind': 'dom', 'page': 'satellites/?nowelcome', 'sel': f'#{f["id"]} .sc-art > :first-child', 'layout': 'square', 'kicker': f'Meet the satellites · {f["operator"]}',
                              'title': f['name'], 'sub': (f'{n:,} in orbit · ' if n else '') + ('Talks to ordinary phones' if f['phone'] else 'Dishes only, not phones'), 'color': f['color']})
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
                  f'<p class=l-credit>Globalstar’s antenna size: TBC. Amazon Leo isn’t shown because it doesn’t talk to phones. {sc_src}</p>'
                  + share_bar(share_item('sat-scale', text='How big is the bit that talks to your phone? Lynk, Starlink and BlueBird antennas drawn to the same scale, next to a 1.8 m person. BlueBird’s is about 223 m².',
                                         title='How big is the bit that talks to your phone?', path='satellites/', anchor='scale-h',
                                         desc='Phone antennas on Lynk, Starlink Direct to Cell and AST’s BlueBirds, drawn to the same scale next to a person.',
                                         alt='Satellite phone antennas drawn to scale next to a person',
                                         render={'kind': 'dom', 'page': 'satellites/?nowelcome', 'sel': '.scale-row', 'layout': 'wide', 'kicker': 'To scale',
                                                 'title': 'How big is the bit that talks to your phone?', 'sub': 'Antennas drawn to the same scale, next to a 1.8 m person'}),
                              root, 'the antennas-to-scale chart') + '</section>')
    # infographic 2: how high they fly
    alts = [('Starlink DTC', 360, 'about 360 km', '#00cfff', ['keeptrack-dtc']), ('BlueBird', 520, 'about 520 km', '#ff9a3c', ['keeptrack-ast']),
            ('Amazon Leo', 630, '590 to 630 km', '#f5c26b', ['wiki-leo']), ('Globalstar', 1414, 'about 1,414 km', '#b58cff', ['gs-fcc-c3'])]
    al_li = ''.join(f'<li style="--c:{c}"><span class=al-n>{esc(n)}</span><span class=al-bar><i style="width:{100 * v / 1414:.1f}%"></i></span><span class=al-v>{esc(t)}</span></li>' for n, v, t, c, _ in alts)
    alt_html = (f'<section class=sat-info aria-labelledby=alt-h><p class=kicker>Height</p><h2 id=alt-h>How high they fly</h2>'
                f'<p class=l-intro>Lower satellites are closer to your phone, so the signal has less distance to cover, but each one passes overhead faster and you need more of them.</p>'
                f'<ul class=alt-chart>{al_li}<li style="--c:#6ee79a"><span class=al-n>Lynk</span><span class="al-bar tbc"></span><span class=al-v>low orbit, height TBC</span></li></ul>'
                f'<p class=l-credit>{src(["keeptrack-dtc", "keeptrack-ast", "wiki-leo", "gs-fcc-c3", "keeptrack-lynk"])}</p>'
                + share_bar(share_item('sat-height', text='How high the satellites that talk to phones fly: ' + ', '.join(f'{n} {t}' for n, v, t, c, _ in alts) + '. Closer means a stronger signal, but you need more of them.',
                                       title='How high phone satellites fly', path='satellites/', anchor='alt-h',
                                       desc='Starlink Direct to Cell, BlueBird, Amazon Leo and Globalstar altitudes compared, with sources.',
                                       alt='Bar chart of satellite altitudes',
                                       render={'kind': 'dom', 'page': 'satellites/?nowelcome', 'sel': '.alt-chart', 'layout': 'wide', 'kicker': 'Height',
                                               'title': 'How high phone satellites fly', 'sub': 'Lower is closer to your phone, but each one passes faster'}),
                            root, 'the satellite heights chart') + '</section>')
    cards = []; rows = []
    for f in fams:
        ci = const_item(f['count_id'])
        if ci and ci['count'] is not None:
            cnt = (f'<p class=sc-count><b>{ci["count"]:,}</b><span>{esc(ci["count_label"])} · as of <time datetime="{ci["as_of"]}">{human(ci["as_of"])}</time> · '
                   f'Source: <a href="{esc(ci["source"]["url"])}">{esc(ci["source"]["label"])}</a></span>'
                   + (f'<span class=sc-cnote>{esc(ci["count_note"])}</span>' if ci.get("count_note") else '') + '</p>')
            cnt_s = f'{ci["count"]:,} ({human(ci["as_of"], False)})'
        else:
            cnt = '<p class=sc-count><b>TBC</b><span>No sourced count yet</span></p>'; cnt_s = 'TBC'
        facts = ''.join(f'<div><dt>{esc(x["k"])}</dt><dd>{esc(x["v"])} {src(x["s"])}</dd></div>' for x in f['facts'])
        nxt = f'<p class=sc-next><strong>What’s next:</strong> {esc(f["next"]["v"])} {src(f["next"]["s"])}</p>'
        badge = f'<span class="sc-badge{"" if f["phone"] else " no"}">{esc(f["badge"])}</span>'
        wv = next((v for v in EXPL['sat_videos'] if v['sat'] == f['id']), None)
        watch = (f'<p class=sc-watch><a class="btn ghost sm" href="{root}explainers/#{wv["id"]}">Watch it unfold<span class=sr>: 30-second video of {esc(f["short"])}</span></a></p>' if wv else '')
        cards.append(f'<article class=satcard id="{f["id"]}" style="--c:{f["color"]}" aria-labelledby="h-{f["id"]}">'
                     f'<figure class=sc-art>{satviz.scene(f["anim"], "card")}<figcaption>Illustration drawn by Full Duplex from public descriptions. Not to scale.</figcaption></figure>'
                     f'<div class=sc-body><p class=kicker>{esc(f["operator"])}</p>{badge}<h2 id="h-{f["id"]}">{esc(f["name"])}</h2><p class=sc-lede>{esc(f["lede"])}</p>'
                     f'{cnt}<dl class=sc-facts>{facts}</dl>{nxt}{watch}{share_bar(sat_share(f, ci), root, f["name"])}</div></article>')
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
            + sources_box(root, 'satellites/index.html')
            + signal_block(root, 'satellites', heading='Get Signal: the weekly direct-to-cell briefing', intro='One email a week on satellite-to-phone, mobile networks and what it means for you, from a mobile network insider with over 13 years in GSM. Plain English, with sources.'))
    ld = [crumbs([('Home', ''), ('Meet the satellites', 'satellites/')]),
          {'@context': 'https://schema.org', '@type': 'Article', 'headline': 'Meet the satellites', 'description': 'What Starlink Direct to Cell, AST SpaceMobile BlueBird, Amazon Leo, Lynk and Globalstar satellites look like, how high they fly and how they reach an ordinary phone.',
           'author': AUTHOR, 'publisher': PUBLISHER, 'mainEntityOfPage': url, 'inLanguage': 'en-GB', 'image': [f'{BASE}assets/og/satellites.jpg'], 'datePublished': SATS['checked']}]
    page(og=('Explainer', 'Meet the satellites that talk to your phone', SAT_CHIPS()), gloss=True, path='satellites/index.html', title='Meet the satellites',
         full_title='Meet the satellites: Starlink, BlueBird, Lynk, Globalstar and Amazon Leo explained | Full Duplex',
         description='What Starlink Direct to Cell, AST SpaceMobile BlueBird, Amazon Leo, Lynk and Globalstar satellites look like, how high they fly and how they reach an ordinary phone. Plain English, with sources.',
         body=body, root=root, current='satellites/index.html', jsonld=ld, cls='is-sats', lastmod=SATS['checked'], scripts=f'<script defer src="{root}assets/share.js"></script>')
# ---------------------------------------------------------------- Starship explainer videos (/explainers/; src/explainers.json + assets/explainers/)
EXPL = json.loads((SRC / 'explainers.json').read_text())
def expl_file(rel, root): return f'{root}{rel}?v={asset_v(rel)}'
def explainers_card(root):
    return (f'<section class="card xcard" aria-labelledby=xc-h><p class=kicker>Explainers · 30 seconds each</p><h2 id=xc-h><a href="{root}explainers/">Starship explained: launch, satellite release and the catch</a></h2>'
            f'<p>Three short animations from Starship Flight 15: how the rocket splits in two, how 26 satellites leave one door, and how the tower caught the ship. Simple physics, and what it means for your phone.</p>'
            f'<p class=row-cta><a class="btn ghost" href="{root}explainers/">Watch the explainers</a></p></section>')
def explainers_page():
    root = '../'
    psh = share_item('explainers', text='Starship explained in 30 seconds: hot staging, how 26 satellites leave one door, and the first tower catch from orbit. Three short animations with the maths:',
                     title='Starship explained in 30 seconds', path='explainers/', desc='Three 30-second animations from Starship Flight 15: hot staging, satellite release and the tower catch.',
                     alt='Three Full Duplex Starship explainer videos', img='assets/explainers/card-explainers.jpg')
    figs, ld_v = '', []
    for i, v in enumerate(EXPL['videos']):
        vid, mp4, poster = v['id'], f'assets/explainers/{v["id"]}.mp4', f'assets/explainers/{v["id"]}.jpg'
        sh = share_item(f'x-{vid}', text=v['share'], title=v['title'], path='explainers/', anchor=vid, desc=v['intro'][:150].rsplit(' ', 1)[0] + '…',
                        alt=v['alt'], img=f'assets/explainers/card-{vid}.jpg')
        figs += (f'<article class=xv id={vid} aria-labelledby={vid}-h><div class=xv-media><video controls playsinline preload=metadata width=864 height=1080 poster="{expl_file(poster, root)}" aria-describedby={vid}-p>'
                 f'<source src="{expl_file(mp4, root)}" type="video/mp4"><a href="{expl_file(mp4, root)}">Download the video (MP4)</a></video></div>'
                 f'<div class=xv-copy><p class=kicker>{esc(v["kicker"])}</p><h2 id={vid}-h>{esc(v["title"])}</h2><p id={vid}-p>{esc(v["intro"])}</p>'
                 f'<p class=xv-facts>{esc(v["facts"])}</p><p class=xv-why><strong>Why it matters for your phone:</strong> {esc(v["phone"])}</p>'
                 + share_bar(sh, root, v['title']) + '</div></article>')
        ld_v.append({'@context': 'https://schema.org', '@type': 'VideoObject', 'name': v['title'], 'description': v['intro'], 'thumbnailUrl': BASE + poster,
                     'contentUrl': BASE + mp4, 'uploadDate': EXPL['updated'] + 'T12:00:00+00:00', 'duration': 'PT30S', 'publisher': PUBLISHER, 'inLanguage': 'en-GB'})
    sat_figs = ''
    for v in EXPL['sat_videos']:
        vid, mp4, poster = v['id'], f'assets/explainers/{v["file"]}.mp4', f'assets/explainers/{v["file"]}.jpg'
        vsrc = ' · '.join(f'<a href="{esc(u)}">{esc(l)}</a>' for l, u in v['sources'])
        stat = f'<p class=xv-facts>{esc(v["status"])}</p>' if v.get('status') else ''
        sat_figs += (f'<article class=xv id={vid} aria-labelledby={vid}-h><div class=xv-media><video controls playsinline preload="none" width=864 height=1080 poster="{expl_file(poster, root)}" aria-label="{esc(v["alt"])}" aria-describedby={vid}-p>'
                     f'<source src="{expl_file(mp4, root)}" type="video/mp4"><a href="{expl_file(mp4, root)}">Download the video (MP4)</a></video></div>'
                     f'<div class=xv-copy><p class=kicker>{esc(v["kicker"])}</p><h2 id={vid}-h>{esc(v["title"])}</h2><p id={vid}-p>{esc(v["intro"])}</p>{stat}'
                     f'<p class=xv-src>Sources: {vsrc}</p>'
                     f'<p class=row-cta><a class="btn ghost sm" href="{root}satellites/#{v["sat"]}">See it on the satellites page</a></p></div></article>')
        ld_v.append({'@context': 'https://schema.org', '@type': 'VideoObject', 'name': v['title'], 'description': v['intro'], 'thumbnailUrl': BASE + poster,
                     'contentUrl': BASE + mp4, 'uploadDate': EXPL['updated'] + 'T12:00:00+00:00', 'duration': 'PT30S', 'publisher': PUBLISHER, 'inLanguage': 'en-GB'})
    srcs = ' · '.join(f'<a href="{esc(s["url"])}">{esc(s["label"])}</a>' for s in EXPL['sources'])
    body = (f'<header class=page-head><p class=kicker><a href="{root}launches/">Launches</a> · Explainers</p><h1>Starship explained in 30 seconds</h1>'
            f'<p class=lede>Three short animations from Starship Flight 15 (13–14 Nov 2026): how the rocket splits in two, how 26 satellites leave one door, and how the tower caught the ship on its way back from orbit. Each shows the simple physics behind the moment. Further down: four short models of the satellites that talk to phones.</p>'
            f'<p class=row-cta>{share_bar(psh, root, "the Starship explainers", tag="span", extra="shr-in")}{follow_btn("btn ghost sm")}</p></header>'
            f'<section class=xlist aria-label="Explainer videos">{figs}</section>'
            f'<section class=xsat aria-labelledby=xs-h><p class=kicker>Satellites · 30 seconds each</p><h2 id=xs-h>The satellites, unfolded</h2>'
            f'<p class=l-intro>Four stylised 3D models of the satellites we cover: how each one is built to reach a phone, with the sources underneath. Our <a href="{root}satellites/">Meet the satellites</a> page has the facts and counts.</p>'
            f'<div class=xlist>{sat_figs}</div></section>'
            f'<section class="card tlink" aria-labelledby=xw-h><p class=kicker>Why Starship matters to telcos</p><h2 id=xw-h><a href="{root}articles/why-starship-is-a-telco-story.html">Why Starship is a telco story</a></h2>'
            f'<p>Cheaper, bigger launches change how many satellites can be put up, and that includes the satellites that talk straight to ordinary phones.</p>'
            f'<p class=row-cta><a class="btn ghost" href="{root}articles/why-starship-is-a-telco-story.html">Read the analysis</a><a class="btn ghost" href="{root}launches/flight/">Open the flight view</a><a class="btn ghost" href="{root}launches/">Upcoming launches</a></p></section>'
            f'<p class=l-credit>The animations use illustrative physics (simple models with round-number inputs), not flight telemetry. Mission times and facts: {srcs}. Videos have captions burned in, so they work with the sound off.</p>'
            + sources_box(root, 'explainers/index.html')
            + signal_block(root, 'explainers', heading='Get launch alerts in Signal', intro='Signal is our free weekly direct-to-cell briefing: the launches that matter for your phone, explained simply, in one email a week.'))
    page(og=('Explainers', 'Starship explained in 30 seconds', [('Hot staging', OGC['cyan']), ('Satellite release', OGC['live']), ('Tower catch', OGC['trial'])]),
         path='explainers/index.html', title='Starship explained in 30 seconds', full_title='Starship explainers: launch, deploy and catch | Full Duplex',
         description='Three 30-second Starship explainers from Flight 15, plus four short 3D models of the Starlink, BlueBird, Lynk and Globalstar satellites.',
         body=body, root=root, current='explainers/index.html', jsonld=ld_v, cls='is-explainers', lastmod=EXPL['updated'],
         scripts=f'<script defer src="{root}assets/share.js"></script>')

# ---------------------------------------------------------------- /resources/ (src/resources.json)
def resources_page():
    root = '../'
    secs, ld_items = '', []
    for s in RES['sections']:
        li = ''.join(f'<li>{ext_link(RES["links"][i])}<span class=res-why>{esc(RES["links"][i]["why"])}</span></li>' for i in s['items'])
        secs += (f'<section class=res-sec id={s["id"]} aria-labelledby={s["id"]}-h><h2 id={s["id"]}-h>{esc(s["title"])}</h2><p class=res-intro>{s["intro"].replace("{root}", root)}</p><ul class=res-list>{li}</ul></section>')
        ld_items += [{'@type': 'ListItem', 'position': len(ld_items) + 1, 'name': RES['links'][i]['label'], 'url': RES['links'][i]['url']} for i in s['items']]
    jump = ''.join(f'<li><a href="#{s["id"]}">{esc(s["title"])}</a></li>' for s in RES['sections'])
    body = (f'<header class=page-head><p class=kicker>Resources</p><h1>Sources and further reading</h1>'
            f'<p class=lede>The official pages, regulators, standards and data sets we use when we write about satellite-to-phone, launches and mobile networks. One line on why each is worth your time.</p>'
            f'<p class=res-disc><strong>Independent site, not affiliated with any company listed.</strong> {esc(RES["disclaimer"])}</p>'
            f'<ul class=res-jump aria-label="Jump to a section">{jump}</ul></header>'
            f'{secs}'
            f'<p class=l-credit>Links last checked {human(RES["checked"])}. Pages change and some sites block automated checks, so if a link has moved, <a href="https://x.com/{X}" target=_blank rel="noopener me">tell us on X</a>. Our own data and sources are on the <a href="{root}tracker.html">tracker</a>, the <a href="{root}launches/">launch tracker</a> and <a href="{root}satellites/">Meet the satellites</a>.</p>'
            + signal_block(root, 'resources', heading='Get Signal: the weekly direct-to-cell briefing', intro='One email a week on satellite-to-phone, mobile networks and what it means for you, from a mobile network insider with over 13 years in GSM. Plain English, with sources.'))
    ld = [{'@context': 'https://schema.org', '@type': 'CollectionPage', 'name': 'Sources and further reading', 'url': BASE + 'resources/', 'publisher': PUBLISHER, 'inLanguage': 'en-GB',
           'mainEntity': {'@type': 'ItemList', 'itemListElement': ld_items}}]
    page(og=('Resources', 'Sources and further reading', [('Launches', OGC['cyan']), ('Satellites', OGC['live']), ('Regulators', OGC['trial'])]),
         path='resources/index.html', title='Sources and further reading', full_title='Satellite, carrier and regulator links | Full Duplex',
         description='Official sites, regulators, standards and data sets for satellite-to-phone, launches and mobile networks, each with a line on why it is useful.',
         body=body, root=root, current='', jsonld=ld, cls='is-resources', lastmod=RES['checked'])
launches_page()
flight_page()
explainers_page()
resources_page()
journey_page()
inner_signal_page()
satellites_page()

def share_pages():
    """share/<slug>/index.html for every share item: per-item X card tags, then straight on to the deep link. Prunes stale items."""
    SHARE_DIR.mkdir(exist_ok=True)
    for it in SHARE.values():
        png = share_has_png(it)
        img = f'{BASE}share/{it["slug"]}/card.jpg?v={SHARE_MAN.get(it["slug"], {}).get("key", "0")}' if png else f'{BASE}{it["img"]}?v={asset_v(it["img"])}' if it.get('img') else f'{BASE}assets/og/{"launches-flight" if it["slug"].startswith("l-") else "launches"}.jpg'
        t = f'{it["title"]} | Full Duplex'; tj = json.dumps(it['target'])
        out = ('<!doctype html><html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
               f'<title>{esc(t)}</title><meta name="description" content="{esc(it["desc"])}"><meta name="robots" content="noindex,follow">'
               f'<meta property="og:site_name" content="Full Duplex"><meta property="og:locale" content="en_GB"><meta property="og:type" content="website">'
               f'<meta property="og:title" content="{esc(t)}"><meta property="og:description" content="{esc(it["desc"])}"><meta property="og:url" content="{share_link(it)}">'
               f'<meta property="og:image" content="{img}"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:image:alt" content="{esc(it["alt"])}">'
               f'<meta name="twitter:card" content="summary_large_image"><meta name="twitter:site" content="@{X}"><meta name="twitter:title" content="{esc(t)}">'
               f'<meta name="twitter:description" content="{esc(it["desc"])}"><meta name="twitter:image" content="{img}"><meta name="twitter:image:alt" content="{esc(it["alt"])}">'
               f'<meta http-equiv="refresh" content="0; url={esc(it["target"])}"><link rel="icon" href="../../assets/favicon-32.png" sizes="32x32" type="image/png">'
               f'<script>location.replace({tj})</script>'
               '<style>body{background:#070b14;color:#e8eef7;font:16px/1.5 system-ui,sans-serif;display:grid;place-items:center;min-height:90vh;margin:0}a{color:#5ec8ff}</style></head>'
               f'<body><p>Opening <a href="{esc(it["target"])}">{esc(it["title"])}</a> on Full Duplex…</p></body></html>\n')
        d = SHARE_DIR / it['slug']; d.mkdir(exist_ok=True)
        if not it.get('render') and (d / 'card.jpg').exists(): (d / 'card.jpg').unlink()  # dropped out of the pre-rendered set
        if (d / 'card.png').exists(): (d / 'card.png').unlink()  # PNG cards replaced by JPEG (Sam, 16 Nov 2026)
        if not (d / 'index.html').exists() or (d / 'index.html').read_text() != out: (d / 'index.html').write_text(out)
    for d in SHARE_DIR.iterdir():  # launches that have gone (or items we no longer make) lose their share page and card
        if d.is_dir() and d.name not in SHARE:
            for f in d.iterdir(): f.unlink()
            d.rmdir()
    items = [{'slug': it['slug'], 'key': it['key'], **it['render']} for it in SHARE.values() if it.get('render')]
    (SHARE_DIR / 'items.json').write_text(json.dumps({'_readme': 'What scripts/render_share.py renders into share/<slug>/card.jpg. Written by build.py.', 'items': items}, ensure_ascii=False, indent=1) + '\n')
    long = [it['slug'] for it in SHARE.values() if len(it['text']) + 24 + len(VIA) > 280]
    if long: print('WARNING: share text too long', long)
share_pages()


# ---------------------------------------------------------------- "Can my phone connect?" checker (src/phones.json + data/tracker.json; logic in assets/check.js)
PHONES = json.loads((SRC / 'phones.json').read_text())
def check_data():
    rows = [{'c': r['country'], 'cs': country_slug(r['country']) if r['iso_n3'] else '', 'o': r['operator'], 'os': slugify(short_op(r['operator'])),
             'p': provider(r['satellite']), 'sat': r['satellite'], 'st': r['status'], 'sv': strip_tags(r['services']),
             'src': [[x['label'], x['url']] for x in r['sources']], 'chk': r['checked'], **({'on': op_names(r['operator'])} if ';' in r['operator'] else {})} for r in ROWS]
    return {'rows': rows, 'phones': PHONES, 'checked': TRACK['last_checked'], 'base': BASE, 'sub': sub_url('check-my-phone'), 'privacy': '../privacy.html'}
def op_names(o):
    """A tracker row can group several networks ("SoftBank; NTT docomo"); the checker offers each one on its own."""
    return {slugify(short_op(n)): n.strip() for n in o.split(';') if n.strip()}
def check_ops():
    ops = {}
    for r in ROWS:
        if not r['iso_n3']: continue
        names = op_names(r['operator']) if ';' in r['operator'] else {slugify(short_op(r['operator'])): r['operator']}
        for slug, name in names.items(): ops.setdefault(country_slug(r['country']), []).append([slug, name])
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
         body=body, root=root, current='check/index.html', cls='is-check', scripts='<script defer src="../assets/check.js"></script>', lastmod=parse_human(TRACK['last_checked']), sources=['src/phones.json', 'data/tracker.json', 'assets/check.js'],
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

# ---------------------------------------------------------------- Start here (src/pages/start.html): reader onboarding, also a post-subscribe landing page
def start_page():
    meta, body, _ = read_src(SRC / 'pages' / 'start.html'); root = '../'
    body = body.replace('{{root}}', root)
    search_text = strip_tags(body)
    body += signal_block(root, 'start-here', heading='Get Signal: the weekly direct-to-cell briefing',
                         intro='One email a week on direct-to-cell, mobile networks and what it means for you, from a mobile network insider with over 13 years in GSM. Plain English, with sources.')
    desc = meta['description']
    ld = [{'@context': 'https://schema.org', '@type': 'WebPage', 'name': 'Start here', 'url': BASE + 'start/', 'description': desc,
           'isPartOf': {'@id': PUBLISHER['@id']}, 'author': AUTHOR, 'inLanguage': 'en-GB'}]
    page(og=('Start here', 'The best places to begin on Full Duplex', [('Inner Signal', OGC['cyan']), ('Check my phone', OGC['muted']), ('Launch tracker', OGC['live'])]),
         path='start/index.html', title=meta['title'], description=desc, body=body, root=root, current='', jsonld=ld, cls='is-start',
         sources=['src/pages/start.html'], search_text=search_text)
start_page()

# ---------------------------------------------------------------- search + 404
body = ('<header class=page-head><p class=kicker>Search</p><h1>Search Full Duplex</h1></header>'
        '<form class=searchbox role=search action="search.html" method=get><label for=q class=sr>Search articles, countries and operators</label>'
        '<input id=q name=q type=search placeholder="Try Starlink, Japan or 2G" autocomplete=off><button type=submit class=btn>Search</button></form>'
        '<p id=s-status class=t-count role=status aria-live=polite></p><ol id=s-results class=results></ol>'
        '<noscript><p>Search needs JavaScript. Browse the <a href="articles/index.html">articles</a> or the <a href="tracker.html">tracker</a>.</p></noscript>')
page(path='search.html', title='Search', description='Search Full Duplex articles, tracker countries and operators.', body=body, current='search.html',
     scripts='<script defer src="assets/search.js"></script>', search=False, index=True, sources=['scripts/build.py', 'assets/search.js'])
body = ('<header class=page-head><p class=kicker>404</p><h1>Lost signal</h1><p class=lede>That page isn’t here. It may have moved.</p></header>'
        f'<p class=row-cta><a class=btn href="{BASE}">Go to the home page</a><a class="btn ghost" href="{BASE}search.html">Search the site</a><a class="btn ghost" href="{BASE}tracker.html">Open the tracker</a></p>')
# 404 is served at any depth, so it uses absolute URLs
page(path='404.html', title='Page not found', description='Page not found.', body=body, root=BASE, search=False, index=False, sticky=False)

# ---------------------------------------------------------------- home: "the race to your phone" hero (assets/hero-race.js) + real-data dashboard
# REDESIGN PREVIEW (branch redesign-preview, 26 Nov 2026). Every number below is read from data/*.json; nothing is typed in by hand.
HERO_IDS = [('starlink-dtc', 'Starlink Direct to Cell', 'Starlink'), ('ast', 'AST SpaceMobile', 'AST SpaceMobile'),
            ('globalstar', 'Globalstar (iPhone)', None), ('lynk', 'Lynk / Elveo', 'Lynk / Elveo'), ('skylo', 'Skylo', 'Skylo')]
BCOL = {cid: col for _, _, cid, _, col in BOARD}
def d2d(cid): return next((i for i in CONST['direct_to_device'] if i['id'] == cid), None)
SAT_TOTAL = sum(i['count'] for i in CONST['direct_to_device'] if i['count'])
SAT_ASOF = max(i['as_of'] for i in CONST['direct_to_device'] if i['count'])
def hero_data():
    race = jdata('data/race.json')
    ser = []
    for cid, label, prov in HERO_IDS:
        c = d2d(cid)
        if not c: continue
        mx = max([f['v'].get(cid, 0) for f in race['frames']] or [0])
        ser.append({'id': cid, 'l': label, 'c': BCOL.get(cid, '#e8eef7'), 'n': c['count'], 'max': mx, **({} if c['count'] else {'note': c.get('count_label', '')})})
    phones = {}
    for cid, label, prov in HERO_IDS:
        if prov: phones[cid] = [[short_op(r['operator']), r['status']] for r in sorted((r for r in ROWS if provider(r['satellite']) == prov), key=lambda r: -RANK[r['status']])]
    # Globalstar has no operator deals in the tracker: its "phone" is the iPhone, per data/constellations.json
    if d2d('globalstar'): phones['globalstar'] = [['iPhone', 'device']]
    frames = [[f['d'], {k: v for k, v in f['v'].items()}] for f in race['frames']]
    events = [[e['d'], e['s'], e['t']] for e in race['events']]
    return {'s': ser, 'f': frames, 'e': events, 'p': phones}
def hero_race():
    D = hero_data(); race = jdata('data/race.json')
    leo = next((i for i in CONST['broadband_only'] if i['id'] == 'amazon-leo'), None)
    nph = {k: len(v) for k, v in D['p'].items()}
    legend = ''.join(f'<li><i style="background:{s["c"]}" aria-hidden=true></i>{esc(s["l"])} <b>{s["n"]:,}</b></li>' if s['n'] else
                     f'<li><i class=hollow style="border-color:{s["c"]}" aria-hidden=true></i>{esc(s["l"])} <b>{esc(s.get("note", ""))}</b></li>' for s in D['s'])
    ms = ''.join(f'<li><time datetime="{e[0]}">{human(e[0])}</time> {esc(e[2])}</li>' for e in D['e'])
    alt = (f'Animation: Earth in the centre with one cluster of dots per network, one dot per phone-capable satellite, growing month by month from {human(race["frames"][0]["d"], False)} to '
           f'{human(race["frames"][-1]["d"])}. Today: ' + ', '.join(f'{s["n"]:,} {s["l"]}' for s in D['s'] if s['n']) +
           f'. Then small phones appear for each partner network in our tracker, coloured live, trial or announced.')
    tot = (f'<ul class=hr-totals aria-label="Totals today"><li><b>{C["live"]}</b><span>live services</span></li><li><b>{NLIVE_C}</b><span>countries live</span></li>'
           f'<li><b>{SAT_TOTAL:,}</b><span>satellites</span></li></ul>')
    cta = (f'<p class=hr-cta><a class="btn hr-primary" href="check/">Check your phone</a><a class="btn ghost" href="{esc(sub_url("home-hero"))}">Get Signal free</a></p>')
    return (f'<section class="hero hr" aria-labelledby=hr-h><div class=hr-copy><p class=kicker>The race to your phone · data checked {human(CHECK_DAY)}</p>'
            f'<h1 id=hr-h>Your phone is about to talk to space.</h1>'
            f'<p class=lede>Satellites that connect straight to ordinary phones are going up every month. We track who’s live, where, and whether your phone can join in.</p>'
            + cta +
            f'<div class=hr-author><span class=hr-av aria-hidden=true>SB</span><p><strong>Plain English from a network insider.</strong> '
            f'By <a href="about.html">{esc(SITE["author"])}</a>, 13+ years in mobile networks (GSM). {follow_btn("xinline")}</p></div>'
            f'<p class=start-hint>New here? <a href="start/">Start here</a>.</p></div>'
            f'<figure class=hr-fig><div id=hr-stage class=hr-stage data-race="{esc(json.dumps(D, ensure_ascii=False, separators=(",", ":")))}">'
            f'<div class=hr-cv><canvas role=img aria-label="{esc(alt)}"></canvas><div class=hr-brand aria-hidden=true>{LOGO_MARK}Full<span>Duplex</span></div></div>'
            f'<div class=hr-bar><div class=hr-clock aria-live=off><span class=hr-date>{esc(human(race["frames"][-1]["d"]))}</span><span class=hr-tot><b>{SAT_TOTAL:,}</b> phone-capable satellites in orbit</span></div>'
            f'<div class=hr-msg><div class=hr-pops aria-hidden=true></div><div class=hr-end>{tot}<p class=hr-clipcta aria-hidden=true>Check your phone at <b>fullduplexhq.com</b></p></div></div>'
            f'<button type=button id=hr-replay class="btn ghost sm hr-replay">↻ Replay<span class=sr> the animation</span></button></div></div>'
            f'<figcaption><ul class=hr-legend aria-label="Phone-capable satellites in orbit, by network">{legend}</ul>'
            f'<p>1 dot = 1 satellite, from <a href="launches/#cnt-h">our launch tracker</a> (as of {human(SAT_ASOF)}). Phones = partner networks in the <a href="tracker.html">tracker</a> '
            f'(<span class=k-live>live</span> <span class=k-trial>trial</span> <span class=k-ann>announced</span>).'
            + (f' Amazon Leo ({leo["count"]:,}) isn’t shown: it serves dishes, not phones.' if leo and leo.get('count') else '') + '</p>'
            f'<details><summary>Milestones in this animation</summary><ol class=hr-ms>{ms}</ol><p>From <a href="launches/#race-h">the race chart</a> data, each with a source.</p></details></figcaption></figure></section>')

def spark(vals, w=120, h=34):
    if len(vals) < 2: return ''
    lo, hi = min(vals), max(vals); rng = (hi - lo) or 1
    pts = ' '.join(f'{i * w / (len(vals) - 1):.1f},{h - 3 - (v - lo) / rng * (h - 6):.1f}' for i, v in enumerate(vals))
    return f'<svg class=spark viewBox="0 0 {w} {h}" width={w} height={h} aria-hidden=true focusable=false><polyline points="{pts}" fill=none stroke=currentColor stroke-width=1.6 stroke-linejoin=round /></svg>'
def dash():
    race = jdata('data/race.json'); tot_series = [sum(f['v'].values()) for f in race['frames']]
    last_ch = CHANGES[0] if CHANGES else None
    def added(st): return sum(1 for it in (last_ch or {}).get('items', []) if it['type'] == 'added' and it['status'] == st)
    skylo_multi = next((r for r in ROWS if provider(r['satellite']) == 'Skylo' and not r['iso_n3'] and r['status'] == 'live'), None)
    trk = f'<p class=d-stamp>Tracker · checked <time datetime="{parse_human(TRACK["last_checked"])}">{TRACK["last_checked"]}</time></p>'
    n_all = sum(C.values())
    split = ''.join(f'<i class=s-{CLS[k]} style="width:{100 * C[k] / n_all:.1f}%"></i>' for k in ('live', 'trial', 'announced'))
    tiles = (f'<li class="dtile t-live"><p class=d-lab>Live services</p><p class=d-num>{C["live"]}</p>'
             f'<p class=d-sub>of {n_all} tracked deals: {C["trial"]} trial, {C["announced"]} announced</p><span class=d-split aria-hidden=true>{split}</span>{trk}</li>'
             f'<li class="dtile t-cty"><p class=d-lab>Countries with live service</p><p class=d-num>{NLIVE_C}</p>'
             + (f'<p class=d-sub>plus Skylo in {esc(skylo_multi["country"])} via partners</p>' if skylo_multi else '') + f'{trk}</li>'
             f'<li class="dtile t-trial"><p class=d-lab>Trials running</p><p class=d-num>{C["trial"]}</p>'
             + (f'<p class=d-sub>{added("trial")} added on {human(last_ch["date"], False)}, {added("live")} new live</p>' if last_ch and (added('trial') or added('live')) else '') + f'{trk}</li>'
             f'<li class="dtile t-sat"><p class=d-lab>Phone-capable satellites</p><p class=d-num>{SAT_TOTAL:,}</p>'
             f'<p class=d-sub>in orbit, by month since {human(race["frames"][0]["d"], False)}</p>{spark(tot_series)}'
             f'<p class=d-stamp>Data checked <time datetime="{CHECK_DAY}">{human(CHECK_DAY)}</time></p></li>')
    # provider leaderboard (same ranking as the tracker's leaderboard: board_rows)
    rows = board_rows(); top_live = max([x['n']['live'] for x in rows] or [1]) or 1
    tr = []
    for i, x in enumerate(rows, 1):
        c = x['const']
        sat = f'{c["count"]:,}' if c and c.get('count') is not None else esc((c or {}).get('count_display') or 'n/a')
        if x['prov']:
            pills = ''.join(f'<span class="dpill s-{CLS[k]}">{x["n"][k]} {LABEL[k].lower()}</span>' for k in ('live', 'trial', 'announced') if x['n'][k])
            cn = f'{len(x["live_c"])}' + (f' <small>+{x["multi_n"]} via partners</small>' if x['multi_n'] else '')
        else:
            pills = '<span class="dpill s-dev">iPhone features</span>'; cn = '<span class=lb-na>n/a</span>'
        bar = f'<span class=d-bar aria-hidden=true><i style="width:{max(2, 100 * x["n"]["live"] / top_live):.0f}%"></i></span>' if x['prov'] else ''
        tr.append(f'<tr style="--c:{x["col"]}"><td class=d-rk>{i}</td><th scope=row><i aria-hidden=true></i>{esc(x["label"])}</th>'
                  f'<td data-l="Status">{pills}{bar}</td><td data-l="Countries live">{cn}</td><td data-l="Satellites">{sat}</td></tr>')
    board = (f'<section class="dcard d-board" aria-labelledby=db-h><div class=d-head><h2 id=db-h>Provider leaderboard</h2><a href="tracker.html#lb-h">Full leaderboard →</a></div>'
             f'<div class=tablewrap><table class=d-table><thead><tr><th scope=col><span class=sr>Rank</span>#</th><th scope=col>Provider</th><th scope=col>Tracker status</th><th scope=col>Countries live</th><th scope=col>Satellites</th></tr></thead>'
             f'<tbody>{"".join(tr)}</tbody></table></div><p class=d-stamp>Ranked by live services, then countries. Tracker {TRACK["last_checked"]} · satellites {human(CONST["last_checked"])}, <a href="launches/#cnt-h">sources</a>.</p></section>')
    # orbit heights, to scale (the orbit view's shells: OSHELLS, from McDowell's catalogue)
    items = [i for i in CONST['direct_to_device'] if i['count'] and i['id'] in OSHELLS]
    alts = sorted({(OSHELLS[i['id']][0][2], i['id']) for i in items})
    W_, H_, top_km = 300, 190, 1500
    y = lambda km: H_ - 18 - km / top_km * (H_ - 34)
    lines = []; ly_prev = -99
    for alt, cid in sorted(alts, reverse=True):  # top to bottom; labels never overlap
        it = d2d(cid); yy = y(alt); ly = max(yy - 5, ly_prev + 14); ly_prev = ly
        lines.append(f'<line x1=8 x2={W_ - 8} y1={yy:.1f} y2={yy:.1f} stroke="{OCOL[cid]}" stroke-opacity=.55 stroke-dasharray="2 3" />'
                     f'<circle cx={W_ - 24} cy={yy:.1f} r=3.4 fill="{OCOL[cid]}" />'
                     f'<text x=12 y={ly:.1f} fill="#e8eef7" font-size=10.5><tspan fill="{OCOL[cid]}">●</tspan> {esc(OSHORT[cid])} · {it["count"]:,} sats · {alt:,} km</text>')
    orbit = (f'<section class="dcard d-orbit" aria-labelledby=do-h><div class=d-head><h2 id=do-h>How high they fly</h2><a href="launches/#ov-h">Orbit view →</a></div>'
             f'<svg viewBox="0 0 {W_} {H_}" role=img aria-label="Orbit heights to scale: ' + '; '.join(f'{OSHORT[c]} {a:,} km' for a, c in alts) + '">'
             f'<defs><linearGradient id=dgE x1=0 x2=0 y1=0 y2=1><stop offset=0 stop-color="#2a5c9a"/><stop offset=1 stop-color="#081a33"/></linearGradient></defs>'
             f'<rect x=0 y={H_ - 18} width={W_} height=18 fill="url(#dgE)" /><text x=8 y={H_ - 5} fill="#9fb0c3" font-size=10>Earth’s surface · 0 km</text>'
             + ''.join(lines) + f'</svg><p class=d-stamp>Heights to scale. Skylo uses partners’ geostationary satellites, far above this chart.</p></section>')
    # daily data status (data/refresh.json + data/launches.json)
    chk = REFRESH.get('checks', []); ver = sum(1 for c in chk if c['status'] == 'verified'); man = sum(1 for c in chk if c['status'] == 'manual')
    lf = LDATA.get('fetched_at')
    status = (f'<section class="dcard d-status" aria-labelledby=ds-h><h2 id=ds-h>Mission control</h2>'
              f'<nav aria-label="Dashboard shortcuts"><ul class=d-nav><li><a href="tracker.html">Tracker</a></li><li><a href="check/">Check my phone</a></li><li><a href="launches/">Launches</a></li>'
              f'<li><a href="articles/index.html">Articles</a></li><li><a href="play/constellation.html">Play</a></li><li><a href="sponsor.html">Sponsor</a></li></ul></nav>'
              f'<h3>Data status</h3><ul class=d-log>'
              + (f'<li><span class="dot ok" aria-hidden=true></span>Daily check <time datetime="{REFRESH["updated"]}">{human_dt(REFRESH["updated"])}</time>: {ver} sources confirmed, {man} checked by hand</li>' if REFRESH.get('updated') else '')
              + (f'<li><span class="dot ok" aria-hidden=true></span>Launches refreshed <time datetime="{lf}">{human_dt(lf)}</time></li>' if lf else '')
              + f'<li><span class=dot aria-hidden=true></span>Tracker rows read by hand, last {TRACK["last_checked"]}</li></ul></section>')
    nl = next_card('')
    return (f'<section class=dash aria-labelledby=dash-h><div class=dash-top><div><p class=kicker>Dashboard · real data, sources linked</p><h2 id=dash-h>Where satellite-to-phone stands today</h2></div>'
            f'<p class=d-stamp>Data checked <time datetime="{CHECK_DAY}">{human(CHECK_DAY)}</time></p></div>'
            f'<ul class=dtiles aria-label="Key numbers">{tiles}</ul>'
            f'<div class=dgrid><div class=d-nl>{nl}</div><div class=d-ck>{check_box("")}</div>{board}{status}{orbit}</div></section>')

# ---------------------------------------------------------------- home
feat, rest = arts[0], arts[1:]
home = (hero_race()
        + dash()
        + f'<section aria-labelledby=latest class=front><h2 id=latest class=sec>Latest analysis</h2><div class=front-grid>{art_card(feat, "", 3, "card feature")}'
          f'<div class=grid3>{"".join(art_card(a) for a in rest[:3])}</div></div></section>'
        + signal_block('', 'home')
        + f'<section aria-labelledby=ft-h class=from-tracker><h2 id=ft-h class=sec>From the tracker</h2><div class=two><div>{change_list(CHANGES, "", 5)}<p><a href="tracker/changes/">All tracker changes</a></p></div>'
          f'<div class="card"><h3><a href="tracker.html">Direct-to-cell tracker</a></h3><p>Who’s live, who’s trialling and who’s announced, country by country, with sources. Filter by status, provider and region, or download the CSV.</p>'
          f'<div class=cclist>{"".join(f"<a class=\"cc s-{CLS[best(rs)]}\" href=\"tracker/{country_slug(c)}/\">{esc(c)}</a>" for c, rs in sorted(COUNTRIES.items(), key=lambda kv: -RANK[best(kv[1])])[:8])}</div></div></div></section>'
        + f'<section aria-labelledby=more-h><h2 id=more-h class=sec>More analysis</h2><div class=list>{"".join(art_card(a, "", 3, "row") for a in rest[3:])}</div><p><a href="articles/index.html">All articles</a></p></section>'
        + '<section aria-labelledby=play-h class="card play"><p class=kicker>Play</p><h2 id=play-h><a href="play/constellation.html">Constellation</a></h2><p>Deploy direct-to-cell satellites into orbit. A 75-second browser game: hit the slots before time runs out.</p></section>'
        + inner_signal_card('') + journey_card('')
        + '<aside class=sponsor-card aria-label="Sponsorship"><p class=kicker>Presented by · slot available</p><h2>Put your brand in front of the people building satellite-to-phone</h2>'
          '<p>Engineers, operator teams, investors and early adopters read Full Duplex. One sponsor at a time, always clearly labelled.</p>'
          '<p><a class="btn ghost" href="sponsor.html">See sponsor options</a></p></aside>')
ld = [{'@context': 'https://schema.org', '@type': 'WebSite', 'name': 'Full Duplex', 'url': BASE, 'inLanguage': 'en-GB', 'publisher': PUBLISHER,
       'potentialAction': {'@type': 'SearchAction', 'target': BASE + 'search.html?q={q}', 'query-input': 'required name=q'}}, ORG]
page(og=('Full Duplex', 'Your phone is about to talk to space.', [(f"{C['live']} live services", OGC['live']), (f'{NLIVE_C} countries', OGC['cyan']), ('Weekly briefing: Signal', OGC['muted'])]), path='index.html', title='Satellite-to-phone and the future of mobile', full_title='Satellite-to-phone and the future of mobile | Full Duplex',
     description=SITE['home_description'], body=home, current='index.html', jsonld=ld, cls='is-home',
     head_extra="<meta name='impact-site-verification' value='129cb172-d554-4bf7-90f2-92a71d514675'>",
     scripts='<script defer src="assets/hero-race.js"></script><script defer src="assets/launches.js"></script>', lastmod=max(a.get('updated', a['published']) for a in arts), sources=['scripts/build.py', 'src/site.json', 'data/tracker.json', 'data/launches.json', 'data/race.json', 'data/constellations.json', 'data/refresh.json', 'assets/hero-race.js', 'src/pages/inner-signal.html', 'src/pages/start.html'], search=False)

# /tracker/ has country pages under it but the tracker itself is /tracker.html: send the bare folder there (UAT 14 Nov 2026)
(ROOT / 'tracker' / 'index.html').write_text('<!doctype html><html lang=en-GB><head><meta charset=utf-8><title>Direct-to-cell tracker | Full Duplex</title>'
    f'<link rel=canonical href="{BASE}tracker.html"><meta name=robots content="noindex,follow"><meta http-equiv=refresh content="0; url=../tracker.html">'
    '<script>location.replace("../tracker.html"+location.search+location.hash)</script></head>'
    '<body><p><a href="../tracker.html">Go to the direct-to-cell tracker</a></p></body></html>\n')

# ---------------------------------------------------------------- feeds, sitemap, search index
sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
for p, lm in sorted(built):
    loc = BASE + (p[:-len('index.html')] if p.endswith('index.html') else p)
    sm.append(f'<url><loc>{loc}</loc>' + (f'<lastmod>{lm}</lastmod>' if lm else '') + '</url>')
sm.append('</urlset>')
(ROOT / 'sitemap.xml').write_text('\n'.join(sm) + '\n')
(ROOT / 'robots.txt').write_text(
    'User-agent: *\nAllow: /\n'
    f'Disallow: {BASE_PATH}src/\n'
    f'Disallow: {BASE_PATH}scripts/\n'
    f'\nSitemap: {BASE}sitemap.xml\n'
)
latest = max(a.get('updated', a['published']) for a in arts)
items = ''.join(f'<item><title>{esc(a["title"])}</title><link>{BASE}articles/{a["slug"]}.html</link><guid>{BASE}articles/{a["slug"]}.html</guid>'
                f'<pubDate>{rfc822(a["published"])}</pubDate><description>{esc(a["description"])}</description></item>'
                for a in sorted(arts, key=lambda a: a['published'], reverse=True))
(ROOT / 'feed.xml').write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel><title>Full Duplex</title><link>{BASE}</link>'
                               f'<atom:link href="{BASE}feed.xml" rel="self" type="application/rss+xml"/><description>{esc(SITE["home_description"])}</description><language>en-gb</language>'
                               f'<lastBuildDate>{rfc822(latest)}</lastBuildDate>{items}</channel></rss>\n')
(ROOT / 'search-index.json').write_text(json.dumps(SEARCH, ensure_ascii=False, separators=(',', ':')) + '\n')
print(f'built {len(built)} indexed pages (+404), {len(COUNTRIES)} country pages, {sum(len(e["items"]) for e in CHANGES)} change-log items; tracker rows: {len(ROWS)}')
