#!/usr/bin/env python3
"""One shared daily data check for Full Duplex (BB-2). Stdlib only. Run by .github/workflows/daily-refresh.yml,
then scripts/build.py. Separate from the 15-minute launch refresh (launches.yml), which it never touches.

What it checks, all in one run, and the one rule for dates: a date only moves when the check passed today.
Anything that could not be verified keeps its old date (and its old number).

  1. Satellite counts in data/constellations.json that come from Jonathan McDowell's stats pages
     (Starlink DTC, Starlink broadband, Globalstar 2nd gen, Lynk, Amazon Leo). Each is the "Total working"
     column of named rows. Same number -> as_of = today. Small change (<= 15% or <= 10 satellites)
     -> new number + as_of = today, logged in data/refresh.json. Bigger change or the page can't be read
     -> nothing changes, flagged for review.
     AST (SEC filing) and Skylo (no count) are manual: never touched here.
  2. data/race.json is rebuilt by scripts/race_data.py when the Starlink DTC count was verified (its last
     frame is that count and date). If the McDowell fetch fails the old file is kept.
  3. Links on /resources/ (src/resources.json): its "Links last checked" date moves only if no link is
     broken (404/410, DNS or connection failure). 401/403/429 count as "site blocks robots", not broken.
  4. Editorial dates (tracker rows, satellites, phones, glossary, explainers) need a person to check the
     source, so they are only listed in the report with their current date.

Writes data/refresh.json: {"updated": <UTC ISO>, "date": <YYYY-MM-DD>, "checks": [...]} = the one shared stamp.
  python3 scripts/daily_refresh.py            # run all checks
  python3 scripts/daily_refresh.py --dry-run  # report only, write nothing
"""
import concurrent.futures as cf, html, json, pathlib, re, sys, urllib.error, urllib.request
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent
UA = {'User-Agent': 'FullDuplex-site-build/1.0 (+https://fullduplexhq.com/)'}
NOW = datetime.now(timezone.utc); TODAY = NOW.date().isoformat()
DRY = '--dry-run' in sys.argv
STATS = {'star': 'https://planet4589.org/space/con/star/stats.html', 'gbl': 'https://planet4589.org/space/con/gbl/stats.html',
         'lynk': 'https://planet4589.org/space/con/lynk/stats.html', 'kp': 'https://planet4589.org/space/con/kp/stats.html'}
WORKING = 10  # index of "Total working" among the 19 numbers in each McDowell summary row

def get(u, timeout=60):
    with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=timeout) as r: return r.read().decode('utf-8', 'replace')
