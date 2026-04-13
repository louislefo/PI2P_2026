import React, { useState, useRef } from 'react';
import { Search, Plus, Trash2, Database, User, Mail, Calendar, Upload, Download, FileText } from 'lucide-react';
import { formatDate } from '../../utils/helpers';

export default function DatabaseView({ plates, addPlate, deletePlate, API_BASE, refreshPlates }) {
  const [searchQuery, setSearchQuery] = useState('');
  const [activeFilter, setActiveFilter] = useState('all'); // 'all' | 'active' | 'expired'
  const [importStatus, setImportStatus] = useState(null); // { type: 'success'|'error', message: '' }
  const fileInputRef = useRef(null);

  // Nouveau state pour le formulaire
  const [formData, setFormData] = useState({
    plate: '',
    owner_name: '',
    email: '',
    valid_until: ''
  });

  // Filter logic
  const filteredPlates = plates.filter(p => {
    // Text search
    const matchesSearch =
      p.plate.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (p.owner_name && p.owner_name.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (p.email && p.email.toLowerCase().includes(searchQuery.toLowerCase()));

    // Status filter
    const isExpired = p.valid_until && new Date(p.valid_until) < new Date();
    if (activeFilter === 'active') return matchesSearch && !isExpired;
    if (activeFilter === 'expired') return matchesSearch && isExpired;
    return matchesSearch;
  });

  const handleAdd = async (e) => {
    e.preventDefault();
    const success = await addPlate(formData);
    if (success) {
      setFormData({ plate: '', owner_name: '', email: '', valid_until: '' });
    }
  };

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  // CSV Import
  const handleImportCSV = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const form = new FormData();
    form.append('file', file);

    try {
      const resp = await fetch(`${API_BASE}/api/config/plates/import-csv`, {
        method: 'POST',
        body: form
      });
      const data = await resp.json();

      if (data.status === 'success') {
        setImportStatus({
          type: 'success',
          message: `${data.imported} plaque(s) importée(s) avec succès.`
        });
        // Refresh plates list from server
        if (refreshPlates) refreshPlates();
      } else {
        setImportStatus({ type: 'error', message: 'Erreur lors de l\'import.' });
      }
    } catch (err) {
      console.error(err);
      setImportStatus({ type: 'error', message: 'Impossible de contacter le serveur.' });
    }

    // Reset file input
    if (fileInputRef.current) fileInputRef.current.value = '';

    // Auto-clear status after 5s
    setTimeout(() => setImportStatus(null), 5000);
  };

  // CSV Template Download
  const handleDownloadTemplate = () => {
    window.open(`${API_BASE}/api/config/plates/template-csv`, '_blank');
  };

  // Count stats
  const expiredCount = plates.filter(p => p.valid_until && new Date(p.valid_until) < new Date()).length;
  const activeCount = plates.length - expiredCount;

  return (
    <div className="view-container">
      <div className="view-header">
        <h1 className="view-title">Base de Données</h1>
        <p className="view-subtitle">Répertoire des Accès Autorisés</p>
      </div>

      {/* Search + Filters + CSV actions */}
      <div className="db-actions">
        <div className="search-input-wrapper">
          <Search size={18} />
          <input
            type="text"
            className="search-input"
            placeholder="Rechercher une plaque, nom ou email..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        
        <div className="db-filter-chips">
          <button
            className={`filter-chip ${activeFilter === 'all' ? 'active' : ''}`}
            onClick={() => setActiveFilter('all')}
          >
            Tous ({plates.length})
          </button>
          <button
            className={`filter-chip ${activeFilter === 'active' ? 'active' : ''}`}
            onClick={() => setActiveFilter('active')}
          >
            Actifs ({activeCount})
          </button>
          <button
            className={`filter-chip ${activeFilter === 'expired' ? 'active' : ''}`}
            onClick={() => setActiveFilter('expired')}
          >
            Expirés ({expiredCount})
          </button>
        </div> 
      </div>

      {/* CSV Actions Bar */}
      <div className="csv-actions">
        <button className="csv-btn" onClick={handleDownloadTemplate} title="Télécharger le modèle CSV">
          <Download size={16} />
          <span>Modèle CSV</span>
        </button>
        <button className="csv-btn import" onClick={() => fileInputRef.current?.click()} title="Importer un fichier CSV">
          <Upload size={16} />
          <span>Importer CSV</span>
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv"
          onChange={handleImportCSV}
          style={{ display: 'none' }}
        />
        {importStatus && (
          <span className={`import-status ${importStatus.type}`}>
            {importStatus.message}
          </span>
        )}
      </div>

      <form className="add-auth-form" onSubmit={handleAdd}>
        <h3 className="form-title">Nouvelle Autorisation</h3>
        <div className="form-row">
          <div className="form-group">
            <label>Plaque d'Immatriculation*</label>
            <input type="text" name="plate" value={formData.plate} onChange={handleChange} placeholder="EX: WW-123-AA" required />
          </div>
          <div className="form-group">
            <label><User size={14}/> Propriétaire (Optionnel)</label>
            <input type="text" name="owner_name" value={formData.owner_name} onChange={handleChange} placeholder="Nom Complet" />
          </div>
          <div className="form-group">
            <label><Mail size={14}/> Contact (Optionnel)</label>
            <input type="email" name="email" value={formData.email} onChange={handleChange} placeholder="email@domaine.com" />
          </div>
          <div className="form-group">
            <label><Calendar size={14}/> Fin Validité (Optionnel)</label>
            <input type="date" name="valid_until" value={formData.valid_until} onChange={handleChange} />
          </div>
          <div className="form-group btn-group">
            <button type="submit" className="add-btn full-width">
              <Plus size={18} />
              Ajouter
            </button>
          </div>
        </div>
      </form>
        
      <div className="db-stats">
          {/*
        <div className="db-stat">
          <span className="db-stat-label">Total</span>
          <span className="db-stat-value">{plates.length}</span>
        </div>
        <div className="db-stat">
          <span className="db-stat-label">Actifs</span>
          <span className="db-stat-value">{activeCount}</span>
        </div>
        <div className="db-stat">
          <span className="db-stat-label">Expirés</span>
          <span className="db-stat-value">{expiredCount}</span>
        </div> */}
      </div> 

      <div className="plates-table expanded">
        <div className="table-header">
          <span>Plaque d'Immatriculation</span>
          <span>Propriétaire</span>
          <span>Date d'Ajout</span>
          <span>Valide Jusqu'à</span>
          <span>Actions</span>
        </div>

        {filteredPlates.length === 0 ? (
          <div className="empty-state">
            <Database size={32} />
            <p>
              {searchQuery || activeFilter !== 'all'
                ? 'Aucun résultat correspondant.'
                : 'Aucun véhicule enregistré.'}
            </p>
          </div>
        ) : (
          filteredPlates.map((item) => {
            const isExpired = item.valid_until && new Date(item.valid_until) < new Date();
            return (
              <div key={item.plate} className={`table-row ${isExpired ? 'expired-row' : ''}`}>
                <div className="plate-text">
                  <div className={`plate-indicator ${isExpired ? 'expired' : ''}`}></div>
                  {item.plate}
                </div>
                <div className="owner-text">
                  {item.owner_name ? (
                    <>
                      <strong>{item.owner_name}</strong>
                      {item.email && <span className="owner-email">{item.email}</span>}
                    </>
                  ) : <span className="text-muted">—</span>}
                </div>
                <span className="plate-date">{item.created_at ? formatDate(item.created_at) : '—'}</span>
                <span className={`plate-date ${isExpired ? 'text-error' : ''}`}>
                  {item.valid_until ? formatDate(item.valid_until) : 'Toujours'}
                </span>
                <button
                  className="delete-btn"
                  onClick={() => deletePlate(item.plate)}
                  title="Supprimer"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
