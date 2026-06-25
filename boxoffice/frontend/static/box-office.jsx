// 432 Bleu — Box Office · main app
//
// OPTIMIZATION NOTES (future):
// - Replace Babel CDN + runtime JSX with a Vite build — removes ~1MB of babel.min.js overhead
// - Add og:image + og:description meta tags to index.html for social sharing previews
// - Lazy-load TicketDrawer (never needed on initial render)

const { useState: uS, useEffect: uE } = React;

function addToCalendar(show) {
  const start = new Date(show.dateISO);
  const end = new Date(start.getTime() + 3 * 60 * 60 * 1000);
  const fmt = (d) => d.toISOString().replace(/[-:]/g, '').split('.')[0] + 'Z';
  const url = 'https://calendar.google.com/calendar/render?action=TEMPLATE' +
    '&text=' + encodeURIComponent('432.BLEU — ' + show.artist) +
    '&dates=' + fmt(start) + '/' + fmt(end) +
    '&details=' + encodeURIComponent(show.tagline + '\n\nhttps://boxoffice.432bleu.com') +
    '&location=' + encodeURIComponent('432.BLEU · ' + show.room);
  window.open(url, '_blank');
}

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "accent": "#00f0ff",
  "intensity": 0.7,
  "heroLayout": "split"
} /*EDITMODE-END*/;

function useViewport() {
  const [w, setW] = uS(typeof window !== 'undefined' ? window.innerWidth : 1200);
  uE(() => {
    const on = () => setW(window.innerWidth);
    window.addEventListener('resize', on);
    return () => window.removeEventListener('resize', on);
  }, []);
  return w;
}

function BoxOffice() {
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const [active, setActive] = uS(null); // selected show for drawer
  const [filter, setFilter] = uS('all');
  const [shows, setShows] = uS([]);
  const [loading, setLoading] = uS(true);
  const vw = useViewport();
  const mobile = vw < 760;
  const accent = t.accent;

  uE(() => {
    fetchShows().then(setShows).finally(() => setLoading(false));
  }, []);

  const [headline, ...rest] = shows;
  const filtered = rest.filter((s) => {
    if (filter === 'all') return true;
    if (filter === 'available') return s.status !== 'sold-out';
    return s.status === filter;
  });

  return (
    <div style={{ position: 'relative', minHeight: '100vh', color: '#fff',
      fontFamily: '"Space Grotesk", system-ui, sans-serif', overflowX: 'hidden' }}>
      <Atmosphere accent={accent} intensity={t.intensity} />
      <Hud accent={accent} shows={shows} />

      <div style={{ position: 'relative', zIndex: 10,
        maxWidth: 1180, margin: '0 auto', padding: mobile ? '0 18px 90px' : '0 40px 100px' }}>
        <Nav accent={accent} mobile={mobile} />
        {loading ? (
          <LoadingState />
        ) : headline ? (
          <>
            <Hero show={headline} accent={accent} mobile={mobile}
            layout={t.heroLayout} onGet={() => setActive(headline)} />
            <Calendar shows={filtered} accent={accent} mobile={mobile}
            filter={filter} setFilter={setFilter} onPick={setActive} />
          </>
        ) : (
          <EmptyState accent={accent} />
        )}
        <FooterBlock accent={accent} mobile={mobile} />
      </div>

      <TicketDrawer show={active} accent={accent} onClose={() => setActive(null)} />

      <TweaksPanel>
        <TweakSection label="Accent" />
        <TweakColor label="Neon accent" value={t.accent}
        options={['#00f0ff', '#ff2bd6', '#7a3bff']}
        onChange={(v) => setTweak('accent', v)} />
        <TweakSection label="Atmosphere" />
        <TweakSlider label="Background intensity" value={t.intensity} min={0} max={1} step={0.05}
        onChange={(v) => setTweak('intensity', v)} />
        <TweakSection label="Hero" />
        <TweakRadio label="Hero layout" value={t.heroLayout}
        options={['split', 'centered']}
        onChange={(v) => setTweak('heroLayout', v)} />
      </TweaksPanel>
    </div>);

}

/* ───────────────────────── LOADING / EMPTY ───────────────────────── */
function LoadingState() {
  return (
    <div style={{ padding: '120px 0', textAlign: 'center', fontFamily: '"JetBrains Mono", monospace',
      fontSize: 12, letterSpacing: '0.3em', color: 'rgba(154,242,232,0.5)' }}>
      TUNING IN…
    </div>);

}

