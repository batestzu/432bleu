// 432 Bleu — Box Office · ticket drawer (tier select, PWYW, qty, confirm)

const { useState, useEffect, useMemo } = React;

function genCode() {
  const seg = () => Math.random().toString(36).slice(2, 6).toUpperCase();
  return `BLEU-${seg()}-${seg()}`;
}

function Stepper({ value, onChange, accent, disabled }) {
  const btn = (label, fn) => (
    <button onClick={fn} disabled={disabled}
      style={{
        width: 34, height: 34, flex: 'none', cursor: disabled ? 'not-allowed' : 'pointer',
        background: 'transparent', color: accent, border: `1px solid ${accent}55`,
        fontFamily: '"JetBrains Mono", monospace', fontSize: 18, lineHeight: 1,
        opacity: disabled ? 0.3 : 1,
      }}>{label}</button>
  );
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 0 }}>
      {btn('–', () => onChange(Math.max(0, value - 1)))}
      <div style={{ width: 40, textAlign: 'center', fontFamily: '"JetBrains Mono", monospace',
        fontSize: 16, color: '#fff' }}>{value}</div>
      {btn('+', () => onChange(value + 1))}
    </div>
  );
}

function TicketDrawer({ show, accent, onClose }) {
  const [qty, setQty] = useState({});
  const [pwyw, setPwyw] = useState({});
  const [done, setDone] = useState(false);
  const [code] = useState(genCode);

  useEffect(() => { setQty({}); setPwyw({}); setDone(false); }, [show && show.id]);

  // lock scroll while open
  useEffect(() => {
    if (show) { document.body.style.overflow = 'hidden'; }
    return () => { document.body.style.overflow = ''; };
  }, [show]);

  const subtotal = useMemo(() => {
    if (!show) return 0;
    return show.tiers.reduce((sum, t) => {
      const q = qty[t.id] || 0;
      const unit = t.price === 'PWYW' ? (Number(pwyw[t.id]) || 0) : t.price;
      return sum + q * unit;
    }, 0);
  }, [show, qty, pwyw]);

  const totalQty = show ? show.tiers.reduce((s, t) => s + (qty[t.id] || 0), 0) : 0;
  const open = !!show;
  const soldOut = show && show.status === 'sold-out';

  return (
    <>
      {/* scrim */}
      <div onClick={onClose} style={{
        position: 'fixed', inset: 0, zIndex: 80,
        background: 'rgba(2,6,10,0.72)', backdropFilter: 'blur(3px)',
        opacity: open ? 1 : 0, pointerEvents: open ? 'auto' : 'none',
        transition: 'opacity 0.3s ease',
      }} />

      {/* panel */}
      <aside style={{
        position: 'fixed', top: 0, right: 0, bottom: 0, zIndex: 90,
        width: 'min(460px, 100vw)', maxWidth: '100vw',
        background: 'linear-gradient(180deg, #061d28 0%, #03101a 60%, #02080e 100%)',
        borderLeft: `1px solid ${accent}55`,
        boxShadow: `-20px 0 80px rgba(0,0,0,0.6), -1px 0 40px ${accent}33`,
        transform: open ? 'translateX(0)' : 'translateX(102%)',
        transition: 'transform 0.42s cubic-bezier(0.22,1,0.36,1)',
        display: 'flex', flexDirection: 'column',
        fontFamily: '"Space Grotesk", system-ui, sans-serif',
        color: '#fff',
      }}>
        {show && !done && (
          <>
            <Header show={show} accent={accent} onClose={onClose} />

            <div style={{ flex: 1, overflowY: 'auto', padding: '8px 26px 20px' }}>
              {soldOut && (
                <div style={{ margin: '12px 0 20px', padding: '14px 16px', border: '1px solid rgba(255,255,255,0.14)',
                  fontFamily: '"JetBrains Mono", monospace', fontSize: 12, letterSpacing: '0.15em',
                  color: 'rgba(255,255,255,0.6)' }}>
                  THIS ROOM IS AT CAPACITY · JOIN THE WAITLIST BELOW
                </div>
              )}
              {show.tiers.map(t => (
                <TierRow key={t.id} tier={t} accent={accent} disabled={soldOut}
                  qty={qty[t.id] || 0}
                  onQty={(v) => setQty(q => ({ ...q, [t.id]: v }))}
                  pwyw={pwyw[t.id] || ''}
                  onPwyw={(v) => setPwyw(p => ({ ...p, [t.id]: v }))} />
              ))}

              <p style={{ fontSize: 12, lineHeight: 1.7, color: 'rgba(154,242,232,0.5)',
                fontFamily: '"JetBrains Mono", monospace', letterSpacing: '0.04em', marginTop: 22 }}>
                All entries 21+. Tuned to {show.hz} Hz. No re-entry after last call.
                Members skip the line at every tier.
              </p>
            </div>

            <Footer accent={accent} subtotal={subtotal} totalQty={totalQty}
              soldOut={soldOut} onConfirm={() => setDone(true)} />
          </>
        )}

        {show && done && (
          <Confirmation show={show} accent={accent} code={code} qty={qty} pwyw={pwyw}
            subtotal={subtotal} totalQty={totalQty} onClose={onClose} />
        )}
      </aside>
    </>
  );
}

