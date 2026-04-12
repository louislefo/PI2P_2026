import React, { useState, useRef } from 'react';
import { DoorOpen, PhoneCall, BarChart3, Clock, Camera, Maximize, RefreshCcw } from 'lucide-react';
import { isAuthorized, formatDate } from '../../utils/helpers';

export default function DashboardView({ 
  status, history, plates, openDoor, API_BASE, setCurrentView 
}) {
  const [videoError, setVideoError] = useState(false);
  const [activeCam, setActiveCam] = useState('CAM_01_IN');
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

  const switchCamera = () => {
    setActiveCam(prev => prev === 'CAM_01_IN' ? 'CAM_02_OUT' : 'CAM_01_IN');
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

      {/* ─── Video & Side Controls ─── */}
      <div className="video-and-controls">
        
        {/* Video Section */}
        <div className="video-section">
          <div className="video-frame" ref={videoRef}>
            {!videoError && (
              <img
                src={`${API_BASE}/video_feed?cam=${activeCam}`}
                alt={`Flux ${activeCam} + OCR`}
                onError={() => setVideoError(true)}
              />
            )}

            {/* LIVE Badge */}
            {!videoError && (
              <div className="video-overlay-badge">
                <span className="live-dot"></span>
                <span>En Direct // {activeCam}</span>
              </div>
            )}

            {/* Switch Camera Button (Top Right) */}
            {!videoError && (
              <div className="video-overlay-top-right">
                <button className="glass-btn" title="Changer de caméra" onClick={switchCamera}>
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
          <button className="side-ctrl-btn barrier" onClick={openDoor}>
            <DoorOpen size={32} />
            <span>Ouvrir Barrière</span>
            <span className="btn-sublabel">Manuel</span>
          </button>

          <button className="side-ctrl-btn call" title="Appel Gardien">
            <PhoneCall size={28} />
            <span>Appel SOS</span>
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
