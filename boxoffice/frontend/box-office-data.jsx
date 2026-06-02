// 432 Bleu — Box Office · season data + brand tokens

const BLEU = {
  ink900:  '#02060a',
  ink800:  '#04101a',
  ink700:  '#062330',
  teal900: '#062f3a',
  teal500: '#15a3a8',
  teal300: '#5fe6dd',
  teal200: '#9af2e8',
  cyan:    '#00f0ff',
  magenta: '#ff2bd6',
  violet:  '#7a3bff',
  lime:    '#c8ff3d',
  paper:   '#eafcff',
};

// Tier shape: { id, name, blurb, price | 'PWYW', cap }
function tiers({ gen, vip, backstage }) {
  return [
    { id: 'gen',  name: 'GEN',       blurb: 'General floor · standing',          price: gen },
    { id: 'vip',  name: 'VIP',       blurb: 'Raised deck · priority entry',      price: vip },
    { id: 'bsg',  name: 'BACKSTAGE', blurb: 'Greenroom access · artist meet',    price: backstage },
  ];
}

// 432 Hz season — June 2026. Headline first.
const SHOWS = [
  {
    id: 'skyler-a-bates',
    artist: 'SKYLER A BATES',
    tagline: 'resonance debut · live frequency set',
    dateISO: '2026-06-02T00:00:00-04:00',
    dateLabel: 'MON 02 JUN',
    timeLabel: '12:00 AM EST',
    room: 'MAIN ROOM',
    hz: '432.000',
    status: 'on-sale',           // on-sale | selling-fast | members | sold-out
    headline: true,
    tiers: tiers({ gen: 'PWYW', vip: 10, backstage: 100 }),
  },
  {
    id: 'veldt',
    artist: 'VELDT',
    tagline: 'modular live · 4-hour standing wave',
    dateISO: '2026-06-06T23:00:00-04:00',
    dateLabel: 'FRI 06 JUN',
    timeLabel: '11:00 PM',
    room: 'MAIN ROOM',
    hz: '216.000',
    status: 'selling-fast',
    tiers: tiers({ gen: 25, vip: 45, backstage: 120 }),
  },
  {
    id: 'lumen-choir',
    artist: 'LUMEN CHOIR',
    tagline: 'ambient chorale · binaural staging',
    dateISO: '2026-06-09T21:00:00-04:00',
    dateLabel: 'TUE 09 JUN',
    timeLabel: '9:00 PM',
    room: 'THE CHAPEL',
    hz: '528.000',
    status: 'on-sale',
    tiers: tiers({ gen: 30, vip: 55, backstage: 140 }),
  },
  {
    id: 'sub-rosa',
    artist: 'SUB ROSA',
    tagline: 'sub-bass ritual · members hours',
    dateISO: '2026-06-13T01:00:00-04:00',
    dateLabel: 'SAT 13 JUN',
    timeLabel: '1:00 AM',
    room: 'THE CELLAR',
    hz: '110.000',
    status: 'members',
    tiers: tiers({ gen: 35, vip: 60, backstage: 160 }),
  },
  {
    id: 'nadia-voss',
    artist: 'NADIA VOSS',
    tagline: 'voice + tape loops · seated',
    dateISO: '2026-06-16T20:00:00-04:00',
    dateLabel: 'TUE 16 JUN',
    timeLabel: '8:00 PM',
    room: 'THE CHAPEL',
    hz: '396.000',
    status: 'on-sale',
    tiers: tiers({ gen: 28, vip: 48, backstage: 130 }),
  },
  {
    id: 'theta-section',
    artist: 'THETA SECTION',
    tagline: 'six-piece live techno · full system',
    dateISO: '2026-06-20T23:30:00-04:00',
    dateLabel: 'SAT 20 JUN',
    timeLabel: '11:30 PM',
    room: 'MAIN ROOM',
    hz: '174.000',
    status: 'selling-fast',
    tiers: tiers({ gen: 32, vip: 58, backstage: 150 }),
  },
  {
    id: 'mariana-deep',
    artist: 'MARIANA DEEP',
    tagline: 'deep listening · 7-hour overnight',
    dateISO: '2026-06-24T22:00:00-04:00',
    dateLabel: 'WED 24 JUN',
    timeLabel: '10:00 PM',
    room: 'THE CELLAR',
    hz: '285.000',
    status: 'on-sale',
    tiers: tiers({ gen: 30, vip: 52, backstage: 135 }),
  },
  {
    id: 'octave-null',
    artist: 'OCTAVE NULL',
    tagline: 'noise / drone · standing only',
    dateISO: '2026-06-27T23:00:00-04:00',
    dateLabel: 'SAT 27 JUN',
    timeLabel: '11:00 PM',
    room: 'MAIN ROOM',
    hz: '639.000',
    status: 'sold-out',
    tiers: tiers({ gen: 34, vip: 60, backstage: 155 }),
  },
  {
    id: 'phase-07',
    artist: 'PHASE_07',
    tagline: 'closing rite · resident collective',
    dateISO: '2026-06-30T01:00:00-04:00',
    dateLabel: 'TUE 30 JUN',
    timeLabel: '1:00 AM',
    room: 'MAIN ROOM',
    hz: '741.000',
    status: 'members',
    tiers: tiers({ gen: 38, vip: 65, backstage: 170 }),
  },
];

const STATUS_META = {
  'on-sale':      { label: 'ON SALE',      key: 'cyan'   },
  'selling-fast': { label: 'SELLING FAST', key: 'lime'   },
  'members':      { label: 'MEMBERS ONLY', key: 'violet' },
  'sold-out':     { label: 'SOLD OUT',     key: 'mute'   },
};

function priceFrom(show) {
  const nums = show.tiers.map(t => t.price).filter(p => typeof p === 'number');
  const hasPwyw = show.tiers.some(t => t.price === 'PWYW');
  if (hasPwyw) return 'PWYW';
  return '$' + Math.min(...nums);
}

Object.assign(window, { BLEU, SHOWS, STATUS_META, priceFrom });
