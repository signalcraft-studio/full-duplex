#!/usr/bin/env python3
"""Full Duplex static site build (Python 3 standard library only).

Sources live in src/ (page bodies with a JSON <!--meta ... --> header) and data/.
Run from anywhere:  python3 scripts/build.py
It rewrites the generated HTML at the repo root, plus sitemap.xml, robots.txt and
feed.xml. GitHub Pages serves the committed output, so commit after building.

IMAGES: no image is referenced anywhere yet. Every place an approved image will
go is marked "TODO(image-approval)". Do not add one until Sam approves a preview.
"""
import html, json, math, pathlib, re, urllib.parse
from datetime import date

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'
SITE = json.loads((SRC / 'site.json').read_text())
BASE = SITE['base_url']            # absolute, ends with /
X = SITE['x_handle']               # without @
SUB = SITE['subscribe_url']
FORM = SITE['beehiiv_form']
MON = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split()
MONL = 'January February March April May June July August September October November December'.split()

def esc(t): return html.escape(str(t), quote=True)
def human(iso, long=True):
    y, m, d = map(int, iso.split('-')); return f"{d} {(MONL if long else MON)[m-1]} {y}"
def rfc822(iso):
    y, m, d = map(int, iso.split('-')); dt = date(y, m, d)
    return dt.strftime('%a, ') + f"{d:02d} {MON[m-1]} {y} 08:00:00 +0000"

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

X_ICON = ''  # text-only buttons: no icons/images until Sam approves artwork

def share_btn(text, url, label='Share on X'):
    return f'<a class="btn ghost share" href="{esc(share_url(text, url))}" target=_blank rel="noopener">{X_ICON}{label}</a>'

def follow_btn(cls='btn ghost'):
    return f'<a class="{cls}" href="https://x.com/{X}" target=_blank rel="noopener me">{X_ICON}Follow @{X}</a>'

def issues_list():
    li = ''.join(f'<li><a href="{esc(i["url"])}"><span class=ino>#{i["no"]}</span> {esc(i["title"])}</a></li>' for i in SITE['issues'][:3])
    return f'<ul class=issues aria-label="Recent issues of Signal">{li}</ul>'

def signal_block(root, surface, variant='full', heading_level=2):
    """Signal subscribe block. The beehiiv embed loads lazily (assets/site.js) when
    the block nears the viewport; the button always works without it."""
    h = f'h{heading_level}'
    privacy = f'<p class=fine>Free. Your email is managed by beehiiv and used only to send Signal. Unsubscribe any time. See our <a href="{root}privacy.html">privacy notice</a>.</p>'
    embed = f'<div class=bh-slot data-form="{FORM}" data-surface="{surface}"></div>'
    if variant == 'mid':
        return (f'<aside class="signal mid" aria-label="Subscribe to Signal"><p class=kicker>Signal · free weekly briefing</p>'
                f'<{h} class=signal-h>The weekly direct-to-cell briefing from an 11-year network insider</{h}>'
                f'{embed}<p class=signal-cta><a class=btn href="{esc(sub_url(surface))}">Send me Signal</a></p>{privacy}</aside>')
    return (f'<section class=signal aria-label="Subscribe to Signal"><p class=kicker>Signal · free weekly briefing</p>'
            f'<{h} class=signal-h>Get Signal: what changed in satellite-to-phone this week</{h}>'
            f'<p>One email a week on direct-to-cell, mobile networks and what it means for you, from an 11-year mobile network insider. Recent issues:</p>'
            f'{issues_list()}{embed}<p class=signal-cta><a class=btn href="{esc(sub_url(surface))}">Send me Signal</a> '
            f'<a class=more href="{esc(SITE["archive_url"])}">Read past issues</a></p>{privacy}</section>')

NAV = [('index.html', 'Home'), ('tracker.html', 'Tracker'), ('about.html', 'About'), ('sponsor.html', 'Sponsor')]

def header(root, current):
    links = ''.join(f'<a href="{root}{h}"{" aria-current=page" if h == current else ""}>{t}</a>' for h, t in NAV)
    return (f'<a class=skip href="#main">Skip to content</a><header class=site><a class=logo href="{root}index.html" aria-label="Full Duplex home">Full<span>Duplex</span></a>'
            f'<nav aria-label="Main">{links}</nav><div class=hdr-cta><a class="xlink" href="https://x.com/{X}" target=_blank rel="noopener me">Follow @{X}</a>'
            f'<a class="btn pill" href="{esc(sub_url("header"))}">Subscribe</a></div></header>')

