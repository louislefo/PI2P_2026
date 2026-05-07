import React, { useState, useEffect } from 'react';
import { 
  Lightbulb, Zap, Volume2, Camera, Activity, 
  RotateCcw, Power, CheckCircle, XCircle, AlertCircle
} from 'lucide-react';

const HW_BASE = 'http://192.168.137.94:8083';
const CAM_CSI = 'http://192.168.137.94:8081/stream';
const CAM_USB = 'http://192.168.137.94:8082/stream';

// ── Composant carte générique ──────────────────────────────────────────────
function TestCard({ title, icon: Icon, children, accent = '#6366f1' }) {
  return (
    <div style={{
      background: 'rgba(255,255,255,0.04)',
      border: '1px solid rgba(255,255,255,0.1)',
      borderRadius: 16,
      padding: '1.5rem',
      backdropFilter: 'blur(10px)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.25rem' }}>
        <div style={{
          width: 36, height: 36, borderRadius: 10,
          background: `${accent}25`,
          border: `1px solid ${accent}50`,
          display: 'flex', alignItems: 'center', justifyContent: 'center'
        }}>
          <Icon size={18} color={accent} />
        </div>
        <h2 style={{ margin: 0, fontSize: '1rem', fontWeight: 600, color: '#f1f5f9' }}>{title}</h2>
      </div>
      {children}
    </div>
  );
}

// ── Indicateur de connexion ────────────────────────────────────────────────
function ConnectionBadge({ online }) {
  return (
    <div style={{
      display: 'inline-flex', alignItems: 'center', gap: '0.4rem',
      padding: '0.25rem 0.75rem', borderRadius: 999,
      background: online ? '#16a34a20' : '#dc262620',
      border: `1px solid ${online ? '#16a34a50' : '#dc262650'}`,
      fontSize: '0.75rem', color: online ? '#4ade80' : '#f87171',
      fontWeight: 500,
    }}>
      <span style={{
        width: 7, height: 7, borderRadius: '50%',
        background: online ? '#4ade80' : '#f87171',
        boxShadow: online ? '0 0 6px #4ade80' : '0 0 6px #f87171',
      }} />
      {online ? 'Connecté' : 'Hors ligne'}
    </div>
  );
}

// ── Bouton action générique ────────────────────────────────────────────────
function ActionBtn({ onClick, disabled, color = '#6366f1', children, fullWidth = false, size = 'md' }) {
  const [pressed, setPressed] = useState(false);
  const pad = size === 'sm' ? '0.4rem 0.9rem' : '0.6rem 1.2rem';
  const fs = size === 'sm' ? '0.8rem' : '0.875rem';

  return (
    <button
      disabled={disabled}
      onClick={async () => {
        setPressed(true);
        await onClick?.();
        setTimeout(() => setPressed(false), 300);
      }}
      style={{
        padding: pad, borderRadius: 10, border: `1px solid ${color}50`,
        background: pressed ? color : `${color}20`,
        color: pressed ? '#fff' : color,
        fontWeight: 600, fontSize: fs, cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.5 : 1,
        transition: 'all 0.15s ease',
        width: fullWidth ? '100%' : undefined,
        display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: '0.4rem',
      }}
    >
      {children}
    </button>
  );
}

