// 432 Bleu — Box Office · brand tokens + live event data

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

const STATUS_META = {
  'on-sale':      { label: 'ON SALE',      key: 'cyan' },
  'selling-fast': { label: 'SELLING FAST', key: 'lime' },
  'sold-out':     { label: 'SOLD OUT',     key: 'mute' },
};

// The API sends offset-carrying ISO ("2026-08-13T19:00:00-04:00"), so `new Date()`
// resolves the correct instant for every viewer. Billing is deliberately rendered in
// VENUE time, not the viewer's: a show billed as 7PM ET is 7PM ET for everybody, and
// the zone suffix on the show time is what tells a remote fan to do the math.
const VENUE_TZ = 'America/New_York';

function venueDateLabel(d) {
  const p = new Intl.DateTimeFormat('en-US', {
    timeZone: VENUE_TZ, weekday: 'short', day: '2-digit', month: 'short',
  }).formatToParts(d).reduce((acc, part) => (acc[part.type] = part.value, acc), {});
  return `${p.weekday} ${p.day} ${p.month}`.toUpperCase();
}

function venueTimeLabel(d, withZone) {
  return new Intl.DateTimeFormat('en-US', {
    timeZone: VENUE_TZ,
    hour: 'numeric',
    minute: '2-digit',
    ...(withZone ? { timeZoneName: 'short' } : {}),
  }).format(d);
}

// Tier shape: { id, name, label, priceCents, capacity, sold, available, description }
function mapTier(t) {
  return {
    id: t.id,
    name: t.name,
    label: t.label,
    priceCents: t.price_cents,
    capacity: t.capacity,
    sold: t.sold,
    available: t.available,
    description: t.description,
  };
}

function deriveStatus(tiers) {
  if (tiers.length > 0 && tiers.every(t => !t.available)) return 'sold-out';
  const sellingFast = tiers.some(t =>
    t.available && t.capacity != null && (t.capacity - t.sold) / t.capacity < 0.2
  );
  return sellingFast ? 'selling-fast' : 'on-sale';
}

// Pull the season from the real backend — GET /api/events for the list, then
// GET /api/events/{id} per show for tier detail.
async function fetchShows() {
  const res = await fetch('/api/events');
  if (!res.ok) return [];
  const events = await res.json();

  return Promise.all(events.map(async (e) => {
    const detail = await fetch(`/api/events/${e.id}`);
    const full = detail.ok ? await detail.json() : { ...e, tiers: [] };
    const tiers = full.tiers.map(mapTier);
    const d = new Date(full.date);
    const doors = full.doors_time ? new Date(full.doors_time) : null;

    return {
      id: full.id,
      artist: full.name,
      tagline: full.description || '',
      dateISO: full.date,
      doorsISO: full.doors_time || null,
      dateLabel: venueDateLabel(d),
      doorsLabel: doors ? venueTimeLabel(doors, false) : null,
      timeLabel: venueTimeLabel(d, true),
      room: 'MAIN ROOM',
      hz: '432.000',
      status: deriveStatus(tiers),
      tiers,
    };
  }));
}

function formatPrice(tier) {
  if (tier.priceCents === 0) {
    return tier.name === 'PWYC' ? 'PAY WHAT YOU CAN' : 'FREE';
  }
  return '$' + (tier.priceCents / 100);
}

function priceFrom(show) {
  const available = show.tiers.filter(t => t.available);
  if (available.length === 0) return 'SOLD OUT';
  if (available.some(t => t.priceCents === 0)) return 'FREE';
  return '$' + (Math.min(...available.map(t => t.priceCents)) / 100);
}

Object.assign(window, { BLEU, STATUS_META, fetchShows, formatPrice, priceFrom });
