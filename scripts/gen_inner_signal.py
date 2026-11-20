#!/usr/bin/env python3
"""Generates src/pages/inner-signal.html for the Full Duplex repo.  Usage: python3 gen_page.py /workspace/fdrepo"""
import sys, json, html
ROOT = sys.argv[1] if len(sys.argv) > 1 else '/workspace/fdrepo'
esc = lambda s: html.escape(s, quote=True)

ICONS = {  # 24x24 line glyphs
 'landline': '<path d="M3 18h18v3H3zM6 18v-3h12v3M4.5 10.5c4.5-3.4 10.500-3.4 15 0l-2 2.200c-3.200-2.200-7.800-2.200-11 0z"/>',
 'phone': '<rect x="7.500" y="2.500" width="9" height="19" rx="2.200"/><path d="M11 18.500h2"/>',
 'exchange': '<path d="M3 21h18M5 21V9.500l7-5.500 7 5.500V21M9 21v-7h6v7"/>',
 'transit': '<path d="M3 7h6l3 5h9M3 17h6l3-5M18 9l3 3-3 3"/>',
 'gate': '<path d="M3 12h13M12 7l5 5-5 5M21 4v16"/>',
 'hlr': '<rect x="5" y="3" width="14" height="18" rx="1.500"/><path d="M5 9h14M5 15h14M10.500 6h3M10.500 12h3M10.500 18h3"/>',
 'vlr': '<path d="M4 21V9l8-5 8 5v12M9 21v-5h6v5M9 12h.01M15 12h.01"/>',
 'sat': '<rect x="9" y="9" width="6" height="6" rx="1" transform="rotate(45 12 12)"/><path d="M3 6l4-3 3 4-4 3zM14 17l3 4 4-3-3-4zM12 3v2M19 12h2"/>',
 'dish': '<path d="M5 14a8 8 0 0 0 14-3L11 3zM12 14l-1 6M7 21h9"/>',
 'eir': '<path d="M12 3l8 3v6c0 5-3.500 8-8 9-4.500-1-8-4-8-9V6zM8.500 12l2.500 2.500 4.500-5"/>',
 'scp': '<circle cx="12" cy="12" r="8.500"/><path d="M14.500 8.500c-.8-1-3.500-1.200-4.200.5-.8 1.800 1 2.700 1.700 3.200.8.6 1.200 1.500.4 2.300-.9.900-3 .6-3.600-.5M8 15.500h7"/>',
 'mgw': '<path d="M4 8h16M16 4l4 4-4 4M20 16H4M8 12l-4 4 4 4"/>',
 'bill': '<path d="M6 3h12v18l-3-2-3 2-3-2-3 2zM9 8h6M9 12h6"/>',
 'vm': '<rect x="2" y="6" width="20" height="12" rx="3"/><circle cx="8" cy="12" r="2.500"/><circle cx="16" cy="12" r="2.500"/><path d="M8 14.500h8"/>',
 'tower': '<path d="M12 8v13M7 21l5-13 5 13M8.500 16h7M4 6a9 9 0 0 0 0 6M20 6a9 9 0 0 1 0 6"/>',
 'vault': '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="12" cy="12" r="4"/><path d="M12 8v8M8 12h8"/>',
 'sim': '<path d="M6 3h8l4 4v14H6zM9 12h6v6H9z"/>',
}
ICONS = {k: v.replace('.500', '.5').replace('.200', '.2').replace('.800', '.8').replace('.900', '.9').replace('.600', '.6').replace('.700', '.7').replace('.400', '.4') for k, v in ICONS.items()}

ZONES = {'land': 'Landline network', 'core': 'Mobile core', 'space': 'Space', 'back': 'Back office'}

