import React from 'react';
import DashboardView from '../components/views/DashboardView';
import DatabaseView from '../components/views/DatabaseView';
import LogsView from '../components/views/LogsView';
import SettingsView from '../components/views/SettingsView';

export default function AppRouter({ 
  currentView, 
  setCurrentView, 
  status, 
  history, 
  plates, 
  openDoor, 
  API_BASE, 
  config, 
  setConfig, 
  addPlate, 
  deletePlate, 
  deleteLog 
}) {
  switch (currentView) {
    case 'dashboard':
      return (
        <DashboardView 
          status={status}
          history={history}
          plates={plates}
          openDoor={openDoor}
          API_BASE={API_BASE}
          setCurrentView={setCurrentView}
        />
      );
    case 'database':
      return (
        <DatabaseView 
          plates={plates}
          addPlate={addPlate}
          deletePlate={deletePlate}
        />
      );
    case 'logs':
      return (
        <LogsView 
          history={history}
          plates={plates}
          API_BASE={API_BASE}
          deleteLog={deleteLog}
        />
      );
    case 'settings':
      return (
        <SettingsView
          config={config}
          setConfig={setConfig}
          API_BASE={API_BASE}
        />
      );
    default:
      return (
        <DashboardView 
          status={status}
          history={history}
          plates={plates}
          openDoor={openDoor}
          API_BASE={API_BASE}
          setCurrentView={setCurrentView}
        />
      );
  }
}
