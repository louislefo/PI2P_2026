import React, { useState, useRef } from 'react';
import { DoorOpen, PhoneCall, BarChart3, Clock, Camera, Maximize, RefreshCcw, AlertCircle } from 'lucide-react';
import { isAuthorized, formatDate } from '../../utils/helpers';

export default function DashboardView({ 
  status, history, plates, openDoor, API_BASE, config, setCurrentView 
}) {
  const [videoError, setVideoError] = useState(false);
  const [activeCam, setActiveCam] = useState('CAM_01_IN');
  const [streamKey, setStreamKey] = useState(Date.now());
  const inactiveCam = activeCam === 'CAM_01_IN' ? 'CAM_02_OUT' : 'CAM_01_IN';
  const videoRef = useRef(null);

  const authorizedCount = history.filter(h => isAuthorized(h.status)).length;
  const authRate = history.length > 0 ? Math.round((authorizedCount / history.length) * 100) : 100;

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      videoRef.current?.requestFullscreen().catch(err => {
        console.error(`Erreur plein écran: ${err.message}`);
      });
    } else {
      document.exitFullscreen();
    }
  };

  const refreshStream = () => {
    setStreamKey(Date.now());
  };

  const startCall = () => {
    if (window.startDirectCall) {
      window.startDirectCall();
    } else {
      console.warn("L'interphone n'est pas prêt.");
    }
  };

  return (
    <>
      {/* ─── Status Banner ─── */}
      <div className="status-banner">
        <div className="status-main">
          <span className="status-label">État Actuel</span>
        </div>
        <div className={`portal-badge ${status.door_open ? 'open' : 'closed'}`}>
          <DoorOpen size={16} />
          {status.door_open ? 'Portail Ouvert' : 'Portail Fermé'}
        </div>
      </div>

      {/* ─── Mode Barrière Banner ─── */}
      <div style={{
        backgroundColor: config?.gate_mode === 'always_open' ? '#f59e0b' : config?.gate_mode === 'always_closed' ? '#ef4444' : '#3b82f6',
        color: 'white',
        padding: '0.5rem 1rem',
        borderRadius: '8px',
        marginBottom: '1rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontWeight: 'bold',
        gap: '8px',
        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
      }}>
        {config?.gate_mode === 'always_open' ? 'MODE OUVERTURE PERMANENTE (Force Ouvert)' : 
         config?.gate_mode === 'always_closed' ? 'MODE BLOCAGE PERMANENT (Force Fermé)' : 
         'MODE AUTOMATIQUE (IA Activée)'}
      </div>

      {/* ─── Video & Side Controls ─── */}
      <div className="video-and-controls">
        
        {/* Video Section */}
        <div className="video-section">
          <div className="video-frame" ref={videoRef}>
            {!videoError && (
              <img
                src={`${API_BASE}/video_feed?cam=${activeCam}&t=${streamKey}`}
                alt={`Flux ${activeCam} + OCR`}
                onError={() => setVideoError(true)}
              />
            )}

            {/* PiP Inactive Cam */}
            {!videoError && (
              <div 
                className="pip-camera" 
                onClick={() => setActiveCam(inactiveCam)}
                title="Basculer vers cette caméra"
                style={{
                  position: 'absolute',
                  bottom: '16px',
                  left: '16px',
                  width: '180px',
                  height: '135px',
                  border: '2px solid rgba(255,255,255,0.5)',
                  borderRadius: '8px',
                  overflow: 'hidden',
                  cursor: 'pointer',
                  boxShadow: '0 4px 10px rgba(0,0,0,0.5)',
                  zIndex: 10,
                  transition: 'border-color 0.2s',
                  backgroundColor: 'black'
                }}
                onMouseEnter={(e) => e.currentTarget.style.borderColor = 'white'}
                onMouseLeave={(e) => e.currentTarget.style.borderColor = 'rgba(255,255,255,0.5)'}
              >
                <img 
                  src={`${API_BASE}/video_feed?cam=${inactiveCam}&t=${streamKey}`} 
                  style={{ width: '100%', height: '100%', objectFit: 'cover' }} 
                  alt="Caméra secondaire"
                />
              </div>
            )}

            {/* LIVE Badge */}
            {!videoError && (
              <div className="video-overlay-badge">
                <span className="live-dot"></span>
                <span>En Direct // {activeCam}</span>
              </div>
            )}

            {/* Refresh Button (Top Right) */}
            {!videoError && (
              <div className="video-overlay-top-right">
                <button className="glass-btn" title="Rafraîchir les flux" onClick={refreshStream}>
                  <RefreshCcw size={18} />
                </button>
              </div>
            )}

            {/* Fullscreen Button (Bottom Right) */}
            {!videoError && (
              <div className="video-overlay-bottom-right">
                <button className="glass-btn" title="Plein écran" onClick={toggleFullscreen}>
                  <Maximize size={18} />
                </button>
              </div>
            )}

            {/* Offline state fallback */}
            {videoError && (
              <div className="video-offline">
                <Camera size={48} />
                <p>Flux vidéo hors ligne. Démarrez le serveur (uvicorn).</p>
              </div>
            )}
          </div>
        </div>

        {/* Side Controls (Right of Video) */}
        <div className="side-controls">
          <button 
            className={`side-ctrl-btn barrier ${status.door_open ? 'open' : ''}`} 
            onClick={openDoor}
            style={status.door_open ? { backgroundColor: 'rgba(34, 197, 94, 0.2)', borderColor: '#22c55e' } : {}}
          >
            <DoorOpen size={32} color={status.door_open ? '#22c55e' : 'white'} />
            <span style={{ color: status.door_open ? '#22c55e' : 'white' }}>
              {status.door_open ? 'Barrière Ouverte' : 'Ouvrir Barrière'}
            </span>
            <span className="btn-sublabel">Manuel</span>
          </button>

          <button className="side-ctrl-btn call" title="Appel" onClick={startCall}>
            <PhoneCall size={28} />
            <span>Appel</span>
          </button>
        </div>
      </div>

      {/* ─── Bottom Panels ─── */}
      <div className="bottom-panels">
        {/* Stats Panel */}
        <div className="stats-panel">
          <div className="panel-header">
            <h2 className="panel-title">
              <BarChart3 size={20} />
              Statistiques
            </h2>
          </div>
          <div>
            <div className="stat-row">
              <span className="stat-label">Entrées Totales</span>
              <span className="stat-value highlight">{history.length}</span>
            </div>
            <div className="stat-row" style={{ marginTop: '0.5rem', marginBottom: '0.5rem' }}>
              <span className="stat-label">Véhicules Analysés</span>
              <span className="stat-value" style={{ color: '#60a5fa' }}>{status.tested_cars || 0}</span>
            </div>
            <div className="stat-bar">
              <div className="stat-bar-fill" style={{ width: `${authRate}%` }}></div>
            </div>
            <div className="stat-row">
              <span className="stat-label">Taux d'Autorisation</span>
              <span className="stat-value">{authRate}%</span>
            </div>
            <div className="stat-row">
              <span className="stat-label">Plaques Enregistrées</span>
              <span className="stat-value">{plates.length}</span>
            </div>
          </div>
        </div>

        {/* Activity Panel */}
        <div className="activity-panel">
          <div className="panel-header">
            <h2 className="panel-title">
              <Clock size={20} />
              Activité Récente
            </h2>
            <button
              className="view-all-link"
              onClick={() => setCurrentView('logs')}
            >
              Tout Voir
            </button>
          </div>
          <div className="activity-list">
            {history.length === 0 ? (
              <div className="empty-state">
                <Clock size={32} />
                <p>Aucune activité récente.</p>
              </div>
            ) : (
              history.slice(0, 5).map((item, index) => (
                <div key={index} className="activity-item">
                  <div className="activity-item-left">
                    <span className="activity-plate">{item.plate}</span>
                    <span className={`activity-status-chip ${isAuthorized(item.status) ? 'authorized' : 'denied'}`}>
                      {isAuthorized(item.status) ? 'Autorisé' : 'Refusé'}
                    </span>
                  </div>
                  <span className="activity-time">{formatDate(item.time)}</span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </>
  );
}
