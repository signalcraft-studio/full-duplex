"""Satellite illustrations and looping animations for /satellites/ and the /launches/ payload cards.

Everything is drawn here in SVG from public descriptions (no company imagery). Illustrative, not to scale.
Animation lives in style.css (".sa" rules): the default, un-animated state is the finished picture
(array unfolded, beam on, message delivered), so prefers-reduced-motion users get a sensible still.
PREVIEW: new artwork needs Sam's approval before it goes on the live site.
"""
COL = {'starlink-dtc': '#00cfff', 'bluebird': '#ff9a3c', 'amazon-leo': '#f5c26b', 'lynk': '#6ee79a', 'globalstar': '#b58cff'}
LABEL = {'starlink-dtc': 'Starlink Direct to Cell satellite', 'bluebird': 'AST SpaceMobile BlueBird satellite',
         'amazon-leo': 'Amazon Leo broadband satellite', 'lynk': 'Lynk satellite', 'globalstar': 'Globalstar satellite'}
BUBBLE = {'starlink-dtc': 'TXT', 'bluebird': '5G', 'amazon-leo': 'WEB', 'lynk': 'SMS', 'globalstar': 'SOS'}

STARS = ''.join(f'<circle cx="{x}" cy="{y}" r="{r}"/>' for x, y, r in
                [(18, 20, .9), (52, 64, .6), (88, 14, .8), (150, 22, .7), (196, 58, .9), (222, 18, .6), (30, 104, .6), (210, 100, .7), (70, 96, .5), (176, 84, .5)])
SAT_Y = 50

def _cells(x, y, w, h, n, col):
    step = w / n
    lines = ''.join(f'M{x + step * i:.1f} {y}v{h}' for i in range(1, n))
    return f'<path d="{lines}M{x} {y + h / 2}h{w}" stroke="{col}" stroke-width=".5" opacity=".55"/>'

def _wing(side, x0, w, h, fill, edge, n, extra_cls=''):
    """A solar wing that unfolds out from the body (side -1 = left, 1 = right)."""
    x = x0 - w if side < 0 else x0
    origin = 'ox-r' if side < 0 else 'ox-l'
    return (f'<g class="unf ux {origin}{extra_cls}"><rect x="{x}" y="{-h / 2}" width="{w}" height="{h}" fill="{fill}" stroke="{edge}" stroke-width=".8"/>'
            + _cells(x, -h / 2, w, h, n, edge) + '</g>')