function Header({ show, accent, onClose }) {
  return (
    <div style={{ padding: '24px 26px 16px', borderBottom: '1px solid rgba(95,230,221,0.16)', position: 'relative' }}>
      <button onClick={onClose} aria-label="Close" style={{
        position: 'absolute', top: 20, right: 20, width: 34, height: 34, cursor: 'pointer',
        background: 'transparent', border: '1px solid rgba(255,255,255,0.2)', color: '#fff',
        fontFamily: '"JetBrains Mono", monospace', fontSize: 16,
      }}>✕</button>
      <div style={{ fontFamily: '"JetBrains Mono", monospace', fontSize: 10, letterSpacing: '0.34em',
        color: accent, marginBottom: 12 }}>SELECT ADMISSION</div>
      <div style={{ fontFamily: '"Unbounded", sans-serif', fontWeight: 700, fontSize: 26,
        letterSpacing: '-0.02em', lineHeight: 1.05, marginBottom: 10 }}>{show.artist}</div>
      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', fontFamily: '"JetBrains Mono", monospace',
        fontSize: 11, letterSpacing: '0.12em', color: 'rgba(154,242,232,0.75)' }}>
        <span>{show.dateLabel}</span>
        <span>{show.timeLabel}</span>
        <span>{show.room}</span>
      </div>
    </div>
  );
}

function TierRow({ tier, accent, qty, onQty, pwyw, onPwyw, disabled }) {
  const isPwyw = tier.price === 'PWYW';
  const active = qty > 0;
  return (
    <div style={{
      padding: '18px 0', borderBottom: '1px solid rgba(95,230,221,0.12)',
      opacity: disabled ? 0.4 : 1, pointerEvents: disabled ? 'none' : 'auto',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 10 }}>
            <span style={{ fontFamily: '"Unbounded", sans-serif', fontWeight: 500, fontSize: 16,
              letterSpacing: '0.02em', color: active ? accent : '#fff' }}>{tier.name}</span>
            <span style={{ fontFamily: '"JetBrains Mono", monospace', fontSize: 13, color: 'rgba(255,255,255,0.85)' }}>
              {isPwyw ? 'PWYW' : '$' + tier.price}
            </span>
          </div>
          <div style={{ fontFamily: '"JetBrains Mono", monospace', fontSize: 11, letterSpacing: '0.06em',
            color: 'rgba(154,242,232,0.55)', marginTop: 5 }}>{tier.blurb}</div>
        </div>
        <Stepper value={qty} onChange={onQty} accent={accent} disabled={disabled} />
      </div>

      {isPwyw && qty > 0 && (
        <div style={{ marginTop: 14, display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontFamily: '"JetBrains Mono", monospace', fontSize: 11, letterSpacing: '0.1em',
            color: 'rgba(154,242,232,0.7)' }}>YOUR PRICE · PER TICKET</span>
          <div style={{ display: 'flex', alignItems: 'center', border: `1px solid ${accent}55`,
            paddingLeft: 10 }}>
            <span style={{ color: accent, fontFamily: '"JetBrains Mono", monospace' }}>$</span>
            <input type="number" min="0" value={pwyw} placeholder="0"
              onChange={e => onPwyw(e.target.value)}
              style={{ width: 70, background: 'transparent', border: 'none', outline: 'none',
                color: '#fff', fontFamily: '"JetBrains Mono", monospace', fontSize: 15, padding: '8px 8px' }} />
          </div>
          <span style={{ fontFamily: '"JetBrains Mono", monospace', fontSize: 10,
            color: 'rgba(255,255,255,0.35)' }}>$0 min · tip the room</span>
        </div>
      )}
    </div>
  );
}

