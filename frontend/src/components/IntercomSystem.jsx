import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Phone, PhoneOff, Mic, MicOff, Volume2 } from 'lucide-react';

const HW_WS_BASE = 'ws://192.168.137.94:8083';

/**
 * Système d'interphone complet :
 * - Écoute le WebSocket /ws/call pour les événements d'appel
 * - Affiche une modal quand le bouton Pi est pressé
 * - Au décroché : capture le micro PC et stream l'audio via /ws/audio vers le jack Pi
 */
export default function IntercomSystem() {
  const [callState, setCallState] = useState('idle'); // idle | ringing | active
  const [isMuted, setIsMuted] = useState(false);
  const [callDuration, setCallDuration] = useState(0);

  const callWsRef   = useRef(null);
  const audioWsRef  = useRef(null);
  const audioCtxRef = useRef(null);
  const processorRef = useRef(null);
  const streamRef    = useRef(null);
  const timerRef     = useRef(null);
  const durationRef  = useRef(0);

  // ── Connexion WebSocket events d'appel ──────────────────────────────────────
  useEffect(() => {
    let ws;
    let retryTimer;

    const connect = () => {
      ws = new WebSocket(`${HW_WS_BASE}/ws/call`);
      callWsRef.current = ws;

      ws.onopen = () => {
        console.log('📡 [INTERCOM] WebSocket call connecté');
      };

      ws.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data);
          console.log('📞 [INTERCOM] Event:', msg);

          if (msg.event === 'incoming_call') {
            setCallState('ringing');
            // Bip sonore dans le navigateur pour alerter l'opérateur
            _playRingTone();
          } else if (msg.event === 'call_ended') {
            _hangup(false); // false = ne pas renvoyer hangup au ws (évite boucle)
          }
        } catch (err) {
          console.error('[INTERCOM] Parse error:', err);
        }
      };

      ws.onclose = () => {
        console.log('📴 [INTERCOM] WS fermé — reconnexion dans 3s');
        retryTimer = setTimeout(connect, 3000);
      };

      ws.onerror = () => ws.close();
    };

    connect();
    return () => {
      clearTimeout(retryTimer);
      ws?.close();
    };
  }, []);

  // ── Sonnerie navigateur (Web Audio API) ─────────────────────────────────────
  const _playRingTone = () => {
    try {
      const ctx = new AudioContext();
      const play = (freq, start, dur) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.frequency.value = freq;
        gain.gain.setValueAtTime(0.3, ctx.currentTime + start);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + start + dur);
        osc.start(ctx.currentTime + start);
        osc.stop(ctx.currentTime + start + dur);
      };
      // Mélodie d'appel
      play(880, 0, 0.15); play(1100, 0.2, 0.15); play(880, 0.4, 0.15); play(1100, 0.6, 0.2);
      setTimeout(() => ctx.close(), 1500);
    } catch (e) {
      console.warn('[INTERCOM] Pas de son navigateur:', e);
    }
  };

  // ── Démarrer l'audio streaming PC → Pi ─────────────────────────────────────
  const _startAudioStream = useCallback(async () => {
    try {
      // 1. Obtenir le micro
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true,
        }
      });
      streamRef.current = stream;

      // 2. Ouvrir le WebSocket audio
      const audioWs = new WebSocket(`${HW_WS_BASE}/ws/audio`);
      audioWs.binaryType = 'arraybuffer';
      audioWsRef.current = audioWs;

      await new Promise((resolve, reject) => {
        audioWs.onopen  = resolve;
        audioWs.onerror = reject;
        setTimeout(reject, 5000);
      });
      console.log('🎙️ [INTERCOM] WebSocket audio ouvert');

      // 3. Capturer le PCM et envoyer
      const audioCtx = new AudioContext({ sampleRate: 16000 });
      audioCtxRef.current = audioCtx;

      const source = audioCtx.createMediaStreamSource(stream);
      // ScriptProcessor : 4096 samples par chunk à 16000Hz ≈ 256ms de latence
      const processor = audioCtx.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;

      processor.onaudioprocess = (e) => {
        if (audioWs.readyState !== WebSocket.OPEN) return;
        if (isMuted) return; // micro muet → on envoie quand même du silence

        const float32 = e.inputBuffer.getChannelData(0);
        // Convertir Float32 → Int16 (format attendu par aplay S16_LE)
        const int16 = new Int16Array(float32.length);
        for (let i = 0; i < float32.length; i++) {
          int16[i] = Math.max(-32768, Math.min(32767, Math.round(float32[i] * 32767)));
        }
        audioWs.send(int16.buffer);
      };

      source.connect(processor);
      processor.connect(audioCtx.destination);

      console.log('✅ [INTERCOM] Streaming audio démarré (16kHz, mono, S16_LE)');
    } catch (err) {
      console.error('[INTERCOM] Erreur démarrage audio:', err);
      alert(`Impossible d'accéder au microphone : ${err.message}`);
    }
  }, [isMuted]);

  // ── Arrêter l'audio streaming ───────────────────────────────────────────────
  const _stopAudioStream = useCallback(() => {
    processorRef.current?.disconnect();
    processorRef.current = null;
    audioCtxRef.current?.close();
    audioCtxRef.current = null;
    streamRef.current?.getTracks().forEach(t => t.stop());
    streamRef.current = null;
    audioWsRef.current?.close();
    audioWsRef.current = null;
    console.log('🛑 [INTERCOM] Streaming audio arrêté');
  }, []);

  // ── Décrocher ──────────────────────────────────────────────────────────────
  const answer = useCallback(async () => {
    setCallState('active');
    durationRef.current = 0;
    setCallDuration(0);
    timerRef.current = setInterval(() => {
      durationRef.current += 1;
      setCallDuration(durationRef.current);
    }, 1000);
    await _startAudioStream();
  }, [_startAudioStream]);

  // ── Raccrocher ─────────────────────────────────────────────────────────────
  const _hangup = useCallback((notifyWs = true) => {
    setCallState('idle');
    clearInterval(timerRef.current);
    setCallDuration(0);
    _stopAudioStream();
    if (notifyWs && callWsRef.current?.readyState === WebSocket.OPEN) {
      callWsRef.current.send(JSON.stringify({ action: 'hangup' }));
    }
    console.log('📴 [INTERCOM] Appel terminé');
  }, [_stopAudioStream]);

  const hangup = useCallback(() => _hangup(true), [_hangup]);

  // ── Mute ───────────────────────────────────────────────────────────────────
  const toggleMute = () => {
    setIsMuted(m => !m);
    if (streamRef.current) {
      streamRef.current.getAudioTracks().forEach(t => {
        t.enabled = isMuted; // inverse car setIsMuted est async
      });
    }
  };

  // ── Format durée ───────────────────────────────────────────────────────────
  const fmtDuration = (s) => `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;

  // ── Rien à afficher si pas d'appel ─────────────────────────────────────────
  if (callState === 'idle') return null;

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 9999,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'rgba(0, 0, 0, 0.75)',
      backdropFilter: 'blur(12px)',
      animation: 'fadeIn 0.2s ease',
    }}>
      <style>{`
        @keyframes fadeIn { from { opacity: 0 } to { opacity: 1 } }
        @keyframes ring { 
          0%, 100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(34,197,94,0.6); }
          50% { transform: scale(1.05); box-shadow: 0 0 0 20px rgba(34,197,94,0); }
        }
        @keyframes pulse-active {
          0%, 100% { box-shadow: 0 0 0 0 rgba(99,102,241,0.5); }
          50% { box-shadow: 0 0 0 12px rgba(99,102,241,0); }
        }
      `}</style>

      <div style={{
        background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)',
        border: '1px solid rgba(255,255,255,0.12)',
        borderRadius: 24,
        padding: '2.5rem 2rem',
        width: 340,
        textAlign: 'center',
        boxShadow: '0 25px 60px rgba(0,0,0,0.6)',
      }}>
        {/* Avatar */}
        <div style={{
          width: 90, height: 90, borderRadius: '50%', margin: '0 auto 1.25rem',
          background: callState === 'ringing'
            ? 'linear-gradient(135deg, #22c55e, #16a34a)'
            : 'linear-gradient(135deg, #6366f1, #4f46e5)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          animation: callState === 'ringing' ? 'ring 1s infinite' : 'pulse-active 2s infinite',
        }}>
          <Phone size={38} color="#fff" />
        </div>

        {/* Titre */}
        <h2 style={{ margin: '0 0 0.25rem', fontSize: '1.3rem', fontWeight: 700, color: '#f1f5f9' }}>
          {callState === 'ringing' ? '🔔 Appel entrant' : '📞 Appel en cours'}
        </h2>

        {/* Sous-titre */}
        <p style={{ margin: '0 0 0.5rem', color: '#94a3b8', fontSize: '0.875rem' }}>
          {callState === 'ringing' ? 'Barrière PI2P — Raspberry Pi' : `Durée : ${fmtDuration(callDuration)}`}
        </p>

        {callState === 'active' && (
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: '0.4rem',
            padding: '0.2rem 0.75rem', borderRadius: 99,
            background: isMuted ? '#ef444420' : '#22c55e20',
            border: `1px solid ${isMuted ? '#ef444450' : '#22c55e50'}`,
            color: isMuted ? '#f87171' : '#4ade80',
            fontSize: '0.75rem', fontWeight: 600, marginBottom: '0.25rem',
          }}>
            {isMuted ? <MicOff size={12} /> : <Mic size={12} />}
            {isMuted ? 'Micro coupé' : 'Micro actif — audio → jack Pi'}
          </div>
        )}

        {callState === 'ringing' && (
          <p style={{ margin: '0.25rem 0 0', color: '#64748b', fontSize: '0.75rem' }}>
            Audio du PC → Jack 3.5mm Pi
          </p>
        )}

        {/* Boutons */}
        <div style={{
          display: 'flex', gap: '1rem', justifyContent: 'center',
          marginTop: '2rem',
        }}>
          {/* Décrocher (sonnerie) ou Mute (actif) */}
          {callState === 'ringing' ? (
            <button
              onClick={answer}
              style={{
                width: 68, height: 68, borderRadius: '50%', border: 'none',
                background: 'linear-gradient(135deg, #22c55e, #16a34a)',
                color: '#fff', cursor: 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                boxShadow: '0 4px 20px rgba(34,197,94,0.5)',
                transition: 'transform 0.15s ease',
              }}
              onMouseEnter={e => e.currentTarget.style.transform = 'scale(1.1)'}
              onMouseLeave={e => e.currentTarget.style.transform = 'scale(1)'}
            >
              <Phone size={28} />
            </button>
          ) : (
            <button
              onClick={toggleMute}
              title={isMuted ? 'Réactiver le micro' : 'Couper le micro'}
              style={{
                width: 68, height: 68, borderRadius: '50%', border: 'none',
                background: isMuted ? 'rgba(239,68,68,0.2)' : 'rgba(99,102,241,0.2)',
                border: `2px solid ${isMuted ? '#ef4444' : '#6366f1'}`,
                color: isMuted ? '#ef4444' : '#6366f1', cursor: 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                transition: 'all 0.15s ease',
              }}
            >
              {isMuted ? <MicOff size={26} /> : <Mic size={26} />}
            </button>
          )}

          {/* Raccrocher */}
          <button
            onClick={hangup}
            style={{
              width: 68, height: 68, borderRadius: '50%', border: 'none',
              background: 'linear-gradient(135deg, #ef4444, #dc2626)',
              color: '#fff', cursor: 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              boxShadow: '0 4px 20px rgba(239,68,68,0.4)',
              transition: 'transform 0.15s ease',
            }}
            onMouseEnter={e => e.currentTarget.style.transform = 'scale(1.1)'}
            onMouseLeave={e => e.currentTarget.style.transform = 'scale(1)'}
          >
            <PhoneOff size={28} />
          </button>
        </div>

        {/* Info */}
        {callState === 'ringing' && (
          <p style={{ marginTop: '1.5rem', fontSize: '0.7rem', color: '#475569' }}>
            <Volume2 size={11} style={{ verticalAlign: 'middle', marginRight: 4 }} />
            En décrochant, votre micro est envoyé sur le jack du Pi
          </p>
        )}
      </div>
    </div>
  );
}
