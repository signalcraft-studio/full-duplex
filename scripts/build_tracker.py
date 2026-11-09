#!/usr/bin/env python3
"""Kept for old notes and routines: the tracker table is now built by scripts/build.py,
which rebuilds the whole site from src/ and data/tracker.json. This runs it."""
import pathlib, runpy
runpy.run_path(str(pathlib.Path(__file__).resolve().parent / 'build.py'), run_name='__main__')