// ──────────────────────────────────────────────────────────────────────────
export default function TestView() {
  const [hwStatus, setHwStatus] = useState(null);
  const [hwOnline, setHwOnline] = useState(false);
  const [leds, setLeds] = useState({ green: false, orange: false, red: false });
  const [servoAngle, setServoAngle] = useState(0);
  const [audioLog, setAudioLog] = useState([]);
  const [camCsiError, setCamCsiError] = useState(false);
  const [camUsbError, setCamUsbError] = useState(false);
  const [loading, setLoading] = useState({});

  // ── Polling status ───────────────────────────────────────────────────────
  useEffect(() => {
    const poll = async () => {
      try {
        const r = await fetch(`${HW_BASE}/status`, { signal: AbortSignal.timeout(2000) });
        if (r.ok) {
          const d = await r.json();
          setHwStatus(d);
          setHwOnline(true);
          setLeds(d.leds);
          setServoAngle(d.servo.angle);
        }
      } catch {
        setHwOnline(false);
      }
    };
    poll();
    const id = setInterval(poll, 2000);
    return () => clearInterval(id);
  }, []);

  // ── Actions ──────────────────────────────────────────────────────────────
  const setLoad = (key, val) => setLoading(p => ({ ...p, [key]: val }));

  const toggleLed = async (color) => {
    setLoad(`led_${color}`, true);
    try {
      const r = await fetch(`${HW_BASE}/led/${color}/toggle`, { method: 'POST' });
      if (r.ok) {
        const d = await r.json();
        setLeds(p => ({ ...p, [color]: d.state === 'on' }));
      }
    } catch (e) {
      console.error(e);
    }
    setLoad(`led_${color}`, false);
  };

  const allLedsOff = async () => {
    for (const c of ['green', 'orange', 'red']) {
      await fetch(`${HW_BASE}/led/${c}/off`, { method: 'POST' }).catch(() => {});
    }
    setLeds({ green: false, orange: false, red: false });
  };

  const moveSevo = async (angle) => {
    setLoad('servo', true);
    try {
      await fetch(`${HW_BASE}/servo/${angle}`, { method: 'POST' });
      setServoAngle(angle);
    } catch (e) { console.error(e); }
    setLoad('servo', false);
  };

  const openBarrier = () => moveSevo(90);
  const closeBarrier = () => moveSevo(0);

  const playAudio = async (pattern) => {
    setLoad(`audio_${pattern}`, true);
    try {
      const r = await fetch(`${HW_BASE}/audio/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pattern, freq: 880, duration: 0.4 }),
      });
      if (r.ok) {
        const now = new Date().toLocaleTimeString('fr-FR');
        setAudioLog(p => [`${now} — Pattern: ${pattern}`, ...p].slice(0, 5));
      }
    } catch (e) { console.error(e); }
    setLoad(`audio_${pattern}`, false);
  };

  // ── LED Config ───────────────────────────────────────────────────────────
  const LED_CONFIG = [
    { key: 'green',  label: 'Verte',  pin: 'BCM27', color: '#22c55e', glow: '#22c55e' },
    { key: 'orange', label: 'Orange', pin: 'BCM17', color: '#f97316', glow: '#f97316' },
    { key: 'red',    label: 'Rouge',  pin: 'BCM22', color: '#ef4444', glow: '#ef4444' },
  ];

  const AUDIO_PATTERNS = [
    { key: 'single',  label: '1 Bip',     emoji: '🔔' },
    { key: 'double',  label: '2 Bips',    emoji: '🔔🔔' },
    { key: 'success', label: 'Succès',    emoji: '✅' },
    { key: 'error',   label: 'Erreur',    emoji: '❌' },
  ];

  return (
    <div style={{ padding: '1rem', maxWidth: 1200, margin: '0 auto' }}>

      {/* ── Header ── */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '0.75rem' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '1.5rem', fontWeight: 700, color: '#f1f5f9' }}>
            🔧 Panneau de Test Hardware
          </h1>
          <p style={{ margin: '0.25rem 0 0', color: '#94a3b8', fontSize: '0.875rem' }}>
            Raspberry Pi · http://192.168.137.94
          </p>
        </div>
        <ConnectionBadge online={hwOnline} />
      </div>

      {/* ── Grid ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '1rem' }}>

        {/* ── Caméras ── */}
        <div style={{ gridColumn: '1 / -1' }}>
          <TestCard title="Flux Caméras en Direct" icon={Camera} accent="#06b6d4">
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
              {[
                { label: 'CSI — OV5647 (nappe)', url: CAM_CSI, error: camCsiError, setError: setCamCsiError },
                { label: 'USB — WCAM100BK', url: CAM_USB, error: camUsbError, setError: setCamUsbError },
              ].map(({ label, url, error, setError }) => (
                <div key={label} style={{ position: 'relative', borderRadius: 10, overflow: 'hidden', background: '#0f172a', aspectRatio: '16/9' }}>
                  {!error ? (
                    <>
                      <img
                        src={url}
                        alt={label}
                        onError={() => setError(true)}
                        style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
                      />
                      <div style={{
                        position: 'absolute', top: 8, left: 8,
                        background: 'rgba(0,0,0,0.6)', borderRadius: 6,
                        padding: '2px 8px', fontSize: '0.7rem', color: '#e2e8f0',
                        display: 'flex', alignItems: 'center', gap: 4,
                      }}>
                        <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#4ade80', boxShadow: '0 0 4px #4ade80' }} />
                        {label}
                      </div>
                    </>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: '0.5rem', color: '#64748b' }}>
                      <Camera size={32} />
                      <span style={{ fontSize: '0.75rem' }}>{label} — Hors ligne</span>
                      <button onClick={() => setError(false)} style={{ fontSize: '0.7rem', color: '#06b6d4', background: 'none', border: 'none', cursor: 'pointer' }}>
                        ↻ Réessayer
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </TestCard>
        </div>

        {/* ── LEDs ── */}
        <TestCard title="Contrôle LEDs" icon={Lightbulb} accent="#eab308">
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {LED_CONFIG.map(({ key, label, pin, color, glow }) => (
              <div key={key} style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '0.75rem 1rem', borderRadius: 10,
                background: leds[key] ? `${color}15` : 'rgba(255,255,255,0.03)',
                border: `1px solid ${leds[key] ? `${color}40` : 'rgba(255,255,255,0.07)'}`,
                transition: 'all 0.2s ease',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  {/* LED visuelle */}
                  <div style={{
                    width: 20, height: 20, borderRadius: '50%',
                    background: leds[key] ? color : '#1e293b',
                    boxShadow: leds[key] ? `0 0 12px ${glow}, 0 0 24px ${glow}50` : 'none',
                    border: `2px solid ${leds[key] ? color : '#334155'}`,
                    transition: 'all 0.2s ease',
                  }} />
                  <div>
                    <div style={{ fontSize: '0.875rem', fontWeight: 600, color: '#e2e8f0' }}>LED {label}</div>
                    <div style={{ fontSize: '0.7rem', color: '#64748b' }}>Pin {pin}</div>
                  </div>
                </div>
                <ActionBtn
                  onClick={() => toggleLed(key)}
                  disabled={!hwOnline || loading[`led_${key}`]}
                  color={leds[key] ? color : '#475569'}
                >
                  <Power size={14} />
                  {leds[key] ? 'Éteindre' : 'Allumer'}
                </ActionBtn>
              </div>
            ))}
            <ActionBtn onClick={allLedsOff} disabled={!hwOnline} color="#ef4444" fullWidth>
              <XCircle size={14} /> Tout éteindre
            </ActionBtn>
          </div>
        </TestCard>

        {/* ── Servomoteur ── */}
        <TestCard title="Servomoteur — Barrière" icon={Zap} accent="#8b5cf6">
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {/* Visualisation servo */}
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '3rem', fontWeight: 700, color: '#8b5cf6', lineHeight: 1 }}>
                {servoAngle}°
              </div>
              <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.25rem' }}>
                BCM12 / PWM0 — Board pin 32
              </div>
            </div>

            {/* Barre de progression */}
            <div style={{ position: 'relative', height: 8, borderRadius: 99, background: '#1e293b' }}>
              <div style={{
                height: '100%', borderRadius: 99,
                background: 'linear-gradient(90deg, #8b5cf6, #6366f1)',
                width: `${(servoAngle / 180) * 100}%`,
                transition: 'width 0.3s ease',
                boxShadow: '0 0 8px #8b5cf680',
              }} />
            </div>

            {/* Slider */}
            <input
              type="range" min={0} max={180} step={5}
              value={servoAngle}
              onChange={e => setServoAngle(Number(e.target.value))}
              onMouseUp={e => moveSevo(Number(e.target.value))}
              onTouchEnd={e => moveSevo(Number(e.target.value))}
              disabled={!hwOnline}
              style={{ width: '100%', accentColor: '#8b5cf6', cursor: hwOnline ? 'pointer' : 'not-allowed' }}
            />

            {/* Presets */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
              <ActionBtn onClick={closeBarrier} disabled={!hwOnline} color="#ef4444" fullWidth>
                🚧 Fermer (0°)
              </ActionBtn>
              <ActionBtn onClick={openBarrier} disabled={!hwOnline} color="#22c55e" fullWidth>
                ✅ Ouvrir (90°)
              </ActionBtn>
              <ActionBtn onClick={() => moveSevo(45)} disabled={!hwOnline} color="#f97316" fullWidth size="sm">
                45°
              </ActionBtn>
              <ActionBtn onClick={() => moveSevo(180)} disabled={!hwOnline} color="#06b6d4" fullWidth size="sm">
                180° (Max)
              </ActionBtn>
            </div>
          </div>
        </TestCard>

        {/* ── Audio ── */}
        <TestCard title="Test Haut-parleur (Jack 3.5mm)" icon={Volume2} accent="#10b981">
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
              {AUDIO_PATTERNS.map(({ key, label, emoji }) => (
                <ActionBtn
                  key={key}
                  onClick={() => playAudio(key)}
                  disabled={!hwOnline || loading[`audio_${key}`]}
                  color="#10b981"
                  fullWidth
                >
                  {loading[`audio_${key}`] ? <Activity size={14} /> : emoji} {label}
                </ActionBtn>
              ))}
            </div>

            {/* Log audio */}
            <div style={{
              marginTop: '0.5rem', padding: '0.75rem', borderRadius: 8,
              background: '#0f172a', border: '1px solid rgba(255,255,255,0.06)',
              minHeight: 80, fontFamily: 'monospace', fontSize: '0.72rem', color: '#64748b',
            }}>
              {audioLog.length === 0
                ? <span style={{ color: '#334155' }}>— Aucun test lancé —</span>
                : audioLog.map((l, i) => <div key={i} style={{ color: i === 0 ? '#4ade80' : '#475569' }}>› {l}</div>)
              }
            </div>

            <div style={{ fontSize: '0.7rem', color: '#475569', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <AlertCircle size={12} />
              Assure-toi que la sortie audio du Pi est configurée sur le jack (raspi-config → Audio → Force jack)
            </div>
          </div>
        </TestCard>

        {/* ── Status JSON ── */}
        <TestCard title="État Brut Hardware Bridge" icon={Activity} accent="#64748b">
          <pre style={{
            margin: 0, fontSize: '0.72rem', color: '#94a3b8',
            background: '#0f172a', borderRadius: 8,
            padding: '0.75rem', overflow: 'auto', maxHeight: 200,
          }}>
            {hwStatus ? JSON.stringify(hwStatus, null, 2) : hwOnline ? 'Chargement...' : 'Hardware bridge hors ligne\nVérifier : docker logs pi2p_2026-hardware-bridge-1'}
          </pre>
        </TestCard>

      </div>
    </div>
  );
}
