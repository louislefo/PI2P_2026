import React, { useState, useEffect } from 'react';
import { Settings2, KeyRound, Lock, Unlock, Zap, Save, Shield, Eye, EyeOff, Camera, Check } from 'lucide-react';

export default function SettingsView({ config, setConfig, API_BASE }) {
  // Extraction des valeurs de la config avec fallbacks
  const initialCode = config.entry_code || '0000#';
  const initialMode = config.gate_mode || 'auto';
  const initialGateOpenTime = config.gate_open_time || 5;
  const initialDetection = config.detection_objects || ['car'];
  const initialVisionCamera = config.vision_camera || 'CSI';

  // États locaux du formulaire
  const [localCode, setLocalCode] = useState(initialCode);
  const [localMode, setLocalMode] = useState(initialMode);
  const [localGateOpenTime, setLocalGateOpenTime] = useState(initialGateOpenTime);
  const [localDetection, setLocalDetection] = useState(initialDetection);
  const [localVisionCamera, setLocalVisionCamera] = useState(initialVisionCamera);
  
  const [showCode, setShowCode] = useState(false);
  const [savedStatus, setSavedStatus] = useState('');

  // Synchronisation si la config change
  useEffect(() => {
    setLocalCode(config.entry_code || '0000#');
    setLocalMode(config.gate_mode || 'auto');
    setLocalGateOpenTime(config.gate_open_time || 5);
    setLocalDetection(config.detection_objects || ['car']);
    setLocalVisionCamera(config.vision_camera || 'CSI');
  }, [config]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSavedStatus('Enregistrement...');
    
    try {
      const payload = {
        entry_code: localCode,
        gate_mode: localMode,
        gate_open_time: parseInt(localGateOpenTime, 10),
        detection_objects: localDetection,
        vision_camera: localVisionCamera
      };

      const resp = await fetch(`${API_BASE}/api/config/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await resp.json();
      if (data.status === 'success') {
        setConfig(data.settings); 
        setSavedStatus('Paramètres sauvegardés avec succès !');
        setTimeout(() => setSavedStatus(''), 3000);
      } else {
        setSavedStatus('Erreur serveur.');
      }
    } catch (err) {
      console.error(err);
      setSavedStatus('Erreur de connexion.');
    }
  };

  const toggleDetection = (id, locked) => {
    if (locked) return;
    setLocalDetection(prev => 
      prev.includes(id) ? prev.filter(item => item !== id) : [...prev, id]
    );
  };

  return (
    <div className="view-container">
      <div className="view-header">
        <h1 className="view-title">Paramètres Système</h1>
        <p className="view-subtitle">Contrôle manuel et configuration matérielle</p>
      </div>

      <div className="settings-content">
        <form onSubmit={handleSubmit} className="settings-form">
          {/* Section Mode Barrière */}
          <section className="settings-section">
            <div className="section-header">
              <Zap size={20} className="section-icon" />
              <h2>Surcharge de la Barrière</h2>
            </div>
            <p className="section-desc">Basculez le mode pour forcer l'état physique du portail.</p>
            
            <div className="mode-cards">
              <label className={`mode-card ${localMode === 'auto' ? 'active' : ''}`}>
                <input type="radio" value="auto" checked={localMode === 'auto'} onChange={(e)=>setLocalMode(e.target.value)} />
                <div className="mode-content">
                  <div className="mode-icon"><Settings2 size={24}/></div>
                  <div className="mode-text">
                    <strong>Automatique (IA)</strong>
                    <span>La barrière réagit aux plaques et se referme seule.</span>
                  </div>
                </div>
              </label>

              <label className={`mode-card ${localMode === 'always_open' ? 'active open' : ''}`}>
                <input type="radio" value="always_open" checked={localMode === 'always_open'} onChange={(e)=>setLocalMode(e.target.value)} />
                <div className="mode-content">
                  <div className="mode-icon"><Unlock size={24}/></div>
                  <div className="mode-text">
                    <strong>Ouverture Permanente</strong>
                    <span>La barrière s'ouvre et reste bloquée en haut.</span>
                  </div>
                </div>
              </label>

              <label className={`mode-card ${localMode === 'always_closed' ? 'active closed' : ''}`}>
                <input type="radio" value="always_closed" checked={localMode === 'always_closed'} onChange={(e)=>setLocalMode(e.target.value)} />
                <div className="mode-content">
                  <div className="mode-icon"><Lock size={24}/></div>
                  <div className="mode-text">
                    <strong>Blocage Permanent</strong>
                    <span>Ignore toutes les plaques et boutons réseau.</span>
                  </div>
                </div>
              </label>
            </div>
          </section>

          {/* Section Code */}
          <section className="settings-section">
            <div className="section-header">
              <KeyRound size={20} className="section-icon" />
              <h2>Code d'Entrée Physique</h2>
            </div>
            <div className="form-group pin-group">
              <label>PIN d'accès</label>
              <div className="pin-input-wrapper">
                <input 
                  type={showCode ? "text" : "password"} 
                  value={localCode} 
                  onChange={(e) => setLocalCode(e.target.value)} 
                  placeholder="Ex: 0302#"
                  className="pin-input"
                />
                <button 
                  type="button" 
                  className="pin-toggle"
                  onClick={() => setShowCode(!showCode)}
                  title={showCode ? "Masquer" : "Afficher"}
                >
                  {showCode ? <EyeOff size={20} /> : <Eye size={20} />}
                </button>
              </div>
            </div>

            <div className="form-group" style={{ marginTop: '1.5rem' }}>
              <label>Temps d'ouverture (secondes)</label>
              <input 
                type="number" 
                min="1"
                max="60"
                value={localGateOpenTime} 
                onChange={(e) => setLocalGateOpenTime(e.target.value)} 
                style={{ 
                  width: '120px', textAlign: 'center', fontSize: '1.2rem', padding: '0.5rem', 
                  borderRadius: '8px', border: '1px solid rgba(255,255,255,0.2)', 
                  background: 'rgba(255,255,255,0.1)', color: '#f8fafc', fontWeight: 'bold' 
                }}
              />
            </div>
          </section>

          {/* Section Caméra */}
          <section className="settings-section" style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '16px', padding: '1.5rem', marginBottom: '1.5rem' }}>
            <div className="section-header" style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
              <div style={{ padding: '8px', background: 'rgba(6, 182, 212, 0.2)', borderRadius: '10px' }}>
                <Camera size={20} color="#06b6d4" />
              </div>
              <h2 style={{ margin: 0, fontSize: '1.1rem', color: '#f8fafc' }}>Caméra d'Analyse IA</h2>
            </div>
            <p style={{ color: '#94a3b8', fontSize: '0.85rem', marginBottom: '1.5rem' }}>
              Choisissez la caméra utilisée par YOLO et EasyOCR pour détecter les véhicules et lire les plaques.
            </p>
            
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <label style={{ 
                position: 'relative', cursor: 'pointer', padding: '1.25rem', borderRadius: '12px',
                border: localVisionCamera === 'CSI' ? '2px solid #06b6d4' : '1px solid rgba(255,255,255,0.1)',
                background: localVisionCamera === 'CSI' ? 'rgba(6, 182, 212, 0.1)' : 'rgba(0,0,0,0.2)',
                transition: 'all 0.2s'
              }}>
                <input type="radio" value="CSI" checked={localVisionCamera === 'CSI'} onChange={(e)=>setLocalVisionCamera(e.target.value)} style={{ display: 'none' }} />
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                  <strong style={{ color: localVisionCamera === 'CSI' ? '#06b6d4' : '#e2e8f0', fontSize: '1.1rem' }}>Caméra CSI</strong>
                  {localVisionCamera === 'CSI' && <Check size={20} color="#06b6d4" />}
                </div>
                <div style={{ color: '#94a3b8', fontSize: '0.8rem' }}>Module officiel OV5647 (Nappe)</div>
              </label>

              <label style={{ 
                position: 'relative', cursor: 'pointer', padding: '1.25rem', borderRadius: '12px',
                border: localVisionCamera === 'USB' ? '2px solid #06b6d4' : '1px solid rgba(255,255,255,0.1)',
                background: localVisionCamera === 'USB' ? 'rgba(6, 182, 212, 0.1)' : 'rgba(0,0,0,0.2)',
                transition: 'all 0.2s'
              }}>
                <input type="radio" value="USB" checked={localVisionCamera === 'USB'} onChange={(e)=>setLocalVisionCamera(e.target.value)} style={{ display: 'none' }} />
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                  <strong style={{ color: localVisionCamera === 'USB' ? '#06b6d4' : '#e2e8f0', fontSize: '1.1rem' }}>Caméra USB</strong>
                  {localVisionCamera === 'USB' && <Check size={20} color="#06b6d4" />}
                </div>
                <div style={{ color: '#94a3b8', fontSize: '0.8rem' }}>Webcam WCAM100BK</div>
              </label>
            </div>
          </section>

          {/* Section Objets de Détection */}
          <section className="settings-section">
            <div className="section-header">
              <Shield size={20} className="section-icon" />
              <h2>Objets à Détecter</h2>
            </div>
            <div className="detection-grid">
              {[
                { id: 'car', label: 'Voitures', locked: true },
                { id: 'truck', label: 'Camions' },
                { id: 'motorcycle', label: 'Motos' },
                { id: 'bicycle', label: 'Vélos' },
                { id: 'person', label: 'Personnes' },
                { id: 'dog', label: 'Chiens' },
                { id: 'cat', label: 'Chats' }
              ].map(obj => {
                const isSelected = localDetection.includes(obj.id);
                return (
                  <div 
                    key={obj.id} 
                    className={`detection-item ${isSelected ? 'selected' : ''} ${obj.locked ? 'locked' : ''}`}
                    onClick={() => toggleDetection(obj.id, obj.locked)}
                  >
                    <span className="obj-label">{obj.label}</span>
                  </div>
                );
              })}
            </div>
          </section>

          <div style={{
            paddingTop: '1.5rem', paddingBottom: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            borderTop: '1px solid rgba(255,255,255,0.05)', marginTop: '2rem'
          }}>
            <span style={{
              color: savedStatus.includes('Erreur') ? '#ef4444' : '#22c55e', 
              fontSize: '0.9rem', fontWeight: 500, opacity: savedStatus ? 1 : 0, transition: 'opacity 0.3s'
            }}>
              {savedStatus || 'Prêt'}
            </span>
            <button type="submit" style={{
              display: 'flex', alignItems: 'center', gap: '0.5rem', background: '#6366f1', color: 'white',
              border: 'none', padding: '0.75rem 1.5rem', borderRadius: '8px', fontSize: '1rem', fontWeight: 600,
              cursor: 'pointer', boxShadow: '0 4px 12px rgba(99, 102, 241, 0.3)', transition: 'background 0.2s'
            }} onMouseEnter={e => e.currentTarget.style.background = '#4f46e5'} onMouseLeave={e => e.currentTarget.style.background = '#6366f1'}>
              <Save size={18} />
              Enregistrer les modifications
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
