import React, { useState, useEffect } from 'react';
import './App.css';

// Layout & Views
import Sidebar from './components/layout/Sidebar';
import CommandHeader from './components/layout/CommandHeader';
import AppRouter from './routes/AppRouter';

function App() {
  const [status, setStatus] = useState({ door_open: false, car_present: false });
  const [plates, setPlates] = useState([]);
  const [history, setHistory] = useState([]);
  const [config, setConfig] = useState({});
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [currentView, setCurrentView] = useState('dashboard');
  const [isOnline, setIsOnline] = useState(false);

  const API_BASE = `http://${window.location.hostname}:8000`;

  // Fetch initial data
  useEffect(() => {
    fetchConfig();
    fetchHistory();
  }, []);

  // WebSocket
  useEffect(() => {
    let ws;
    let reconnectTimer;

    const connect = () => {
      ws = new WebSocket(`ws://${window.location.hostname}:8000/ws`);

      ws.onopen = () => {
        setIsOnline(true);
      };

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

      ws.onclose = () => {
        setIsOnline(false);
        reconnectTimer = setTimeout(connect, 3000);
      };

      ws.onerror = () => {
        if (ws) ws.close();
      };
    };

    connect();

    return () => {
      clearTimeout(reconnectTimer);
      if (ws) ws.close();
    };
  }, []);

  const fetchConfig = async () => {
    try {
      const resp = await fetch(`${API_BASE}/api/config`);
      const data = await resp.json();
      setPlates(data.authorized_plates || []);
      setConfig(data);
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

  const addPlate = async (plateData) => {
    if (!plateData.plate.trim()) return false;
    try {
      const resp = await fetch(`${API_BASE}/api/config/plates`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(plateData)
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

  const deleteLog = async (logId) => {
    try {
      await fetch(`${API_BASE}/api/history/${logId}`, {
        method: 'DELETE'
      });
      // La websocket gérera la mise à jour (broadcast_history)
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
        <CommandHeader isOnline={isOnline} />

        <AppRouter 
          currentView={currentView}
          setCurrentView={setCurrentView}
          status={status}
          history={history}
          plates={plates}
          openDoor={openDoor}
          API_BASE={API_BASE}
          config={config}
          setConfig={setConfig}
          addPlate={addPlate}
          deletePlate={deletePlate}
          deleteLog={deleteLog}
        />
      </main>
    </div>
  );
}

export default App;