def _sat(kind):
    c = COL[kind]
    if kind == 'starlink-dtc':  # flat slab bus, long solar wings, square phone antenna underneath
        return (_wing(-1, -15, 86, 13, '#0d2a4a', '#5ec8ff', 8) + _wing(1, 15, 86, 13, '#0d2a4a', '#5ec8ff', 8)
                + '<rect x="-16" y="-9" width="32" height="18" rx="1.5" fill="#dfe8f3"/><path d="M-16 -3h32M-16 3h32" stroke="#9fb0c3" stroke-width=".6"/>'
                + f'<g class="unf uy oy-t"><rect x="-10.5" y="9" width="21" height="8" rx="1" fill="#06324a" stroke="{c}" stroke-width="1"/>{_cells(-10.5, 9, 21, 8, 4, c)}</g>')
    if kind == 'bluebird':  # one huge flat array, 3x3 panels, shown in perspective
        def tile(x, y):
            return (f'<rect x="{x}" y="{y}" width="28" height="28" fill="#1a2a44" stroke="{c}" stroke-width="1.2"/>'
                    f'<path d="M{x + 7} {y}v28M{x + 14} {y}v28M{x + 21} {y}v28M{x} {y + 7}h28M{x} {y + 14}h28M{x} {y + 21}h28" stroke="#ffc08a" stroke-width=".5" opacity=".45"/>')
        left = ''.join(tile(-42, y) for y in (-42, -14, 14)); right = ''.join(tile(14, y) for y in (-42, -14, 14))
        return (f'<g transform="skewX(-32) scale(1 .42)">'
                f'<g class="unf uy oy-b d1">{tile(-14, -42)}</g><g class="unf uy oy-t d1">{tile(-14, 14)}</g>{tile(-14, -14)}'
                f'<g class="unf ux ox-r d2">{left}</g><g class="unf ux ox-l d2">{right}</g></g>')
    if kind == 'amazon-leo':  # generic flat-panel broadband satellite (dimensions TBC)
        return (_wing(-1, -10, 52, 12, '#2e2410', c, 6) + _wing(1, 10, 52, 12, '#2e2410', c, 6)
                + '<rect x="-10" y="-13" width="20" height="26" rx="1.5" fill="#dfe8f3"/>'
                + f'<rect x="-7" y="-9" width="14" height="10" rx="1" fill="#3a2a0a" stroke="{c}" stroke-width=".8"/><circle cx="0" cy="7" r="2.4" fill="{c}"/>')
    if kind == 'lynk':  # small box, short panels, deployable antenna
        return (_wing(-1, -7, 20, 9, '#0f2f22', c, 3) + _wing(1, 7, 20, 9, '#0f2f22', c, 3)
                + '<rect x="-7" y="-5.5" width="14" height="11" rx="1.2" fill="#dfe8f3"/>'
                + f'<g class="unf uy oy-t"><path d="M0 5.5v12M-6 17.5h12M-4 12h8" stroke="{c}" stroke-width="1.3" stroke-linecap="round"/></g>')
    if kind == 'globalstar':  # trapezoid body, two wings on booms
        return ('<path d="M-17 -4h34" stroke="#7f93a8" stroke-width="1.2"/>'
                + _wing(-1, -17, 50, 14, '#221838', c, 5) + _wing(1, 17, 50, 14, '#221838', c, 5)
                + '<path d="M-11 -9H11L15 9H-15Z" fill="#dfe8f3"/>'
                + f'<g class="unf uy oy-t"><path d="M-9 9h18l-2 5h-14z" fill="#221838" stroke="{c}" stroke-width=".8"/></g>')
    raise KeyError(kind)

def _phone(c, x, y):
    return (f'<g transform="translate({x} {y})"><rect x="-7" y="-12" width="14" height="24" rx="3" fill="#1b2840" stroke="#8fdbff" stroke-width="1.2"/>'
            f'<rect x="-5" y="-9" width="10" height="17" rx="1.5" fill="#060c18"/><rect class="glow" x="-5" y="-9" width="10" height="17" rx="1.5" fill="{c}" opacity=".35"/></g>')

def _dish(c, x, y):
    return (f'<g transform="translate({x} {y})"><path d="M-10 10h20M-3 10l3-9 3 9" stroke="#7f93a8" stroke-width="1.4" fill="none"/>'
            f'<path d="M-12 -9a13 13 0 0 0 20 10z" fill="#dfe8f3" transform="rotate(-20)"/><circle class="glow" cx="3" cy="-8" r="2.2" fill="{c}"/></g>')

def _station(c, x, y):
    return (f'<g transform="translate({x} {y})"><rect x="-9" y="2" width="18" height="8" rx="1" fill="#16243d" stroke="#7f93a8" stroke-width=".8"/>'
            f'<path d="M-9 -8a11 11 0 0 0 16 8z" fill="#dfe8f3" transform="rotate(25)"/><path d="M0 2v-5" stroke="#7f93a8" stroke-width="1.2"/><circle class="glow g2" cx="0" cy="-5" r="1.8" fill="{c}"/></g>')

def _bubble(c, x, y, txt):
    w = 8 + 6 * len(txt)
    return (f'<g class="bub"><rect x="{x}" y="{y}" width="{w}" height="13" rx="6.5" fill="{c}"/><path d="M{x + 5} {y + 12}l-3 5 7-5z" fill="{c}"/>'
            f'<text x="{x + w / 2}" y="{y + 9.3}" text-anchor="middle" font-family="JetBrains Mono,ui-monospace,monospace" font-size="8" font-weight="700" fill="#06101c">{txt}</text></g>')

