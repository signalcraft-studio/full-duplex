#!/usr/bin/env python3
"""Generates src/pages/inner-signal.html for the Full Duplex repo."""
import sys, json, html
ROOT = sys.argv[1] if len(sys.argv) > 1 else '/workspace/fdrepo'
esc = lambda s: html.escape(s, quote=True)

ICONS = {
 'phone': '<rect x="7.5" y="2.5" width="9" height="19" rx="2.2"/><path d="M11 18.5h2"/>',
 'bts': '<path d="M12 8v13M7 21l5-13 5 13M8.5 16h7M4 6a9 9 0 0 0 0 6M20 6a9 9 0 0 1 0 6"/>',
 'exchange': '<path d="M3 21h18M5 21V9.5l7-5.5 7 5.5V21M9 21v-7h6v7"/>',
 'gate': '<path d="M3 12h13M12 7l5 5-5 5M21 4v16"/>',
 'hlr': '<rect x="5" y="3" width="14" height="18" rx="1.5"/><path d="M5 9h14M5 15h14M10.5 6h3M10.5 12h3M10.5 18h3"/>',
 'vlr': '<path d="M4 21V9l8-5 8 5v12M9 21v-5h6v5M9 12h.01M15 12h.01"/>',
 'sat': '<rect x="9" y="9" width="6" height="6" rx="1" transform="rotate(45 12 12)"/><path d="M3 6l4-3 3 4-4 3zM14 17l3 4 4-3-3-4zM12 3v2M19 12h2"/>',
 'dish': '<path d="M5 14a8 8 0 0 0 14-3L11 3zM12 14l-1 6M7 21h9"/>',
 'eir': '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6zM8.5 12l2.5 2.5 4.5-5"/>',
 'scp': '<circle cx="12" cy="12" r="8.5"/><path d="M14.5 8.5c-.8-1-3.5-1.2-4.2.5-.8 1.8 1 2.7 1.7 3.2.8.6 1.2 1.5.4 2.3-.9.9-3 .6-3.6-.5M8 15.5h7"/>',
 'mgw': '<path d="M4 8h16M16 4l4 4-4 4M20 16H4M8 12l-4 4 4 4"/>',
 'bill': '<path d="M6 3h12v18l-3-2-3 2-3-2-3 2zM9 8h6M9 12h6"/>',
 'vm': '<rect x="2" y="6" width="20" height="12" rx="3"/><circle cx="8" cy="12" r="2.5"/><circle cx="16" cy="12" r="2.5"/><path d="M8 14.5h8"/>',
 'vault': '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="12" cy="12" r="4"/><path d="M12 8v8M8 12h8"/>',
 'sim': '<path d="M6 3h8l4 4v14H6zM9 12h6v6H9z"/>',
 'mask': '<path d="M3 12c2-6 6-8 9-8s7 2 9 8c-2 5-5 7-9 7s-7-2-9-7zM8 11h.01M16 11h.01M9 15c1.2 1 4.8 1 6 0"/>',
}

ZONES = {'her': 'Her network', 'join': 'The join', 'his': 'His network', 'space': 'Space', 'back': 'Back office'}

