#!/usr/bin/env python3
"""Build data/race.json for the /launches/ race chart (phone-capable satellites in orbit over time). Stdlib only.

  python3 scripts/race_data.py     # fetches Jonathan McDowell's public data (CC-BY), a few MB

Every monthly value is computed from a published per-satellite or per-day record, never estimated:
  * Starlink Direct to Cell: McDowell's Starlink index, "Gen 2A DTC" table (launch and re-entry date of every
    DTC satellite), counted as launched and not yet re-entered at each month end.
  * Lynk: McDowell's Lynk launch-history data file (log.dat), column "Up" (in orbit) at each month end.
  * AST SpaceMobile BlueBirds and Globalstar second generation: dated launches below, each with a source
    (McDowell's GCAT catalogue and the companies' own launch announcements). Constant between launches.
The last frame is today's working count from data/constellations.json, so the chart ends on the same
numbers as the panel above it. Months in between are shown as steps, not smoothed; the animation only
tweens bar lengths between consecutive month-end values.
"""
import json, pathlib, re, urllib.request
from datetime import date, timedelta

ROOT = pathlib.Path(__file__).resolve().parent.parent
UA = {'User-Agent': 'FullDuplex-site-build/1.0 (+https://signalcraft-studio.github.io/full-duplex/)'}
STAR_INDEX = 'https://planet4589.org/space/con/star/starindex.html'
LYNK_LOG = 'https://planet4589.org/space/con/lynk/log.dat'
GCAT = 'https://planet4589.org/space/gcat/'
MON = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split()

def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60) as r: return r.read().decode('utf-8', 'replace')
def pdate(s):
    m = re.match(r'(\d{4}) (\w{3})\s+(\d+)', s.strip()); return date(int(m[1]), MON.index(m[2]) + 1, int(m[3])) if m else None

AST_LAUNCHES = [  # date (UTC), satellites added to orbit, label, source
    ('2024-09-12', 5, 'BlueBirds 1–5 (Block 1) launch on Falcon 9', {'label': 'McDowell GCAT catalogue (SpaceMobile-001 to -005)', 'url': GCAT}),
    ('2025-12-24', 1, 'BlueBird 6, the first Block 2, launches on India’s LVM3', {'label': 'McDowell GCAT catalogue (SpaceMobile-006)', 'url': GCAT}),
    ('2026-04-19', 0, 'BlueBird 7 is lost after New Glenn leaves it in too low an orbit', {'label': 'McDowell GCAT catalogue (SpaceMobile-007, re-entered 20 Apr 2026)', 'url': GCAT}),
    ('2026-06-17', 3, 'BlueBirds 8–10 launch on Falcon 9', {'label': 'McDowell GCAT catalogue (SpaceMobile-008 to -010)', 'url': GCAT}),
    ('2026-08-05', 3, 'BlueBirds 11–13 launch on Falcon 9', {'label': 'AST SpaceMobile, 5 Aug 2026', 'url': 'https://www.businesswire.com/news/home/20260805761351/en/AST-SpaceMobile-Announces-Successful-Orbital-Launch-of-BlueBirds-11-12-and-13'}),
]
GLOBALSTAR_BASE = (25, 'Globalstar second-generation satellites in orbit before 2026: 24 launched 2010–2013 plus 1 spare launched June 2022, none re-entered (McDowell GCAT catalogue)')
GLOBALSTAR_LAUNCHES = [
    ('2026-08-16', 8, '8 Globalstar replacement satellites launch on Falcon 9 (15 Aug, US time)', {'label': 'Globalstar, 16 Aug 2026', 'url': 'https://investors.globalstar.com/news-releases/news-release-details/globalstar-confirms-successful-launch-all-8-hibleo-4-replacement/'}),
]

def month_ends(start, end):
    out = []; y, m = start.year, start.month
    while True:
        d = (date(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1))
        if d > end: break
        out.append(d); y, m = (y + (m == 12), m % 12 + 1)
    return out