def footer(root, sticky=True):
    bar = (f'<div class=stickybar hidden role=region aria-label="Subscribe to Signal"><p><strong>Signal</strong> · the weekly direct-to-cell briefing</p>'
           f'<a class="btn pill" href="{esc(sub_url("sticky-bar"))}">Subscribe free</a><button class=x type=button aria-label="Dismiss">×</button></div>') if sticky else ''
    return (f'<footer class=site><div><a class=logo href="{root}index.html">Full<span>Duplex</span></a><p>Independent analysis of satellite-to-phone and mobile networks. Made in the UK.</p></div>'
            f'<nav aria-label="Footer"><a href="{esc(sub_url("footer"))}">Subscribe to Signal</a><a href="https://x.com/{X}" target=_blank rel="noopener me">Follow @{X} on X</a>'
            f'<a href="{root}tracker.html">Tracker</a><a href="{root}feed.xml">RSS</a><a href="{root}sponsor.html">Sponsor</a><a href="{root}privacy.html">Privacy</a></nav>'
            f'<p class=copy>© 2026 Full Duplex.</p></footer>{bar}')

def page(*, path, title, description, body, root='', current='', og_type='website', jsonld=None,
         head_extra='', scripts='', viewport='width=device-width,initial-scale=1', sticky=True, full_title=None):
    url = BASE + path.replace('index.html', '') if path.endswith('index.html') else BASE + path
    ft = full_title or f'{title} | Full Duplex'
    ld = ''.join(f'<script type="application/ld+json">{json.dumps(j, ensure_ascii=False)}</script>' for j in (jsonld or []))
    head = (f'<!doctype html><html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="{viewport}">'
            f'<title>{esc(ft)}</title><meta name="description" content="{esc(description)}"><link rel="canonical" href="{url}">'
            f'<meta name="theme-color" content="#0b1220"><meta name="color-scheme" content="dark">'
            f'<meta property="og:site_name" content="Full Duplex"><meta property="og:locale" content="en_GB"><meta property="og:type" content="{og_type}">'
            f'<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(description)}"><meta property="og:url" content="{url}">'
            f'<!-- TODO(image-approval): add og:image (1200x630), og:image:alt and switch twitter:card to summary_large_image once Sam approves the OG card preview. -->'
            f'<meta name="twitter:card" content="summary"><meta name="twitter:site" content="@{X}"><meta name="twitter:title" content="{esc(title)}"><meta name="twitter:description" content="{esc(description)}">'
            f'<link rel="alternate" type="application/rss+xml" title="Full Duplex" href="{BASE}feed.xml">'
            f'<link rel="stylesheet" href="{root}style.css">{head_extra}{ld}</head><body>')
    out = (head + header(root, current) + f'<main id=main>{body}</main>' + footer(root, sticky)
           + f'<script src="{root}assets/site.js" defer></script>{scripts}</body></html>\n')
    (ROOT / path).parent.mkdir(parents=True, exist_ok=True)
    (ROOT / path).write_text(out)
    return url

PUBLISHER = {'@type': 'Organization', 'name': 'Full Duplex', 'url': BASE, 'sameAs': [f'https://x.com/{X}']}
AUTHOR = {'@type': 'Person', 'name': SITE['author'], 'url': BASE + 'about.html'}

# ---------- tracker ----------
TRACK = json.loads((ROOT / 'data/tracker.json').read_text())
CLS = {'live': 'live', 'trial': 'trial', 'announced': 'ann'}

def tracker_table():
    rows = ["<tr><th scope=col>Country</th><th scope=col>Operator partner</th><th scope=col>Satellite provider</th><th scope=col>Status</th><th scope=col>Services</th><th scope=col>Source</th><th scope=col>Last checked</th></tr>"]
    for r in TRACK['rows']:
        src = ' · '.join(f"<a href='{s['url']}'>{s['label']}</a>" for s in r['sources'])
        rows.append("<tr>" f"<td data-label='Country'>{r['country']}</td>" f"<td data-label='Operator partner'>{r['operator']}</td>"
                    f"<td data-label='Satellite provider'>{r['satellite']}</td>" f"<td data-label='Status' class={CLS[r['status']]}>{r['status']}</td>"
                    f"<td data-label='Services'>{r['services']}</td>" f"<td data-label='Source'>{src}</td>" f"<td data-label='Last checked'>{r['checked']}</td></tr>")
    return ("<!-- TRACKER-TABLE:START (generated from data/tracker.json by scripts/build.py; do not edit by hand) -->"
            "<table id=tracker-table><caption class=sr>Direct-to-cell services by country</caption>" + ''.join(rows) + "</table><!-- TRACKER-TABLE:END -->")