function EmptyState({ accent }) {
  return (
    <div style={{ padding: '120px 0', textAlign: 'center' }}>
      <div style={{ fontFamily: '"JetBrains Mono", monospace', fontSize: 11, letterSpacing: '0.3em',
        color: accent, marginBottom: 12 }}>NO SIGNAL</div>
      <h2 style={{ fontFamily: '"Unbounded", sans-serif', fontWeight: 700, fontSize: 32,
        margin: 0, letterSpacing: '-0.02em' }}>No upcoming shows</h2>
      <p style={{ fontFamily: '"JetBrains Mono", monospace', fontSize: 12, letterSpacing: '0.06em',
        color: 'rgba(154,242,232,0.55)', marginTop: 14 }}>
        Check back soon — the season is being tuned.
      </p>
    </div>);

}

/* ───────────────────────── NAV ───────────────────────── */
function Nav({ accent, mobile }) {
  return (
    <nav style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: mobile ? '24px 0 14px' : '34px 0 18px' }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
        <span style={{ fontFamily: '"Unbounded", sans-serif', fontWeight: 900, fontSize: mobile ? 24 : 28,
          letterSpacing: '-0.04em', color: '#fff',
          textShadow: `0 0 18px ${accent}77` }}>432</span>
        <span style={{ fontFamily: '"Unbounded", sans-serif', fontWeight: 300, fontSize: mobile ? 13 : 15,
          letterSpacing: '0.42em', paddingLeft: '0.42em', color: BLEU.magenta,
          textShadow: '0 0 12px rgba(255,43,214,0.7)' }}>BLEU</span>
      </div>
      {!mobile &&
      <div style={{ display: 'flex', gap: 30, fontFamily: '"JetBrains Mono", monospace',
        fontSize: 11, letterSpacing: '0.22em', color: 'rgba(154,242,232,0.7)' }}>
          {[['CALENDAR', '#'], ['THE ROOM', 'https://play.432bleu.com'], ['MEMBERSHIP', '/membership']].map(([x, href]) =>
        <a key={x} href={href} style={{ color: 'inherit', textDecoration: 'none' }}
        onMouseEnter={(e) => e.currentTarget.style.color = accent}
        onMouseLeave={(e) => e.currentTarget.style.color = 'rgba(154,242,232,0.7)'}>{x}</a>
        )}
        </div>
      }
      <button onClick={() => window.location.href = '/membership'}
        style={{ background: 'transparent', border: `1px solid ${accent}66`, color: accent,
        padding: mobile ? '9px 14px' : '10px 20px', cursor: 'pointer',
        fontFamily: '"JetBrains Mono", monospace', fontSize: 11, letterSpacing: '0.2em' }}>
        MEMBER LOGIN
      </button>
    </nav>);

}

