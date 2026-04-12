import React, { useState } from 'react';
import { Search, Plus, Trash2, Database, User, Mail, Calendar } from 'lucide-react';
import { formatDate } from '../../utils/helpers';

export default function DatabaseView({ plates, addPlate, deletePlate }) {
  const [searchQuery, setSearchQuery] = useState('');
  
  // Nouveau state pour le formulaire
  const [formData, setFormData] = useState({
    plate: '',
    owner_name: '',
    email: '',
    valid_until: ''
  });

  const filteredPlates = plates.filter(p =>
    p.plate.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (p.owner_name && p.owner_name.toLowerCase().includes(searchQuery.toLowerCase()))
  );

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

  return (
    <div className="view-container">
      <div className="view-header">
        <h1 className="view-title">Base de Données</h1>
        <p className="view-subtitle">Répertoire des Accès Autorisés</p>
      </div>

      <div className="db-actions">
        <div className="search-input-wrapper">
          <Search size={18} />
          <input
            type="text"
            className="search-input"
            placeholder="Rechercher une plaque ou un nom..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
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
        <div className="db-stat">
          <span className="db-stat-label">Total Actif</span>
          <span className="db-stat-value">{plates.length}</span>
        </div>
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
              {searchQuery
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