# on-screen chips use portrait keys
CH = [
 dict(n=1, zone='her', title='She presses call',
  node=[('phone', 'Her mobile', 0), ('bts', 'Nearest mast', 0)],
  chip='07700 900123', reply='', proto='Radio · call setup',
  cap='In a kitchen in Warminster, she types her son’s mobile number and presses call. We shrink down and climb aboard the Call Pod. Her phone is already on a normal UK mast, so the first hop is a short radio hop: the number, and a request to place the call, go up to the lighthouse on the hill.',
  real='Phone  →  mast (BTS / eNodeB)   radio signalling\n   GSM-style:  CM Service Request  (MO call), then  SETUP\n              with calledPartyBCDNumber = 07700 900123\n   Today’s VoLTE:  SIP  INVITE  to her IMS core (via the P-CSCF)\n              Request-URI / To: +447700900123\n   07700 900000 to 900999 is Ofcom’s reserved drama range',
  notes=['On a mobile she does not send each digit as a musical tone, the way a landline does. The whole number travels in the setup message once she presses call.',
         '07700 900000 to 07700 900999 is the mobile range Ofcom sets aside for TV and drama, so no real person will ever answer it.'],
  on=[('pod', 'Call Pod')],
  art=('she-dials', 'A woman at her kitchen table taps a smartphone while the sleek Call Pod hovers beside it, linked by a swirl of cyan light')),
 dict(n=2, zone='her', title='Up the mast',
  node=[('phone', 'Her phone', 0), ('bts', 'BTS / eNodeB', 0), ('exchange', 'Her MSC', 0)],
  chip='into the core', reply='', proto='Um / Uu · terrestrial radio',
  cap='The mast is a base station: a BTS in the old language, an eNodeB or gNodeB on a 4G or 5G network. Our lighthouse keeper takes the Call Pod in from the air and sends it down a cable, into her operator’s core. From here the call is a visitor in a very large, very tidy machine.',
  real='Phone  ↔  BTS/eNodeB     Um (2G) or Uu (4G/5G) radio link, encrypted once ciphering is on\nBTS/eNodeB  →  BSC/RNC or directly to the core     backhaul (fibre, or microwave)\nCore        →  MSC (classic) or IMS S-CSCF / TAS (VoLTE)',
  notes=['The mast does not decide whether she may place the call. It is a radio doorway. The decisions happen further in.'],
  on=[('bts', 'BTS lighthouse keeper'), ('msc', 'MSC signalman')],
  portraits=['bts', 'msc']),
 dict(n=3, zone='her', title='“Prove you’re you”',
  node=[('exchange', 'Her VLR / AuC', 0), ('sim', 'Her SIM', 0)],
  chip='RAND', reply='SRES', proto='GSM security · DTAP  (or AKA in 4G/5G)',
  cap='The network must be sure her secret agent is genuine, without ever asking for the secret itself. In a live network this check usually ran when her phone last signed on, and it can run again when she starts a call. We show it here so you can see it happen. The network sends a random number, the RAND. Inside her SIM, the glowing key (Ki) scrambles it into an answer (SRES). In the network’s AuC vault, the twin key has already worked out the right answer. If they match, the agent is real. Both sides also make a one-off ciphering key, and her conversation is scrambled from here on. Ki itself never leaves either vault. Over the air she wears her TMSI disguise, not her real name.',
  real='AuC (in advance)  RAND → A3(Ki) = SRES,  A8(Ki) = Kc   →  triplet to her VLR\nVLR → phone   Authentication Request   RAND (128 bit)\nHer SIM        SRES′ = A3(Ki, RAND);   Kc = A8(Ki, RAND)\nphone → VLR    Authentication Response   SRES′\nVLR            SRES′ = SRES ?   yes →  Cipher Mode Command',
  notes=['An eSIM is only a downloadable profile. It still holds the IMSI and the Ki, so the same authentication applies whether the profile arrived on a plastic SIM or over the air.',
         'Newer networks (3G, 4G, 5G) also make the network prove itself to the phone. Original GSM only checked the phone.',
         'The TMSI is a temporary mask, handed out by the VLR and changed regularly, so one hidden number cannot be followed from place to place.'],
  on=[('imsi-her', 'Her IMSI'), ('tmsi', 'TMSI mask'), ('ki', 'Ki'), ('auc', 'AuC vault guardian')],
  art=('twin-keys', 'Her IMSI agent stands by a golden key locked in a glass dome while a matching twin key sits in the network vault; a lightning-bolt challenge crosses between them as the Call Pod watches')),
 dict(n=4, zone='her', title='The bouncer at the door',
  node=[('exchange', 'Her MSC', 0), ('scp', 'Online charging (SCP)', 0)],
  chip='InitialDP', reply='Continue ✓', proto='CAMEL · CAP  (or online charging over Diameter)',
  cap='She is the one placing the call, so she is the one who pays. Before the call is allowed out of her network, the charging system is asked: is this call allowed, and is there credit? The question travels over CAMEL, a rulebook that lets a prepaid platform step into any call. Credit is fine, so the bouncer waves the Call Pod through. If she had been out of credit, the journey would have ended here, with a short recorded message instead of a ring.',
  real='Originating MSC → SCP   CAP  InitialDP\n   serviceKey, callingPartyNumber, calledPartyNumber (07700 900123),\n   imsi (hers), eventTypeBCSM = collectedInfo\nSCP → charging   balance and rate check  (a UK-to-UK mobile call, plus any satellite surcharge)\nSCP → MSC       CAP  Continue     (or ReleaseCall to refuse, ApplyCharging to set a time limit)',
  notes=['This is why the credit check sits on her side. In the UK the caller usually pays. Receiving a call on your home network is typically free, though there are exceptions, for example if you are roaming abroad and someone rings you.',
         'On a 4G or 5G network the same job is done by online charging over Diameter, talking to a CHF or OCS. The bouncer is the same, the doorway is newer.',
         'SCP stands for Service Control Point, the “brain” that runs prepaid rules. This is where a lot of real operator money is made and lost.'],
  on=[('bouncer', 'Charging bouncer'), ('imsi-her', 'Her IMSI')],
  portraits=['bouncer']),
 dict(n=5, zone='join', title='Across the interconnect',
  node=[('exchange', 'Her MSC', 0), ('gate', 'His Gateway MSC', 0)],
  chip='IAM', reply='', proto='SS7 · ISUP  (or SIP at the interconnect)',
  cap='Her signalman sees a number that belongs to another operator (people can switch network and keep their number, so he has to check). He hands the Call Pod over at the interconnect, the official join between the two companies. Waiting at the far door is the passport officer: his network’s Gateway MSC, which takes calls arriving from the outside world. The message that does the handing over is called an IAM.',
  real='Her MSC/GMSC  →  his Gateway MSC    ISUP  IAM  (Initial Address Message)\n   Called party number  : +44 7700 900123\n   Calling party number : her mobile (presentation allowed)\n   Transmission medium  : speech\n   sent at a Point of Interconnect',
  notes=['On today’s UK networks this would usually be a 4G or 5G voice call (VoLTE), handled by an IMS core rather than a classic MSC. The jobs are the same: check who you are, check you can pay, and hand the call to the other operator. We keep the older names here because they make the roles easier to follow.',
         'ISUP is the call-setup language of the old telephone network. It runs over SS7 signalling links, and today often over IP as SIP-I or native SIP.'],
  on=[('msc', 'MSC signalman'), ('gmsc', 'Gateway MSC passport officer'), ('pod', 'Call Pod')],
  portraits=['msc', 'gmsc']),
 dict(n=6, zone='his', title='“Where is he?”',
  node=[('gate', 'Gateway MSC', 0), ('hlr', 'HLR', 0)],
  chip='SendRoutingInfo', reply='IMSI found, VLR known', proto='SS7 · MAP',
  cap='The Gateway MSC has a phone number but no idea where the phone is. It asks the HLR, the network’s master register of subscribers. The archivist takes the public name (the MSISDN, which is simply the phone number) and finds the secret agent behind it: his IMSI, the identity that lives in his SIM. The number everyone knows is not who he really is. His agent steps out of the archive and joins the story.',
  real='GMSC → HLR   MAP  SendRoutingInfo\n   msisdn            : 447700900123\n   interrogationType : basicCall\nHLR: look up MSISDN → IMSI  001 01 0123456789  (illustrative, ITU test range)\nHLR: known? barred? diverts set? which VLR is he registered in?',
  notes=['In 4G and 5G the HLR’s job is done by the HSS and UDM. Same idea: a very large database that says who you are and where you are.',
         'IMSI is 15 digits: a country code (234 for the UK), a network code, then a personal number. The IMSI in these examples is from the ITU test range, not a real customer.'],
  on=[('hlr', 'HLR archivist'), ('imsi-him', 'His IMSI'), ('pod', 'Call Pod')],
  art=('hlr-archive', 'The HLR archivist holds a blank glowing folder beside his IMSI agent in a navy suit, while the Call Pod flies down an aisle of wooden drawers; a Nokia 3310 sits on a cabinet'),
  egg='nokia'),
 dict(n=7, zone='his', title='A room key for one call',
  node=[('hlr', 'HLR', 0), ('vlr', 'VLR (visitor register)', 0)],
  chip='ProvideRoamingNumber', reply='MSRN', proto='SS7 · MAP',
  cap='The archivist knows which area his phone last reported in, but that is not a number you can ring. So she asks the visitor register there (the VLR) for a temporary routing number made for this one call, the MSRN. The receptionist cuts a hotel room key that works once, then is useless. The HLR passes it back, and the Gateway MSC sends the Call Pod on towards it.',
  real='HLR → VLR   MAP  ProvideRoamingNumber\n   imsi, msc-Number, msisdn\nVLR → HLR   result: roamingNumber (MSRN)   (from the serving MSC’s own number pool)\nHLR → GMSC  SendRoutingInfo result: MSRN\nGMSC → serving MSC   ISUP  IAM  to the MSRN',
  notes=['The VLR is the network’s short-term memory of who is currently in its area. It also holds the TMSI mask that goes with each IMSI.',
         'If he had set “divert all calls”, the HLR would have returned the diversion number instead of an MSRN.'],
  on=[('vlr', 'VLR receptionist'), ('imsi-him', 'His IMSI')],
  portraits=['vlr']),
 dict(n=8, zone='space', title='The twist: there is no mast',
  node=[('vault', 'His serving MSC', 0), ('dish', 'Ground gateway', 0), ('sat', 'Satellite', -26), ('phone', 'His phone', 0)],
  chip='feeder up, service down', reply='', proto='Satellite radio',
  cap='Here is the clever bit. Her son is in a glen with no ordinary mobile signal, but a satellite overhead is acting as a mobile mast in space: our orbiting lighthouse. The Call Pod rides a beam from a ground station (the gateway) up to the satellite, which relays it down to his phone on ordinary mobile frequencies. His phone treats it as an ordinary cell.',
  real='Mobile core  ↔  Ground gateway      fibre\nGround gateway  ↔  Satellite         FEEDER LINK: radio link between satellite and ground\nSatellite  ↔  His phone              SERVICE LINK: mobile-band spectrum, standard handset',
  notes=['Some designs put the base station inside the satellite. Others keep it on the ground and use the satellite as a relay. Direct-to-cell services such as Starlink’s are built so an ordinary phone can treat the satellite as a normal cell. 3GPP’s NTN standards (Release 17 onwards) also give the phone extra help with long delay and Doppler shift.',
         'Real satellite-to-phone systems are 4G or 5G based (the 3GPP “NTN” standards), so voice would run as VoLTE rather than through an MSC. We draw the classic path because it is the clearest way to see who does what.'],
  on=[('sat', 'Satellite lighthouse'), ('pod', 'Call Pod')],
  art=('satellite-beam', 'A hiker on a misty Highland hillside holds up a phone while a friendly satellite-lighthouse beams cyan light over the glen and the Call Pod rides the beam upward'),
  honesty=True),
 dict(n=9, zone='space', title='Shouting his disguise across the glen',
  node=[('vlr', 'Serving MSC / VLR', 0), ('sat', 'Satellite beam', -14), ('phone', 'His phone', 0)],
  chip='Paging: TMSI', reply='Paging response', proto='BSSMAP · radio paging', rings=True,
  cap='Now the network has to find him. It calls out his temporary disguise, the TMSI, across the whole satellite beam, which is far bigger than a normal mobile cell. A disguise matters: shouting his real identity over a wide area would let anyone with a radio follow him around. Only one phone in the glen recognises the mask, and it answers.',
  real='MSC/VLR → radio network   BSSMAP  PAGING  (tmsi 0xA1B2C3D4, location area)\nRadio network → air          Paging Request on the paging channel, every cell in the area\nPhone → network              Channel Request, then Paging Response (TMSI)',
  notes=['Paging a big beam costs a lot of radio capacity, which is one reason satellite networks are careful about how often they do it.'],
  on=[('tmsi', 'TMSI mask'), ('imsi-him', 'His IMSI'), ('sat', 'Satellite lighthouse')],
  portraits=['tmsi', 'sat']),
 dict(n=10, zone='space', title='“Prove you’re you,” again',
  node=[('vlr', 'His network (AuC vault)', 0), ('sim', 'His SIM', 0)],
  chip='RAND', reply='SRES', proto='GSM security · DTAP',
  cap='His network now runs the same check she passed, with his own agent and his own key. A new random challenge goes out. Inside his SIM, his Ki scrambles an answer. The twin in his operator’s AuC vault already knows what the answer should be. They match, a fresh ciphering key is made, and his radio link is locked. Two keys, two vaults, two agents: neither secret has crossed the air.',
  real='His AuC     RAND → A3(Ki) = SRES,  A8(Ki) = Kc   →  triplet to his VLR\nVLR → phone  Authentication Request   RAND\nHis SIM      SRES′ = A3(Ki, RAND);   Kc = A8(Ki, RAND)\nphone → VLR  Authentication Response   SRES′\nVLR          match →  Cipher Mode Command (A5 or the 4G equivalent, key Kc / Kasme)',
  notes=['The two authentications are independent. Her network proved she is she; his network now proves he is he. Neither operator has to trust the other’s key.'],
  on=[('imsi-him', 'His IMSI'), ('ki', 'Ki'), ('auc', 'AuC vault guardian')],
  portraits=['imsi-him', 'auc', 'ki']),
 dict(n=11, zone='his', title='Border control for the ship',
  node=[('phone', 'His handset (IMEI)', 0), ('eir', 'EIR register', 0)],
  chip='CheckIMEI', reply='white list ✓', proto='SS7 · MAP',
  cap='The agent checks out, but what about the ship he is travelling in? Every phone has a unique 15-digit serial number, the IMEI, stamped on its hull. Many operators then ask the EIR, the border-control register, and the sniffer dog is sent out. The check is optional and depends on the operator’s policy. In this story the hull number is not on the stolen-phone list. Green light: cleared to proceed.',
  real='MSC → phone   DTAP  Identity Request (IMEI)\nphone → MSC   Identity Response   IMEI 35 123456 654321 1   (illustrative)\nMSC → EIR     MAP  CheckIMEI (imei)\nEIR → MSC     equipmentStatus = whiteListed',
  notes=['The first 8 digits say which make and model (the TAC), the next 6 are the serial number, and the last is a check digit.',
         'When the check is done, the EIR can return white, grey or black list. Stolen phones are often added to a shared industry list, so a phone reported stolen on one UK network can be blocked on others. Not every network checks the IMEI on every call.'],
  on=[('imei', 'IMEI'), ('dog', 'EIR sniffer dog')],
  art=('border-control', 'A robot sniffer dog inspects a small grey smartphone-shaped ship in a cyan scanner ring while the Call Pod waits; a soft green glow shows the all-clear')),
 dict(n=12, zone='join', title='Ring ring: the agents meet',
  node=[('phone', 'His phone', 0), ('exchange', 'Her MSC', 0)],
  chip='ACM, then ANM', reply='', proto='ISUP · DTAP', meter=True, bars=True,
  cap='His phone buzzes in his pocket. A message called ACM (Address Complete) races all the way back to her network, which plays her the ringing tone. He answers, and a second message, ANM (Answer), tells every exchange along the route that the call is connected. At that moment the meter starts, and the two secret agents meet in the middle: her IMSI and his IMSI, shaking hands over a living call.',
  cap2='Now her voice is on the move. Because both ends are mobiles, it can often stay in the compact mobile format (AMR) the whole way. It only gets transcoded into the old 64 kbit/s telephone format if the join between the two operators still needs it. Up at the satellite, travelling at about 17,000 mph, the network constantly adjusts timing and frequency to cancel the Doppler effect: the same trick that makes an ambulance siren change pitch as it passes.',
  real='phone → MSC   DTAP  Alerting         →  ISUP  ACM  back to her network  →  ringback tone\nphone → MSC   DTAP  Connect          →  ISUP  ANM  →  charging starts\nSCP           CAP  EventReportBCSM (oAnswer)  →  her prepaid timer begins\nVoice path    AMR end to end where the interconnect allows it;\n              otherwise transcoded (AMR ↔ G.711) at a media gateway\nSatellite     typical low orbit a few hundred kilometres up, speed about 7.5 km/s (about 17,000 mph);\n              Doppler and timing advance pre-compensated (3GPP NTN, Release 17 onwards)',
  notes=['No ANM means no billing. Until someone answers, the call is free, which is why a lot of fraud tries to get calls “answered” without a person.',
         'Standard GSM timing only copes with distances up to about 35 km. Satellite systems need extra timing tricks, which is part of what the NTN standards add.'],
  on=[('imsi-her', 'Her IMSI'), ('imsi-him', 'His IMSI'), ('pod', 'Call Pod')],
  art=('agents-meet', 'Her IMSI agent in a fedora and his IMSI agent in a navy suit shake hands in a cyan-lit hall, with the Call Pod hovering behind them')),
 dict(n=13, zone='back', title='Hang-up, and a line on two bills',
  node=[('phone', 'His phone', 0), ('exchange', 'Her MSC', 0), ('bill', 'Both billing systems', 0)],
  chip='REL, then two CDRs', reply='RLC', proto='ISUP · CDRs · settlement', receipt=True,
  cap='When she says goodbye and hangs up, a REL (Release) message goes hop by hop along the route, and each exchange answers RLC (Release Complete) once it has let go of the line. Behind the pod the lights go out, one stop at a time. Then the afterlife begins. Both networks write a small receipt, a CDR (call detail record): hers for the call she placed, his for the call he received. The receipts drift to mediation, where they are tidied and merged, then to rating, which puts a price on them, and to billing. The two operators also settle up with each other, because her operator pays his operator a small fee for delivering the call. The grave is a line on her bill.',
  real='She hangs up  →  ISUP  REL  (cause 16: normal call clearing)  hop by hop\nEach switch    →  ISUP  RLC  once its circuit is freed\nRadio side     →  DTAP  Disconnect, Release, Release Complete;  radio channel freed\nSCP            →  CAP  EventReportBCSM (oDisconnect), final charge reported\nHer network    MO CDR   (A and B numbers, start and end, duration 252 s, her IMSI, cell)\nHis network    MT CDR   (same call, his IMSI, IMEI, serving cell / satellite beam)\nMediation      collect, validate, remove duplicates, join records\nRating         252 s × her tariff;   wholesale: mobile termination (and any satellite fee)\nBilling        invoice line:   07700 900123    4 min 12s\nSettlement     originating operator pays the terminating operator, usually netted off',
  notes=['For prepaid there is no monthly bill. The record feeds the charging system that already took the money while she talked.',
         'Two receipts for one call is normal. Each operator only sees its own half clearly, which is why mediation and wholesale billing exist.'],
  on=[('bill', 'Billing accountants'), ('imsi-her', 'Her IMSI'), ('imsi-him', 'His IMSI')],
  art=('the-bill', 'Three different accountants work a conveyor of blank glowing receipts while the Call Pod waves goodbye from above')),
 dict(n=14, zone='his', title='Alternate ending: nobody answers',
  node=[('gate', 'Gateway MSC', 0), ('vm', 'Voicemail (IVR)', 0)],
  chip='diverted: no reply', reply='', proto='ISUP · call forwarding', egg='virgin',
  cap='In another universe he is deep in a peat bog with his phone in his bag, and does not answer. After 20 to 30 seconds of ringing, the network’s no-reply timer runs out and the call is quietly diverted to voicemail. A friendly robot voice (the IVR) asks her to leave a message after the tone. If his phone had been out of reach altogether, the network would have diverted her at once, and she would never have heard a ring.',
  real='GMSC/MSC   no-reply timer (NRy, typically 20 to 30 s) expires\nHLR profile  call forwarding on no reply → voicemail access number\nISUP IAM     redirecting number = his number, redirection reason = no reply  →  voicemail platform\nIVR          plays greeting, records message\nVoicemail    SMS to him: “You have a new voicemail”   (MAP MT-ForwardSM)',
  notes=['The “not reachable” case (switched off, no signal at all) is a separate setting and diverts immediately.',
         'IVR means Interactive Voice Response: any computer that talks to callers and listens to their key presses or voice.',
         'When voicemail answers, the network treats the call as connected (an ANM is sent). Whether she is charged, and how much, depends on her tariff: some UK tariffs make voicemail free or cheap, others apply a short rate.'],
  on=[('pod', 'Call Pod'), ('hlr', 'HLR archivist')],
  portraits=['hlr']),
]