/* ───────────────────────── HERO ───────────────────────── */
function Hero({ show, accent, mobile, layout, onGet }) {
  const meta = STATUS_META[show.status];
  const centered = layout === 'centered';

  const eyebrow =
  <div style={{ display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap',
    justifyContent: centered ? 'center' : 'flex-start' }}>
      <span style={{ fontFamily: '"JetBrains Mono", monospace', fontSize: 11, letterSpacing: '0.3em',
      color: accent }}>SEASON OPENER · {show.hz} Hz</span>
      <StatusPill status={show.status} accent={accent} />
    </div>;


  const title =
  <h1 style={{ fontWeight: 800,
    fontSize: mobile ? 44 : centered ? 88 : 76, lineHeight: 0.95, letterSpacing: '-0.04em',
    margin: '20px 0 0', textWrap: 'balance',
    color: '#eafcff',
    textShadow: `0 0 24px ${accent}66, 0 0 2px ${accent}44`, fontFamily: "Unbounded" }}>
      {show.artist}
    </h1>;


  const tagline =
  <p style={{ fontFamily: '"Space Grotesk", sans-serif', fontSize: mobile ? 15 : 18,
    color: 'rgba(154,242,232,0.8)', margin: '16px 0 0', letterSpacing: '0.01em' }}>
      {show.tagline}
    </p>;


  const datestack =
  <div style={{ display: 'flex', gap: mobile ? 22 : 40, flexWrap: 'wrap',
    justifyContent: centered ? 'center' : 'flex-start', marginTop: 26 }}>
      {[['DATE', show.dateLabel], ['DOORS', show.timeLabel], ['ROOM', show.room]].map(([k, v]) =>
    <div key={k}>
          <div style={{ fontFamily: '"JetBrains Mono", monospace', fontSize: 10, letterSpacing: '0.28em',
        color: 'rgba(95,230,221,0.55)', marginBottom: 6 }}>{k}</div>
          <div style={{ fontFamily: '"Unbounded", sans-serif', fontWeight: 400, fontSize: mobile ? 16 : 19,
        color: '#fff', letterSpacing: '-0.01em' }}>{v}</div>
        </div>
    )}
    </div>;


  const tierline =
  <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginTop: 26,
    justifyContent: centered ? 'center' : 'flex-start' }}>
      {show.tiers.map((tr) =>
    <div key={tr.id} style={{ border: '1px solid rgba(95,230,221,0.22)', padding: '8px 14px',
      fontFamily: '"JetBrains Mono", monospace', fontSize: 12, letterSpacing: '0.08em' }}>
          <span style={{ color: '#fff' }}>{tr.name}</span>
          <span style={{ color: accent, marginLeft: 8 }}>{formatPrice(tr)}</span>
        </div>
    )}
    </div>;


  const cta =
  <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap', marginTop: 30,
    justifyContent: centered ? 'center' : 'flex-start' }}>
      <button onClick={onGet} style={{
      background: accent, color: '#02060a', border: 'none', cursor: 'pointer',
      padding: '16px 30px', fontFamily: '"Unbounded", sans-serif', fontWeight: 700,
      fontSize: 14, letterSpacing: '0.12em', boxShadow: `0 0 36px ${accent}66` }}>
        GET TICKETS
      </button>
      <button onClick={() => addToCalendar(show)} style={{ background: 'transparent', color: '#fff', border: '1px solid rgba(255,255,255,0.25)',
      cursor: 'pointer', padding: '16px 26px', fontFamily: '"JetBrains Mono", monospace',
      fontSize: 12, letterSpacing: '0.14em' }}>
        ADD TO CALENDAR
      </button>
    </div>;


  // shared blob backdrop
  const blob = (opacity, scale) =>
  <div style={{ position: 'absolute', pointerEvents: 'none', opacity,
    filter: 'blur(0.2px)', mixBlendMode: 'screen' }}>
      <CymaticBlob size={mobile ? 320 : 540} mode={2} />
    </div>;


  if (centered) {
    return (
      <header style={{ position: 'relative', textAlign: 'center',
        padding: mobile ? '34px 0 20px' : '70px 0 30px' }}>
        <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center',
          justifyContent: 'center', zIndex: 0, opacity: 0.5, pointerEvents: 'none',
          mixBlendMode: 'screen' }}>
          <CymaticBlob size={mobile ? 360 : 620} mode={2} />
        </div>
        <div style={{ position: 'relative', zIndex: 2, display: 'flex', flexDirection: 'column',
          alignItems: 'center' }}>
          {eyebrow}{title}{tagline}{datestack}{tierline}{cta}
        </div>
      </header>);

  }

  // split layout
  return (
    <header style={{ position: 'relative', display: 'grid',
      gridTemplateColumns: mobile ? '1fr' : '1.15fr 0.85fr', gap: mobile ? 10 : 40,
      alignItems: 'center', padding: mobile ? '26px 0 16px' : '56px 0 36px' }}>
      <div style={{ position: 'relative', zIndex: 2 }}>
        {eyebrow}{title}{tagline}{datestack}{cta}
      </div>
      <div style={{ position: 'relative', zIndex: 1, display: 'flex', alignItems: 'center',
        justifyContent: 'center', minHeight: mobile ? 240 : 380 }}>
        <div style={{ position: 'absolute', opacity: 0.62, mixBlendMode: 'screen', pointerEvents: 'none' }}>
          <CymaticBlob size={mobile ? 300 : 460} mode={2} />
        </div>
        <div style={{ position: 'relative', zIndex: 2, width: mobile ? '100%' : 'auto' }}>
          {tierline}
        </div>
      </div>
    </header>);

}

