import React from 'react';
import { Activity } from 'lucide-react';
import { useSystemStatus } from '../../hooks/useSystemStatus';

export const Header: React.FC = () => {
  const { status, loading, error } = useSystemStatus();
  
  const getStatusColor = () => {
    if (loading) return 'bg-yellow-500'; // Loading
    if (error) return 'bg-red-500'; // Error
    
    switch (status?.health.operational_status) {
      case 'fully_operational':
        return 'bg-green-500'; // Green: Everything working, subscribers connected
      case 'core_and_network_ready':
        return 'bg-blue-500'; // Blue: gNodeBs connected, ready for subscribers
      case 'core_ready':
        return 'bg-yellow-500'; // Yellow: Core up, ready to connect gNodeBs
      default:
        return 'bg-red-500'; // Red: Down or unknown
    }
  };

  const getStatusTitle = () => {
    if (loading) return 'Loading system status...';
    if (error) return 'Connection Error - Cannot reach Attocore';
    
    switch (status?.health.operational_status) {
      case 'fully_operational':
        return `Fully Operational - ${status.subscribers.connected} subscribers connected`;
      case 'core_and_network_ready':
        return `5G Core and Network Ready - ${status.gnodebs.total} gNodeB(s) connected, ready for subscribers`;
      case 'core_ready':
        return '5G Core Ready - Ready to connect gNodeBs';
      default:
        return 'Core Down';
    }
  };

  return (
    <header className="bg-accent-charcoal text-white shadow-lg">
      <div className="px-6 py-4 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <Activity className="w-8 h-8 text-primary" />
          <div>
            <h1 className="text-2xl font-heading">Surfcontrol</h1>
            <p className="text-sm text-gray-400 font-body">Attocore Management Console</p>
          </div>
        </div>
        <div className="flex items-center space-x-4">
          <span className="text-sm font-body text-gray-400">
            {loading ? 'Loading...' : status?.system_name || 'Attocore System'}: {loading ? 'Loading...' : status?.host || 'Unknown'}
          </span>
          <div 
            className={`w-2 h-2 rounded-full ${getStatusColor()} ${status?.health.core_operational ? 'animate-pulse' : ''}`}
            title={getStatusTitle()}
          />
        </div>
      </div>
    </header>
  );
};