CAMEO = '''<aside class="cameo" aria-labelledby="cameo-h">
<h3 id="cameo-h" class="kicker">How it used to work</h3>
<p>If she had placed this call from a landline, the first hop would have been a copper wire into a local exchange, which would have handed the call to a transit switch and then to the mobile operator. The UK’s old analogue phone network, the PSTN, is due to go digital on <a href="https://www.openreach.com/big-switch-off">31 January 2027</a>. After that, a “landline” call is really a broadband call that arrives at the same mobile front door.</p>
<ul class="era-strip" aria-label="Characters from earlier eras of the telephone">
<li><figure><img src="../assets/img/inner-signal/era/past-switchboard.webp" width="960" height="540" alt="A switchboard operator in a navy uniform plugs a cord into a wooden board" loading="lazy" decoding="async"><figcaption>Switchboard operator</figcaption></figure></li>
<li><figure><img src="../assets/img/inner-signal/era/past-strowger.webp" width="960" height="540" alt="A brass automaton whose torso is a Strowger stepping switch, with a vertical bank of contacts and a wiper arm" loading="lazy" decoding="async"><figcaption>Strowger switch</figcaption></figure></li>
<li><figure><img src="../assets/img/inner-signal/era/past-telegraph.webp" width="960" height="540" alt="A telegraph messenger in a peaked cap, holding an envelope beside a bicycle" loading="lazy" decoding="async"><figcaption>Telegraph messenger</figcaption></figure></li>
<li><figure><img src="../assets/img/inner-signal/era/past-rotary.webp" width="960" height="540" alt="A friendly character in the shape of a dark red rotary-dial telephone" loading="lazy" decoding="async"><figcaption>Rotary telephone</figcaption></figure></li>
<li><figure><img src="../assets/img/inner-signal/era/past-k6.webp" width="960" height="540" alt="A character in the shape of a red K6 telephone box" loading="lazy" decoding="async"><figcaption>K6 phone box</figcaption></figure></li>
<li><figure><img src="../assets/img/inner-signal/era/past-brick.webp" width="960" height="540" alt="A chunky 1980s brick mobile phone standing as a character" loading="lazy" decoding="async"><figcaption>1985 brick phone</figcaption></figure></li>
<li><figure><img src="../assets/img/inner-signal/era/past-nokia.webp" width="960" height="540" alt="A Nokia 3310 character with a small separate screen, oval navigation key and 12-button keypad" loading="lazy" decoding="async"><figcaption>Nokia 3310</figcaption></figure></li>
<li><figure><img src="../assets/img/inner-signal/era/past-lineman.webp" width="960" height="540" alt="A copper lineman in a peaked cap, holding a coil of cable beside a telegraph pole" loading="lazy" decoding="async"><figcaption>Copper lineman</figcaption></figure></li>
</ul>
<div class="baton">
<figure><img src="../assets/img/inner-signal/era/past-switchboard.webp" width="960" height="540" alt="The switchboard operator at her board" loading="lazy" decoding="async"><figcaption>Switchboard operator</figcaption></figure>
<p class="baton-mark" aria-hidden="true"><span class="baton-stick"></span></p>
<figure><img src="../assets/img/inner-signal/era/today-msc.webp" width="960" height="540" alt="Today’s MSC signalman, ready to take the call on" loading="lazy" decoding="async"><figcaption>MSC signalman</figcaption></figure>
</div>
<p class="baton-cap">The switchboard operator hands the baton to today’s MSC signalman. The job is the same: take the call, and send it on.</p>
</aside>'''

