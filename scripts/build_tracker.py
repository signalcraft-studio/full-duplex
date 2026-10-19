#!/usr/bin/env python3
"""Rebuild the tracker table in tracker.html from data/tracker.json.
Usage (from repo root): python3 scripts/build_tracker.py
The map (assets/tracker-map.js) reads data/tracker.json directly in the browser."""
import json, pathlib, re
root = pathlib.Path(__file__).resolve().parent.parent
d = json.loads((root/'data/tracker.json').read_text())
cls = {'live':'live','trial':'trial','announced':'ann'}
rows = ["<tr><th>Country</th><th>Operator partner</th><th>Satellite provider</th><th>Status</th><th>Services</th><th>Source</th><th>Last checked</th></tr>"]
for r in d['rows']:
    src = ' · '.join(f"<a href='{s['url']}'>{s['label']}</a>" for s in r['sources'])
    rows.append(f"<tr><td>{r['country']}</td><td>{r['operator']}</td><td>{r['satellite']}</td><td class={cls[r['status']]}>{r['status']}</td><td>{r['services']}</td><td>{src}</td><td>{r['checked']}</td></tr>")
p = root/'tracker.html'
s = p.read_text()
new = "<!-- TRACKER-TABLE:START (generated from data/tracker.json by scripts/build_tracker.py; do not edit by hand) --><table id=tracker-table>" + ''.join(rows) + "</table><!-- TRACKER-TABLE:END -->"
s, n = re.subn(r'<!-- TRACKER-TABLE:START.*?TRACKER-TABLE:END -->', lambda m: new, s, flags=re.S)
assert n == 1, 'markers not found'
s = re.sub(r'<span id=tracker-checked>.*?</span>', f"<span id=tracker-checked>{d['last_checked']}</span>", s)
p.write_text(s)
print('tracker.html rebuilt:', len(d['rows']), 'rows')
