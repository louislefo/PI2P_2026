import React, { useState } from 'react';
import { Search, Plus, Trash2, Database } from 'lucide-react';

export default function DatabaseView({ plates, addPlate, deletePlate }) {
  const [searchQuery, setSearchQuery] = useState('');
  const [newPlate, setNewPlate] = useState('');

  const filteredPlates = plates.filter(p =>
    p.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleAdd = async (e) => {
    e.preventDefault();
    const success = await addPlate(newPlate);
    if (success) {
      setNewPlate('');
    }
  };

  return (
    <div className="view-container">
      <div className="view-header">
        <h1 className="view-title">Base de Données</h1>
        <p className="view-subtitle">Répertoire des Plaques Autorisées</p>
      </div>

      <div className="db-actions">
        <div className="search-input-wrapper">
          <Search size={18} />
          <input
            type="text"
            className="search-input"
            placeholder="Rechercher une plaque..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        <form className="add-plate-form" onSubmit={handleAdd}>
          <input
            type="text"
            className="plate-input"
            value={newPlate}
            onChange={(e) => setNewPlate(e.target.value)}
            placeholder="EX: WW-123-AA"
          />
          <button type="submit" className="add-btn">
            <Plus size={18} />
            Ajouter
          </button>
        </form>
      </div>

      <div className="db-stats">
        <div className="db-stat">
          <span className="db-stat-label">Total Actif</span>
          <span className="db-stat-value">{plates.length}</span>
        </div>
      </div>

      <div className="plates-table">
        <div className="table-header">
          <span>Plaque d'Immatriculation</span>
          <span>Date d'Ajout</span>
          <span>Actions</span>
        </div>

        {filteredPlates.length === 0 ? (
          <div className="empty-state">
            <Database size={32} />
            <p>
              {searchQuery
                ? 'Aucune plaque trouvée.'
                : 'Aucun véhicule enregistré.'}
            </p>
          </div>
        ) : (
          filteredPlates.map((plate) => (
            <div key={plate} className="table-row">
              <div className="plate-text">
                <div className="plate-indicator"></div>
                {plate}
              </div>
              <span className="plate-date">—</span>
              <button
                className="delete-btn"
                onClick={() => deletePlate(plate)}
                title="Supprimer"
              >
                <Trash2 size={16} />
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