def counts():
    c = {'live': 0, 'trial': 0, 'announced': 0}
    for r in TRACK['rows']: c[r['status']] += 1
    live_countries = {r['country'] for r in TRACK['rows'] if r['status'] == 'live' and r['iso_n3']}
    return c, len(live_countries)

# ---------- articles ----------
arts = []
for slug in SITE['article_order']:
    meta, body, _ = read_src(SRC / 'articles' / f'{slug}.html'); meta['body'] = body; arts.append(meta)

def reading_time(body):
    words = len(re.sub(r'<[^>]+>', ' ', body).split()); return max(1, math.ceil(words / 230))

def insert_mid(body, block):
    hs = [m.start() for m in re.finditer(r'<h2[ >]', body)]
    if len(hs) >= 2: return body[:hs[1]] + block + body[hs[1]:]
    return body + block

built = []  # (path, lastmod)
for a in arts:
    path = f"articles/{a['slug']}.html"; url = BASE + path; root = '../'
    dates = f"Published <time datetime=\"{a['published']}\">{human(a['published'])}</time>"
    if a.get('updated'): dates += f" · Updated <time datetime=\"{a['updated']}\">{human(a['updated'])}</time>"
    byline = (f'<div class=byline><p>By <a href="{root}about.html">{esc(SITE["author"])}</a> · {dates} · {reading_time(a["body"])} min read</p>'
              f'{share_btn(a["title"], url)}</div>')
    body = (f'<article><header class=art-head><p class=kicker><a href="{root}index.html#latest">Analysis</a></p><h1>{esc(a["title"])}</h1>{byline}</header>'
            + insert_mid(a['body'], signal_block(root, 'mid-article', 'mid'))
            + f'<div class=share-end><p>Found this useful? Share it, or follow us for daily updates.</p>{share_btn(a["title"], url)}{follow_btn()}</div></article>'
            + signal_block(root, 'end-article'))
    ld = [{'@context': 'https://schema.org', '@type': 'NewsArticle', 'headline': a['title'], 'description': a['description'],
           'datePublished': a['published'], 'dateModified': a.get('updated', a['published']), 'author': AUTHOR,
           'publisher': PUBLISHER, 'mainEntityOfPage': url, 'inLanguage': 'en-GB'}]  # TODO(image-approval): add "image"
    page(path=path, title=a['title'], description=a['description'], body=body, root=root, og_type='article', jsonld=ld,
         full_title=f"{a['short_title']} | Full Duplex",
         head_extra=f'<meta property="article:published_time" content="{a["published"]}"><meta property="article:author" content="{esc(SITE["author"])}">')
    built.append((path, a.get('updated', a['published'])))

# ---------- simple pages ----------
for p in ['about', 'sponsor', 'privacy']:
    meta, body, scripts = read_src(SRC / 'pages' / f'{p}.html')
    if p == 'about':
        body = body + f'<p class=follow-row>{follow_btn()}</p>' + signal_block('', 'about')
    page(path=f'{p}.html', title=meta['title'], description=meta['description'], body=body, current=f'{p}.html', sticky=(p != 'privacy'))
    built.append((f'{p}.html', None))

meta, body, scripts = read_src(SRC / 'pages' / 'constellation.html')
body = body + f'<div class=share-end><p>Beat your score? Challenge someone.</p>{share_btn("I just played Constellation: deploy direct-to-cell satellites before time runs out.", BASE + "play/constellation.html", "Share the game on X")}{follow_btn()}</div>' + signal_block('../', 'game')
page(path='play/constellation.html', title=meta['title'], description=meta['description'], body=body, root='../',
     head_extra=meta['head_extra'], scripts=scripts, viewport=meta['viewport'], full_title='Constellation — deploy D2C satellites | Full Duplex')
built.append(('play/constellation.html', None))

# tracker
meta, body, scripts = read_src(SRC / 'pages' / 'tracker.html')
c, nlive = counts()
body = body.replace('<!--TRACKER-TABLE-->', tracker_table())
body = body.replace('<span id=tracker-checked>4 Nov 2026</span>', f"<span id=tracker-checked>{TRACK['last_checked']}</span>")
body += (f'<div class=share-end><p>Cite or share the tracker.</p>{share_btn(f"Direct-to-cell tracker: {c["live"]} live services, {c["trial"]} trials, {c["announced"]} announced. Country by country, with sources.", BASE + "tracker.html")}{follow_btn()}</div>'
         + signal_block('', 'tracker'))
