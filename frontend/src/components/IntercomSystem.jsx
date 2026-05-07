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
  const [micError, setMicError]     = useState(null);
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
              setMicError(null);
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

  // ── Audio streaming PC → Jack Pi ──────────────────────────────────────────
  const _startAudioStream = useCallback(async () => {
    if (!navigator.mediaDevices?.getUserMedia) {
      setMicError(window.location.protocol === 'http:' ? 'http_blocked' : 'unavailable');
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, sampleRate: 16000, echoCancellation: true, noiseSuppression: true }
      });
      streamRef.current = stream;

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
        const f32  = e.inputBuffer.getChannelData(0);
        const i16  = new Int16Array(f32.length);
        const gain = isMuted ? 0 : 1;
        for (let i = 0; i < f32.length; i++) {
          i16[i] = Math.max(-32768, Math.min(32767, Math.round(f32[i] * 32767 * gain)));
        }
        audioWs.send(i16.buffer);
      };
      source.connect(proc);
      proc.connect(audioCtx.destination);
    } catch (err) {
      setMicError(err.name === 'NotAllowedError' ? 'denied' : 'error');
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

  const answer = useCallback(async () => {
    stopRingRef.current?.();
    stopRingRef.current = null;
    setCallState('active');
    durationRef.current = 0;
    setCallDuration(0);
    timerRef.current = setInterval(() => {
      durationRef.current += 1;
      setCallDuration(durationRef.current);
    }, 1000);
    await _startAudioStream();
  }, [_startAudioStream]);

  const _hangup = useCallback((notifyWs = true) => {
    stopRingRef.current?.();
    stopRingRef.current = null;
    setCallState('idle');
    setMicError(null);
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

  return (
    <>
      <style>{`
        @keyframes fadeModal { from{opacity:0;transform:scale(0.94)} to{opacity:1;transform:scale(1)} }
        @keyframes wave1 { 0%{transform:scale(1);opacity:.7} 100%{transform:scale(2.4);opacity:0} }
        @keyframes wave2 { 0%{transform:scale(1);opacity:.5} 100%{transform:scale(3.0);opacity:0} }
        @keyframes wave3 { 0%{transform:scale(1);opacity:.3} 100%{transform:scale(3.6);opacity:0} }
        @keyframes phoneBounce {
          0%,100%{transform:rotate(0deg)} 20%{transform:rotate(-12deg)} 40%{transform:rotate(12deg)}
          60%{transform:rotate(-8deg)} 80%{transform:rotate(8deg)}
        }
        @keyframes activeGlow {
          0%,100%{box-shadow:0 0 0 0 rgba(99,102,241,.4)}
          50%    {box-shadow:0 0 0 14px rgba(99,102,241,0)}
        }
      `}</style>

      {/* Backdrop */}
      <div style={{
        position:'fixed', inset:0, zIndex:9999,
        display:'flex', alignItems:'center', justifyContent:'center',
        background:'rgba(0,0,0,0.82)', backdropFilter:'blur(16px)',
      }}>
        <div style={{
          background:'linear-gradient(150deg,#0f172a,#1a2540)',
          border:'1px solid rgba(255,255,255,0.1)',
          borderRadius:28,
          width: isRinging ? 340 : 400,
          overflow:'hidden',
          boxShadow:'0 40px 100px rgba(0,0,0,0.8)',
          animation:'fadeModal 0.25s cubic-bezier(0.34,1.56,0.64,1)',
        }}>

          {/* ── Caméra USB (appel actif seulement) ── */}
          {!isRinging && (
            <div style={{ position:'relative', background:'#000', aspectRatio:'16/9' }}>
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
                  height:200, gap:'0.5rem', color:'#475569',
                }}>
                  <Camera size={36} />
                  <span style={{fontSize:'0.8rem'}}>Caméra USB hors ligne</span>
                  <button
                    onClick={() => setCamError(false)}
                    style={{fontSize:'0.75rem',color:'#6366f1',background:'none',border:'none',cursor:'pointer'}}
                  >↻ Réessayer</button>
                </div>
              )}

              {/* Badge durée */}
              <div style={{
                position:'absolute', top:10, left:12,
                background:'rgba(0,0,0,0.65)', borderRadius:8,
                padding:'3px 10px', fontSize:'0.75rem',
                color:'#f1f5f9', display:'flex', alignItems:'center', gap:6,
              }}>
                <span style={{
                  width:7, height:7, borderRadius:'50%',
                  background:'#ef4444', boxShadow:'0 0 5px #ef4444',
                  display:'inline-block',
                }}/>
                {fmt(callDuration)}
              </div>

              {/* Badge micro */}
              <div style={{
                position:'absolute', top:10, right:12,
                background: isMuted ? 'rgba(239,68,68,0.85)' : 'rgba(99,102,241,0.85)',
                borderRadius:8, padding:'3px 10px',
                fontSize:'0.72rem', color:'#fff',
                display:'flex', alignItems:'center', gap:5,
              }}>
                {isMuted ? <MicOff size={11}/> : <Mic size={11}/>}
                {isMuted ? 'Micro coupé' : 'Audio → Pi'}
              </div>
            </div>
          )}

          {/* ── Corps de la modal ── */}
          <div style={{ padding:'1.75rem 1.75rem 2rem', textAlign:'center' }}>

            {/* Avatar + ondes (sonnerie) */}
            <div style={{ position:'relative', width:90, height:90, margin:'0 auto 1.25rem' }}>
              {isRinging && [
                {anim:'wave1 1.8s ease-out infinite',   color:'rgba(34,197,94,0.2)'},
                {anim:'wave2 1.8s ease-out .35s infinite', color:'rgba(34,197,94,0.13)'},
                {anim:'wave3 1.8s ease-out .7s infinite',  color:'rgba(34,197,94,0.07)'},
              ].map((w,i) => (
                <div key={i} style={{
                  position:'absolute', inset:0, borderRadius:'50%',
                  background:w.color, animation:w.anim,
                }}/>
              ))}

              <div style={{
                position:'relative', zIndex:1,
                width:90, height:90, borderRadius:'50%',
                background: isRinging
                  ? 'linear-gradient(135deg,#22c55e,#16a34a)'
                  : 'linear-gradient(135deg,#6366f1,#4f46e5)',
                display:'flex', alignItems:'center', justifyContent:'center',
                animation: isRinging
                  ? 'phoneBounce 0.5s ease-in-out 0s 2' // rebond au démarrage
                  : 'activeGlow 2s infinite',
                boxShadow: isRinging
                  ? '0 8px 30px rgba(34,197,94,0.5)'
                  : '0 8px 30px rgba(99,102,241,0.45)',
              }}>
                <Phone size={38} color="#fff" />
              </div>
            </div>

            {/* Titre */}
            <h2 style={{margin:'0 0 0.25rem', fontSize:'1.25rem', fontWeight:700, color:'#f1f5f9'}}>
              {isRinging ? '📞 Appel entrant' : 'En communication'}
            </h2>
            <p style={{margin:0, color:'#64748b', fontSize:'0.85rem'}}>
              Barrière PI2P — Raspberry Pi
            </p>

            {/* Erreur micro */}
            {micError && (
              <div style={{
                margin:'1rem 0 0', padding:'0.75rem', borderRadius:10,
                background:'#7c341520', border:'1px solid #f9731640',
                fontSize:'0.73rem', color:'#fdba74', textAlign:'left', lineHeight:1.7,
              }}>
                {micError === 'http_blocked' ? <>
                  <strong>🔒 Micro bloqué (HTTP)</strong><br/>
                  Chrome → <code style={{background:'#0f172a',padding:'1px 4px',borderRadius:4}}>
                    chrome://flags/#unsafely-treat-insecure-origin-as-secure
                  </code><br/>
                  → Ajoute <code style={{background:'#0f172a',padding:'1px 4px',borderRadius:4}}>
                    http://192.168.137.94
                  </code> → Relance Chrome
                </> : micError === 'denied'
                  ? '🚫 Accès micro refusé dans le navigateur.'
                  : '❌ Micro indisponible.'}
              </div>
            )}

            {/* Boutons */}
            <div style={{display:'flex', gap:'1.5rem', justifyContent:'center', marginTop:'1.75rem'}}>
              {isRinging ? (
                <RoundBtn onClick={answer} color="#22c55e" shadow="rgba(34,197,94,0.5)" label="Décrocher">
                  <Phone size={30}/>
                </RoundBtn>
              ) : (
                <RoundBtn
                  onClick={toggleMute}
                  color={isMuted ? '#ef4444' : '#6366f1'}
                  shadow={isMuted ? 'rgba(239,68,68,.4)' : 'rgba(99,102,241,.4)'}
                  label={isMuted ? 'Activer micro' : 'Muter'}
                  outline
                >
                  {isMuted ? <MicOff size={26}/> : <Mic size={26}/>}
                </RoundBtn>
              )}

              <RoundBtn onClick={hangup} color="#ef4444" shadow="rgba(239,68,68,0.5)" label="Raccrocher">
                <PhoneOff size={30}/>
              </RoundBtn>
            </div>

            {isRinging && (
              <p style={{marginTop:'1.25rem', fontSize:'0.7rem', color:'#475569'}}>
                <Volume2 size={11} style={{verticalAlign:'middle', marginRight:4}}/>
                Votre voix sera transmise sur le haut-parleur Pi (jack 3.5mm)
              </p>
            )}
          </div>
        </div>
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
