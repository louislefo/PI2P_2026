import React from 'react';
import { LayoutDashboard, Database, ScrollText, Settings, PanelLeftOpen, PanelLeftClose, AlertTriangle, Shield } from 'lucide-react';

const navItems = [
  { id: 'dashboard', label: 'Tableau de Bord', icon: LayoutDashboard },
  { id: 'database', label: 'Base de Données', icon: Database },
  { id: 'logs', label: "Journal d'Activité", icon: ScrollText },
];

export default function Sidebar({ currentView, setCurrentView, collapsed, setCollapsed }) {
  return (
    <aside className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
      {/* Logo / Title */}
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <img src="/ESILV_LOGO.png" alt="ESILV Logo" style={{ width: '28px', height: '28px', objectFit: 'contain' }} />
        </div>
        <div className="sidebar-title">
          <h1>IA Parking</h1>
          <span>ESILV (Mr Zanette)</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="sidebar-nav">
        {navItems.map(item => (
          <button
            key={item.id}
            className={`nav-item ${currentView === item.id ? 'active' : ''}`}
            onClick={() => setCurrentView(item.id)}
            title={collapsed ? item.label : undefined}
          >
            <item.icon className="nav-icon" size={20} />
            <span className="nav-label">{item.label}</span>
          </button>
        ))}
      </nav>

      {/* Footer */}
      <div className="sidebar-footer">
        <button
          className={`nav-item ${currentView === 'settings' ? 'active' : ''}`}
          onClick={() => setCurrentView('settings')}
          title={collapsed ? 'Paramètres' : undefined}
        >
          <Settings className="nav-icon" size={20} />
          <span className="nav-label">Paramètres</span>
        </button>

        <button
          className="sidebar-toggle"
          onClick={() => setCollapsed(!collapsed)}
        >
          {collapsed
            ? <PanelLeftOpen size={18} />
            : <><PanelLeftClose size={18} /><span className="nav-label">Réduire</span></>
          }
        </button>

        <button className="emergency-btn" title="Arrêt d'Urgence">
          <AlertTriangle size={18} />
          <span className="emergency-label">Arrêt d'Urgence</span>
        </button>
      </div>
    </aside>
  );
}
