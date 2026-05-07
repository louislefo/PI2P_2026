import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Phone, PhoneOff, Mic, MicOff, Volume2, Camera } from 'lucide-react';

const HW_WS_BASE  = 'ws://192.168.137.94:8083';
const CAM_USB_URL = 'http://192.168.137.94:8082/stream';

// ── Génère une sonnerie "téléphone classique" via Web Audio ─────────────────
// Double-ring : 0.4s bip / 0.2s silence / 0.4s bip / 2s silence (en boucle)
function createRingtone() {
  let stopped = false;
  let timeoutId = null;

  const playRing = () => {
    if (stopped) return;
    try {
      const ctx = new AudioContext();
      // Sonnerie classique : deux fréquences mélangées (440 Hz + 480 Hz)
      const playBip = (startTime, duration) => {
        [440, 480].forEach(freq => {
          const osc  = ctx.createOscillator();
          const gain = ctx.createGain();
          osc.connect(gain);
          gain.connect(ctx.destination);
          osc.type = 'sine';
          osc.frequency.value = freq;

          // Enveloppe : montée rapide → plateau → descente
          gain.gain.setValueAtTime(0, startTime);
          gain.gain.linearRampToValueAtTime(0.18, startTime + 0.02);
          gain.gain.setValueAtTime(0.18, startTime + duration - 0.04);
          gain.gain.linearRampToValueAtTime(0, startTime + duration);

          osc.start(startTime);
          osc.stop(startTime + duration);
        });
      };

      const now = ctx.currentTime;
      playBip(now,        0.4);   // 1er bip
      playBip(now + 0.6,  0.4);   // 2e bip

      // Fermer le contexte après la séquence + programmer le prochain cycle
      timeoutId = setTimeout(() => {
        ctx.close();
        if (!stopped) timeoutId = setTimeout(playRing, 2200); // pause entre cycles
      }, 1200);
    } catch (_) {}
  };

  playRing();

  return () => {               // stop()
    stopped = true;
    clearTimeout(timeoutId);
  };
}