function Footer({ accent, subtotal, totalQty, soldOut, onConfirm }) {
  const can = totalQty > 0 && !soldOut;
  return (
    <div style={{ padding: '18px 26px 26px', borderTop: `1px solid ${accent}44`,
      background: 'rgba(2,8,14,0.6)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 14 }}>
        <span style={{ fontFamily: '"JetBrains Mono", monospace', fontSize: 11, letterSpacing: '0.2em',
          color: 'rgba(154,242,232,0.7)' }}>{totalQty} TICKET{totalQty === 1 ? '' : 'S'}</span>
        <span style={{ fontFamily: '"Unbounded", sans-serif', fontWeight: 600, fontSize: 26, color: '#fff' }}>
          ${subtotal.toFixed(2)}
        </span>
      </div>
      <button onClick={can ? onConfirm : undefined} disabled={!can}
        style={{
          width: '100%', padding: '16px', cursor: can ? 'pointer' : 'not-allowed',
          background: can ? accent : 'rgba(255,255,255,0.06)',
          color: can ? '#02060a' : 'rgba(255,255,255,0.35)',
          border: 'none', fontFamily: '"Unbounded", sans-serif', fontWeight: 700,
          fontSize: 14, letterSpacing: '0.14em',
          boxShadow: can ? `0 0 30px ${accent}66` : 'none',
          transition: 'all 0.2s ease',
        }}>
        {soldOut ? 'JOIN WAITLIST' : 'SECURE TICKETS'}
      </button>
      <div style={{ textAlign: 'center', marginTop: 12, fontFamily: '"JetBrains Mono", monospace',
        fontSize: 10, letterSpacing: '0.2em', color: 'rgba(255,255,255,0.3)' }}>
        ENCRYPTED · NO FEES AT THE DOOR
      </div>
    </div>
  );
}

function Confirmation({ show, accent, code, qty, pwyw, subtotal, totalQty, onClose }) {
  const lines = show.tiers.filter(t => (qty[t.id] || 0) > 0).map(t => {
    const unit = t.price === 'PWYW' ? (Number(pwyw[t.id]) || 0) : t.price;
    return { name: t.name, q: qty[t.id], unit };
  });
  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', padding: '30px 26px',
      overflowY: 'auto' }}>
      <button onClick={onClose} aria-label="Close" style={{
        position: 'absolute', top: 20, right: 20, width: 34, height: 34, cursor: 'pointer',
        background: 'transparent', border: '1px solid rgba(255,255,255,0.2)', color: '#fff',
        fontFamily: '"JetBrains Mono", monospace', fontSize: 16,
      }}>✕</button>

      <div style={{ textAlign: 'center', marginTop: 10 }}>
        <CymaticBlob size={150} mode={1} />
      </div>
      <div style={{ textAlign: 'center', marginTop: 6 }}>
        <div style={{ fontFamily: '"JetBrains Mono", monospace', fontSize: 11, letterSpacing: '0.34em',
          color: accent }}>RESONANCE LOCKED</div>
        <div style={{ fontFamily: '"Unbounded", sans-serif', fontWeight: 700, fontSize: 24, marginTop: 12,
          letterSpacing: '-0.02em' }}>You're on the list.</div>
        <div style={{ fontFamily: '"Space Grotesk", sans-serif', fontSize: 14, color: 'rgba(154,242,232,0.7)',
          marginTop: 8, lineHeight: 1.5 }}>
          {totalQty} pass{totalQty === 1 ? '' : 'es'} for <strong style={{ color: '#fff' }}>{show.artist}</strong><br />
          {show.dateLabel} · {show.timeLabel} · {show.room}
        </div>
      </div>

      <div style={{ margin: '24px 0', padding: '18px 20px', border: `1px dashed ${accent}66`,
        background: 'rgba(0,240,255,0.04)' }}>
        <div style={{ fontFamily: '"JetBrains Mono", monospace', fontSize: 10, letterSpacing: '0.3em',
          color: 'rgba(154,242,232,0.6)', marginBottom: 8 }}>ENTRY CODE</div>
        <div style={{ fontFamily: '"JetBrains Mono", monospace', fontSize: 22, letterSpacing: '0.12em',
          color: accent, textShadow: `0 0 16px ${accent}88` }}>{code}</div>
        <div style={{ marginTop: 16, display: 'flex', flexDirection: 'column', gap: 6 }}>
          {lines.map((l, i) => (
            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', gap: 12,
              fontFamily: '"JetBrains Mono", monospace', fontSize: 12, color: 'rgba(255,255,255,0.8)' }}>
              <span style={{ whiteSpace: 'nowrap' }}>{l.q} × {l.name}</span>
              <span style={{ whiteSpace: 'nowrap' }}>${(l.q * l.unit).toFixed(2)}</span>
            </div>
          ))}
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8, paddingTop: 8,
            borderTop: '1px solid rgba(255,255,255,0.12)', fontFamily: '"JetBrains Mono", monospace',
            fontSize: 13, color: '#fff' }}>
            <span>TOTAL</span><span>${subtotal.toFixed(2)}</span>
          </div>
        </div>
      </div>

      <p style={{ fontFamily: '"JetBrains Mono", monospace', fontSize: 11, lineHeight: 1.7,
        color: 'rgba(154,242,232,0.5)', textAlign: 'center', letterSpacing: '0.04em' }}>
        Sent to your device. Screenshot the code or pull it from your member wallet at the door.
      </p>

      <button onClick={onClose} style={{
        marginTop: 'auto', padding: '15px', cursor: 'pointer', background: 'transparent',
        color: accent, border: `1px solid ${accent}`, fontFamily: '"Unbounded", sans-serif',
        fontWeight: 600, fontSize: 13, letterSpacing: '0.14em',
      }}>BACK TO CALENDAR</button>
    </div>
  );
}

Object.assign(window, { TicketDrawer });