function StatusPill({ status, accent }) {
  const meta = STATUS_META[status];
  const colorMap = { cyan: accent, lime: BLEU.lime, mute: 'rgba(255,255,255,0.4)' };
  const c = colorMap[meta.key];
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 7,
      fontFamily: '"JetBrains Mono", monospace', fontSize: 10, letterSpacing: '0.2em',
      color: c, border: `1px solid ${c}55`, padding: '5px 10px' }}>
      <span style={{ width: 6, height: 6, borderRadius: '50%', background: c,
        boxShadow: `0 0 8px ${c}` }} />
      {meta.label}
    </span>);

}

/* ───────────────────────── CALENDAR ───────────────────────── */
function Calendar({ shows, accent, mobile, filter, setFilter, onPick }) {
  const filters = [['all', 'ALL'], ['available', 'AVAILABLE'], ['sold-out', 'SOLD OUT']];
  return (
    <section style={{ marginTop: mobile ? 44 : 80 }}>
      <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between',
        flexWrap: 'wrap', gap: 16, marginBottom: 26,
        borderBottom: '1px solid rgba(95,230,221,0.16)', paddingBottom: 18 }}>
        <div>
          <div style={{ fontFamily: '"JetBrains Mono", monospace', fontSize: 11, letterSpacing: '0.3em',
            color: accent, marginBottom: 8 }}>THE SEASON · JUN 2026</div>
          <h2 style={{ fontFamily: '"Unbounded", sans-serif', fontWeight: 700, fontSize: mobile ? 28 : 38,
            margin: 0, letterSpacing: '-0.03em' }}>Upcoming nights</h2>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {filters.map(([k, label]) =>
          <button key={k} onClick={() => setFilter(k)} style={{
            cursor: 'pointer', padding: '8px 13px', background: filter === k ? accent : 'transparent',
            color: filter === k ? '#02060a' : 'rgba(154,242,232,0.7)',
            border: `1px solid ${filter === k ? accent : 'rgba(95,230,221,0.25)'}`,
            fontFamily: '"JetBrains Mono", monospace', fontSize: 10, letterSpacing: '0.16em' }}>
              {label}
            </button>
          )}
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: mobile ? 12 : 0 }}>
        {shows.length === 0 &&
        <div style={{ padding: '40px 0', textAlign: 'center', fontFamily: '"JetBrains Mono", monospace',
          fontSize: 13, letterSpacing: '0.1em', color: 'rgba(154,242,232,0.5)' }}>
            NO NIGHTS MATCH THIS FILTER.
          </div>
        }
        {shows.map((s, i) =>
        <ShowRow key={s.id} show={s} accent={accent} mobile={mobile} onPick={onPick} first={i === 0} />
        )}
      </div>
    </section>);

}

