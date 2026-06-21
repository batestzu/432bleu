// 432 Bleu — Box Office · ticket drawer (tier select, contact info, real checkout)

const { useState, useEffect } = React;

function TicketDrawer({ show, accent, onClose }) {
  const [selectedTierId, setSelectedTierId] = useState(null);
  const [pwycAmount, setPwycAmount] = useState('');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [done, setDone] = useState(false);
  const [attempted, setAttempted] = useState(false);

  useEffect(() => {
    setSelectedTierId(null);
    setPwycAmount('');
    setName('');
    setEmail('');
    setSubmitting(false);
    setError('');
    setDone(false);
    setAttempted(false);
  }, [show && show.id]);

  // lock scroll while open
  useEffect(() => {
    if (show) { document.body.style.overflow = 'hidden'; }
    return () => { document.body.style.overflow = ''; };
  }, [show]);

  const open = !!show;
  const selectedTier = show && show.tiers.find(t => t.id === selectedTierId);
  const isPwyc = !!(selectedTier && selectedTier.name === 'PWYC');
  const amountCents = !selectedTier ? 0
    : isPwyc ? Math.round((parseFloat(pwycAmount) || 0) * 100)
    : selectedTier.priceCents;
  const canSubmit = !!selectedTier && name.trim() !== '' && email.includes('@') && !submitting;
  const allSoldOut = !!show && show.tiers.length > 0 && show.tiers.every(t => !t.available);
  const nameInvalid = attempted && name.trim() === '';
  const emailInvalid = attempted && !email.includes('@');

  async function handleConfirm() {
    if (!canSubmit) { setAttempted(true); return; }
    setSubmitting(true);
    setError('');
    try {
      if (amountCents === 0) {
        const res = await fetch('/api/tickets/free', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            event_id: show.id, tier_id: selectedTier.id,
            email: email.trim(), name: name.trim(),
          }),
        });
        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.detail || 'Something went wrong. Please try again.');
        }
        setDone(true);
        setSubmitting(false);
      } else {
        const res = await fetch('/api/checkout', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            event_id: show.id, tier_id: selectedTier.id,
            email: email.trim(), name: name.trim(), amount_cents: amountCents,
          }),
        });
        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.detail || 'Something went wrong. Please try again.');
        }
        const { checkout_url } = await res.json();
        window.location.href = checkout_url; // leaving the SPA for Stripe
      }
    } catch (e) {
      setError(e.message || 'Something went wrong. Please try again.');
      setSubmitting(false);
    }
  }

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
              {allSoldOut && (
                <div style={{ margin: '12px 0 20px', padding: '14px 16px', border: '1px solid rgba(255,255,255,0.14)',
                  fontFamily: '"JetBrains Mono", monospace', fontSize: 12, letterSpacing: '0.15em',
                  color: 'rgba(255,255,255,0.6)' }}>
                  ALL TICKETS FOR THIS SHOW ARE CURRENTLY SOLD OUT
                </div>
              )}

              <ContactForm accent={accent} name={name} email={email}
                onName={setName} onEmail={setEmail}
                nameInvalid={nameInvalid} emailInvalid={emailInvalid} />

              {show.tiers.map(t => (
                <TierRow key={t.id} tier={t} accent={accent}
                  selected={t.id === selectedTierId}
                  onSelect={() => setSelectedTierId(t.id)}
                  pwycAmount={pwycAmount}
                  onPwycAmount={setPwycAmount} />
              ))}

              <p style={{ fontSize: 12, lineHeight: 1.7, color: 'rgba(154,242,232,0.5)',
                fontFamily: '"JetBrains Mono", monospace', letterSpacing: '0.04em', marginTop: 22 }}>
                All entries 21+. Tuned to {show.hz} Hz. No re-entry after last call.
                Your ticket code will be emailed after checkout.
              </p>
            </div>

            <Footer accent={accent} tier={selectedTier} amountCents={amountCents}
              canSubmit={canSubmit} submitting={submitting} error={error}
              onConfirm={handleConfirm} />
          </>
        )}

        {show && done && (
          <Confirmation show={show} accent={accent} tier={selectedTier}
            amountCents={amountCents} email={email} onClose={onClose} />
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

function TierRow({ tier, accent, selected, onSelect, pwycAmount, onPwycAmount }) {
  const isPwyc = tier.name === 'PWYC';
  const remaining = tier.capacity != null ? Math.max(0, tier.capacity - tier.sold) : null;

  return (
    <div onClick={tier.available ? onSelect : undefined}
      style={{
        padding: '16px 18px', margin: '12px 0', cursor: tier.available ? 'pointer' : 'not-allowed',
        border: `1px solid ${selected ? accent : 'rgba(95,230,221,0.16)'}`,
        background: selected ? `${accent}14` : 'rgba(255,255,255,0.02)',
        opacity: tier.available ? 1 : 0.45,
        transition: 'border-color 0.2s ease, background 0.2s ease',
      }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 12 }}>
        <span style={{ fontFamily: '"Unbounded", sans-serif', fontWeight: 500, fontSize: 16,
          letterSpacing: '0.02em', color: selected ? accent : '#fff' }}>
          {tier.label}{!tier.available ? ' — SOLD OUT' : ''}
        </span>
        <span style={{ fontFamily: '"JetBrains Mono", monospace', fontSize: 13, color: 'rgba(255,255,255,0.85)' }}>
          {formatPrice(tier)}
        </span>
      </div>

      {tier.description &&
        <div style={{ fontFamily: '"JetBrains Mono", monospace', fontSize: 11, letterSpacing: '0.06em',
          color: 'rgba(154,242,232,0.55)', marginTop: 5 }}>{tier.description}</div>
      }

      {remaining !== null && tier.available &&
        <div style={{ fontFamily: '"JetBrains Mono", monospace', fontSize: 10, letterSpacing: '0.1em',
          color: 'rgba(255,255,255,0.35)', marginTop: 6 }}>{remaining} remaining</div>
      }

      {isPwyc && selected && (
        <div onClick={e => e.stopPropagation()} style={{ marginTop: 14, display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
          <span style={{ fontFamily: '"JetBrains Mono", monospace', fontSize: 11, letterSpacing: '0.1em',
            color: 'rgba(154,242,232,0.7)' }}>YOUR AMOUNT</span>
          <div style={{ display: 'flex', alignItems: 'center', border: `1px solid ${accent}55`,
            paddingLeft: 10 }}>
            <span style={{ color: accent, fontFamily: '"JetBrains Mono", monospace' }}>$</span>
            <input type="number" min="0" step="1" value={pwycAmount} placeholder="0"
              onChange={e => onPwycAmount(e.target.value)}
              style={{ width: 70, background: 'transparent', border: 'none', outline: 'none',
                color: '#fff', fontFamily: '"JetBrains Mono", monospace', fontSize: 15, padding: '8px 8px' }} />
          </div>
          <span style={{ fontFamily: '"JetBrains Mono", monospace', fontSize: 10,
            color: 'rgba(255,255,255,0.35)' }}>$0 OK · tip the room</span>
        </div>
      )}
    </div>
  );
}

function ContactForm({ accent, name, email, onName, onEmail, nameInvalid, emailInvalid }) {
  const field = (label, value, onChange, type, placeholder, autoComplete, invalid) => (
    <div style={{ flex: 1, minWidth: 160 }}>
      <label style={{ display: 'block', fontFamily: '"JetBrains Mono", monospace', fontSize: 10,
        letterSpacing: '0.3em', color: invalid ? '#ff6b6b' : 'rgba(154,242,232,0.6)', marginBottom: 8 }}>{label}</label>
      <input type={type} value={value} placeholder={placeholder} autoComplete={autoComplete}
        onChange={e => onChange(e.target.value)}
        style={{ width: '100%',
          background: invalid ? 'rgba(255,107,107,0.08)' : 'rgba(255,255,255,0.04)',
          border: `1px solid ${invalid ? '#ff6b6b' : 'rgba(95,230,221,0.2)'}`,
          color: '#fff', fontFamily: '"Space Grotesk", sans-serif', fontSize: 14, padding: '12px 14px',
          outline: 'none', boxSizing: 'border-box', transition: 'border-color 0.2s ease, background 0.2s ease' }} />
    </div>
  );

  return (
    <div style={{ marginTop: 22 }}>
      <div style={{ fontFamily: '"JetBrains Mono", monospace', fontSize: 10, letterSpacing: '0.34em',
        color: accent, marginBottom: 14 }}>YOUR INFO</div>
      <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap' }}>
        {field('NAME', name, onName, 'text', 'Your name', 'name', nameInvalid)}
        {field('EMAIL', email, onEmail, 'email', 'ticket@example.com', 'email', emailInvalid)}
      </div>
    </div>
  );
}

function Footer({ accent, tier, amountCents, canSubmit, submitting, error, onConfirm }) {
  const priceLabel = !tier ? '—' : amountCents === 0 ? 'FREE' : '$' + (amountCents / 100).toFixed(2);
  const btnLabel = submitting ? 'PROCESSING…'
    : !tier ? 'SELECT A TICKET'
    : amountCents === 0 ? 'CLAIM FREE TICKET'
    : 'SECURE TICKETS';

  return (
    <div style={{ padding: '18px 26px 26px', borderTop: `1px solid ${accent}44`,
      background: 'rgba(2,8,14,0.6)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 14 }}>
        <span style={{ fontFamily: '"JetBrains Mono", monospace', fontSize: 11, letterSpacing: '0.2em',
          color: 'rgba(154,242,232,0.7)' }}>{tier ? tier.label : 'NO TICKET SELECTED'}</span>
        <span style={{ fontFamily: '"Unbounded", sans-serif', fontWeight: 600, fontSize: 26, color: '#fff' }}>
          {priceLabel}
        </span>
      </div>
      <button onClick={onConfirm} disabled={submitting}
        style={{
          width: '100%', padding: '16px', cursor: canSubmit ? 'pointer' : 'not-allowed',
          background: canSubmit ? accent : 'rgba(255,255,255,0.06)',
          color: canSubmit ? '#02060a' : 'rgba(255,255,255,0.35)',
          border: 'none', fontFamily: '"Unbounded", sans-serif', fontWeight: 700,
          fontSize: 14, letterSpacing: '0.14em',
          boxShadow: canSubmit ? `0 0 30px ${accent}66` : 'none',
          transition: 'all 0.2s ease',
        }}>
        {btnLabel}
      </button>
      {error &&
        <div style={{ marginTop: 12, textAlign: 'center', fontFamily: '"JetBrains Mono", monospace',
          fontSize: 11, letterSpacing: '0.06em', color: '#ff6b6b' }}>{error}</div>
      }
      <div style={{ textAlign: 'center', marginTop: 12, fontFamily: '"JetBrains Mono", monospace',
        fontSize: 10, letterSpacing: '0.2em', color: 'rgba(255,255,255,0.3)' }}>
        ENCRYPTED · NO FEES AT THE DOOR
      </div>
    </div>
  );
}

function Confirmation({ show, accent, tier, amountCents, email, onClose }) {
  const priceLabel = amountCents === 0 ? 'FREE' : '$' + (amountCents / 100).toFixed(2);
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
          {tier.label} · {priceLabel} for <strong style={{ color: '#fff' }}>{show.artist}</strong><br />
          {show.dateLabel} · {show.timeLabel} · {show.room}
        </div>
      </div>

      <div style={{ margin: '24px 0', padding: '18px 20px', border: `1px dashed ${accent}66`,
        background: 'rgba(0,240,255,0.04)', textAlign: 'center' }}>
        <div style={{ fontFamily: '"JetBrains Mono", monospace', fontSize: 10, letterSpacing: '0.3em',
          color: 'rgba(154,242,232,0.6)', marginBottom: 10 }}>YOUR TICKET CODE</div>
        <div style={{ fontFamily: '"Space Grotesk", sans-serif', fontSize: 13, color: '#fff', lineHeight: 1.6 }}>
          On its way to <strong>{email}</strong>. Check your inbox and bring the code to the door.
        </div>
      </div>

      <p style={{ fontFamily: '"JetBrains Mono", monospace', fontSize: 11, lineHeight: 1.7,
        color: 'rgba(154,242,232,0.5)', textAlign: 'center', letterSpacing: '0.04em' }}>
        Tuned to {show.hz} Hz. All entries 21+.
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