def rows(page):
    """McDowell summary table -> {row name: [19 ints]}. Rows look like 'Lynk 12 0 0 3 1 4 8 0 0 0 8 0 ...'."""
    t = html.unescape(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', page)))
    i = t.find('Summary status table'); j = t.find('Note: The letters', i)
    if i < 0 or j < 0: raise ValueError('summary table not found')
    t = t[i:j]; t = t[t.find(' O ') + 3:]
    out = {}
    for m in re.finditer(r'(\S(?:.*?\S)??)\s((?:\[?\d+\]? ){18}\[?\d+\]?)(?=\s|$)', t):
        name = m[1].strip(); nums = [int(x.strip('[]')) if not x.startswith('[') else 0 for x in m[2].split()]
        out[name] = nums
    if not out: raise ValueError('no rows parsed')
    return out
def find(rs, pat):
    hits = [v for k, v in rs.items() if re.search(pat, k)]
    if not hits: raise ValueError(f'row {pat!r} not found')
    return hits

def check_counts(const, log):
    pages = {}
    for k, u in STATS.items():
        try: pages[k] = rows(get(u))
        except Exception as e: pages[k] = e
    def star_dtc(): return sum(r[WORKING] for r in find(pages['star'], r'DTC Shell \d'))
    def star_total(): return find(pages['star'], r'^Total Star Total$|^Total$|Star Total$')[-1][WORKING]
    calc = {
        'starlink-dtc': ('star', star_dtc),
        'starlink-broadband': ('star', lambda: star_total() - star_dtc()),
        'globalstar': ('gbl', lambda: find(pages['gbl'], r'Globalstar-2 series')[0][WORKING]),
        'lynk': ('lynk', lambda: find(pages['lynk'], r'^Lynk$')[0][WORKING]),
        'amazon-leo': ('kp', lambda: find(pages['kp'], r'Total$')[-1][WORKING]),
    }
    items = {i['id']: i for k in ('direct_to_device', 'broadband_only') for i in const[k]}
    ok_any = False; dtc_ok = False
    for cid, item in items.items():
        if cid not in calc:
            log.append({'item': f'count:{cid}', 'status': 'manual', 'as_of': item['as_of'], 'note': 'Not from McDowell; needs a person to check the source.'}); continue
        src, fn = calc[cid]
        if isinstance(pages[src], Exception):
            log.append({'item': f'count:{cid}', 'status': 'failed', 'as_of': item['as_of'], 'note': f'Could not read {STATS[src]}: {pages[src]}'}); continue
        try: new = int(fn())
        except Exception as e:
            log.append({'item': f'count:{cid}', 'status': 'failed', 'as_of': item['as_of'], 'note': f'Parse error: {e}'}); continue
        old = item['count']
        if old is not None and new != old and (new < 0 or abs(new - old) > max(10, 0.15 * old)):
            log.append({'item': f'count:{cid}', 'status': 'review', 'as_of': item['as_of'], 'note': f'Source now says {new}, we show {old}: change too big to apply automatically.'}); continue
        entry = {'item': f'count:{cid}', 'status': 'verified' if new == old else 'updated', 'as_of': TODAY, 'was_as_of': item['as_of']}
        if new != old:
            entry['note'] = f'{old} -> {new} (McDowell)'; item['count'] = new
        item['as_of'] = TODAY; ok_any = True; dtc_ok |= cid == 'starlink-dtc'
        log.append(entry)
    # keep the sourced explanation in step with the numbers
    sb, sd = items.get('starlink-broadband'), items.get('starlink-dtc')
    if sb and sd and sb['as_of'] == TODAY and sd['as_of'] == TODAY:
        sb['source']['label'] = re.sub(r'\([\d,]+ working in total, minus [\d,]+ DTC\)', f'({sb["count"] + sd["count"]:,} working in total, minus {sd["count"]:,} DTC)', sb['source']['label'])
        sb['count_label'] = re.sub(r'not counting the [\d,]+ direct-to-cell', f'not counting the {sd["count"]:,} direct-to-cell', sb.get('count_label', ''))
    if ok_any: const['last_checked'] = TODAY
    return dtc_ok

def check_links(res, log):
    urls = sorted({v['url'] for v in (res.get('links') or {}).values() if isinstance(v, dict) and v.get('url')})
    def probe(u, again=True):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers=UA, method='GET'), timeout=25) as r: return u, r.status
        except urllib.error.HTTPError as e: return u, e.code
        except Exception as e:
            return probe(u, False) if again else (u, f'error: {type(e).__name__}')
    with cf.ThreadPoolExecutor(8) as ex: res_ = list(ex.map(probe, urls))
    broken = [(u, s) for u, s in res_ if not (isinstance(s, int) and (s < 400 or s in (401, 403, 405, 406, 429, 451, 999)))]
    blocked = [(u, s) for u, s in res_ if isinstance(s, int) and s >= 400 and (u, s) not in broken]
    if urls and not broken:
        log.append({'item': 'resources-links', 'status': 'verified', 'as_of': TODAY, 'was_as_of': res['checked'], 'note': f'{len(urls)} links OK' + (f', {len(blocked)} block robots' if blocked else '')})
        res['checked'] = TODAY; return True
    log.append({'item': 'resources-links', 'status': 'review' if urls else 'failed', 'as_of': res['checked'],
                'note': f'{len(broken)} of {len(urls)} links look broken: ' + '; '.join(f'{u} ({s})' for u, s in broken[:10])})
    return False

def main():
    log = []
    cp = ROOT / 'data/constellations.json'; const = json.loads(cp.read_text())
    dtc_ok = check_counts(const, log)
    rp = ROOT / 'src/resources.json'; res = json.loads(rp.read_text())
    links_ok = check_links(res, log)
    if not DRY:
        cp.write_text(json.dumps(const, ensure_ascii=False, indent=1) + '\n')
        if links_ok: rp.write_text(json.dumps(res, ensure_ascii=False, indent=1) + '\n')
    # race chart (its last frame = today's Starlink DTC count and date)
    if dtc_ok and not DRY:
        try:
            sys.path.insert(0, str(ROOT / 'scripts')); import race_data; race_data.main()
            log.append({'item': 'race-chart', 'status': 'verified', 'as_of': TODAY})
        except Exception as e:
            log.append({'item': 'race-chart', 'status': 'failed', 'as_of': json.loads((ROOT / 'data/race.json').read_text()).get('generated'), 'note': str(e)[:200]})
    else:
        log.append({'item': 'race-chart', 'status': 'skipped', 'as_of': json.loads((ROOT / 'data/race.json').read_text()).get('generated')})
    # editorial dates: listed only
    tr = json.loads((ROOT / 'data/tracker.json').read_text())
    log.append({'item': 'tracker', 'status': 'manual', 'as_of': tr.get('last_checked'), 'note': 'Tracker rows need a person to read each source.'})
    for f, k in (('src/satellites.json', 'checked'), ('src/phones.json', 'checked'), ('src/glossary.json', 'checked'), ('src/explainers.json', 'updated')):
        log.append({'item': f, 'status': 'manual', 'as_of': json.loads((ROOT / f).read_text()).get(k)})
    out = {'_readme': 'Written by scripts/daily_refresh.py (daily-refresh.yml). "date" is the one shared "data checked" stamp; each item keeps its own as_of and only moves when its check passed.',
           'updated': NOW.strftime('%Y-%m-%dT%H:%M:%SZ'), 'date': TODAY, 'checks': log}
    if not DRY: (ROOT / 'data/refresh.json').write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n')
    for e in log: print(f"{e['status']:9} {e['item']:28} {e.get('as_of')}  {e.get('note', '')}")
    bad = [e for e in log if e['status'] in ('failed', 'review')]
    if bad and not DRY:
        print(f'::warning::{len(bad)} check(s) need a look: ' + ', '.join(e['item'] for e in bad))

if __name__ == '__main__': main()