# each chapter: n, zone, title, kicker, caption, nodes [(icon,label,dy)], chip, reply, chipAt, protocol, real(code), notes, onscreen, art(img file,alt)
CH = [
 dict(n=1, zone='land', title='Gran picks up the phone', node=[('landline', 'Gran’s landline', 0), ('exchange', 'Local exchange', 0)],
  chip='dial tone, then 07700 900123', reply='', proto='Analogue line signalling',
  cap='In a kitchen in Warminster, Gran lifts the handset. That closes an electrical circuit on her phone line, and the exchange down the road notices straight away. It plays a dial tone, which really means “I’m listening”. She taps in her grandson’s mobile number, and we shrink down and climb aboard the Call Pod.',
  real='Handset lifted  →  line loop closes, exchange detects off-hook\nExchange  →  dial tone: 350 Hz + 450 Hz (UK)\nGran dials 07700 900123  →  DTMF, two tones per digit\n   “7” = 852 Hz + 1209 Hz     “0” = 941 Hz + 1336 Hz',
  notes=['Tone dialling (DTMF) sends each digit as two pitches at once, so the exchange can tell them apart from speech.',
         'UK landlines are moving off the old copper phone network (the PSTN) and onto broadband. Openreach says that happens on <a href="https://www.openreach.com/big-switch-off">31 January 2027</a>. The story below is the classic version, and the call still ends up in the same place.'],
  on=['Call Pod'], art=('off-hook', 'Gran on her kitchen landline while sparkling sound waves from the handset swirl around the tiny Call Pod hovering beside her')),
 dict(n=2, zone='land', title='The exchange hands it on', node=[('exchange', 'Local exchange', 0), ('transit', 'Transit exchange', 0), ('gate', 'Gateway MSC', 0)],
  chip='IAM', reply='', proto='SS7 · ISUP',
  cap='Gran’s exchange sees a number starting 07. That means mobile, and it isn’t one of its own, so it passes the call up to a bigger “transit” exchange. That works out which mobile operator looks after the number (people can switch network and keep their number, so it has to check) and hands the call over at the operator’s front door, the Gateway MSC. The message that does the handing over is called an IAM.',
  real='ISUP  IAM  (Initial Address Message)\n   Called party number  : +44 7700 900123\n   Calling party number : Gran’s landline (presentation allowed)\n   Transmission medium  : speech\n   → sent at a Point of Interconnect to the mobile operator’s Gateway MSC',
  notes=['ISUP is the call-setup language of the old telephone network. It runs over SS7 signalling links, and today often over IP as SIP-I.',
         'MSC means Mobile Switching Centre: the exchange of a mobile network. The “Gateway” one is the one that takes calls arriving from other networks.'],
  on=['Call Pod'], art=None),
 dict(n=3, zone='core', title='“Where is he?”', node=[('gate', 'Gateway MSC', 0), ('hlr', 'HLR', 0)],
  chip='SendRoutingInfo', reply='IMSI found, VLR known', proto='SS7 · MAP',
  cap='The Gateway MSC has a phone number but no idea where the phone is. It asks the HLR, the network’s master register of subscribers. The HLR takes the public name tag (the MSISDN, which is simply the phone number) and finds the secret agent behind it: the IMSI, the identity that lives in the SIM. The number everyone knows is not who you really are.',
  real='GMSC → HLR   MAP  SendRoutingInfo\n   msisdn            : 447700900123\n   interrogationType : basicCall\nHLR: look up MSISDN → IMSI  001 01 0123456789  (illustrative)\nHLR: known? barred? diverts set? which VLR is he registered in?',
  notes=['In 4G and 5G the HLR’s job is done by the HSS and UDM. Same idea: a very large database that says who you are and where you are.',
         'IMSI = 15 digits: country code (234 for the UK), network code, then your personal number. The IMSI in these examples is from the ITU test range, not a real customer.'],
  on=['MSISDN', 'IMSI'], art=('hlr-archive', 'The Call Pod flies through the HLR archive while IMSI the secret agent pulls a file card from a drawer; a Nokia 3310 sits on top of the cabinet'), egg='nokia'),
 dict(n=4, zone='core', title='A room key for one call', node=[('hlr', 'HLR', 0), ('vlr', 'VLR (visitor register)', 0)],
  chip='ProvideRoamingNumber', reply='MSRN', proto='SS7 · MAP',
  cap='The HLR knows which area his phone last reported in, but that is not a number you can ring. So it asks the visitor register there (the VLR) for a temporary routing number made for this one call, the MSRN. Think of a hotel room key cut for a single stay: it works once, then it is useless. The HLR passes it back, and the Gateway MSC sends the call on towards it.',
  real='HLR → VLR   MAP  ProvideRoamingNumber\n   imsi, msc-Number, msisdn\nVLR → HLR   result: roamingNumber (MSRN)   (from the serving MSC’s own number pool)\nHLR → GMSC   SendRoutingInfo result: MSRN\nGMSC → serving MSC   ISUP  IAM  to the MSRN',
  notes=['The VLR is the network’s short-term memory of who is currently in its area. It also holds the TMSI mask that goes with each IMSI.',
         'If he had set “divert all calls”, the HLR would have returned the diversion number instead of an MSRN.'],
  on=['IMSI', 'MSISDN'], art=None),
 dict(n=5, zone='space', title='The twist: there is no mast', node=[('vault', 'Mobile core', 0), ('dish', 'Ground gateway', 0), ('sat', 'Satellite', -26), ('phone', 'His phone', 0)],
  chip='feeder link up, service link down', reply='', proto='Satellite radio',
  cap='Here is the clever bit. The grandson is in a glen with no mobile signal, but a satellite overhead is acting as a mobile mast in space. The Call Pod rides a beam from a ground station (the gateway) up to the satellite, which relays it down to his phone on ordinary mobile frequencies. His phone does not know it is not talking to a mast.',
  real='Mobile core ↔ Ground gateway     fibre\nGround gateway ↔ Satellite        FEEDER LINK: radio link between satellite and ground\nSatellite ↔ His phone             SERVICE LINK: mobile-band spectrum, standard handset',
  notes=['Some designs put the base station inside the satellite. Others keep it on the ground and use the satellite as a relay. Either way the phone sees a normal cell.',
         'Real satellite-to-phone systems are 4G or 5G based (the 3GPP “NTN” standards), so voice would run as VoLTE rather than through an MSC. We draw the classic GSM path because it is the clearest way to see who does what.'],
  on=['Call Pod'], art=('satellite-beam', 'A hiker with no mobile signal in the Highlands while a satellite beams a cone of light over the glen and the Call Pod rides a beam up to it'), honesty=True),
 dict(n=6, zone='space', title='Shouting his disguise across the glen', node=[('vlr', 'Serving MSC / VLR', 0), ('sat', 'Satellite beam', -14), ('phone', 'His phone', 0)],
  chip='Paging: TMSI', reply='Paging response', proto='BSSMAP · radio paging', rings=True,
  cap='Now the network has to find him. It calls out his temporary disguise, the TMSI, across the whole satellite beam, which is far bigger than a normal mobile cell. A disguise matters: shouting his real identity over a wide area would let anyone with a radio follow him around. Only one phone in the glen recognises the mask, and it answers.',
  real='MSC/VLR → radio network   BSSMAP  PAGING  (tmsi 0xA1B2C3D4, location area)\nRadio network → air          Paging Request on the paging channel, every cell in the area\nPhone → network              Channel Request, then Paging Response (TMSI)',
  notes=['The TMSI is handed out by the VLR and changed regularly, so one hidden number cannot be followed from place to place.',
         'Paging a big beam costs a lot of radio capacity, which is one reason satellite networks are careful about how often they do it.'],
  on=['IMSI', 'TMSI mask'], art=None),
 dict(n=7, zone='space', title='“Prove you’re you”', node=[('vlr', 'Network (AuC vault)', 0), ('sim', 'His SIM', 0)],
  chip='RAND', reply='SRES', proto='GSM security · DTAP',
  cap='Before connecting, the network checks the agent is genuine without ever asking for his secret. It sends a random number, the RAND. Inside the SIM, the glowing key (Ki) scrambles it into an answer (SRES). Back in the network’s AuC vault, the twin key has already worked out the right answer. If they match, the agent is real. Both sides also make a one-off ciphering key (Kc) that scrambles the call. Ki itself never leaves either vault.',
  real='AuC (in advance)  RAND → A3(Ki) = SRES,  A8(Ki) = Kc   →  triplet (RAND, SRES, Kc) to the VLR\nVLR → phone   DTAP  Authentication Request   RAND (128 bit)\nSIM           SRES′ = A3(Ki, RAND)  (32 bit);   Kc = A8(Ki, RAND)  (64 bit)\nphone → VLR   Authentication Response   SRES′\nVLR           SRES′ = SRES ?   yes →  Cipher Mode Command (A5 encryption, key Kc)',
  notes=['A3 and A8 are the operator’s choice of algorithm. Newer networks (3G, 4G, 5G) also make the network prove itself to the phone. Original GSM only checked the phone.',
         'The AuC usually works the answers out ahead of time and hands the VLR a ready-made “triplet”, so the vault does not need to be woken for every call.'],
  on=['IMSI', 'Ki', 'Ki’s twin (AuC)'], art=('twin-keys', 'The golden key character Ki in the SIM and its twin in the network vault exchange a lightning-bolt challenge while the Call Pod watches')),
 dict(n=8, zone='core', title='Border control for the ship', node=[('phone', 'His handset (IMEI)', 0), ('eir', 'EIR register', 0)],
  chip='CheckIMEI', reply='white list ✓', proto='SS7 · MAP',
  cap='The agent checks out, but what about the ship he is travelling in? Every phone has a unique 15-digit serial number, the IMEI, stamped on its hull. The network asks the EIR, the border-control register, whether that number has been reported stolen. Green light: cleared to proceed.',
  real='MSC → phone   DTAP  Identity Request (IMEI)\nphone → MSC   Identity Response   IMEI 35 123456 654321 1   (illustrative)\nMSC → EIR     MAP  CheckIMEI (imei)\nEIR → MSC     equipmentStatus = whiteListed',
  notes=['The first 8 digits say which make and model (the TAC), the next 6 are the serial number, and the last is a check digit.',
         'Stolen phones are added to a shared block list, so a phone reported stolen on one UK network can be blocked on all of them.'],
  on=['IMEI', 'EIR'], art=('border-control', 'A robot border officer scans the hull number of IMEI the smartphone-shaped ship and a green Cleared sign lights up while the Call Pod waits')),
 dict(n=9, zone='core', title='The bouncer at the bar', node=[('gate', 'Gateway MSC', 0), ('scp', 'Prepaid charging (SCP)', 0)],
  chip='InitialDP', reply='Continue ✓', proto='CAMEL · CAP',
  cap='His SIM is prepaid, so before his phone rings the operator’s charging system is asked: is this call allowed, and is there credit? Receiving a call on your home network is usually free in the UK, but the same check guards roaming and satellite services, which can cost money. The question travels over CAMEL, a rulebook that lets an operator’s prepaid platform step into any call. Credit is fine, so the bouncer waves us through.',
  real='GMSC → SCP   CAP  InitialDP\n   serviceKey, calledPartyNumber, imsi, eventTypeBCSM = termAttemptAuthorized\nSCP → charging   balance and rate check\nSCP → GMSC   CAP  Continue     (or Connect to change the number, ReleaseCall to refuse,\n                                 ApplyCharging to set a time limit)',
  notes=['In a live network the Gateway MSC often asks this earlier, before the phone is paged. We tell it here so the “is he allowed?” checks sit together just before the ring.',
         'SCP stands for Service Control Point, the “brain” that runs prepaid and other intelligent-network rules. This is where a lot of real operator money is made and lost.'],
  on=['IMSI'], art=None),
 dict(n=10, zone='land', title='Ring ring: the meter starts', node=[('phone', 'His phone', 0), ('exchange', 'Gran’s exchange', 0)],
  chip='ACM (ringing) then ANM (answered)', reply='', proto='ISUP · DTAP', meter=True,
  cap='His phone buzzes in his pocket. A message called ACM (Address Complete) races all the way back to Gran’s exchange, which plays her the ringing tone. He answers with a cheery “hello?”, and a second message, ANM (Answer), tells every exchange along the route that the call is connected. At that moment, the meter starts.',
  real='phone → MSC   DTAP  Alerting         →  ISUP  ACM  back to Warminster  →  ringback tone\nphone → MSC   DTAP  Connect          →  ISUP  ANM  →  charging starts\nSCP           CAP  EventReportBCSM (tAnswer)  →  prepaid timer begins',
  notes=['No ANM means no billing. Until someone answers, the call is free, which is why a lot of fraud tries to get calls “answered” without a person.'],
  on=['Call Pod'], art=None),
 dict(n=11, zone='space', title='Her voice, in disguise', node=[('landline', 'Gran’s voice', 0), ('mgw', 'Media gateway', 0), ('sat', 'Satellite', -20), ('phone', 'His phone', 0)],
  chip='64k PCM to AMR', reply='', proto='G.711 · AMR · radio', bars=True,
  cap='On Gran’s side, her voice is digital audio at 64 thousand bits a second (G.711, the telephone network’s standard since the 1970s). That is too bulky for a radio link, so a media gateway squeezes it into a mobile format called AMR, using a fifth of the space or less. Up it goes to the satellite, which is travelling at about 17,000 mph, so the network constantly adjusts timing and frequency to cancel the Doppler effect: the same trick that makes an ambulance siren change pitch as it passes.',
  real='Gran’s side    G.711 A-law PCM   8 kHz × 8 bit = 64 kbit/s\nMedia gateway  transcode G.711 → AMR   (AMR-NB 12.2 kbit/s, or AMR-WB up to 23.85 kbit/s)\nSatellite      low orbit ~550 km, speed ≈ 7.6 km/s ≈ 17,000 mph\nRadio          Doppler shift of tens of kHz at ~2 GHz is pre-compensated;\n               timing advance is corrected for the long distance (3GPP NTN, Release 17)',
  notes=['12.2 kbit/s is about 19% of 64 kbit/s. Newer wideband codecs sound better and still use far less than the old standard.',
         'Standard GSM timing only copes with distances up to about 35 km. Satellite systems need extra timing tricks, which is part of what the NTN standards add.'],
  on=['Call Pod'], art=None),
 dict(n=12, zone='land', title='Hang-up: the lights go out', node=[('landline', 'Gran’s landline', 0), ('exchange', 'Local exchange', 0), ('gate', 'Gateway MSC', 0), ('phone', 'His phone', 0)],
  chip='REL', reply='RLC', proto='SS7 · ISUP · DTAP',
  cap='When Gran says goodbye and puts the phone down, the end of the call travels the same road. A REL (Release) message goes hop by hop along the route, and each exchange answers RLC (Release Complete) once it has let go of the line. Behind the pod the lights go out, one stop at a time. The radio channel is handed back, the beam moves on to other people, and the voice path ceases to exist.',
  real='Gran hangs up  →  ISUP  REL  (cause 16: normal call clearing)  hop by hop\nEach switch   →  ISUP  RLC  once its circuit is freed\nRadio side    →  DTAP  Disconnect, Release, Release Complete;  radio channel freed\nSCP           →  CAP  EventReportBCSM (tDisconnect), final charge reported',
  notes=['“Cause 16” is the polite code. Others tell you the number was busy, unallocated or that the network ran out of capacity.'],
  on=['Call Pod'], art=None),
 dict(n=13, zone='back', title='The afterlife: a line on a bill', node=[('gate', 'Switch writes a CDR', 0), ('transit', 'Mediation', 0), ('scp', 'Rating', 0), ('bill', 'Billing', 0)],
  chip='CDR', reply='', proto='Billing · settlement', receipt=True,
  cap='A call does not really end when you hang up. The switch writes a small receipt, a CDR (call detail record). It drifts to mediation, which tidies and merges receipts from lots of machines. Rating puts a price on it, billing puts it on an invoice, and the operators settle up with each other, because Gran’s operator pays the mobile operator a small fee for delivering the call. The grave: one line on Gran’s bill.',
  real='MSC/GMSC  →  CDR   (A and B numbers, start and end time, duration 252 s, cause, IMSI, IMEI, cell)\nMediation   collect, validate, remove duplicates, join records, convert to billing format\nRating      252 s × Gran’s tariff;   wholesale: mobile termination charge\nBilling     invoice line:   07700 900123    4 min 12s\nSettlement  originating operator pays the terminating operator, usually netted off in wholesale billing',
  notes=['For prepaid there is no monthly bill. The record feeds the charging system that already took the money while you talked.',
         '07700 900xxx is a range Ofcom sets aside for TV and drama, so no real person will ever answer it.'],
  on=['IMSI', 'IMEI'], art=('the-bill', 'A glowing call receipt travels along a conveyor through cleaning, pricing and invoicing stations to a bill line reading 07xx xxx xxx 4 min 12s while IMSI tips his hat')),
 dict(n=14, zone='core', title='Alternate ending: nobody answers', node=[('gate', 'Gateway MSC', 0), ('vm', 'Voicemail (IVR)', 0)],
  chip='diverted: no reply', reply='', proto='ISUP · call forwarding', egg='virgin',
  cap='In another universe the grandson is deep in a peat bog with his phone in his bag, and does not answer. After 20 to 30 seconds of ringing, the network’s no-reply timer runs out and the call is quietly diverted to voicemail. A friendly robot voice (the IVR) asks Gran to leave a message after the tone. If his phone had been out of reach altogether, the network would have diverted her at once.',
  real='GMSC/MSC   no-reply timer (NRy, typically 20 to 30 s) expires\nHLR profile  call forwarding on no reply → voicemail access number\nISUP IAM     redirecting number = his number, redirection reason = no reply  →  voicemail platform\nIVR          plays greeting, records message\nVoicemail    SMS to him: “You have a new voicemail”   (MAP MT-ForwardSM)',
  notes=['The “not reachable” case (switched off, no signal) is a separate setting and diverts immediately, so Gran never hears a ring.',
         'IVR means Interactive Voice Response: any computer that talks to callers and listens to their key presses or voice.'],
  on=['Call Pod'], art=None),
]
for c in CH: c.setdefault('art', None)