export default function IntercomSystem() {
  const [callState, setCallState]   = useState('idle'); // idle | ringing | active
  const [isMuted, setIsMuted]       = useState(false);
  const [callDuration, setCallDuration] = useState(0);
  const [micState, setMicState]     = useState('idle'); // idle | requesting | active | denied | http_blocked
  const [camError, setCamError]     = useState(false);

  const callWsRef    = useRef(null);
  const audioWsRef   = useRef(null);
  const audioCtxRef  = useRef(null);
  const processorRef = useRef(null);
  const streamRef    = useRef(null);
  const timerRef     = useRef(null);
  const durationRef  = useRef(0);
  const stopRingRef  = useRef(null);

  // ── WS événements d'appel ─────────────────────────────────────────────────
  useEffect(() => {
    let ws, retryTimer;
    const connect = () => {
      try {
        ws = new WebSocket(`${HW_WS_BASE}/ws/call`);
        callWsRef.current = ws;
        ws.onmessage = (e) => {
          try {
            const msg = JSON.parse(e.data);
            if (msg.event === 'incoming_call') {
              setCallState('ringing');
              setCamError(false);
              setMicState('idle');
              stopRingRef.current = createRingtone();
            } else if (msg.event === 'call_ended') {
              _hangup(false);
            }
          } catch (_) {}
        };
        ws.onclose = () => { retryTimer = setTimeout(connect, 3000); };
        ws.onerror = () => ws.close();
      } catch (_) {}
    };
    connect();
    return () => { clearTimeout(retryTimer); ws?.close(); };
  }, []);

  // ── Demande d'accès micro (déclenchée manuellement) ───────────────────────
  const requestMic = useCallback(async () => {
    // Vérifie si l'API est disponible (bloquée sur HTTP non-localhost)
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setMicState('http_blocked');
      return;
    }

    setMicState('requesting');

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true,
        }
      });
      streamRef.current = stream;

      // Ouvre le WebSocket audio vers le Pi
      const audioWs = new WebSocket(`${HW_WS_BASE}/ws/audio`);
      audioWs.binaryType = 'arraybuffer';
      audioWsRef.current = audioWs;

      await new Promise((res, rej) => {
        audioWs.onopen  = res;
        audioWs.onerror = () => rej(new Error('WS audio failed'));
        setTimeout(() => rej(new Error('Timeout')), 5000);
      });

      const audioCtx = new AudioContext({ sampleRate: 16000 });
      audioCtxRef.current = audioCtx;
      const source = audioCtx.createMediaStreamSource(stream);
      const proc   = audioCtx.createScriptProcessor(4096, 1, 1);
      processorRef.current = proc;

      proc.onaudioprocess = (e) => {
        if (audioWs.readyState !== WebSocket.OPEN) return;
        const f32 = e.inputBuffer.getChannelData(0);
        const i16 = new Int16Array(f32.length);
        for (let i = 0; i < f32.length; i++) {
          i16[i] = Math.max(-32768, Math.min(32767,
            Math.round(f32[i] * 32767 * (isMuted ? 0 : 1))));
        }
        audioWs.send(i16.buffer);
      };

      source.connect(proc);
      proc.connect(audioCtx.destination);
      setMicState('active');

    } catch (err) {
      console.error('[INTERCOM] Mic error:', err.name, err.message);
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setMicState('denied');
      } else {
        setMicState('http_blocked');
      }
    }
  }, [isMuted]);

  const _stopAudioStream = useCallback(() => {
    processorRef.current?.disconnect();
    processorRef.current = null;
    audioCtxRef.current?.close();
    audioCtxRef.current = null;
    streamRef.current?.getTracks().forEach(t => t.stop());
    streamRef.current = null;
    audioWsRef.current?.close();
    audioWsRef.current = null;
  }, []);

  // Décrocher → démarre le timer, PAS le micro (bouton séparé)
  const answer = useCallback(() => {
    stopRingRef.current?.();
    stopRingRef.current = null;
    setCallState('active');
    setMicState('idle');
    durationRef.current = 0;
    setCallDuration(0);
    timerRef.current = setInterval(() => {
      durationRef.current += 1;
      setCallDuration(durationRef.current);
    }, 1000);
  }, []);

  const _hangup = useCallback((notifyWs = true) => {
    stopRingRef.current?.();
    stopRingRef.current = null;
    setCallState('idle');
    setMicState('idle');
    clearInterval(timerRef.current);
    setCallDuration(0);
    _stopAudioStream();
    if (notifyWs && callWsRef.current?.readyState === WebSocket.OPEN) {
      callWsRef.current.send(JSON.stringify({ action: 'hangup' }));
    }
  }, [_stopAudioStream]);

  const hangup = useCallback(() => _hangup(true), [_hangup]);

  const toggleMute = () => {
    const next = !isMuted;
    setIsMuted(next);
    streamRef.current?.getAudioTracks().forEach(t => { t.enabled = !next; });
  };

  const fmt = (s) => `${String(Math.floor(s/60)).padStart(2,'0')}:${String(s%60).padStart(2,'0')}`;

  if (callState === 'idle') return null;

  const isRinging = callState === 'ringing';

  // ── Panneau micro selon l'état ────────────────────────────────────────────
  const MicPanel = () => {
    if (micState === 'active') {
      return (
        <div style={{ display:'flex', gap:'0.5rem', justifyContent:'center', marginTop:'0.75rem' }}>
          <button
            onClick={toggleMute}
            style={{
              display:'inline-flex', alignItems:'center', gap:'0.4rem',
              padding:'0.4rem 1rem', borderRadius:99,
              background: isMuted ? '#ef444420' : '#22c55e20',
              border:`1px solid ${isMuted ? '#ef444450' : '#22c55e50'}`,
              color: isMuted ? '#f87171' : '#4ade80',
              fontSize:'0.8rem', fontWeight:600, cursor:'pointer',
            }}
          >
            {isMuted ? <MicOff size={13}/> : <Mic size={13}/>}
            {isMuted ? 'Micro coupé — Cliquer pour activer' : 'Micro actif → jack Pi'}
          </button>
        </div>
      );
    }

    if (micState === 'requesting') {
      return (
        <div style={{ textAlign:'center', marginTop:'0.75rem', color:'#94a3b8', fontSize:'0.8rem' }}>
          <span style={{ animation:'pulse 1s infinite' }}>⏳ En attente de votre autorisation...</span>
        </div>
      );
    }

    if (micState === 'denied') {
      return (
        <div style={{
          margin:'0.75rem 0 0', padding:'0.6rem 0.9rem', borderRadius:10,
          background:'#ef444415', border:'1px solid #ef444440',
          fontSize:'0.75rem', color:'#f87171', textAlign:'center',
        }}>
          🚫 Accès micro refusé.<br/>
          <span style={{color:'#94a3b8'}}>Clique sur l'icône 🔒 dans la barre d'adresse → Autorise le micro</span>
        </div>
      );
    }

    if (micState === 'http_blocked') {
      return (
        <div style={{
          margin:'0.75rem 0 0', padding:'0.75rem', borderRadius:10,
          background:'#78350f20', border:'1px solid #f9731640',
          fontSize:'0.72rem', color:'#fdba74', textAlign:'left', lineHeight:1.7,
        }}>
          <strong>🔒 Micro bloqué (HTTP)</strong><br/>
          Chrome → <code style={{background:'#0f172a', padding:'1px 5px', borderRadius:4}}>
            chrome://flags/#unsafely-treat-insecure-origin-as-secure
          </code><br/>
          → Ajoute <code style={{background:'#0f172a', padding:'1px 5px', borderRadius:4}}>
            http://192.168.137.94
          </code> → Relance Chrome
        </div>
      );
    }

    // idle → bouton d'autorisation
    return (
      <div style={{ textAlign:'center', marginTop:'0.75rem' }}>
        <button
          onClick={requestMic}
          style={{
            display:'inline-flex', alignItems:'center', gap:'0.5rem',
            padding:'0.55rem 1.4rem', borderRadius:99,
            background:'linear-gradient(135deg,#6366f1,#4f46e5)',
            border:'none', color:'#fff',
            fontSize:'0.85rem', fontWeight:600, cursor:'pointer',
            boxShadow:'0 4px 16px rgba(99,102,241,0.45)',
            transition:'transform 0.15s ease',
          }}
          onMouseEnter={e => e.currentTarget.style.transform='scale(1.05)'}
          onMouseLeave={e => e.currentTarget.style.transform='scale(1)'}
        >
          <Mic size={15}/>
          Autoriser le microphone
        </button>
        <div style={{ marginTop:'0.4rem', fontSize:'0.7rem', color:'#475569' }}>
          Votre voix sera transmise sur le jack Pi
        </div>
      </div>
    );
  };

  return (
    <>
      <style>{`
        @keyframes fadeModal { from{opacity:0;transform:scale(0.97)} to{opacity:1;transform:scale(1)} }
        @keyframes wave1 { 0%{transform:scale(1);opacity:.7} 100%{transform:scale(2.4);opacity:0} }
        @keyframes wave2 { 0%{transform:scale(1);opacity:.5} 100%{transform:scale(3.1);opacity:0} }
        @keyframes wave3 { 0%{transform:scale(1);opacity:.3} 100%{transform:scale(3.8);opacity:0} }
        @keyframes phoneBounce {
          0%,100%{transform:rotate(0deg)} 20%{transform:rotate(-14deg)} 40%{transform:rotate(14deg)}
          60%{transform:rotate(-8deg)} 80%{transform:rotate(8deg)}
        }
        @keyframes activeGlow {
          0%,100%{box-shadow:0 0 0 0 rgba(99,102,241,.45)}
          50%    {box-shadow:0 0 0 16px rgba(99,102,241,0)}
        }
        @keyframes recDot { 0%,100%{opacity:1} 50%{opacity:0.2} }
      `}</style>

      {/* Backdrop */}
      <div style={{
        position:'fixed', inset:0, zIndex:9999,
        display:'flex', alignItems:'center', justifyContent:'center',
        background:'rgba(0,0,0,0.85)', backdropFilter:'blur(18px)',
        padding:'1rem',
      }}>

        {/* ══ SONNERIE : modal centrée verticale compact ══ */}
        {isRinging && (
          <div style={{
            background:'linear-gradient(150deg,#0f172a,#1a2540)',
            border:'1px solid rgba(255,255,255,0.12)',
            borderRadius:28, width:340, overflow:'hidden',
            boxShadow:'0 40px 100px rgba(0,0,0,0.85)',
            animation:'fadeModal 0.25s cubic-bezier(0.34,1.56,0.64,1)',
          }}>
            <div style={{ padding:'2.25rem 2rem 2rem', textAlign:'center' }}>

              {/* Avatar + ondes */}
              <div style={{ position:'relative', width:96, height:96, margin:'0 auto 1.5rem' }}>
                {[
                  {anim:'wave1 1.8s ease-out infinite',      color:'rgba(34,197,94,0.22)'},
                  {anim:'wave2 1.8s ease-out .35s infinite', color:'rgba(34,197,94,0.13)'},
                  {anim:'wave3 1.8s ease-out .70s infinite', color:'rgba(34,197,94,0.07)'},
                ].map((w,i) => (
                  <div key={i} style={{ position:'absolute', inset:0, borderRadius:'50%', background:w.color, animation:w.anim }}/>
                ))}
                <div style={{
                  position:'relative', zIndex:1, width:96, height:96, borderRadius:'50%',
                  background:'linear-gradient(135deg,#22c55e,#16a34a)',
                  display:'flex', alignItems:'center', justifyContent:'center',
                  animation:'phoneBounce 0.5s ease-in-out 0s 2',
                  boxShadow:'0 10px 32px rgba(34,197,94,0.55)',
                }}>
                  <Phone size={42} color="#fff"/>
                </div>
              </div>

              <h2 style={{ margin:'0 0 0.3rem', fontSize:'1.3rem', fontWeight:700, color:'#f1f5f9' }}>
                📞 Appel entrant
              </h2>
              <p style={{ margin:'0 0 2rem', color:'#64748b', fontSize:'0.85rem' }}>
                Barrière PI2P — Raspberry Pi
              </p>

              <div style={{ display:'flex', gap:'1.5rem', justifyContent:'center' }}>
                <RoundBtn onClick={answer} color="#22c55e" shadow="rgba(34,197,94,0.55)" label="Décrocher">
                  <Phone size={30}/>
                </RoundBtn>
                <RoundBtn onClick={hangup} color="#ef4444" shadow="rgba(239,68,68,0.5)" label="Refuser">
                  <PhoneOff size={30}/>
                </RoundBtn>
              </div>

              <p style={{ marginTop:'1.5rem', fontSize:'0.7rem', color:'#475569' }}>
                <Volume2 size={11} style={{ verticalAlign:'middle', marginRight:4 }}/>
                Décrochez puis autorisez le microphone pour parler
              </p>
            </div>
          </div>
        )}

        {/* ══ APPEL ACTIF : layout paysage ══ */}
        {!isRinging && (
          <div style={{
            background:'linear-gradient(150deg,#0f172a,#111827)',
            border:'1px solid rgba(255,255,255,0.1)',
            borderRadius:24,
            display:'flex',
            width:'min(900px, 96vw)',
            maxHeight:'85vh',
            overflow:'hidden',
            boxShadow:'0 40px 120px rgba(0,0,0,0.9)',
            animation:'fadeModal 0.3s cubic-bezier(0.34,1.2,0.64,1)',
          }}>

            {/* ── Caméra USB (gauche, ~65%) ── */}
            <div style={{
              flex:'1 1 65%',
              position:'relative',
              background:'#000',
              minHeight:320,
            }}>
              {!camError ? (
                <img
                  src={CAM_USB_URL}
                  alt="Caméra USB"
                  onError={() => setCamError(true)}
                  style={{ width:'100%', height:'100%', objectFit:'cover', display:'block' }}
                />
              ) : (
                <div style={{
                  display:'flex', flexDirection:'column',
                  alignItems:'center', justifyContent:'center',
                  height:'100%', gap:'0.75rem', color:'#475569',
                }}>
                  <Camera size={48}/>
                  <span style={{ fontSize:'0.85rem' }}>Caméra USB hors ligne</span>
                  <button
                    onClick={() => setCamError(false)}
                    style={{ fontSize:'0.78rem', color:'#6366f1', background:'none', border:'none', cursor:'pointer' }}
                  >↻ Réessayer</button>
                </div>
              )}

              {/* Overlay gradient bas */}
              <div style={{
                position:'absolute', bottom:0, left:0, right:0, height:80,
                background:'linear-gradient(to top, rgba(0,0,0,0.7), transparent)',
                pointerEvents:'none',
              }}/>

              {/* Badge durée — haut gauche */}
              <div style={{
                position:'absolute', top:14, left:14,
                background:'rgba(0,0,0,0.7)', borderRadius:10,
                padding:'4px 12px', fontSize:'0.8rem',
                color:'#f1f5f9', display:'flex', alignItems:'center', gap:7,
                backdropFilter:'blur(6px)',
              }}>
                <span style={{
                  width:8, height:8, borderRadius:'50%',
                  background:'#ef4444', boxShadow:'0 0 6px #ef4444',
                  display:'inline-block',
                  animation:'recDot 1.4s infinite',
                }}/>
                <strong>{fmt(callDuration)}</strong>
              </div>

              {/* Badge micro — haut droit */}
              <div style={{
                position:'absolute', top:14, right:14,
                background: micState === 'active'
                  ? (isMuted ? 'rgba(239,68,68,0.85)' : 'rgba(34,197,94,0.85)')
                  : 'rgba(0,0,0,0.6)',
                borderRadius:10, padding:'4px 12px',
                fontSize:'0.75rem', color:'#fff',
                display:'flex', alignItems:'center', gap:5,
                backdropFilter:'blur(6px)',
              }}>
                {micState === 'active'
                  ? (isMuted ? <><MicOff size={12}/> Micro coupé</> : <><Mic size={12}/> Audio → Pi</>)
                  : <><Mic size={12}/> Micro inactif</>
                }
              </div>

              {/* Label cam — bas */}
              <div style={{
                position:'absolute', bottom:12, left:14,
                fontSize:'0.7rem', color:'rgba(255,255,255,0.5)',
              }}>
                📷 WCAM100BK — USB
              </div>
            </div>

            {/* ── Panneau contrôles (droite, ~35%) ── */}
            <div style={{
              flex:'0 0 280px',
              display:'flex', flexDirection:'column',
              padding:'1.75rem 1.5rem',
              borderLeft:'1px solid rgba(255,255,255,0.07)',
              justifyContent:'space-between',
            }}>
              {/* Titre */}
              <div>
                <div style={{ display:'flex', alignItems:'center', gap:'0.6rem', marginBottom:'0.5rem' }}>
                  <div style={{
                    width:36, height:36, borderRadius:'50%',
                    background:'linear-gradient(135deg,#6366f1,#4f46e5)',
                    display:'flex', alignItems:'center', justifyContent:'center',
                    animation:'activeGlow 2s infinite',
                    boxShadow:'0 4px 16px rgba(99,102,241,0.4)',
                    flexShrink:0,
                  }}>
                    <Phone size={16} color="#fff"/>
                  </div>
                  <div>
                    <div style={{ fontSize:'0.95rem', fontWeight:700, color:'#f1f5f9', lineHeight:1.2 }}>
                      En communication
                    </div>
                    <div style={{ fontSize:'0.72rem', color:'#64748b' }}>Barrière PI2P</div>
                  </div>
                </div>
              </div>

              {/* Micro panel */}
              <div style={{ flex:1, display:'flex', flexDirection:'column', justifyContent:'center', gap:'0.75rem' }}>
                <MicPanel />
              </div>

              {/* Boutons d'action */}
              <div style={{ display:'flex', flexDirection:'column', gap:'0.6rem' }}>
                <button
                  onClick={hangup}
                  style={{
                    width:'100%', padding:'0.75rem',
                    borderRadius:12, border:'none',
                    background:'linear-gradient(135deg,#ef4444,#dc2626)',
                    color:'#fff', fontWeight:700, fontSize:'0.9rem',
                    cursor:'pointer', display:'flex', alignItems:'center',
                    justifyContent:'center', gap:'0.5rem',
                    boxShadow:'0 4px 18px rgba(239,68,68,0.45)',
                    transition:'transform 0.15s ease, box-shadow 0.15s ease',
                  }}
                  onMouseEnter={e => { e.currentTarget.style.transform='scale(1.02)'; }}
                  onMouseLeave={e => { e.currentTarget.style.transform='scale(1)'; }}
                >
                  <PhoneOff size={18}/> Raccrocher
                </button>
              </div>
            </div>
          </div>
        )}

      </div>
    </>
  );
}


function RoundBtn({ onClick, color, shadow, label, children, outline = false }) {
  const [hover, setHover] = useState(false);
  return (
    <div style={{display:'flex', flexDirection:'column', alignItems:'center', gap:'0.4rem'}}>
      <button
        onClick={onClick}
        onMouseEnter={() => setHover(true)}
        onMouseLeave={() => setHover(false)}
        title={label}
        style={{
          width:70, height:70, borderRadius:'50%',
          border: outline ? `2px solid ${color}` : 'none',
          background: outline
            ? (hover ? `${color}25` : `${color}12`)
            : `linear-gradient(135deg, ${color}, ${color}bb)`,
          color: outline ? color : '#fff',
          cursor:'pointer',
          display:'flex', alignItems:'center', justifyContent:'center',
          boxShadow: hover ? `0 8px 28px ${shadow}` : `0 4px 14px ${shadow}70`,
          transform: hover ? 'scale(1.1)' : 'scale(1)',
          transition:'all 0.15s ease',
        }}
      >
        {children}
      </button>
      <span style={{fontSize:'0.68rem', color:'#64748b'}}>{label}</span>
    </div>
  );
}