ld = [{'@context': 'https://schema.org', '@type': 'Dataset', 'name': 'Full Duplex direct-to-cell tracker', 'description': meta['description'],
       'url': BASE + 'tracker.html', 'creator': PUBLISHER, 'isAccessibleForFree': True, 'inLanguage': 'en-GB',
       'distribution': [{'@type': 'DataDownload', 'encodingFormat': 'application/json', 'contentUrl': BASE + 'data/tracker.json'}]}]
page(path='tracker.html', title=meta['title'], description=meta['description'], body=body, current='tracker.html',
     head_extra=meta['head_extra'], scripts=scripts, jsonld=ld)
built.append(('tracker.html', None))

# ---------- home ----------
def art_card(a, level=3):
    return (f'<div class=card><h{level}><a href="articles/{a["slug"]}.html">{esc(a["title"])}</a></h{level}><p>{esc(a["summary"])}</p>'
            f'<p class=meta><time datetime="{a["published"]}">{human(a["published"])}</time> · {reading_time(a["body"])} min read</p></div>')
home = (f'<section class=hero><p class=kicker>Both directions, all at once</p><h1>Your phone is about to talk to space.</h1>'
        f'<p class=lede>Full Duplex explains direct-to-cell satellites, GSM and the shake-up coming to the mobile industry.</p>'
        f'<p class=byl>By <a href="about.html">{esc(SITE["author"])}</a>, an 11-year mobile network insider</p>'
        f'<p class=hero-cta><a class=btn href="{esc(sub_url("home-hero"))}">Send me Signal</a>{follow_btn()}</p></section>'
        + signal_block('', 'home')
        + '<h2 class=sec>Explore</h2>'
        + f'<div class=card><h3><a href=tracker.html>Direct-to-cell tracker</a></h3><p>Who\'s live, who\'s trialling and who\'s announced, country by country, with sources. {c["live"]} live services, {c["trial"]} trials, {c["announced"]} announced.</p></div>'
        + '<div class=card><h3><a href=play/constellation.html>Play: Constellation</a></h3><p>Deploy direct-to-cell satellites into orbit. A 75-second browser game: hit the slots before time runs out.</p></div>'
        + '<h2 class=sec id=latest>Latest</h2>' + ''.join(art_card(a) for a in arts)
        + '<aside class=sponsor-card aria-label="Sponsorship"><p class=kicker>Presented by · slot available</p><h2>Put your brand in front of the people building satellite-to-phone</h2>'
          '<p>Engineers, operator teams, investors and early adopters read Full Duplex. One sponsor at a time, always clearly labelled.</p>'
          '<p><a class="btn ghost" href="sponsor.html">See sponsor options</a></p></aside>')
ld = [{'@context': 'https://schema.org', '@type': 'WebSite', 'name': 'Full Duplex', 'url': BASE, 'inLanguage': 'en-GB', 'publisher': PUBLISHER}]
page(path='index.html', title='Satellite-to-phone and the future of mobile', full_title='Satellite-to-phone and the future of mobile | Full Duplex',
     description=SITE['home_description'], body=home, current='index.html', jsonld=ld)
built.append(('index.html', None))

# ---------- feeds ----------
latest = max(a.get('updated', a['published']) for a in arts)
sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
for p, lm in sorted(built):
    loc = BASE + ('' if p == 'index.html' else p)
    sm.append(f'<url><loc>{loc}</loc>' + (f'<lastmod>{lm}</lastmod>' if lm else '') + '</url>')
sm.append('</urlset>')
(ROOT / 'sitemap.xml').write_text('\n'.join(sm) + '\n')
(ROOT / 'robots.txt').write_text(f'User-agent: *\nAllow: /\n\nSitemap: {BASE}sitemap.xml\n')
items = ''.join(f'<item><title>{esc(a["title"])}</title><link>{BASE}articles/{a["slug"]}.html</link><guid>{BASE}articles/{a["slug"]}.html</guid>'
                f'<pubDate>{rfc822(a["published"])}</pubDate><description>{esc(a["description"])}</description></item>'
                for a in sorted(arts, key=lambda a: a['published'], reverse=True))
(ROOT / 'feed.xml').write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel><title>Full Duplex</title><link>{BASE}</link>'
                               f'<atom:link href="{BASE}feed.xml" rel="self" type="application/rss+xml"/><description>{esc(SITE["home_description"])}</description><language>en-gb</language>'
                               f'<lastBuildDate>{rfc822(latest)}</lastBuildDate>{items}</channel></rss>\n')
print(f'built {len(built)} pages + sitemap.xml, robots.txt, feed.xml; tracker rows: {len(TRACK["rows"])}')