# ---- helpers (route diagrams, eggs, chapters)
def chip(x, y, text, at, anchor='middle', cls='chip'):
    w = int(len(text) * 8.4 + 26)
    x0 = x - w / 2 if anchor == 'middle' else x
    tx = x if anchor == 'middle' else x + w / 2
    return (f'<g class="{cls}" style="--at:{at}"><rect x="{x0:.0f}" y="{y-17}" width="{w}" height="30" rx="15"/>'
            f'<text x="{tx:.0f}" y="{y+3}" text-anchor="middle">{esc(text)}</text></g>')

def node(x, y, icon, label, horizontal=True):
    g = (f'<g class="nd" transform="translate({x:.0f} {y:.0f})"><rect x="-30" y="-30" width="60" height="60" rx="16"/>'
         f'<g transform="translate(-14 -14) scale(1.1667)" class="ic">{ICONS[icon]}</g>')
    if horizontal:
        words = label.split(' ')
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
        W, H = 640, 216; xs = [70 + i * (500 / max(k - 1, 1)) for i in range(k)]
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
    if not vertical:
        mx = (pts[0][0] + pts[-1][0]) / 2
        parts.append(chip(mx, 28, c['chip'], .3))
        if c['reply']: parts.append(chip(mx, H - 22, '← ' + c['reply'], .7, cls='chip reply'))
    else:
        my = (pts[0][1] + pts[-1][1]) / 2
        parts.append(chip(100, my - 14, c['chip'], .3, anchor='start'))
        if c['reply']: parts.append(chip(100, my + 26, '↑ ' + c['reply'], .7, anchor='start', cls='chip reply'))
    ex, ey = pts[-1]
    parts.append(f'<g class="pod" transform="translate({ex:.0f} {ey:.0f})"><use href="#is-pod" x="-26" y="-23" width="52" height="46"/></g>')
    parts.append('</svg>')
    return ''.join(parts)

