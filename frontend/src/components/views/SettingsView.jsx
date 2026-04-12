import React, { useState, useEffect } from 'react';
import { Settings2, KeyRound, Lock, Unlock, Zap, Save, Shield } from 'lucide-react';

export default function SettingsView({ config, setConfig, API_BASE }) {
  // Extraction des valeurs de la config avec fallbacks
  const initialCode = config.entry_code || '0000#';
  const initialMode = config.gate_mode || 'auto';
  const initialDetection = config.detection_objects || ['car'];

  // États locaux du formulaire (Source de vérité locale)
  const [localCode, setLocalCode] = useState(initialCode);
  const [localMode, setLocalMode] = useState(initialMode);
  const [localDetection, setLocalDetection] = useState(initialDetection);
  const [savedStatus, setSavedStatus] = useState('');

  // Synchronisation si la config change (ex: fetch initial)
  useEffect(() => {
    setLocalCode(config.entry_code || '0000#');
    setLocalMode(config.gate_mode || 'auto');
    setLocalDetection(config.detection_objects || ['car']);
  }, [config]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSavedStatus('Enregistrement...');
    
    try {
      const payload = {
        entry_code: localCode,
        gate_mode: localMode,
        detection_objects: localDetection
      };

      const resp = await fetch(`${API_BASE}/api/config/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await resp.json();
      if (data.status === 'success') {
        // MAJ de l'état global de l'App uniquement après succès
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
              <input 
                type="text" 
                value={localCode} 
                onChange={(e) => setLocalCode(e.target.value)} 
                placeholder="Ex: 0302#"
                className="pin-input"
              />
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
                { id: 'car', label: 'Voitures', icon: '🚗', locked: true },
                { id: 'truck', label: 'Camions', icon: '🚛' },
                { id: 'motorcycle', label: 'Motos', icon: '🏍️' },
                { id: 'bicycle', label: 'Vélos', icon: '🚲' },
                { id: 'person', label: 'Personnes', icon: '🚶' },
                { id: 'dog', label: 'Chiens', icon: '🐕' },
                { id: 'cat', label: 'Chats', icon: '🐈' }
              ].map(obj => {
                const isSelected = localDetection.includes(obj.id);
                return (
                  <div 
                    key={obj.id} 
                    className={`detection-item ${isSelected ? 'selected' : ''} ${obj.locked ? 'locked' : ''}`}
                    onClick={() => toggleDetection(obj.id, obj.locked)}
                  >
                    <span className="obj-icon">{obj.icon}</span>
                    <span className="obj-label">{obj.label}</span>
                  </div>
                );
              })}
            </div>
          </section>

          <div className="settings-footer">
            <span className={`save-status ${savedStatus.includes('Erreur') ? 'error' : ''}`}>{savedStatus}</span>
            <button type="submit" className="save-btn">
              <Save size={18} />
              Enregistrer les modifications
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
