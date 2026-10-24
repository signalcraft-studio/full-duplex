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
    rows.append(
        "<tr>"
        f"<td data-label='Country'>{r['country']}</td>"
        f"<td data-label='Operator partner'>{r['operator']}</td>"
        f"<td data-label='Satellite provider'>{r['satellite']}</td>"
        f"<td data-label='Status' class={cls[r['status']]}>{r['status']}</td>"
        f"<td data-label='Services'>{r['services']}</td>"
        f"<td data-label='Source'>{src}</td>"
        f"<td data-label='Last checked'>{r['checked']}</td>"
        "</tr>"
    )
p = root/'tracker.html'
s = p.read_text()
new = "<!-- TRACKER-TABLE:START (generated from data/tracker.json by scripts/build_tracker.py; do not edit by hand) --><table id=tracker-table>" + ''.join(rows) + "</table><!-- TRACKER-TABLE:END -->"
s, n = re.subn(r'<!-- TRACKER-TABLE:START.*?TRACKER-TABLE:END -->', lambda m: new, s, flags=re.S)
assert n == 1, 'markers not found'
s = re.sub(r'<span id=tracker-checked>.*?</span>', f"<span id=tracker-checked>{d['last_checked']}</span>", s)
p.write_text(s)
print('tracker.html rebuilt:', len(d['rows']), 'rows')