EGG_NOKIA = ('<span class="egg egg-nokia"><button type="button" class="egg-b" aria-describedby="egg-n" aria-label="Easter egg: a Nokia 3310"><svg viewBox="0 0 40 70" aria-hidden="true" focusable="false"><rect x="4" y="2" width="32" height="66" rx="9" fill="#2b3a52" stroke="#8fdbff"/><rect x="9" y="10" width="22" height="16" rx="2" fill="#9fd29a"/><path d="M12 32h16M12 38h16M12 44h16M12 50h16M12 56h16" stroke="#8fdbff" stroke-width="3" stroke-linecap="round"/></svg></button><span class="egg-t" id="egg-n" role="tooltip">A Nokia 3310, still in the archive. It would like you to know it also holds a very good game of Snake.</span></span>')
EGG_VIRGIN = ('<span class="egg egg-desk"><button type="button" class="egg-b" aria-describedby="egg-v" aria-label="Easter egg: a tech support desk with a Virgin Mobile 2007 badge"><svg viewBox="0 0 120 80" aria-hidden="true" focusable="false"><rect x="4" y="58" width="82" height="7" rx="2" fill="#2b3a52" stroke="#8fdbff"/><path d="M12 65v13M78 65v13" stroke="#8fdbff" stroke-width="3"/><rect x="24" y="28" width="42" height="26" rx="3" fill="#0b1426" stroke="#8fdbff"/><path d="M45 54v4M36 58h18" stroke="#8fdbff" stroke-width="3"/><path d="M31 36h26M31 42h16" stroke="#5ec8ff" stroke-width="2"/><rect x="58" y="2" width="60" height="24" rx="4" fill="#d6212b"/><text x="88" y="13" font-size="9" font-weight="800" fill="#fff" text-anchor="middle" font-family="Inter,sans-serif">VIRGIN MOBILE</text><text x="88" y="23" font-size="9" font-weight="800" fill="#fff" text-anchor="middle" font-family="Inter,sans-serif">2007</text></svg></button><span class="egg-t" id="egg-v" role="tooltip">Tech support desk, circa 2007. “Have you tried turning it off and on again?” An in-joke from the author’s days on the support floor.</span></span>')
EGGS = {'nokia': EGG_NOKIA, 'virgin': EGG_VIRGIN}

CAST = [
 ('pod', 'The Call Pod', 'Our shrunken craft', 'It carries her voice from the moment she presses call to the line on her bill.'),
 ('imsi-her', 'Her IMSI', 'The caller’s secret agent', 'Lives in her SIM and in her network’s register. Over the air she wears a TMSI disguise, which the network swaps regularly so nobody can follow her.'),
 ('imsi-him', 'His IMSI', 'The receiver’s secret agent', 'Lives in his SIM. The two agents meet in the middle when the call connects.'),
 ('tmsi', 'TMSI', 'The disguise', 'A temporary mask, handed out by the visitor register and changed often. The real agent almost never shows their face over the air.'),
 ('ki', 'Ki', 'The key that never leaves', 'A glowing secret key locked inside the SIM, with a twin locked in the network’s AuC vault. They are never in the same room, which is exactly why the trick works.'),
 ('imei', 'IMEI', 'The ship', 'The handset itself, with a unique 15-digit hull number stamped on it. Border control (the EIR) checks it against the stolen-phone list.'),
 ('bts', 'BTS lighthouse keeper', 'The mast', 'He takes the radio call in from her phone and sends it into her network.'),
 ('msc', 'MSC signalman', 'Her exchange', 'He sets the call up on her network and hands it to the other operator.'),
 ('bouncer', 'Charging bouncer', 'The credit check', 'Because she is placing the call, he asks her network whether she can pay, before the Call Pod is allowed out.'),
 ('gmsc', 'Gateway MSC passport officer', 'The front door', 'He meets calls arriving from other operators and asks the archive where the person being rung actually is.'),
 ('hlr', 'HLR archivist', 'The master register', 'She turns a phone number (the MSISDN, the public name) into the secret agent behind it.'),
 ('vlr', 'VLR receptionist', 'The visitor register', 'She issues a room key (the MSRN) that works for this one call, then is useless.'),
 ('auc', 'AuC vault guardian', 'The twin key’s vault', 'He looks after the twin keys and the random challenges that prove an agent is genuine.'),
 ('sat', 'Satellite lighthouse', 'A mast in space', 'A satellite acting as a mobile cell, already covering the glen.'),
 ('dog', 'EIR sniffer dog', 'Border control', 'He checks the ship’s hull number against the stolen-phone list.'),
 ('bill', 'Billing accountants', 'The afterlife', 'They clean the receipts from both networks, put a price on them and print the bill.'),
]

