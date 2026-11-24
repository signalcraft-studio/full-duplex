#!/usr/bin/env python3
"""Decide whether the Refresh launches workflow should run this tick.

Used as a cheap first step so the 15-minute cron can no-op most of the time
without calling Launch Library 2 or building the site.

  python3 scripts/launch_refresh_due.py
  python3 scripts/launch_refresh_due.py --event schedule --now 2026-11-24T10:00:00Z

Prints GitHub Actions outputs (mode, due, reason) and exits 0.

Modes:
  full       — hourly (or stale) 5-query refresh, and any workflow_dispatch
  imminent   — a precise tracked launch has NET in the next 6 hours, or in
               the past hour (to catch a scrub), and a full refresh is not due
  skip       — neither of the above
"""
import argparse
import json
import pathlib
import sys
from datetime import datetime, timedelta, timezone

import fetch_launches as fl

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'data' / 'launches.json'
# If the last full refresh is this old, run a full refresh even mid-hour.
# 50 minutes (not 60) so a delayed or missed :00 tick is picked up at :15.
FULL_AGE_MIN = 50


def parse_iso(s):
    if not s:
        return None
    return datetime.fromisoformat(s.replace('Z', '+00:00'))


def fmt_delta(td):
    secs = int(abs(td.total_seconds()))
    h, rem = divmod(secs, 3600)
    m = rem // 60
    if h and m:
        return f'{h}h {m}m'
    if h:
        return f'{h}h'
    return f'{m}m'


def next_precise(launches, now):
    future = []
    for launch in launches:
        if launch.get('precision') not in fl.PRECISE:
            continue
        net = parse_iso(launch['net'])
        if net and net > now:
            future.append((net, launch))
    if not future:
        return None
    future.sort(key=lambda item: item[0])
    return future[0]


def decide(event, now, data, full_fetched_override=None):
    if event == 'workflow_dispatch':
        return 'full', 'workflow_dispatch always runs a full refresh'

    launches = data.get('launches') or []
    imminent = fl.imminent_launches(launches, now)

    if full_fetched_override is not None:
        full_at = full_fetched_override
    else:
        full_at = parse_iso(data.get('full_fetched_at') or data.get('fetched_at'))
    full_age = (now - full_at) if full_at else timedelta(days=99)
    full_due = full_at is None or full_age >= timedelta(minutes=FULL_AGE_MIN)
    age_txt = 'never' if not full_at else f'{fmt_delta(full_age)} ago'

    if full_due:
        extra = ''
        if imminent:
            names = ', '.join(fl.launch_label(l) for l in imminent)
            extra = f'; also in window: {names}'
        return 'full', f'last full refresh {age_txt}{extra}'

    if imminent:
        parts = []
        for launch in imminent:
            net = parse_iso(launch['net'])
            rel = 'in' if net >= now else 'was'
            parts.append(f'{fl.launch_label(launch)} (NET {rel} {fmt_delta(net - now)})')
        return 'imminent', 'precise launch in window: ' + '; '.join(parts)

    nxt = next_precise(launches, now)
    if nxt:
        net, launch = nxt
        return 'skip', (
            f'next precise launch in {fmt_delta(net - now)} '
            f'({fl.launch_label(launch)}); last full refresh {age_txt}'
        )
    return 'skip', f'no precise upcoming launches; last full refresh {age_txt}'


def main(argv):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--event', default='schedule',
                   help='GitHub event name (schedule or workflow_dispatch)')
    p.add_argument('--now', help='UTC time to evaluate, e.g. 2026-11-24T10:00:00Z')
    p.add_argument('--full-fetched-at',
                   help='Override last full-refresh time (for local tests)')
    p.add_argument('--file', type=pathlib.Path, default=OUT,
                   help='Path to launches.json')
    args = p.parse_args(argv)

    now = parse_iso(args.now) if args.now else datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    data = json.loads(args.file.read_text()) if args.file.exists() else {}
    override = parse_iso(args.full_fetched_at) if args.full_fetched_at else None
    mode, reason = decide(args.event, now, data, override)
    due = 'true' if mode != 'skip' else 'false'
    # GitHub Actions outputs, also readable as a local dry run.
    print(f'mode={mode}')
    print(f'due={due}')
    print(f'reason={reason}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