# ---- strip svgs
def chip(x, y, text, at, anchor='middle', cls='chip'):
    w = int(len(text) * 8.4 + 26)
    x0 = x - w / 2 if anchor == 'middle' else x
    tx = x if anchor == 'middle' else x + w / 2
    return (f'<g class="{cls}" style="--at:{at}"><rect x="{x0:.0f}" y="{y-17}" width="{w}" height="30" rx="15"/>'
            f'<text x="{tx:.0f}" y="{y+3}" text-anchor="middle">{esc(text)}</text></g>')

def node(x, y, icon, label, horizontal=True):
    g = f'<g class="nd" transform="translate({x:.0f} {y:.0f})"><rect x="-30" y="-30" width="60" height="60" rx="16"/><g transform="translate(-14 -14) scale(1.1667)" class="ic">{ICONS[icon]}</g>'
    if horizontal:
        words = label.split(' ')
        # two lines if long
        if len(label) > 14 and len(words) > 1:
            m = len(words) // 2 if len(words) > 2 else 1
            l1, l2 = ' '.join(words[:m]), ' '.join(words[m:])
            g += f'<text y="50" text-anchor="middle">{esc(l1)}</text><text y="67" text-anchor="middle">{esc(l2)}</text>'
        else:
            g += f'<text y="52" text-anchor="middle">{esc(label)}</text>'
    else:
        g += f'<text x="46" y="5" text-anchor="start">{esc(label)}</text>'
    return g + '</g>'