def portraits_html(keys, alt_suffix=''):
    if not keys: return ''
    figs = []
    labels = {k: n for k, n, _, _ in CAST}
    for k in keys:
        figs.append(f'<figure><img src="../assets/img/inner-signal/p-{k}.webp" width="400" height="400" alt="{esc(labels.get(k, k)+alt_suffix)}" loading="lazy" decoding="async"><figcaption>{esc(labels.get(k, k))}</figcaption></figure>')
    return f'<div class="art-chars n{len(keys)}">{"".join(figs)}</div>'

def chapter(c):
    n = c['n']; zone = c['zone']
    art = ''
    if c.get('art'):
        f, alt = c['art']
        art = f'<figure class="art"><img src="../assets/img/inner-signal/{f}.webp" width="1280" height="720" alt="{esc(alt)}" loading="lazy" decoding="async"></figure>'
    elif c.get('portraits'):
        art = portraits_html(c['portraits'])
    extras = ''
    if c.get('meter'):
        extras += '<p class="meter" aria-live="off"><span class="m-l">Meter</span> <span class="m-v" data-meter>4:12</span> <span class="m-s">call connected, charging</span></p>'
    if c.get('bars'):
        extras += ('<div class="bars" role="img" aria-label="Voice format: AMR end to end where possible, or transcoded to 64 kilobits per second if the interconnect needs it">'
                   '<p><span>Often, end to end: AMR</span><i style="--w:19%"></i><b>12.2 kbit/s</b></p>'
                   '<p><span>Only if the join needs it: G.711</span><i style="--w:100%"></i><b>64 kbit/s</b></p></div>')
    if c.get('receipt'):
        extras += ('<div class="receipt" role="img" aria-label="Bill line: 07700 900123, 4 minutes 12 seconds"><span class="r-h">Her bill</span>'
                   '<span class="r-l"><b>07700 900123</b><i>4 min 12s</i></span></div>')
    egg = EGGS.get(c.get('egg'), '')
    honesty = ''
    if c.get('honesty'):
        honesty = '<p class="honest"><strong>An honest note.</strong> As of November 2026, the only live UK satellite-to-phone service is Virgin Media O2’s O2 Satellite service, over Starlink Direct to Cell: texts, location sharing and a short list of apps, including WhatsApp. WhatsApp calls can work, but they are internet (VoIP) calls over the app’s data, not a normal phone call, so quality varies and they can drop as satellites pass. Standard phone calls, including 999, are not supported yet. VodafoneThree has said its planned AST SpaceMobile service is expected to include voice, with beta testing expected in early 2027. This leg of the story shows that near future, not a native voice call you can place over satellite today.</p>'
    on = ''.join(f'<li><img src="../assets/img/inner-signal/c-{k}.webp" width="24" height="24" alt="" loading="lazy">{esc(lab)}</li>' for k, lab in c['on'])
    notes = ''.join(f'<li>{x}</li>' for x in c['notes'])
    cameo = CAMEO if n == 1 else ''
    return f'''<section class="ch z-{zone}" id="ch-{n}" data-n="{n}" data-zone="{ZONES[zone]}" data-title="{esc(c['title'])}" aria-labelledby="ch{n}-h">
<header class="ch-h"><span class="num" aria-hidden="true">{n:02d}</span><p class="kicker">Chapter {n} of 14 · {ZONES[zone]}</p><h2 id="ch{n}-h">{c['title']}</h2></header>
<div class="ch-vis">{art}<div class="strip">{strip_svg(c, False)}{strip_svg(c, True)}{egg}</div>{extras}</div>
<div class="ch-txt"><p class="cap">{c['cap']}</p>{("<p class=\"cap cap2\">"+c["cap2"]+"</p>") if c.get("cap2") else ""}{honesty}<ul class="onscr" aria-label="On screen in this chapter">{on}</ul>
<button type="button" class="real-b" aria-expanded="false" aria-controls="real-{n}">Show me the real thing</button>
<div class="real" id="real-{n}"><p class="proto">{esc(c['proto'])}</p><pre><code>{esc(c['real'])}</code></pre><ul class="rn">{notes}</ul></div></div>
</section>
{cameo}'''

# sleek new pod: bubble canopy, cyan stripes, brown hair
POD = '''<svg class="jdefs" width="0" height="0" aria-hidden="true" focusable="false"><defs>
<symbol id="is-pod" viewBox="-26 -23 52 46" overflow="visible">
<ellipse cx="0" cy="20" rx="20" ry="3" fill="#00cfff" opacity=".25"/>
<path d="M-20 8c0 6 9 10 20 10s20-4 20-10v2c0 6-9 9-20 9s-20-3-20-9z" fill="#3aa3d6"/>
<ellipse cx="0" cy="7" rx="22" ry="13" fill="#e8eef7"/>
<path d="M-22 8h44" stroke="#5ec8ff" stroke-width="2.4"/>
<path d="M-16 5a16 16 0 0 1 32 0z" fill="#8fdbff" fill-opacity=".4" stroke="#cdeeff" stroke-width="1.3"/>
<circle cx="0" cy="-2.5" r="5.6" fill="#e2b089"/>
<path d="M-6-3.2c.6-4.2 3-6.2 6-6.2s5.4 2 6 6.2c-1.8-2.6-3.8-3.5-6-3.5s-4.2.9-6 3.5z" fill="#6b3d2a"/>
<circle cx="-2" cy="-2.2" r=".7" fill="#223"/><circle cx="2" cy="-2.2" r=".7" fill="#223"/>
<path d="M-1.8.4q1.8 1.4 3.6 0" stroke="#a5544c" stroke-width=".8" fill="none"/>
<circle cx="-16" cy="13" r="2.6" fill="#5ec8ff"/><circle cx="16" cy="13" r="2.6" fill="#5ec8ff"/>
</symbol></defs></svg>'''

