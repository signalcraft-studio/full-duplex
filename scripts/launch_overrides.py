"""Apply data/launch-overrides.json (sourced corrections) to Launch Library 2 launches.

Used by scripts/fetch_launches.py before it saves data/launches.json and by scripts/build.py when it
loads it, so a correction survives the 4x-daily refresh. Idempotent. An override matches one launch by
id and expires automatically: it stops applying 3 hours after the launch's NET (the launch is past) or
after its 'expires' date. Window fixes only apply while the launch keeps the window start the source quoted.
"""
import json, pathlib
from datetime import datetime, timedelta, timezone

PATH = pathlib.Path(__file__).resolve().parent.parent / 'data' / 'launch-overrides.json'

def _dt(s): return datetime.fromisoformat(s.replace('Z', '+00:00'))

def load():
    return json.loads(PATH.read_text()).get('overrides', []) if PATH.exists() else []

def apply(launches, now=None):
    now = now or datetime.now(timezone.utc)
    by_id = {o['id']: o for o in load()}
    used = []
    for l in launches:
        o = by_id.get(l.get('id'))
        if not o: continue
        if o.get('expires') and now > _dt(o['expires']): continue
        if l.get('net') and now > _dt(l['net']) + timedelta(hours=3): continue
        src = o['source']
        if o.get('payload_count'): l['payload_count'] = o['payload_count']
        w = o.get('window')
        if w and (l.get('window_start') or '').startswith(w['when_window_start']): l['window_end'] = w['window_end']
        for field, pairs in (o.get('replace_text') or {}).items():
            t = l.get(field) or ''
            for a, b in pairs: t = t.replace(a, b)
            if field in l: l[field] = t
        l['override_source'] = {'label': src['label'], 'url': src['url'], 'checked': src.get('checked')}
        used.append(o['label'])
    return used