function ShowRow({ show, accent, mobile, onPick, first }) {
  const [hov, setHov] = uS(false);
  const soldOut = show.status === 'sold-out';

  if (mobile) {
    return (
      <div onClick={() => onPick(show)} style={{
        border: '1px solid rgba(95,230,221,0.16)', padding: '18px', cursor: 'pointer',
        background: 'rgba(6,29,40,0.4)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontFamily: '"JetBrains Mono", monospace', fontSize: 12, letterSpacing: '0.14em',
            color: accent }}>{show.dateLabel}</span>
          <StatusPill status={show.status} accent={accent} />
        </div>
        <div style={{ fontFamily: '"Unbounded", sans-serif', fontWeight: 600, fontSize: 22,
          margin: '10px 0 4px', letterSpacing: '-0.02em' }}>{show.artist}</div>
        <div style={{ fontFamily: '"JetBrains Mono", monospace', fontSize: 11,
          color: 'rgba(154,242,232,0.6)' }}>{show.timeLabel} · {show.room}</div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 14 }}>
          <span style={{ fontFamily: '"JetBrains Mono", monospace', fontSize: 13, color: '#fff' }}>
            FROM {priceFrom(show)}</span>
          <span style={{ fontFamily: '"Unbounded", sans-serif', fontWeight: 700, fontSize: 12,
            letterSpacing: '0.1em', color: soldOut ? 'rgba(255,255,255,0.4)' : accent }}>
            {soldOut ? 'WAITLIST →' : 'TICKETS →'}</span>
        </div>
      </div>);

  }

  return (
    <div onClick={() => onPick(show)}
    onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
    style={{ display: 'grid', gridTemplateColumns: '150px 1fr 150px 150px 160px',
      alignItems: 'center', gap: 20, padding: '24px 18px', cursor: 'pointer',
      borderTop: first ? 'none' : '1px solid rgba(95,230,221,0.12)',
      background: hov ? 'rgba(0,240,255,0.05)' : 'transparent',
      transition: 'background 0.2s ease, padding-left 0.2s ease',
      paddingLeft: hov ? 28 : 18,
      position: 'relative' }}>
      {hov && <div style={{ position: 'absolute', left: 0, top: 12, bottom: 12, width: 2,
        background: accent, boxShadow: `0 0 12px ${accent}` }} />}
      <div>
        <div style={{ fontFamily: '"Unbounded", sans-serif', fontWeight: 500, fontSize: 17,
          color: hov ? accent : '#fff', transition: 'color 0.2s' }}>{show.dateLabel}</div>
        <div style={{ fontFamily: '"JetBrains Mono", monospace', fontSize: 11,
          color: 'rgba(154,242,232,0.55)', marginTop: 4 }}>{show.timeLabel}</div>
      </div>
      <div>
        <div style={{ fontFamily: '"Unbounded", sans-serif', fontWeight: 600, fontSize: 22,
          letterSpacing: '-0.02em' }}>{show.artist}</div>
        <div style={{ fontFamily: '"Space Grotesk", sans-serif', fontSize: 13,
          color: 'rgba(154,242,232,0.6)', marginTop: 4 }}>{show.tagline}</div>
      </div>
      <div style={{ fontFamily: '"JetBrains Mono", monospace', fontSize: 12,
        letterSpacing: '0.1em', color: 'rgba(154,242,232,0.7)' }}>{show.room}</div>
      <StatusPill status={show.status} accent={accent} />
      <div style={{ textAlign: 'right' }}>
        <div style={{ fontFamily: '"JetBrains Mono", monospace', fontSize: 11,
          color: 'rgba(154,242,232,0.55)' }}>FROM</div>
        <div style={{ fontFamily: '"Unbounded", sans-serif', fontWeight: 700, fontSize: 18,
          color: hov ? accent : '#fff', transition: 'color 0.2s' }}>{priceFrom(show)}</div>
      </div>
    </div>);

}

/* ───────────────────────── FOOTER ───────────────────────── */
function FooterBlock({ accent, mobile }) {
  return (
    <footer style={{ marginTop: mobile ? 56 : 90, paddingTop: 30,
      borderTop: '1px solid rgba(95,230,221,0.16)',
      display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 24 }}>
      <div style={{ maxWidth: 360 }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, marginBottom: 12 }}>
          <span style={{ fontFamily: '"Unbounded", sans-serif', fontWeight: 900, fontSize: 22,
            color: '#fff' }}>432</span>
          <span style={{ fontFamily: '"Unbounded", sans-serif', fontWeight: 300, fontSize: 12,
            letterSpacing: '0.4em', paddingLeft: '0.4em', color: BLEU.magenta }}>BLEU</span>
        </div>
        <p style={{ fontFamily: '"JetBrains Mono", monospace', fontSize: 12, lineHeight: 1.8,
          color: 'rgba(154,242,232,0.55)', letterSpacing: '0.04em' }}>A members-first room tuned to 432 Hz. Where you can go out an stay in at the same time. Doors hour before show· last call when the room says so.


        </p>
      </div>
      <div style={{ display: 'flex', gap: mobile ? 30 : 60, flexWrap: 'wrap' }}>
        {[['VISIT', ['SECTOR 11', 'THE WAREHOUSE DISTRICT', 'NO STREET NUMBER']],
        ['HOURS', ['THU–SUN', 'DOORS 23:00', 'CLOSE — ???']],
        ['SIGNAL', ['@432.BLEU', 'JOIN THE LIST', 'PRESS / GUESTLIST']]].map(([h, items]) =>
        <div key={h}>
            <div style={{ fontFamily: '"JetBrains Mono", monospace', fontSize: 10, letterSpacing: '0.28em',
            color: accent, marginBottom: 12 }}>{h}</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {items.map((x) =>
            <span key={x} style={{ fontFamily: '"JetBrains Mono", monospace', fontSize: 12,
              color: 'rgba(154,242,232,0.65)', letterSpacing: '0.06em' }}>{x}</span>
            )}
            </div>
          </div>
        )}
      </div>
    </footer>);

}

ReactDOM.createRoot(document.getElementById('root')).render(<BoxOffice />);