CARD_LABELS = {  # (x, y, anchor, text) in the 240x180 box; card-size only
    'starlink-dtc': [(12, 34, 'start', 'Solar wings'), (136, 80, 'start', 'Phone antenna'), (150, 172, 'start', 'Your 4G phone')],
    'bluebird': [(10, 22, 'start', 'Array unfolds in orbit'), (150, 172, 'start', 'Your 4G/5G phone')],
    'amazon-leo': [(10, 32, 'start', 'Solar wings'), (148, 172, 'start', 'Dish, not a phone')],
    'lynk': [(10, 34, 'start', 'Small: about 1 m'), (150, 172, 'start', 'Any phone')],
    'globalstar': [(10, 30, 'start', 'Flies at 1,414 km'), (150, 172, 'start', 'iPhone 14+'), (26, 172, 'start', 'Ground station')],
}

def scene(kind, size='mini'):
    """Inline SVG. size='mini' for payload cards (decorative), 'card' for /satellites/ (labelled)."""
    c = COL[kind]; sy = SAT_Y
    tx, ty = (168, 140)
    ground = _dish(c, tx, ty) if kind == 'amazon-leo' else _phone(c, tx, ty - 2)
    beam = (f'<g class="beam"><path d="M{120 - 8} {sy + 10}L{120 + 8} {sy + 10}L{tx + 16} {ty + 6}L{tx - 14} {ty + 6}Z" fill="{c}" opacity=".16"/>'
            f'<path class="flow" d="M120 {sy + 10}L{tx} {ty - 12}" stroke="{c}" stroke-width="1.6" stroke-dasharray="3 6" stroke-linecap="round"/></g>')
    extra = ''
    if kind == 'globalstar':  # bent pipe: phone -> satellite -> ground station
        sx, sty = 52, 146
        extra = (_station(c, sx, sty) + f'<g class="beam b2"><path class="flow" d="M120 {sy + 10}L{sx + 2} {sty - 12}" stroke="{c}" stroke-width="1.4" stroke-dasharray="3 6" stroke-linecap="round"/></g>')
    bub = _bubble(c, tx + 8, ty - 38, BUBBLE[kind])
    labels = ''
    if size == 'card':
        labels = '<g class="lbl" font-family="Inter Tight,ui-sans-serif,system-ui,sans-serif" font-size="9" fill="#cfdbe8">' + ''.join(
            f'<text x="{x}" y="{y}" text-anchor="{a}">{t}</text>' for x, y, a, t in CARD_LABELS[kind]) + '</g>'
    aria = (f'role="img" aria-label="Illustration: {LABEL[kind]} unfolding and beaming a signal down to '
            + ('a dish on the ground (not a phone)' if kind == 'amazon-leo' else 'a phone') + '. Not to scale."') if size == 'card' else 'aria-hidden="true" focusable="false"'
    return (f'<svg class="sa sa-{kind} sa-{size}" viewBox="0 0 240 180" {aria}>'
            f'<rect width="240" height="180" rx="14" fill="#0b1426"/><g fill="#cfe6ff" opacity=".8">{STARS}</g>'
            f'<path d="M0 156Q120 128 240 156V180H0z" fill="#13233d"/><path d="M0 156Q120 128 240 156" fill="none" stroke="#2b4a73"/>'
            f'<g class="sc">{beam}{extra}{ground}<g transform="translate(120 {sy})"><g class="drift">{_sat(kind)}</g></g>{bub}</g>{labels}</svg>')

def kind_of(tag, text, who):
    """Which animation a launch gets. None = no animation (e.g. Starlink broadband, other missions)."""
    if tag == 'starlink-dtc': return 'starlink-dtc'
    if tag == 'ast': return 'bluebird'
    if tag == 'amazon-leo': return 'amazon-leo'
    if 'Globalstar' in text: return 'globalstar'
    if 'lynk' in who: return 'lynk'
    return None
