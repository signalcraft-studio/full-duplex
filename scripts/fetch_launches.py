#!/usr/bin/env python3
"""Fetch upcoming launches from The Space Devs Launch Library 2 into data/launches.json (stdlib only).

  python3 scripts/fetch_launches.py           # refresh if the cache is older than MIN_AGE_H hours
  python3 scripts/fetch_launches.py --force   # refresh now (full 5-query refresh)
  python3 scripts/fetch_launches.py --imminent
      # update only precise launches with NET in the next 6 hours or the past
      # 1 hour (one request per launch, capped). Used by the 15-minute workflow
      # tick so we stay under the free-tier 15 requests/hour limit.

Free tier: 15 requests per hour per IP. A full refresh makes len(QUERIES) = 5
requests, spaced out, so even back-to-back manual runs stay under the limit.
An imminent tick typically makes 1 request (capped at IMMINENT_MAX). The
workflow runs a full refresh at most once an hour, and imminent ticks the
rest of the time only when a launch is in the window, so usage stays under 15
requests/hour. Any error (rate limit, timeout, bad JSON) keeps the existing
cache, so the site build never breaks because the API is down.
Data: The Space Devs, https://thespacedevs.com/ (free API; attribution on the launches page).
"""
import json, pathlib, sys, time, urllib.parse, urllib.request
import launch_overrides  # sourced corrections (data/launch-overrides.json), kept across refreshes
from datetime import datetime, timedelta, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'data' / 'launches.json'
API = 'https://ll.thespacedevs.com/2.3.0/launches/upcoming/'
LAUNCH_API = 'https://ll.thespacedevs.com/2.3.0/launches/'
MIN_AGE_H = 2
HORIZON_DAYS = 400   # drop far-future placeholders (e.g. "2029" Amazon Leo slots)
QUERIES = {          # label -> query string. lsp__id 121 = SpaceX.
    'spacex': {'lsp__id': 121, 'limit': 100},
    'ast': {'search': 'BlueBird', 'limit': 20},
    'amazon-leo': {'search': 'Amazon Leo', 'limit': 30},
    'lynk': {'search': 'Lynk', 'limit': 10},
    'globalstar': {'search': 'Globalstar', 'limit': 10},
}
UA = 'FullDuplex-site-build/1.0 (+https://fullduplexhq.com/)'
# Match scripts/build.py: only these NETs are precise enough for a countdown
# or a 15-minute watch. Day/Month/Year placeholders must not trip the gate.
PRECISE = ('Second', 'Minute', 'Hour')
WINDOW_BEFORE = timedelta(hours=6)
WINDOW_AFTER = timedelta(hours=1)
# Cap imminent requests so 1 full refresh + 3 imminent ticks stay under 15/hour.
# 5 + 3*3 = 14. Typical ticks fetch 0 or 1 launch.
IMMINENT_MAX = 3


def get(params):
    q = dict(params, mode='normal', hide_recent_previous='true')
    req = urllib.request.Request(API + '?' + urllib.parse.urlencode(q), headers={'User-Agent': UA, 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def get_one(launch_id):
    url = LAUNCH_API + urllib.parse.quote(launch_id, safe='') + '/'
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json'})
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


def launch_label(launch):
    return launch.get('mission') or launch.get('name') or launch.get('id')


def imminent_launches(launches, now):
    """Precise tracked launches whose NET is in the next 6 hours or the past 1 hour."""
    found = []
    for launch in launches:
        if launch.get('precision') not in PRECISE:
            continue
        net = datetime.fromisoformat(launch['net'].replace('Z', '+00:00'))
        if now - WINDOW_AFTER <= net <= now + WINDOW_BEFORE:
            found.append(launch)
    found.sort(key=lambda l: l['net'])
    return found


def write_out(launches, now, full_fetched_at, old, always_touch_fetched=True):
    # Imminent path: leave the file alone if launch rows did not change, so
    # the workflow does not commit or deploy a timestamp-only update.
    if not always_touch_fetched and old and old.get('launches') == launches:
        print('launches: no field changes; leaving cache as-is')
        return 0
    fetched_at = now.strftime('%Y-%m-%dT%H:%M:%SZ')
    ordered = {'fetched_at': fetched_at}
    if full_fetched_at:
        ordered['full_fetched_at'] = full_fetched_at
    ordered['source'] = 'The Space Devs Launch Library 2 (' + API + ')'
    ordered['launches'] = launches
    OUT.write_text(json.dumps(ordered, ensure_ascii=False, indent=1) + '\n')
    print(f'launches: saved {len(launches)} upcoming launches')
    return 0


def refresh_full(force=False):
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
    used = launch_overrides.apply(launches, now)
    if used: print('launches: applied sourced overrides for', ', '.join(used))
    full_at = now.strftime('%Y-%m-%dT%H:%M:%SZ')
    return write_out(launches, now, full_at, old, always_touch_fetched=True)


def refresh_imminent():
    if not OUT.exists():
        print('launches: no cache yet; skip imminent (need a full refresh first)'); return 0
    old = json.loads(OUT.read_text())
    now = datetime.now(timezone.utc)
    watch = imminent_launches(old.get('launches') or [], now)
    if not watch:
        print('launches: no precise launch in the -1h..+6h window; nothing to update'); return 0
    if len(watch) > IMMINENT_MAX:
        print(f'launches: {len(watch)} in window, fetching the {IMMINENT_MAX} soonest (cap)')
        watch = watch[:IMMINENT_MAX]
    try:
        fetched = []
        for i, launch in enumerate(watch):
            if i: time.sleep(2)
            fetched.append(slim(get_one(launch['id'])))
    except Exception as e:
        print(f'launches: imminent fetch failed ({e.__class__.__name__}: {e}); keeping cached data/launches.json'); return 0
    by_id = {s['id']: s for s in fetched}
    merged = []
    for launch in old['launches']:
        if launch['id'] not in by_id:
            merged.append(launch)
            continue
        updated = dict(by_id[launch['id']])
        if 'queries' in launch:
            updated['queries'] = launch['queries']
        merged.append(updated)
    used = launch_overrides.apply(merged, now)
    if used: print('launches: applied sourced overrides for', ', '.join(used))
    names = ', '.join(launch_label(l) for l in watch)
    print(f'launches: checked {len(watch)} imminent launch(es): {names}')
    return write_out(merged, now, old.get('full_fetched_at'), old, always_touch_fetched=False)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if '--imminent' in argv and '--force' in argv:
        print('launches: use only one of --force or --imminent'); return 2
    if '--imminent' in argv:
        return refresh_imminent()
    return refresh_full(force='--force' in argv)


if __name__ == '__main__':
    sys.exit(main())
