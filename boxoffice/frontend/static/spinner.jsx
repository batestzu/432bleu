// 432 Blue — cymatic blob spinner

function CymaticBlob({ size = 260, speed = 1, mode = 0 }){
  const ref = React.useRef(null);
  const N = 220; // path resolution
  const presets = [
    // [base radius, modes...]: each mode is {n: harmonic, amp: amplitude, phaseSpeed: how fast its phase rotates}
    { base: 0.62, modes: [
      { n: 3, amp: 0.06, phaseSpeed: 0.6 },
      { n: 5, amp: 0.04, phaseSpeed: -0.9 },
      { n: 8, amp: 0.025, phaseSpeed: 1.4 },
    ]},
    { base: 0.6, modes: [
      { n: 4, amp: 0.07, phaseSpeed: 0.5 },
      { n: 7, amp: 0.035, phaseSpeed: -1.1 },
      { n: 11, amp: 0.018, phaseSpeed: 1.7 },
    ]},
    { base: 0.58, modes: [
      { n: 2, amp: 0.09, phaseSpeed: 0.4 },
      { n: 6, amp: 0.04, phaseSpeed: -0.8 },
      { n: 13, amp: 0.015, phaseSpeed: 2.2 },
    ]},
  ];

  React.useEffect(() => {
    let raf;
    const start = performance.now();
    const cfg = presets[mode % presets.length];
    function tick(now){
      const t = (now - start) / 1000 * speed;
      const cx = 100, cy = 100;
      let d = '';
      for (let i = 0; i <= N; i++){
        const a = (i / N) * Math.PI * 2;
        let r = cfg.base * 100;
        for (const m of cfg.modes){
          r += m.amp * 100 * Math.sin(m.n * a + t * m.phaseSpeed * Math.PI);
        }
        const x = cx + Math.cos(a) * r;
        const y = cy + Math.sin(a) * r;
        d += (i === 0 ? 'M' : 'L') + x.toFixed(2) + ' ' + y.toFixed(2) + ' ';
      }
      d += 'Z';
      if (ref.current) {
        ref.current.querySelector('.blob-fill').setAttribute('d', d);
        ref.current.querySelector('.blob-stroke').setAttribute('d', d);
        ref.current.querySelector('.blob-stroke-2').setAttribute('d', d);
        ref.current.querySelector('.blob-stroke-3').setAttribute('d', d);
      }
      raf = requestAnimationFrame(tick);
    }
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [mode, speed]);

  return (
    <svg ref={ref} viewBox="0 0 200 200" width={size} height={size} style={{display:'block', overflow:'visible'}}>
      <defs>
        <radialGradient id={`blob-grad-${mode}`} cx="50%" cy="40%" r="60%">
          <stop offset="0%" stopColor="#9af2e8" stopOpacity="0.95"/>
          <stop offset="45%" stopColor="#00f0ff" stopOpacity="0.7"/>
          <stop offset="80%" stopColor="#7a3bff" stopOpacity="0.55"/>
          <stop offset="100%" stopColor="#ff2bd6" stopOpacity="0.35"/>
        </radialGradient>
        <filter id={`blob-glow-${mode}`} x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="3"/>
        </filter>
        <filter id={`blob-glow-strong-${mode}`} x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="6"/>
        </filter>
      </defs>

      {/* outer halo */}
      <path className="blob-stroke-3" d="" fill="none" stroke="#00f0ff" strokeWidth="0.6" opacity="0.4" filter={`url(#blob-glow-strong-${mode})`}/>
      {/* magenta echo (slightly outside via stroke) */}
      <path className="blob-stroke-2" d="" fill="none" stroke="#ff2bd6" strokeWidth="0.4" opacity="0.55" filter={`url(#blob-glow-${mode})`}/>
      {/* fill */}
      <path className="blob-fill" d="" fill={`url(#blob-grad-${mode})`} opacity="0.85"/>
      {/* crisp edge */}
      <path className="blob-stroke" d="" fill="none" stroke="#00f0ff" strokeWidth="0.7" opacity="0.95"/>

      {/* internal cymatic rings */}
      <g opacity="0.55" style={{mixBlendMode:'screen'}}>
        {[20, 32, 44].map((r,i) => (
          <circle key={i} cx="100" cy="100" r={r}
            fill="none" stroke="#5fe6dd" strokeWidth="0.3"
            strokeDasharray="2 4"
            style={{transformOrigin:'100px 100px', animation:`spin-${i} ${(i+2)*4}s linear infinite ${i%2?'reverse':''}`}}/>
        ))}
      </g>

      {/* nodes around */}
      <g>
        {Array.from({length:12}).map((_,i)=>{
          const a = (i/12)*Math.PI*2;
          const r = 78;
          return <circle key={i} cx={100+Math.cos(a)*r} cy={100+Math.sin(a)*r} r="0.7" fill="#00f0ff" opacity="0.6"/>;
        })}
      </g>

      <style>{`
        @keyframes spin-0 { from{transform:rotate(0)} to{transform:rotate(360deg)} }
        @keyframes spin-1 { from{transform:rotate(0)} to{transform:rotate(360deg)} }
        @keyframes spin-2 { from{transform:rotate(0)} to{transform:rotate(360deg)} }
      `}</style>
    </svg>
  );
}

// Spinner card with frequency readout
function SpinnerCard({ mode = 0, label = "TUNING" }){
  const [hz, setHz] = React.useState(432.000);
  React.useEffect(() => {
    let raf;
    const start = performance.now();
    function tick(now){
      const t = (now - start) / 1000;
      // small oscillation around 432
      setHz(432 + Math.sin(t * 1.3) * 0.34 + Math.sin(t * 3.1) * 0.08);
      raf = requestAnimationFrame(tick);
    }
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, []);

  return (
    <div style={{
      width:380, height:380,
      background:'radial-gradient(ellipse at 50% 30%, #062330 0%, #02060a 70%)',
      display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center',
      gap:18,
      fontFamily:'"JetBrains Mono", monospace',
      color:'#5fe6dd',
      position:'relative',
      overflow:'hidden',
    }}>
      <div style={{
        position:'absolute', inset:0,
        backgroundImage:'repeating-linear-gradient(0deg, rgba(0,240,255,0.05) 0 1px, transparent 1px 4px)',
      }}/>
      <div style={{
        fontSize:10, letterSpacing:'0.4em', color:'rgba(95,230,221,0.7)',
        zIndex:2,
      }}>{label}</div>

      <div style={{zIndex:2}}>
        <CymaticBlob size={220} mode={mode}/>
      </div>

      <div style={{zIndex:2, textAlign:'center', lineHeight:1.1}}>
        <div style={{fontSize:24, color:'#00f0ff', letterSpacing:'0.05em', textShadow:'0 0 8px rgba(0,240,255,0.6)'}}>
          {hz.toFixed(3)} <span style={{color:'rgba(95,230,221,0.6)', fontSize:12}}>Hz</span>
        </div>
        <div style={{fontSize:9, letterSpacing:'0.4em', color:'rgba(255,43,214,0.85)', marginTop:6}}>RESONANCE LOCK</div>
      </div>
    </div>
  );
}

// Bare inline spinner (small applications)
function SpinnerInline(){
  return (
    <div style={{
      width:200, height:200,
      background:'#02060a',
      display:'flex', alignItems:'center', justifyContent:'center',
    }}>
      <CymaticBlob size={150} mode={1}/>
    </div>
  );
}

window.CymaticBlob = CymaticBlob;
window.SpinnerCard = SpinnerCard;
window.SpinnerInline = SpinnerInline;
