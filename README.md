# full-duplex
Full Duplex: satellite-to-phone, GSM and the future of mobile.

Live site: https://fullduplexhq.com/ (GitHub Pages custom domain, served from `main`; the `CNAME` file and the Pages custom-domain setting must both say `fullduplexhq.com`. Old https://signalcraft-studio.github.io/full-duplex/ URLs redirect here).

## How the site is built
- Page bodies live in `src/` (`src/articles/*.html`, `src/pages/*.html`), each with a JSON `<!--meta ... -->` header. Site settings (X handle, Signal issues, beehiiv form, article order) are in `src/site.json`.
- Tracker data lives in `data/tracker.json` (single source of truth for the table and map).
- Run `python3 scripts/build.py` (standard library only), then commit the generated files. The Deploy Pages workflow uploads only the built site to GitHub Pages (it leaves out `src/`, `scripts/`, `.github/` and build-only data files).
- The build produces every page plus: shared header/footer, meta/OG tags, Signal subscribe blocks, the articles index, Tracker 2.0 (filters, CSV at `data/tracker.csv`), one page per country under `tracker/<country>/`, the change log (`tracker/changes/`, data in `data/tracker-changes.json`, rebuilt from the git history of `data/tracker.json`), the home globe data (`assets/globe-dots.json`), `search-index.json` for `search.html`, `sitemap.xml`, `robots.txt`, `feed.xml` and `404.html`. Do not hand-edit generated HTML.
- New country in the tracker? Add its region to `regions` in `src/site.json` (the build warns if one is missing).
- Fonts (Inter Tight, Newsreader, JetBrains Mono; SIL OFL, see `assets/fonts/OFL.txt`) are embedded in `assets/fonts.css` and load without blocking the page.

## Launch tracker (`launches/`)
- `python3 scripts/fetch_launches.py` pulls upcoming launches from The Space Devs Launch Library 2 (free API, 15 requests/hour) into `data/launches.json`. It makes 5 requests, skips the fetch if the cache is under 2 hours old (use `--force` to override), and keeps the cached file if the API fails. Then run `python3 scripts/build.py`.
- `ci/launches.yml` (move to `.github/workflows/` to activate) does fetch + build + commit four times a day once it is on `main` (scheduled workflows only run from the default branch).
- Each launch is tagged by telco relevance in `scripts/build.py` (`classify`). A Starlink launch is tagged Direct to Cell only if the launch data says so; to tag one by hand, add its Launch Library id to `data/launch-tags.json` with a source.
- Satellite counts for the comparison panel live in `data/constellations.json`. Every number needs a source URL and an `as_of` date; use `null` (shown as "Not disclosed") rather than an estimate. Phone-capable and broadband-only networks are kept in separate lists.
- Calendar files are generated in `launches/cal/` for launches with a set day or time.

## Share to X (`share/`, preview 16 Nov 2026, needs Sam's approval)
- Launch cards, the flight view, the orbit view, the race chart and each section of `/satellites/` have **Post to X** (a plain `x.com/intent/post` link, no X scripts) and **Save image**.
- Each share points at a static page `share/<slug>/index.html` with its own `og:image`/`twitter:image` (`summary_large_image`), which sends people straight on to the deep link (`launches/flight/?l=<slug>`, or a `#anchor`) with `utm_source=x&utm_medium=share&utm_campaign=infographic`. X's crawler runs no JavaScript, so this is the only way to get a different card per infographic on GitHub Pages.
- `scripts/build.py` writes the share pages and `share/items.json` (what to render), and deletes share pages for launches that have gone. `scripts/render_share.py` screenshots the real globe/infographic in headless Chromium and adds logo A and a caption (Pillow) -> `share/<slug>/card.jpg` (1200x630 JPEG, quality 88). It only renders cards that are missing or whose details changed (`share/manifest.json`); `--all` re-renders everything. Run `python3 scripts/build.py` again afterwards.
- Pre-rendered cards: 16 launches, phone/direct-to-cell first, then Starlink/Amazon Leo/OneWeb broadband, then other commercial communications; military/NRO launches never get one plus the orbit view, race chart, flight-view globe and the satellites sections. Other launches share the flight view's normal card. The refresh workflow renders new cards only when needed.
- Save image downloads the pre-rendered card; on the two globes it saves the live globe with a small Full Duplex watermark.

## Images
All artwork below was approved by Sam on 9 Nov 2026. New artwork needs a preview approved before it goes on the site.

- Logo A: `assets/logo.svg` (inlined as `LOGO_MARK` in `scripts/build.py`; `src/img/logo-a-512.png` is its render for share cards). Favicon A:  `assets/favicon.svg` plus PNG fallbacks (`favicon-32.png`, `apple-touch-icon.png`, `icon-192/512.png`, `site.webmanifest`).
- Home hero, article header plate, tracker backdrop (decorative only, faint) and sponsor card plate: originals in `src/img/`, responsive WebP in `assets/img/`. Regenerate with `python3 scripts/images.py` (needs Pillow).
- Share cards: `assets/og/<page>.jpg` (1200x630) are drawn per page by `scripts/build.py` when Pillow is installed (`pip install pillow`); without Pillow the committed cards are kept.
- Fonts: self-hosted WOFF2 in `assets/fonts/`, declared at the top of `style.css`.
