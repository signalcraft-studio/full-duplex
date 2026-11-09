# full-duplex
Full Duplex: satellite-to-phone, GSM and the future of mobile.

Live site: https://signalcraft-studio.github.io/full-duplex/ (GitHub Pages, served from `main`).

## How the site is built
- Page bodies live in `src/` (`src/articles/*.html`, `src/pages/*.html`), each with a JSON `<!--meta ... -->` header. Site settings (X handle, Signal issues, beehiiv form, article order) are in `src/site.json`.
- Tracker data lives in `data/tracker.json` (single source of truth for the table and map).
- Run `python3 scripts/build.py` (standard library only), then commit the generated files. GitHub Pages serves the committed output; there is no CI step.
- Shared header, footer, meta/OG tags, Signal subscribe blocks, sitemap, robots.txt and RSS are all produced by the build. Do not hand-edit generated HTML.

## Images
No images are used yet. Places where approved artwork will go are marked `TODO(image-approval)`. Nothing is added until Sam approves a preview.
