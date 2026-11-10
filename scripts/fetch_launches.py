#!/usr/bin/env python3
"""Fetch upcoming launches from The Space Devs Launch Library 2 into data/launches.json (stdlib only).

  python3 scripts/fetch_launches.py           # refresh if the cache is older than MIN_AGE_H hours
  python3 scripts/fetch_launches.py --force   # refresh now

Free tier: 15 requests per hour per IP. One refresh makes len(QUERIES) = 5 requests, spaced out,
so even back-to-back manual runs stay under the limit. Any error (rate limit, timeout, bad JSON)
keeps the existing cache, so the site build never breaks because the API is down.
Data: The Space Devs, https://thespacedevs.com/ (free API; attribution on the launches page).
"""
import json, pathlib, sys, time, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'data' / 'launches.json'
API = 'https://ll.thespacedevs.com/2.3.0/launches/upcoming/'
MIN_AGE_H = 2
HORIZON_DAYS = 400   # drop far-future placeholders (e.g. "2029" Amazon Leo slots)
QUERIES = {          # label -> query string. lsp__id 121 = SpaceX.
    'spacex': {'lsp__id': 121, 'limit': 100},
    'ast': {'search': 'BlueBird', 'limit': 20},
    'amazon-leo': {'search': 'Amazon Leo', 'limit': 30},
    'lynk': {'search': 'Lynk', 'limit': 10},
    'globalstar': {'search': 'Globalstar', 'limit': 10},
}
UA = 'FullDuplex-site-build/1.0 (+https://signalcraft-studio.github.io/full-duplex/)'

def get(params):
    q = dict(params, mode='normal', hide_recent_previous='true')
    req = urllib.request.Request(API + '?' + urllib.parse.urlencode(q), headers={'User-Agent': UA, 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def slim(r):
    m = r.get('mission') or {}; pad = r.get('pad') or {}; rk = (r.get('rocket') or {}).get('configuration') or {}
    lsp = r.get('launch_service_provider') or {}
    return {
        'id': r['id'], 'slug': r.get('slug'), 'name': r['name'],
        'net': r['net'], 'window_start': r.get('window_start'), 'window_end': r.get('window_end'),
        'precision': ((r.get('net_precision') or {}).get('name')) or 'Unknown',
        'status': (r.get('status') or {}).get('name'), 'status_abbrev': (r.get('status') or {}).get('abbrev'),
        'provider': lsp.get('name'), 'rocket': rk.get('full_name') or rk.get('name'),
        'mission': m.get('name'), 'mission_type': m.get('type'), 'mission_description': m.get('description'),
        'orbit': ((m.get('orbit') or {}).get('abbrev')),
        'mission_agencies': [a.get('name') for a in (m.get('agencies') or [])],
        'pad': pad.get('name'), 'location': (pad.get('location') or {}).get('name'),
        'pad_lat': float(pad['latitude']) if pad.get('latitude') not in (None, '') else None, 'pad_lon': float(pad['longitude']) if pad.get('longitude') not in (None, '') else None,
        'webcast_live': r.get('webcast_live'), 'last_updated': r.get('last_updated'),
        'll2_url': r.get('url'),
    }

def main(force=False):
    old = json.loads(OUT.read_text()) if OUT.exists() else None
    if old and not force:
        age = datetime.now(timezone.utc) - datetime.fromisoformat(old['fetched_at'].replace('Z', '+00:00'))
        if age < timedelta(hours=MIN_AGE_H):
            print(f'launches: cache is {age.total_seconds()/3600:.1f} h old, not refetching'); return 0
    seen = {}; now = datetime.now(timezone.utc); horizon = now + timedelta(days=HORIZON_DAYS)
    try:
        for i, (label, params) in enumerate(QUERIES.items()):
            if i: time.sleep(2)
            for r in get(params).get('results', []):
                s = slim(r); net = datetime.fromisoformat(s['net'].replace('Z', '+00:00'))
                if net > horizon: continue
                seen.setdefault(s['id'], s).setdefault('queries', []).append(label)
    except Exception as e:  # rate limit, network, JSON: keep the cache
        print(f'launches: fetch failed ({e.__class__.__name__}: {e}); keeping cached data/launches.json'); return 0
    launches = sorted(seen.values(), key=lambda s: s['net'])
    if not launches and old:
        print('launches: API returned nothing; keeping cache'); return 0
    out = {'fetched_at': now.strftime('%Y-%m-%dT%H:%M:%SZ'), 'source': 'The Space Devs Launch Library 2 (' + API + ')', 'launches': launches}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n')
    print(f'launches: saved {len(launches)} upcoming launches')
    return 0

if __name__ == '__main__':
    sys.exit(main('--force' in sys.argv))