def pathd(pts):
    d = f'M{pts[0][0]:.0f} {pts[0][1]:.0f}'
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        if abs(bx - ax) >= abs(by - ay):
            mx = (ax + bx) / 2
            d += f' C{mx:.0f} {ay:.0f} {mx:.0f} {by:.0f} {bx:.0f} {by:.0f}'
        else:
            my = (ay + by) / 2
            d += f' C{ax:.0f} {my:.0f} {bx:.0f} {my:.0f} {bx:.0f} {by:.0f}'
    return d

def strip_svg(c, vertical):
    nodes = c['node']; k = len(nodes)
    if not vertical:
        W, H = 640, 200; xs = [70 + i * (500 / (k - 1)) for i in range(k)]
        pts = [(x, 98 + dy) for x, (_, _, dy) in zip(xs, nodes)]
    else:
        W = 340; step = 118 if k <= 3 else 104; H = 70 + step * (k - 1) + 52
        pts = [(52, 62 + i * step) for i in range(k)]
    parts = [f'<svg class="sv {"sv-v" if vertical else "sv-h"}" viewBox="0 0 {W} {H}" role="img" aria-label="{esc(" to ".join(n[1] for n in nodes))}: {esc(c["title"])}" focusable="false">']
    d = pathd(pts)
    parts.append(f'<path class="route-bg" d="{d}"/><path class="route" d="{d}" data-end="{pts[-1][0]:.0f} {pts[-1][1]:.0f}"/>')
    if c.get('rings'):
        px, py = pts[-1]
        parts.append(''.join(f'<circle class="ring r{i}" cx="{px:.0f}" cy="{py:.0f}" r="34"/>' for i in range(3)))
    for (x, y), (ic, lab, _) in zip(pts, nodes):
        parts.append(node(x, y, ic, lab, not vertical))
    # chips
    if not vertical:
        mx = (pts[0][0] + pts[-1][0]) / 2
        parts.append(chip(mx, 28, c['chip'], .3))
        if c['reply']: parts.append(chip(mx, H - 22, '← ' + c['reply'], .7, cls='chip reply'))
    else:
        my = (pts[0][1] + pts[-1][1]) / 2
        cx = 100
        parts.append(chip(cx, my - 14, c['chip'], .3, anchor='start'))
        if c['reply']: parts.append(chip(cx, my + 26, '↑ ' + c['reply'], .7, anchor='start', cls='chip reply'))
    ex, ey = pts[-1]
    parts.append(f'<g class="pod" transform="translate({ex:.0f} {ey:.0f})"><use href="#is-pod" x="-26" y="-23" width="52" height="46"/></g>')
    parts.append('</svg>')
    return ''.join(parts)