SHORT={'bts':'Lighthouse keeper','msc':'Signalman','gmsc':'Passport officer','hlr':'Archivist','vlr':'Receptionist','auc':'Vault guardian','sat':'Satellite lighthouse','dog':'Sniffer dog','bill':'Accountants','bouncer':'Bouncer'}
strip_items = ''.join(
    f'<li><a href="#cast-{k}"><img src="../assets/img/inner-signal/p-{k}.webp" width="400" height="400" alt="" loading="lazy" decoding="async"><span class="cs-name">{esc(SHORT.get(k,name))}</span><span class="cs-role">{esc(role)}</span></a></li>'
    for k, name, role, _ in CAST)

cast_cards = ''.join(
    f'<li class="cc-card" id="cast-{k}"><img src="../assets/img/inner-signal/p-{k}.webp" width="400" height="400" alt="" loading="lazy" decoding="async"><div><p class="kicker">{esc(role)}</p><h3>{esc(name)}</h3><p>{txt}</p></div></li>'
    for k, name, role, txt in CAST)

rail_dots = ''.join(f'<a href="#ch-{c["n"]}" class="dot" aria-label="Chapter {c["n"]}: {esc(c["title"])}"><i></i></a>' for c in CH)
toc = ''.join(f'<li><a href="#ch-{c["n"]}"><span>{c["n"]:02d}</span>{c["title"]}</a></li>' for c in CH)

HEAD = f'''{POD}
<header class="page-head is-head"><p class="kicker">Explainer · the life of a phone call</p><h1>Inner Signal: the life of a phone call</h1>
<p class="lede">A woman in Warminster rings her son’s mobile from her own phone. He is hiking in the Highlands, miles from the nearest mast. We shrink down and ride the call, from the moment she presses call to the line on her bill.</p>
<p class="jcred">Written by a mobile network insider with over 13 years in GSM, from IVR and SMS to call routing and thin and thick MVNOs.</p>
<p class="honest top"><strong>An honest note.</strong> As of November 2026, the only live UK satellite-to-phone service is Virgin Media O2’s O2 Satellite service, over Starlink Direct to Cell. It offers texts, location sharing and a short list of apps, including WhatsApp. WhatsApp calls can work, but they are internet (VoIP) calls over the app’s data, not a normal phone call, so quality varies and they can drop as satellites pass. Standard phone calls, including 999, are not supported yet. This story’s satellite voice leg is the near future being built, not something you can dial today.</p>
<p class="row-cta"><a class="btn" href="#ch-1">Start the journey <span aria-hidden="true">↓</span></a><button type="button" class="btn ghost" id="all-real" aria-pressed="false">Show me the real thing, everywhere</button></p>
<!--SHARE-TOP-->
</header>
<section class="cast" aria-labelledby="cast-h"><h2 id="cast-h">Meet the cast</h2>
<div class="cast-strip-wrap"><p class="cast-hint">Scroll the strip, or jump into a chapter when you are ready.</p>
<ul class="cast-strip">{strip_items}</ul></div>
<figure class="cast-fig"><img src="../assets/img/inner-signal/cast.webp" width="1280" height="1280" alt="The Inner Signal cast in a 16-tile lineup: the Call Pod, the two IMSI agents, the TMSI disguise, Ki the key, the IMEI ship, the mast keeper, the signalman, the charging bouncer, the passport officer, the archivist, the receptionist, the vault guardian, the satellite lighthouse, the sniffer dog and the three billing accountants" decoding="async"></figure>
<ul class="cast-l">{cast_cards}</ul>
<p class="fine">Every number in this story is made up. Phone numbers, IMSI and IMEI values are examples, and 07700 900xxx is a range set aside for drama. Names and message formats are the real ones.</p></section>
<nav class="toc" aria-labelledby="toc-h"><h2 id="toc-h">The route</h2><ol>{toc}</ol></nav>
<div class="rail" id="rail" aria-hidden="true"><div class="rail-in"><p class="rail-t"><b id="rail-n">1</b><span> / 14</span> <span id="rail-title">She presses call</span> <em id="rail-zone">Her network</em></p>
<div class="rail-bar"><i id="rail-fill"></i><span class="rail-pod"><svg viewBox="-26 -23 52 46" width="26" height="23" focusable="false"><use href="#is-pod"/></svg></span></div></div></div>
<div class="chapters" id="chapters">
'''

