import React, { useState, useEffect } from 'react';
import './App.css';

// Layout & Views
import Sidebar from './components/layout/Sidebar';
import CommandHeader from './components/layout/CommandHeader';
import DashboardView from './components/views/DashboardView';
import DatabaseView from './components/views/DatabaseView';
import LogsView from './components/views/LogsView';

function App() {
  const [status, setStatus] = useState({ door_open: false, car_present: false });
  const [plates, setPlates] = useState([]);
  const [history, setHistory] = useState([]);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [currentView, setCurrentView] = useState('dashboard');

  const API_BASE = `http://${window.location.hostname}:8000`;

  // Fetch initial data
  useEffect(() => {
    fetchConfig();
    fetchHistory();
  }, []);

  // WebSocket
  useEffect(() => {
    const ws = new WebSocket(`ws://${window.location.hostname}:8000/ws`);
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'status') {
          setStatus(data.data);
        } else if (data.type === 'history') {
          setHistory(data.data);
        }
      } catch (err) {
        console.error(err);
      }
    };
    return () => ws.close();
  }, []);

  const fetchConfig = async () => {
    try {
      const resp = await fetch(`${API_BASE}/api/config`);
      const data = await resp.json();
      setPlates(data.authorized_plates || []);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchHistory = async () => {
    try {
      const resp = await fetch(`${API_BASE}/api/history`);
      const data = await resp.json();
      setHistory(data || []);
    } catch (err) {
      console.error(err);
    }
  };

  const openDoor = async () => {
    try {
      await fetch(`${API_BASE}/door/open`, { method: 'POST' });
    } catch (err) {
      console.error(err);
    }
  };

  const addPlate = async (plateToAdd) => {
    if (!plateToAdd.trim()) return false;
    try {
      const resp = await fetch(`${API_BASE}/api/config/plates`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ plate: plateToAdd.toUpperCase().trim() })
      });
      const data = await resp.json();
      setPlates(data.plates);
      return true;
    } catch (err) {
      console.error(err);
      return false;
    }
  };

  const deletePlate = async (plate) => {
    try {
      const resp = await fetch(`${API_BASE}/api/config/plates/${encodeURIComponent(plate)}`, {
        method: 'DELETE'
      });
      const data = await resp.json();
      setPlates(data.plates);
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="app-shell">
      <Sidebar 
        currentView={currentView}
        setCurrentView={setCurrentView}
        collapsed={sidebarCollapsed}
        setCollapsed={setSidebarCollapsed}
      />
      
      <main className="main-content">
        <CommandHeader />

        {currentView === 'dashboard' && (
          <DashboardView 
            status={status}
            history={history}
            plates={plates}
            openDoor={openDoor}
            API_BASE={API_BASE}
            setCurrentView={setCurrentView}
          />
        )}

        {currentView === 'database' && (
          <DatabaseView 
            plates={plates}
            addPlate={addPlate}
            deletePlate={deletePlate}
          />
        )}

        {currentView === 'logs' && (
          <LogsView 
            history={history}
          />
        )}
      </main>
    </div>
  );
}

export default App;