EGG_NOKIA = ('<span class="egg egg-nokia"><button type="button" class="egg-b" aria-describedby="egg-n" aria-label="Easter egg: a Nokia 3310"><svg viewBox="0 0 40 70" aria-hidden="true" focusable="false"><rect x="4" y="2" width="32" height="66" rx="9" fill="#2b3a52" stroke="#8fdbff"/><rect x="9" y="10" width="22" height="16" rx="2" fill="#9fd29a"/><path d="M12 32h16M12 38h16M12 44h16M12 50h16M12 56h16" stroke="#8fdbff" stroke-width="3" stroke-linecap="round"/></svg></button><span class="egg-t" id="egg-n" role="tooltip">A Nokia 3310, still in the archive. It would like you to know it also holds a very good game of Snake.</span></span>')
EGG_VIRGIN = ('<span class="egg egg-desk"><button type="button" class="egg-b" aria-describedby="egg-v" aria-label="Easter egg: a tech support desk with a Virgin Mobile 2007 badge"><svg viewBox="0 0 120 80" aria-hidden="true" focusable="false"><rect x="4" y="58" width="82" height="7" rx="2" fill="#2b3a52" stroke="#8fdbff"/><path d="M12 65v13M78 65v13" stroke="#8fdbff" stroke-width="3"/><rect x="24" y="28" width="42" height="26" rx="3" fill="#0b1426" stroke="#8fdbff"/><path d="M45 54v4M36 58h18" stroke="#8fdbff" stroke-width="3"/><path d="M31 36h26M31 42h16" stroke="#5ec8ff" stroke-width="2"/><rect x="58" y="2" width="60" height="24" rx="4" fill="#d6212b"/><text x="88" y="13" font-size="9" font-weight="800" fill="#fff" text-anchor="middle" font-family="Inter,sans-serif">VIRGIN MOBILE</text><text x="88" y="23" font-size="9" font-weight="800" fill="#fff" text-anchor="middle" font-family="Inter,sans-serif">2007</text></svg></button><span class="egg-t" id="egg-v" role="tooltip">Tech support desk, circa 2007. “Have you tried turning it off and on again?” An in-joke from the author’s days on the support floor.</span></span>')
EGGS = {'nokia': EGG_NOKIA, 'virgin': EGG_VIRGIN}

