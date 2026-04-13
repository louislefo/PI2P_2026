import React, { useState } from 'react';
import { ScrollText, Camera, Trash2, Image, X, User } from 'lucide-react';
import { isAuthorized, formatDate } from '../../utils/helpers';

export default function LogsView({ history, plates, API_BASE, deleteLog }) {
  const [selectedImage, setSelectedImage] = useState(null);
  const authorizedCount = history.filter(h => isAuthorized(h.status)).length;
  const authRate = history.length > 0 ? Math.round((authorizedCount / history.length) * 100) : 100;

  // Lookup driver info from plates list by matching plate number
  const getDriverInfo = (plate) => {
    if (!plates || !plate) return null;
    return plates.find(p => p.plate.replace(/[\s-]/g, '').toUpperCase() === plate.replace(/[\s-]/g, '').toUpperCase());
  };

  return (
    <div className="view-container">
      <div className="view-header">
        <h1 className="view-title">Journal d'Activité</h1>
        <p className="view-subtitle">Historique Complet des Passages</p>
      </div>

      <div className="db-stats">
        <div className="db-stat">
          <span className="db-stat-label">Total Passages</span>
          <span className="db-stat-value">{history.length}</span>
        </div>
        <div className="db-stat">
          <span className="db-stat-label">Autorisés</span>
          <span className="db-stat-value">{authorizedCount}</span>
        </div>
        <div className="db-stat">
          <span className="db-stat-label">Taux</span>
          <span className="db-stat-value">{authRate}%</span>
        </div>
      </div>

      <div className="logs-list">
        {history.length === 0 ? (
          <div className="empty-state">
            <ScrollText size={32} />
            <p>Aucune entrée dans le journal.</p>
          </div>
        ) : (
          history.map((item, index) => {
            const driver = getDriverInfo(item.plate);
            return (
              <div key={index} className="log-item">
                <div className="log-left">
                  {item.image_filename ? (
                    <button 
                      className="log-image-btn" 
                      onClick={() => setSelectedImage(`${API_BASE}/api/images/${item.image_filename}`)}
                      title="Voir la capture"
                    >
                      <Image size={18} />
                    </button>
                  ) : (
                    <div className="log-image-btn empty">
                      <Camera size={18} />
                    </div>
                  )}
                  <div className="log-info">
                    <div className="log-plate">{item.plate}</div>
                    {driver && driver.owner_name && (
                      <>
                        <div className="log-divider"></div>
                        <div className="log-driver">
                          <User size={12} />
                          <span className="log-driver-name">{driver.owner_name}</span>
                          {driver.email && <span className="log-driver-email">{driver.email}</span>}
                        </div>
                      </>
                    )}
                  </div>
                  <span className={`activity-status-chip ${isAuthorized(item.status) ? 'authorized' : 'denied'}`}>
                    {isAuthorized(item.status) ? 'Autorisé' : 'Refusé'}
                  </span>
                </div>
                <div className="log-right">
                  <span className="log-time">{formatDate(item.time)}</span>
                  <button 
                    className="delete-log-btn" 
                    onClick={() => deleteLog(item.id)}
                    title="Supprimer ce log"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Image Modal */}
      {selectedImage && (
        <div className="image-modal-overlay" onClick={() => setSelectedImage(null)}>
          <div className="image-modal-content" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Capture de Passage</h3>
              <button className="close-modal-icon" onClick={() => setSelectedImage(null)}>
                <X size={20} />
              </button>
            </div>
            <div className="modal-body">
              <img src={selectedImage} alt="Agrandissement capture" />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
