import React, { useState, useEffect } from 'react';
import { Camera, DoorOpen, Car, Zap, List, Plus, Trash2, Clock } from 'lucide-react';

function App() {
  const [status, setStatus] = useState({ door_open: false, car_present: false });
  const [plates, setPlates] = useState([]);
  const [history, setHistory] = useState([]);
  const [newPlate, setNewPlate] = useState('');
  
  const API_BASE = `http://${window.location.hostname}:8000`;

  useEffect(() => {
    fetchConfig();
    fetchHistory();
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

  const openDoor = async () => {
    try {
      await fetch(`${API_BASE}/door/open`, { method: 'POST' });
    } catch (err) {
      console.error(err);
    }
  };

  const addPlate = async (e) => {
    e.preventDefault();
    if (!newPlate.trim()) return;
    try {
      const resp = await fetch(`${API_BASE}/api/config/plates`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ plate: newPlate.toUpperCase().trim() })
      });
      const data = await resp.json();
      setPlates(data.plates);
      setNewPlate('');
    } catch (err) {
      console.error(err);
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

  const formatDate = (isoString) => {
    const date = new Date(isoString);
    return date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 flex flex-col font-sans">
      <header className="py-4 px-8 border-b border-gray-800 bg-gray-900 shadow-xl flex justify-between items-center z-10">
        <h1 className="text-2xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-emerald-400 flex items-center gap-3">
          <Zap className="text-emerald-400" size={28} />
          Parking Automatisé (OCR)
        </h1>
        <div className="flex gap-4">
          <div className={`px-4 py-1.5 rounded-full text-sm font-bold border flex items-center gap-2 transition-colors ${status.door_open ? 'bg-blue-500/20 text-blue-400 border-blue-500/30 shadow-[0_0_15px_rgba(59,130,246,0.3)]' : 'bg-gray-800 text-gray-400 border-gray-700'}`}>
            <DoorOpen size={16} /> PORTAIL: {status.door_open ? 'OUVERT' : 'FERMÉ'}
          </div>
        </div>
      </header>

      <div className="flex-1 flex flex-col lg:flex-row overflow-hidden">
        {/* BIG VIDEO SECTION (Left) */}
        <div className="flex-2 flex flex-col p-6 items-center justify-center bg-black/50 overflow-hidden w-full lg:w-2/3">
          <div className="w-full aspect-video bg-gray-900 rounded-3xl overflow-hidden shadow-[0_0_50px_rgba(0,0,0,0.5)] border border-gray-800 relative">
            <div className="absolute top-4 left-4 z-10 bg-black/60 backdrop-blur-md px-3 py-1.5 rounded-lg border border-white/10 flex items-center gap-2">
              <div className="w-2.5 h-2.5 bg-red-500 rounded-full animate-pulse shadow-[0_0_10px_red]"></div>
              <span className="text-xs font-semibold text-white tracking-widest">IA & OCR EN DIRECT</span>
            </div>
            <img 
              src={`${API_BASE}/video_feed`} 
              alt="Flux WebCam YOLO OCR" 
              className="w-full h-full object-contain"
              onError={(e) => { e.target.style.display='none'; e.target.nextSibling.style.display='flex'; }}
            />
            <div className="absolute inset-0 hidden flex-col items-center justify-center text-gray-500 gap-4">
               <Camera size={48} className="opacity-20" />
               <p>Flux vidéo hors ligne. Démarrez uvicorn.</p>
            </div>
          </div>
        </div>

        {/* SIDEBAR COMMANDS (Right) */}
        <div className="w-full lg:w-1/3 bg-gray-900 border-l border-gray-800 flex flex-col shadow-2xl z-10 h-full overflow-hidden">
          
          <div className="p-6 border-b border-gray-800">
            <button 
              onClick={openDoor}
              className="w-full relative inline-flex items-center justify-center px-8 py-4 font-bold text-white transition-all duration-200 bg-emerald-600 rounded-2xl focus:outline-none focus:ring-2 focus:ring-emerald-600 hover:bg-emerald-500 shadow-[0_0_30px_rgba(16,185,129,0.2)] active:scale-[0.98]"
            >
              <DoorOpen className="mr-3 h-6 w-6" />
              <span className="text-lg tracking-wide">OUVERTURE MANUELLE</span>
            </button>
          </div>

          <div className="flex-1 flex flex-col overflow-hidden">
            {/* Top Half: Authorized Plates */}
            <div className="h-1/2 flex flex-col bg-gray-800/20 border-b border-gray-800">
              <div className="p-4 border-b border-gray-800 bg-gray-800/40">
                <h2 className="text-sm font-semibold text-gray-300 flex items-center gap-2 uppercase tracking-wider">
                  <List className="text-purple-400" size={16} /> Plaques Autorisées
                </h2>
              </div>
              
              <div className="p-3 border-b border-gray-800">
                <form onSubmit={addPlate} className="flex gap-2">
                  <input 
                    type="text" 
                    value={newPlate}
                    onChange={(e) => setNewPlate(e.target.value)}
                    placeholder="EX: WW-123-AA" 
                    className="flex-1 w-0 bg-gray-950 border border-gray-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500 uppercase placeholder:normal-case font-mono text-sm"
                  />
                  <button type="submit" className="bg-purple-600 hover:bg-purple-500 text-white p-2 rounded-xl transition-colors shadow-lg shadow-purple-600/30 flex-shrink-0 active:scale-90">
                    <Plus size={20} />
                  </button>
                </form>
              </div>

              <div className="flex-1 overflow-y-auto p-3">
                {plates.length === 0 ? (
                  <div className="text-center text-gray-500 p-6 text-sm">
                    Aucun véhicule enregistré.
                  </div>
                ) : (
                  <ul className="space-y-2">
                    {plates.map((plate) => (
                      <li key={plate} className="flex justify-between items-center bg-gray-900/60 p-2.5 rounded-lg border border-gray-700/50 hover:border-purple-500/30 transition-colors group">
                        <span className="font-mono text-sm font-bold text-gray-200">{plate}</span>
                        <button onClick={() => deletePlate(plate)} className="text-gray-500 hover:text-red-400 p-1 rounded-lg">
                          <Trash2 size={16} />
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>

            {/* Bottom Half: History */}
            <div className="h-1/2 flex flex-col bg-gray-900 overflow-hidden">
              <div className="p-4 border-b border-gray-800 bg-gray-800/40 sticky top-0">
                <h2 className="text-sm font-semibold text-gray-300 flex items-center gap-2 uppercase tracking-wider">
                  <Clock className="text-blue-400" size={16} /> Historique des Passages
                </h2>
              </div>
              <div className="flex-1 overflow-y-auto p-3">
                {history.length === 0 ? (
                  <div className="text-center text-gray-500 p-6 text-sm">
                    Aucune ouverture récente.
                  </div>
                ) : (
                  <ul className="space-y-2 border-l-2 border-gray-800 ml-2">
                    {history.map((item, index) => (
                      <li key={index} className="relative pl-4 py-2">
                        <div className="absolute w-2 h-2 bg-blue-500 rounded-full -left-[5px] top-4 shadow-[0_0_8px_blue]"></div>
                        <div className="flex justify-between items-center bg-gray-800/30 p-2.5 rounded-lg border border-gray-800">
                          <div>
                            <div className="font-mono text-sm font-bold text-gray-100">{item.plate}</div>
                            <div className="text-xs text-gray-500 mt-0.5">{item.status}</div>
                          </div>
                          <div className="text-xs font-medium text-gray-400 bg-gray-900 px-2 py-1 rounded-md">
                            {formatDate(item.time)}
                          </div>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
            
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