CAST = [
 ('imsi', 'IMSI', 'The secret agent', 'Lives in the SIM and in the network’s HLR vault. It is your real identity, and it almost never travels over the air. Over the air he wears a disguise mask, the <strong>TMSI</strong>, which the network swaps regularly so nobody can follow him.'),
 ('imei', 'IMEI', 'The ship', 'The handset itself, with a unique 15-digit hull number stamped on it. Border control (the EIR) checks it against the stolen-phone list.'),
 ('ki', 'Ki', 'The key that never leaves', 'A glowing secret key locked inside the SIM, with a twin locked in the network’s AuC vault. They are never in the same room, which is exactly why the trick works.'),
 ('msisdn', 'MSISDN', 'The public name tag', 'The phone number everyone knows. It is only a label, and the network translates it into the IMSI behind the scenes.'),
 ('pod', 'The Call Pod', 'Our shrunken craft', 'It carries Gran’s voice from the moment she lifts the handset to the line on her bill.'),
]

def chapter(c):
    n = c['n']; zone = c['zone']
    art = ''
    if c['art']:
        f, alt = c['art']
        art = f'<figure class="art"><img src="../assets/img/inner-signal/{f}.webp" width="1280" height="720" alt="{esc(alt)}" loading="lazy" decoding="async"></figure>'
    extras = ''
    if c.get('meter'):
        extras += '<p class="meter" aria-live="off"><span class="m-l">Meter</span> <span class="m-v" data-meter>4:12</span> <span class="m-s">call connected, charging</span></p>'
    if c.get('bars'):
        extras += ('<div class="bars" role="img" aria-label="Bit rate comparison: 64 kilobits per second for Gran’s side, 12.2 kilobits per second after squeezing to AMR">'
                   '<p><span>Gran’s line: G.711</span><i style="--w:100%"></i><b>64 kbit/s</b></p><p><span>Mobile: AMR</span><i style="--w:19%"></i><b>12.2 kbit/s</b></p></div>')
    if c.get('receipt'):
        extras += ('<div class="receipt" role="img" aria-label="Bill line: 07700 900123, 4 minutes 12 seconds"><span class="r-h">Gran’s bill</span>'
                   '<span class="r-l"><b>07700 900123</b><i>4 min 12s</i></span></div>')
    egg = EGGS.get(c.get('egg'), '')
    honesty = ''
    if c.get('honesty'):
        honesty = '<p class="honest"><strong>An honest note.</strong> In the UK today, satellite-to-phone means texts and some apps. Voice calls are the next step. This leg of the story shows the near future being built, not something you can dial today.</p>'
    AV = {'IMSI':'imsi','TMSI mask':'imsi','IMEI':'imei','Ki':'ki','Ki’s twin (AuC)':'ki','MSISDN':'msisdn','Call Pod':'pod'}
    on = ''.join((f'<li><img src="../assets/img/inner-signal/cast-{AV[x]}.webp" width="24" height="24" alt="" loading="lazy">{esc(x)}</li>' if x in AV else f'<li>{esc(x)}</li>') for x in c['on'])
    notes = ''.join(f'<li>{x}</li>' for x in c['notes'])
    return f'''<section class="ch z-{zone}" id="ch-{n}" data-n="{n}" data-zone="{ZONES[zone]}" data-title="{esc(c['title'])}" aria-labelledby="ch{n}-h">
<header class="ch-h"><span class="num" aria-hidden="true">{n:02d}</span><p class="kicker">Chapter {n} of 14 · {ZONES[zone]}</p><h2 id="ch{n}-h">{c['title']}</h2></header>
<div class="ch-vis">{art}<div class="strip">{strip_svg(c, False)}{strip_svg(c, True)}{egg}</div>{extras}</div>
<div class="ch-txt"><p class="cap">{c['cap']}</p>{honesty}<ul class="onscr" aria-label="On screen in this chapter">{on}</ul>
<button type="button" class="real-b" aria-expanded="false" aria-controls="real-{n}">Show me the real thing</button>
<div class="real" id="real-{n}"><p class="proto">{esc(c['proto'])}</p><pre><code>{esc(c['real'])}</code></pre><ul class="rn">{notes}</ul></div></div>
</section>'''

