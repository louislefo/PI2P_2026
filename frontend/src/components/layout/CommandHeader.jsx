import React, { useState, useEffect } from 'react';
import { Wifi } from 'lucide-react';
import { formatTime } from '../../utils/helpers';

export default function CommandHeader() {
  const [currentTime, setCurrentTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <header className="command-header">
      <div className="floating-island">
        <div className="status-chip">
          <span className="status-dot online"></span>
          <span>En Ligne</span>
        </div>
        <div className="island-divider"></div>
        <div className="system-time">{formatTime(currentTime)}</div>
      </div>
    </header>
  );
}
