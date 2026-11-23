#!/usr/bin/env python3
"""Fetch recent orbits of telco-relevant satellites from CelesTrak for the /launches/flight/ globe.

Writes data/gp-recent.json: newly launched satellites (CelesTrak's "last 30 days" group), filtered to
mobile and broadband networks (Starlink, Amazon Leo/Kuiper, AST BlueBird, Globalstar, OneWeb, Lynk,
Qianfan, China SatNet), grouped by launch, as OMM mean elements that satellite.js propagates in the browser.

CelesTrak usage guidance (https://celestrak.org/NORAD/documentation/gp-data-formats.php): GP data updates
about every 2 hours, so never fetch more often than that. This script refuses to fetch again within
MIN_HOURS of the last successful fetch (unless --force) and is run from the scheduled launches workflow
(4 times a day). Pages never call CelesTrak: browsers only read the cached JSON from our own site.
If CelesTrak fails or blocks us (HTTP 403), the cached file is kept unchanged.
"""
import json, re, sys, time, pathlib, urllib.request, urllib.error
from datetime import datetime, timezone, timedelta

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'data' / 'gp-recent.json'
GP = 'https://celestrak.org/NORAD/elements/gp.php?GROUP=last-30-days&FORMAT=json'
SATCAT = 'https://celestrak.org/satcat/records.php?INTDES={}&FORMAT=json'
UA = 'FullDuplexSite/1.0 (+https://fullduplexhq.com/; cached 4x daily)'
MIN_HOURS = 3
# name pattern -> (network id, display name, phone-capable?)
NETS = [
    (r'^STARLINK', 'starlink', 'Starlink', False),
    (r'^(KUIPER|AMAZON)', 'amazon-leo', 'Amazon Leo', False),
    (r'^BLUEBIRD|^BLUEWALKER', 'ast', 'AST SpaceMobile BlueBird', True),
    (r'^GLOBALSTAR', 'globalstar', 'Globalstar', True),
    (r'^LYNK', 'lynk', 'Lynk', True),
    (r'^ONEWEB', 'oneweb', 'Eutelsat OneWeb', False),
    (r'^QIANFAN', 'qianfan', 'Qianfan (China)', False),
    (r'^HULIANWANG|^GUOWANG', 'guowang', 'China SatNet (Guowang)', False),
]
KEEP = ('OBJECT_NAME', 'OBJECT_ID', 'NORAD_CAT_ID', 'EPOCH', 'MEAN_MOTION', 'ECCENTRICITY', 'INCLINATION', 'RA_OF_ASC_NODE',
        'ARG_OF_PERICENTER', 'MEAN_ANOMALY', 'BSTAR', 'MEAN_MOTION_DOT', 'MEAN_MOTION_DDOT')

def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=60) as r:
        body = r.read().decode('utf-8', 'replace')
    try: return json.loads(body)
    except ValueError: raise RuntimeError('Not JSON (CelesTrak message?): ' + body[:200])

def net_of(name):
    for rx, k, label, phone in NETS:
        if re.search(rx, name): return k, label, phone
    return None

def main():
    force = '--force' in sys.argv
    src = next((a.split('=', 1)[1] for a in sys.argv if a.startswith('--from-file=')), None)
    old = json.loads(OUT.read_text()) if OUT.exists() else {}
    if old.get('fetched_at') and not force and not src:
        age = datetime.now(timezone.utc) - datetime.fromisoformat(old['fetched_at'].replace('Z', '+00:00'))
        if age < timedelta(hours=MIN_HOURS):
            print(f'gp-recent.json is {age} old; CelesTrak asks for no more than one fetch per update. Skipping.'); return
    try:
        rows = json.loads(pathlib.Path(src).read_text()) if src else get(GP)
        if not isinstance(rows, list) or not rows: raise RuntimeError('empty GP response')
    except (urllib.error.URLError, RuntimeError, ValueError) as e:
        print('CelesTrak fetch failed, keeping cache:', e); return
    known = {g['id']: g for g in old.get('groups', [])}
    groups = {}
    for o in rows:
        n = net_of(o.get('OBJECT_NAME', ''))
        if not n: continue
        intl = o['OBJECT_ID'][:8]
        g = groups.setdefault(intl, {'id': intl, 'net': n[0], 'label': n[1], 'phone': n[2], 'objects': []})
        g['objects'].append({k: o[k] for k in KEEP if k in o})
    for intl, g in groups.items():
        g['objects'].sort(key=lambda x: x['OBJECT_ID'])
        g['n'] = len(g['objects'])
        g['launch_date'] = (known.get(intl) or {}).get('launch_date')
        if not g['launch_date']:  # one small SATCAT lookup per new launch only
            try:
                cat = get(SATCAT.format(intl)); g['launch_date'] = cat[0]['LAUNCH_DATE'] if cat else None
                g['launch_site'] = cat[0].get('LAUNCH_SITE') if cat else None
                time.sleep(1)
            except Exception as e: print('SATCAT lookup failed for', intl, e)
        elif known.get(intl, {}).get('launch_site'): g['launch_site'] = known[intl]['launch_site']
    when = datetime.fromtimestamp(pathlib.Path(src).stat().st_mtime, timezone.utc) if src else datetime.now(timezone.utc)
    out = {'fetched_at': when.strftime('%Y-%m-%dT%H:%M:%SZ'),
           'source': 'CelesTrak GP data (group: last 30 days), OMM JSON; launch dates from CelesTrak SATCAT',
           'source_url': 'https://celestrak.org/NORAD/elements/gp.php?GROUP=last-30-days&FORMAT=json',
           'groups': sorted(groups.values(), key=lambda g: (g.get('launch_date') or '', g['id']), reverse=True)}
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(',', ':')) + '\n')
    print(f"Wrote {OUT.name}: {len(out['groups'])} launches, {sum(g['n'] for g in out['groups'])} satellites")

if __name__ == '__main__': main()