cast_html = ''.join(f'<li class="cc-card"><img src="../assets/img/inner-signal/cast-{k}.webp" width="240" height="240" alt="" loading="lazy" decoding="async"><div><p class="kicker">{esc(role)}</p><h3>{esc(name)}</h3><p>{txt}</p></div></li>' for k, name, role, txt in CAST)
rail_dots = ''.join(f'<a href="#ch-{c["n"]}" class="dot" aria-label="Chapter {c["n"]}: {esc(c["title"])}"><i></i></a>' for c in CH)
toc = ''.join(f'<li><a href="#ch-{c["n"]}"><span>{c["n"]:02d}</span>{c["title"]}</a></li>' for c in CH)

POD = '''<svg class="jdefs" width="0" height="0" aria-hidden="true" focusable="false"><defs>
<symbol id="is-pod" viewBox="-26 -23 52 46" overflow="visible"><ellipse cx="0" cy="20" rx="20" ry="3" fill="#00cfff" opacity=".25"/><path d="M-22 6a22 14 0 0 0 44 0v2a22 12 0 0 1-44 0z" fill="#5ec8ff"/><ellipse cx="0" cy="6" rx="23" ry="13" fill="#e8eef7"/><path d="M-23 7h46" stroke="#5ec8ff" stroke-width="3"/><path d="M-15 4a15 17 0 0 1 30 0z" fill="#8fdbff" fill-opacity=".45" stroke="#cdeeff" stroke-width="1.4"/><circle cx="0" cy="-3" r="6.2" fill="#f1c9a6"/><path d="M-6.600-3a6.600 7 0 0 1 13.200 0c-2-3-4-4-6.600-4s-4.600 1-6.600 4z" fill="#cfd6df"/><circle cx="-2.200" cy="-2.500" r=".8" fill="#223"/><circle cx="2.200" cy="-2.500" r=".8" fill="#223"/><path d="M-2 .3q2 1.600 4 0" stroke="#a5544c" stroke-width=".9" fill="none"/><circle cx="-15" cy="14" r="3" fill="#5ec8ff"/><circle cx="15" cy="14" r="3" fill="#5ec8ff"/></symbol></defs></svg>'''.replace('.600','.6').replace('.200','.2').replace('.500','.5').replace('.300','.3')

