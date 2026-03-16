// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (c) 2025 Waveriders Collective Inc.

import React from 'react';
import { Activity } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useSystemStatus } from '../../hooks/useSystemStatus';

export const Header: React.FC = () => {
  const { status, loading, error } = useSystemStatus();

  const getStatusColor = () => {
    if (loading) return 'bg-yellow-500';
    if (error) return 'bg-red-500';

    switch (status?.health.operational_status) {
      case 'fully_operational':
        return 'bg-green-500';
      case 'core_and_network_ready':
        return 'bg-blue-500';
      case 'core_ready':
        return 'bg-yellow-500';
      default:
        return 'bg-red-500';
    }
  };

  const getStatusTitle = () => {
    if (loading) return 'Loading system status...';
    if (error) return 'Connection Error - Cannot reach Open5GS';

    const is5g = status?.network_mode === '5g';
    const ranTotal = is5g ? (status?.gnodebs?.total ?? 0) : (status?.enodebs?.total ?? 0);
    const ranLabel = is5g ? 'gNodeB' : 'eNodeB';
    const coreLabel = is5g ? '5G' : '4G';

    switch (status?.health.operational_status) {
      case 'fully_operational':
        return `Fully Operational - ${status.subscribers.connected} devices connected`;
      case 'core_and_network_ready':
        return `${coreLabel} Core and Network Ready - ${ranTotal} ${ranLabel}(s) connected`;
      case 'core_ready':
        return `${coreLabel} Core Ready - Waiting for ${ranLabel} connection`;
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
            <h1 className="text-2xl font-heading">openSurfControl</h1>
            <p className="text-sm text-gray-400 font-body">Open5GS Management Console</p>
          </div>
        </div>
        <Link
          to="/services"
          className="flex items-center space-x-4 cursor-pointer transition-opacity hover:opacity-80"
          title={getStatusTitle()}
        >
          <span className="text-sm font-body text-gray-400">
            {loading ? 'Loading...' : status?.system_name || 'Open5GS'}
          </span>
          <div
            className={`w-2 h-2 rounded-full ${getStatusColor()} ${status?.health.core_operational ? 'animate-pulse' : ''}`}
          />
        </Link>
      </div>
    </header>
  );
};