def main():
    const = {i['id']: i for i in json.loads((ROOT / 'data/constellations.json').read_text())['direct_to_device']}
    t = get(STAR_INDEX)
    parts = re.split(r'<B>(.*?)</B></TD></TR>', t)
    dtc = []
    for name, body in zip(parts[1::2], parts[2::2]):
        if 'DTC' not in name: continue
        for r in re.findall(r'<TR>(.*?)</TR>', body, re.S):
            c = [re.sub(r'<[^>]+>', '', x).strip() for x in re.split(r'<TD>', r, flags=re.I)[1:]]
            if len(c) < 6 or c[4] == 'Not launched': continue
            dtc.append((pdate(c[4]), pdate(c[5]) if c[5] != '-' else None))
    lynk = {}
    for line in get(LYNK_LOG).splitlines():
        if line.startswith('#') or not line.strip(): continue
        c = line.split(); m = re.search(r'(\d{4}) (\w{3})\s+(\d+) \d{4}:\d\d$', line.strip())
        lynk[date(int(m[1]), MON.index(m[2]) + 1, int(m[3]))] = int(c[8])
    def steps(base, launches, d): return base + sum(n for ds, n, *_ in launches if date.fromisoformat(ds) <= d)
    today = date.fromisoformat(const['starlink-dtc']['as_of'])
    frames = []
    for d in [date(2023, 12, 31)] + month_ends(date(2024, 1, 1), today):
        ld = max(k for k in lynk if k <= d)
        frames.append({'d': d.isoformat(), 'v': {
            'starlink-dtc': sum(1 for l, x in dtc if l <= d and (x is None or x > d)),
            'ast': steps(0, AST_LAUNCHES, d),
            'globalstar': steps(GLOBALSTAR_BASE[0], GLOBALSTAR_LAUNCHES, d),
            'lynk': lynk[ld]}})
    frames.append({'d': today.isoformat(), 'final': True, 'v': {k: const[k]['count'] for k in ('starlink-dtc', 'ast', 'globalstar', 'lynk')}})
    events = [{'d': '2024-01-03', 's': 'starlink-dtc', 't': 'First 6 Starlink Direct to Cell satellites launch', 'src': {'label': 'McDowell Starlink index (Group 7-9)', 'url': STAR_INDEX}}]
    events += [{'d': d, 's': 'ast', 't': txt, 'src': src} for d, n, txt, src in AST_LAUNCHES]
    events += [{'d': '2026-05-03', 's': 'lynk', 't': '2 more Lynk satellites launch', 'src': {'label': 'McDowell GCAT catalogue (Lynk Tower Gen1A-1 and -2)', 'url': GCAT}}]
    events += [{'d': d, 's': 'globalstar', 't': txt, 'src': src} for d, n, txt, src in GLOBALSTAR_LAUNCHES]
    events.sort(key=lambda e: e['d'])
    out = {
        '_readme': 'Generated by scripts/race_data.py. Phone-capable (direct-to-device) satellites in orbit at each month end, from published per-satellite records. Do not hand-edit numbers; fix the script or its sourced launch lists.',
        'generated': date.today().isoformat(),
        'metric': 'Satellites in orbit (launched and not yet re-entered) at each month end. The last frame is the working count from data/constellations.json.',
        'series': [
            {'id': 'starlink-dtc', 'label': 'Starlink Direct to Cell', 'color': '#00cfff', 'sources': [{'label': 'Jonathan McDowell, Starlink index: Gen 2A DTC (per-satellite launch and re-entry dates)', 'url': STAR_INDEX}]},
            {'id': 'ast', 'label': 'AST SpaceMobile BlueBirds', 'color': '#ff9a3c', 'sources': [s for *_, s in AST_LAUNCHES], 'note': 'BlueBirds only. The BlueWalker 3 test satellite (2022) is not counted.'},
            {'id': 'globalstar', 'label': 'Globalstar (iPhone)', 'color': '#b58cff', 'sources': [{'label': GLOBALSTAR_BASE[1], 'url': GCAT}] + [s for *_, s in GLOBALSTAR_LAUNCHES], 'note': 'Second-generation satellites only. Today 33 are in orbit and McDowell counts 32 as working.'},
            {'id': 'lynk', 'label': 'Lynk / Elveo', 'color': '#6ee79a', 'sources': [{'label': 'Jonathan McDowell, Lynk launch history data (in orbit)', 'url': LYNK_LOG}], 'note': 'Includes small Lynk test satellites, as in the count above.'},
        ],
        'target': {'series': 'ast', 'value': 45, 'label': '≈45 BlueBirds by mid-2027 (AST target)', 'source': const['ast']['planned']['source']},
        'events': events,
        'frames': frames,
    }
    (ROOT / 'data/race.json').write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n')
    print('race: %d frames, final %s' % (len(frames), frames[-1]['v']))
    for f in frames[::3] + [frames[-2]]: print(' ', f['d'], f['v'])

if __name__ == '__main__': main()