HEAD = f'''{POD}
<header class="page-head is-head"><p class="kicker">Explainer · the life of a phone call</p><h1>Inner Signal: the life of a phone call</h1>
<p class="lede">A grandmother in Warminster rings her grandson’s mobile from her landline. He is hiking in the Highlands, miles from the nearest mast. We shrink down and ride the call, from the moment she lifts the handset to the line on her bill.</p>
<p class="jcred">Written by a mobile network insider with over 13 years in GSM, from IVR and SMS to call routing and thin and thick MVNOs. <span class="prot">Preview build</span></p>
<p class="honest top"><strong>An honest note.</strong> In the UK today, satellite-to-phone means texts and some apps. Voice calls are the next step. The satellite leg of this story shows the near future being built.</p>
<p class="row-cta"><a class="btn" href="#ch-1">Start the journey <span aria-hidden="true">↓</span></a><button type="button" class="btn ghost" id="all-real" aria-pressed="false">Show me the real thing, everywhere</button></p>
<!--SHARE-TOP-->
</header>
<section class="cast" aria-labelledby="cast-h"><h2 id="cast-h">Meet the cast</h2>
<figure class="cast-fig"><img src="../assets/img/inner-signal/cast.webp" width="1280" height="720" alt="The cast: IMSI the secret agent in a fedora and domino mask, IMEI the smartphone-shaped ship, Ki the golden key in a glass dome, MSISDN the name-tag badge and the Call Pod with Gran inside" decoding="async"></figure>
<ul class="cast-l">{cast_html}</ul>
<p class="fine">Every number in this story is made up. Phone numbers, IMSI and IMEI values are examples, and 07700 900xxx is a range set aside for drama. Names and message formats are the real ones.</p></section>
<nav class="toc" aria-labelledby="toc-h"><h2 id="toc-h">The route</h2><ol>{toc}</ol></nav>
<div class="rail" id="rail" aria-hidden="true"><div class="rail-in"><p class="rail-t"><b id="rail-n">1</b><span> / 14</span> <span id="rail-title">Gran picks up the phone</span> <em id="rail-zone">Landline network</em></p>
<div class="rail-bar"><i id="rail-fill"></i><span class="rail-pod"><svg viewBox="-26 -23 52 46" width="26" height="23" focusable="false"><use href="#is-pod"/></svg></span></div></div></div>
<div class="chapters" id="chapters">
'''

END = '''</div>
<section class="wrapup" aria-labelledby="wu-h"><h2 id="wu-h">The whole trip in one breath</h2>
<p>One tap of a landline, a dozen different computers, two radio links, one satellite moving at 17,000 mph and a billing system that would not give up. It all took a few seconds to connect and left a single line on a bill: <strong>07700 900123, 4 min 12s</strong>.</p>
<p>Satellite voice calls to ordinary phones are not here in the UK yet, but the pieces in this story are being built right now. Signal is where we follow them.</p>
<details class="srcs"><summary>Where the details come from</summary><ul><li>Call setup and routing: ITU-T Q.763 (ISUP messages), 3GPP TS 23.018 (basic call handling), 3GPP TS 29.002 (MAP).</li><li>Prepaid and CAMEL: 3GPP TS 23.078 and TS 29.078 (CAP).</li><li>Numbers and identities (IMSI, TMSI, IMEI, MSRN): 3GPP TS 23.003.</li><li>GSM security (RAND, SRES, Kc, A3, A8, A5): 3GPP TS 43.020.</li><li>Satellite access to ordinary phones: 3GPP NTN work, Release 17 onwards.</li><li>UK landline switch-off: <a href="https://www.openreach.com/big-switch-off">Openreach, Big Switch Off</a>.</li></ul></details></section>
<!--SHARE-END-->
'''
out = {
 'slug': 'inner-signal', 'title': 'Inner Signal: the life of a phone call', 'short_title': 'Inner Signal',
 'description': 'Ride a phone call from a grandmother’s landline to a hiker’s phone via satellite, then on to the bill. Fourteen animated chapters, plain English.',
 'summary': 'A scroll-driven journey through a phone call: landline, mobile core, satellite, billing.'}
body = HEAD + '\n'.join(chapter(c) for c in CH) + END
open(f'{ROOT}/src/pages/inner-signal.html', 'w').write('<!--meta\n' + json.dumps(out, ensure_ascii=False, indent=1) + '\n-->\n' + body)
print('ok', len(body))
