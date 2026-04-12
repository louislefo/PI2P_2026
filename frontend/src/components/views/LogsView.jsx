import React from 'react';
import { ScrollText } from 'lucide-react';
import { isAuthorized, formatDate } from '../../utils/helpers';

export default function LogsView({ history }) {
  const authorizedCount = history.filter(h => isAuthorized(h.status)).length;
  const authRate = history.length > 0 ? Math.round((authorizedCount / history.length) * 100) : 100;

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
          history.map((item, index) => (
            <div key={index} className="log-item">
              <div className="log-left">
                <span className="log-plate">{item.plate}</span>
                <span className={`activity-status-chip ${isAuthorized(item.status) ? 'authorized' : 'denied'}`}>
                  {isAuthorized(item.status) ? 'Autorisé' : 'Refusé'}
                </span>
              </div>
              <div className="log-right">
                <span className="log-time">{formatDate(item.time)}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
