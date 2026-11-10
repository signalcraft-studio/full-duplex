# full-duplex
Full Duplex: satellite-to-phone, GSM and the future of mobile.

Live site: https://signalcraft-studio.github.io/full-duplex/ (GitHub Pages, served from `main`).

## How the site is built
- Page bodies live in `src/` (`src/articles/*.html`, `src/pages/*.html`), each with a JSON `<!--meta ... -->` header. Site settings (X handle, Signal issues, beehiiv form, article order) are in `src/site.json`.
- Tracker data lives in `data/tracker.json` (single source of truth for the table and map).
- Run `python3 scripts/build.py` (standard library only), then commit the generated files. GitHub Pages serves the committed output; there is no CI step.
- The build produces every page plus: shared header/footer, meta/OG tags, Signal subscribe blocks, the articles index, Tracker 2.0 (filters, CSV at `data/tracker.csv`), one page per country under `tracker/<country>/`, the change log (`tracker/changes/`, data in `data/tracker-changes.json`, rebuilt from the git history of `data/tracker.json`), the home globe data (`assets/globe-dots.json`), `search-index.json` for `search.html`, `sitemap.xml`, `robots.txt`, `feed.xml` and `404.html`. Do not hand-edit generated HTML.
- New country in the tracker? Add its region to `regions` in `src/site.json` (the build warns if one is missing).
- Fonts (Inter Tight, Newsreader, JetBrains Mono; SIL OFL, see `assets/fonts/OFL.txt`) are embedded in `assets/fonts.css` and load without blocking the page.

## Launch tracker (`launches/`)
- `python3 scripts/fetch_launches.py` pulls upcoming launches from The Space Devs Launch Library 2 (free API, 15 requests/hour) into `data/launches.json`. It makes 5 requests, skips the fetch if the cache is under 2 hours old (use `--force` to override), and keeps the cached file if the API fails. Then run `python3 scripts/build.py`.
- `ci/launches.yml` (move to `.github/workflows/` to activate) does fetch + build + commit four times a day once it is on `main` (scheduled workflows only run from the default branch).
- Each launch is tagged by telco relevance in `scripts/build.py` (`classify`). A Starlink launch is tagged Direct to Cell only if the launch data says so; to tag one by hand, add its Launch Library id to `data/launch-tags.json` with a source.
- Satellite counts for the comparison panel live in `data/constellations.json`. Every number needs a source URL and an `as_of` date; use `null` (shown as "Not disclosed") rather than an estimate. Phone-capable and broadband-only networks are kept in separate lists.
- Calendar files are generated in `launches/cal/` for launches with a set day or time.

## Images
All artwork below was approved by Sam on 9 Nov 2026. New artwork needs a preview approved before it goes on the site.

- Logo A: `assets/logo.svg` (inlined as `LOGO_MARK` in `scripts/build.py`; `src/img/logo-a-512.png` is its render for share cards). Favicon A:  `assets/favicon.svg` plus PNG fallbacks (`favicon-32.png`, `apple-touch-icon.png`, `icon-192/512.png`, `site.webmanifest`).
- Home hero, article header plate, tracker backdrop (decorative only, faint) and sponsor card plate: originals in `src/img/`, responsive WebP in `assets/img/`. Regenerate with `python3 scripts/images.py` (needs Pillow).
- Share cards: `assets/og/<page>.jpg` (1200x630) are drawn per page by `scripts/build.py` when Pillow is installed (`pip install pillow`); without Pillow the committed cards are kept.
- Fonts: self-hosted WOFF2 in `assets/fonts/`, declared at the top of `style.css`.
