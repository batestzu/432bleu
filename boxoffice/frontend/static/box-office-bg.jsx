// 432 Bleu — Box Office · background atmosphere + HUD chrome

// Concentric resonance rings, perspective floor, scanlines, vignettes.
// `intensity` 0..1 scales ring/scanline opacity. `accent` is the active neon hex.
function Atmosphere({ accent, intensity = 0.7 }) {
  const ringOpacity = 0.05 + intensity * 0.22;
  const scanOpacity = 0.015 + intensity * 0.05;
  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 0, overflow: 'hidden', pointerEvents: 'none' }}>
      {/* base radial */}
      <div style={{ position: 'absolute', inset: 0,
        background: 'radial-gradient(ellipse at 50% 18%, #07212e 0%, #04101a 48%, #02060a 100%)' }} />

      {/* concentric resonance rings */}
      <svg viewBox="0 0 1000 1000" preserveAspectRatio="xMidYMid slice"
        style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', opacity: intensity }}>
        {Array.from({ length: 16 }).map((_, i) => (
          <circle key={i} cx="500" cy="320" r={70 + i * 46}
            fill="none" stroke={accent} strokeWidth="0.6"
            opacity={ringOpacity * (1 - i / 18)}
            strokeDasharray={i % 3 === 0 ? '6 12' : '0'}
            style={{ transformOrigin: '500px 320px',
              animation: `bo-ring-${i % 2} ${34 + i * 3}s linear infinite` }} />
        ))}
      </svg>

      {/* perspective floor */}
      <svg viewBox="0 0 1000 600" preserveAspectRatio="none"
        style={{ position: 'absolute', left: 0, right: 0, bottom: 0, width: '100%', height: '46%', opacity: 0.45 * intensity + 0.15 }}>
        <defs>
          <linearGradient id="bo-floor" x1="0" y1="1" x2="0" y2="0">
            <stop offset="0%" stopColor={accent} stopOpacity="0.5" />
            <stop offset="100%" stopColor={accent} stopOpacity="0" />
          </linearGradient>
        </defs>
        {Array.from({ length: 12 }).map((_, i) => {
          const t = i / 11; const y = 600 - Math.pow(t, 1.7) * 600;
          return <line key={'h' + i} x1="0" y1={y} x2="1000" y2={y} stroke="url(#bo-floor)" strokeWidth="0.6" />;
        })}
        {Array.from({ length: 25 }).map((_, i) => {
          const x = (i - 12) / 12;
          return <line key={'v' + i} x1={500 + x * 1500} y1="600" x2="500" y2="0" stroke="url(#bo-floor)" strokeWidth="0.4" />;
        })}
      </svg>

      {/* color vignettes */}
      <div style={{ position: 'absolute', inset: 0,
        background: 'radial-gradient(ellipse at 82% 2%, rgba(255,43,214,0.16), transparent 46%)' }} />
      <div style={{ position: 'absolute', inset: 0,
        background: 'radial-gradient(ellipse at 8% 100%, rgba(122,59,255,0.20), transparent 52%)' }} />

      {/* scanlines */}
      <div style={{ position: 'absolute', inset: 0, mixBlendMode: 'overlay',
        backgroundImage: `repeating-linear-gradient(0deg, rgba(255,255,255,${scanOpacity}) 0 1px, transparent 1px 3px)` }} />

      <style>{`
        @keyframes bo-ring-0 { from{transform:rotate(0)} to{transform:rotate(360deg)} }
        @keyframes bo-ring-1 { from{transform:rotate(0)} to{transform:rotate(-360deg)} }
      `}</style>
    </div>
  );
}

// HUD corner brackets + persistent status rails.
function Hud({ accent, shows }) {
  const [display, setDisplay] = React.useState('');
  const [live, setLive] = React.useState(false);

  React.useEffect(() => {
    const next = shows
      .filter(s => s.status !== 'sold-out')
      .map(s => ({ ...s, _d: new Date(s.dateISO) }))
      .filter(s => s._d > new Date())
      .sort((a, b) => a._d - b._d)[0];

    if (!next) { setDisplay('NO UPCOMING SHOWS'); return; }

    function tick() {
      const now = new Date();
      const doorsTarget = next.doorsISO ? new Date(next.doorsISO) : next._d;
      const diffToShow = next._d - now;
      const diffToDoors = doorsTarget - now;

      if (diffToShow <= 0) {
        setLive(true);
        setDisplay('');
        return;
      }
      if (diffToDoors <= 0 && next.doorsISO) {
        setLive(false);
        setDisplay(`DOORS OPEN · SHOW @ ${next.timeLabel}`);
        return;
      }
      setLive(false);
      const diff = diffToDoors;
      const d = Math.floor(diff / 86400000);
      const h = Math.floor((diff % 86400000) / 3600000);
      const m = Math.floor((diff % 3600000) / 60000);
      const s = Math.floor((diff % 60000) / 1000);
      if (d > 0) {
        setDisplay(`${next.artist} · ${d}D ${String(h).padStart(2,'0')}H ${String(m).padStart(2,'0')}M`);
      } else {
        setDisplay(`${next.artist} · ${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`);
      }
    }

    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [shows]);

  return (
    <>
      {[[0, 0], [1, 0]].map(([x, y], i) => (
        <div key={i} style={{
          position: 'fixed', [x ? 'right' : 'left']: 16, top: 16,
          width: 26, height: 26, zIndex: 60, pointerEvents: 'none', opacity: 0.6,
          [x ? 'borderRight' : 'borderLeft']: `1px solid ${accent}`,
          borderTop: `1px solid ${accent}`,
        }} />
      ))}
      <div style={{
        position: 'fixed', left: 0, right: 0, bottom: 0, height: 38, zIndex: 60,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 22px', pointerEvents: 'none',
        background: 'linear-gradient(0deg, rgba(2,6,10,0.95) 0%, rgba(2,6,10,0.7) 60%, transparent 100%)',
        fontFamily: '"JetBrains Mono", monospace', fontSize: 10, letterSpacing: '0.3em',
        color: 'rgba(95,230,221,0.6)',
      }}>
        <span>432.BLEU · BOX OFFICE</span>
        <span style={{ color: live ? BLEU.magenta : 'rgba(95,230,221,0.8)' }}>
          {live ? '● LIVE' : `▷ NEXT · ${display}`}
        </span>
      </div>
    </>
  );
}

Object.assign(window, { Atmosphere, Hud });