END = '''</div>
<section class="next" id="what-comes-next" aria-labelledby="next-h">
<h2 id="next-h">What comes next</h2>
<p>Today’s crew still does the work you have just ridden through. These characters are a look at what is arriving, or still expected, around that same journey.</p>
<ul class="next-grid">
<li>
<figure><img src="../assets/img/inner-signal/era/future-satellite.webp" width="960" height="540" alt="A lighthouse-shaped satellite with the Full Duplex logo glowing on its face screen, beaming down towards Earth" loading="lazy" decoding="async">
<figcaption>Direct-to-cell satellite</figcaption></figure>
<p>In the UK, Virgin Media O2’s O2 Satellite service is already live for texts, location sharing and some apps, over Starlink Direct to Cell. A native voice call to an ordinary phone, of the kind this story rides, is the next step being built, using 3GPP Non-Terrestrial Networks from Release 17 onwards.</p>
</li>
<li>
<figure><img src="../assets/img/inner-signal/era/future-beam.webp" width="960" height="540" alt="A living cyan radio-beam sprite with a disc-shaped wavefront and concentric rings" loading="lazy" decoding="async">
<figcaption>Orbital beam</figcaption></figure>
<p>Those NTN standards give the radio extra help with long delay and Doppler shift, so a phone in a glen can treat a fast-moving satellite as a cell. Later 3GPP releases add further enhancements.</p>
</li>
<li>
<figure><img src="../assets/img/inner-signal/era/future-orchestrator.webp" width="960" height="540" alt="A holographic conductor whose orchestra is made of phones, masts, network nodes and satellites" loading="lazy" decoding="async">
<figcaption>AI orchestrator</figcaption></figure>
<p>AI-driven networks are being trialled and are emerging. They are not deployed everywhere, and this character stands for that work in progress, not a system you will find in every core today.</p>
</li>
<li>
<figure><img src="../assets/img/inner-signal/era/future-esim.webp" width="960" height="540" alt="A friendly character in the shape of an eSIM chip" loading="lazy" decoding="async">
<figcaption>eSIM</figcaption></figure>
<p>An eSIM is a downloadable profile. It still holds the IMSI and the Ki, so the same authentication you met in this story applies, whether the profile arrived on a plastic SIM or over the air.</p>
</li>
<li>
<figure><img src="../assets/img/inner-signal/era/future-ntn.webp" width="960" height="540" alt="A ring-shaped NTN core station in orbit, with solar wings and a friendly face at the centre" loading="lazy" decoding="async">
<figcaption>NTN core</figcaption></figure>
<p>3GPP’s Non-Terrestrial Networks work, from Release 17 onwards, is how ordinary phones and satellites are being standardised to talk to each other. 6G is expected around 2030, as 3GPP studies the groundwork in Releases 20 and 21. That date is an expectation, not a fact.</p>
</li>
<li>
<figure><img src="../assets/img/inner-signal/era/future-gateway.webp" width="960" height="540" alt="A ground-station keeper in a navy coat, holding a glowing tablet between three satellite dishes" loading="lazy" decoding="async">
<figcaption>Gateway station</figcaption></figure>
<p>Many designs still bring the call down through a ground station before it reaches the core. The keeper is expected to remain part of the path, even as more of the radio moves into orbit.</p>
</li>
</ul>
<figure class="family-fig">
<img src="../assets/img/inner-signal/era/family-tree.webp" width="1600" height="1067" alt="A family tree of Inner Signal characters in three eras, past, today and future, across switching, the handset and the radio path" loading="lazy" decoding="async">
<figcaption>Three eras, one family. Today’s crew still carries the 14 chapters you have just read.</figcaption>
</figure>
</section>
<section class="wrapup" aria-labelledby="wu-h"><h2 id="wu-h">The whole trip in one breath</h2>
<p>One tap on a mobile, two networks, two secret agents who meet in the middle, a satellite moving at 17,000 mph, and a pair of billing systems that would not give up. It all took a few seconds to connect and left a single line on her bill: <strong>07700 900123, 4 min 12s</strong>.</p>
<p>Standard voice calls from an ordinary UK phone, over a satellite, are not here yet. Virgin Media O2’s O2 Satellite service is live for texts, some apps, and WhatsApp calls over the app’s data. Other operators have native voice in their plans. Signal is where we follow what comes next.</p>
<details class="srcs"><summary>Where the details come from</summary><ul>
<li>Call setup and routing: ITU-T <a href="https://www.itu.int/rec/T-REC-Q.763">Q.763</a> (ISUP message formats) and <a href="https://www.itu.int/rec/T-REC-Q.764">Q.764</a> (ISUP procedures); 3GPP <a href="https://portal.3gpp.org/desktopmodules/Specifications/SpecificationDetails.aspx?specificationId=796">TS 23.018</a> (basic call handling) and <a href="https://portal.3gpp.org/desktopmodules/Specifications/SpecificationDetails.aspx?specificationId=1660">TS 29.002</a> (MAP).</li>
<li>Mobile-originated prepaid and CAMEL: 3GPP <a href="https://portal.3gpp.org/desktopmodules/Specifications/SpecificationDetails.aspx?specificationId=598">TS 23.078</a> and <a href="https://portal.3gpp.org/desktopmodules/Specifications/SpecificationDetails.aspx?specificationId=1678">TS 29.078</a> (CAP). On a mobile-originated call the usual trigger is DP Collected_Info, at the originating MSC. 4G and 5G online charging uses Diameter or a CHF, with the same job.</li>
<li>Numbers and identities (IMSI, TMSI, IMEI, MSRN, MSISDN): 3GPP <a href="https://portal.3gpp.org/desktopmodules/Specifications/SpecificationDetails.aspx?specificationId=730">TS 23.003</a>. Drama numbers: Ofcom’s reserved range <a href="https://www.ofcom.org.uk/phones-telecoms-and-internet/information-for-industry/numbering/numbers-for-drama">07700 900000 to 900999</a>.</li>
<li>GSM security (RAND, SRES, Kc, A3, A8, A5): 3GPP <a href="https://portal.3gpp.org/desktopmodules/Specifications/SpecificationDetails.aspx?specificationId=2713">TS 43.020</a>. 4G and 5G use AKA to do the same job, in <a href="https://portal.3gpp.org/desktopmodules/Specifications/SpecificationDetails.aspx?specificationId=2296">TS 33.401</a> and <a href="https://portal.3gpp.org/desktopmodules/Specifications/SpecificationDetails.aspx?specificationId=3169">TS 33.501</a>.</li>
<li>VoLTE / IMS: 3GPP <a href="https://portal.3gpp.org/desktopmodules/Specifications/SpecificationDetails.aspx?specificationId=821">TS 23.228</a>. We keep the older MSC and HLR names in the story because the roles are easier to follow; today’s UK voice calls usually run this way over IMS.</li>
<li>Satellite access to ordinary phones: 3GPP Non-Terrestrial Networks, <a href="https://www.3gpp.org/technologies/ntn-overview">Release 17 onwards</a>, including radio adaptations for long delay and Doppler shift. Later releases add further enhancements. UK service in November 2026: Virgin Media O2’s <a href="https://www.o2.co.uk/help/products-and-services/offers-and-extras/o2-satellite">O2 Satellite</a> service (texts, location and some apps; WhatsApp calls over the app’s data, with variable quality; not standard voice). Launch: <a href="https://news.virginmediao2.co.uk/virgin-media-o2-becomes-the-first-uk-mobile-network-to-switch-on-direct-to-device-satellite-connectivity-with-the-launch-of-o2-satellite/">Virgin Media O2, 26 February 2026</a>.</li>
<li>UK landline switch-off: <a href="https://www.openreach.com/big-switch-off">Openreach, Big Switch Off</a>, 31 January 2027.</li>
<li>Wholesale settlement: the originating operator pays the terminating operator a regulated mobile termination rate. Ofcom reviews this market periodically.</li>
</ul></details></section>
<!--SHARE-END-->
'''

meta = {
    'slug': 'inner-signal',
    'title': 'Inner Signal: the life of a phone call',
    'short_title': 'Inner Signal',
    'description': 'Ride a phone call from a mobile in Warminster to a hiker’s phone via satellite, then on to the bill. Fourteen animated chapters, plain English.',
    'summary': 'A scroll-driven journey through a mobile-to-mobile phone call: two networks, a satellite, and the bill.',
}
# SEO description length 70-160
assert 70 <= len(meta['description']) <= 160, len(meta['description'])
body = HEAD + '\n'.join(chapter(c) for c in CH) + END
# no em dashes
assert ' - ' not in body, 'em dash found'
open(f'{ROOT}/src/pages/inner-signal.html', 'w').write('<!--meta\n' + json.dumps(meta, ensure_ascii=False, indent=1) + '\n-->\n' + body)
print('ok', len(body), 'chars, chapters', len(CH))
