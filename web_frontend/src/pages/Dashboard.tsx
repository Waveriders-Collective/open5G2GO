import React, { useEffect, useState } from 'react';
import { Users, Activity, Radio, Server } from 'lucide-react';
import { StatCard, Card, Badge, Table, LoadingSpinner } from '../components/ui';
import { api } from '../services/api';
import type { SystemStatusResponse, ActiveConnectionsResponse } from '../types/open5gs';

export const Dashboard: React.FC = () => {
  const [status, setStatus] = useState<SystemStatusResponse | null>(null);
  const [connections, setConnections] = useState<ActiveConnectionsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [statusData, connectionsData] = await Promise.all([
        api.getSystemStatus(),
        api.getActiveConnections(),
      ]);
      setStatus(statusData);
      setConnections(connectionsData);
    } catch (err: unknown) {
      const error = err as { response?: { data?: { error?: string } }; message?: string };
      setError(error.response?.data?.error || error.message || 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <p className="text-red-800 font-body">Error: {error}</p>
        <button
          onClick={fetchData}
          className="mt-4 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 font-body"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h2 className="text-3xl font-heading text-gray-charcoal">System Dashboard</h2>
        <div className="text-sm text-gray-medium font-body">
          Last updated: {status?.timestamp || 'N/A'}
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Provisioned Devices"
          value={status?.subscribers.provisioned || 0}
          icon={<Users className="w-12 h-12" />}
        />
        <StatCard
          title="Registered UEs"
          value={status?.subscribers.registered || 0}
          icon={<Activity className="w-12 h-12" />}
        />
        <StatCard
          title="Connected Devices"
          value={status?.subscribers.connected || 0}
          icon={<Radio className="w-12 h-12" />}
        />
        <StatCard
          title="Connected eNodeBs"
          value={status?.enodebs.total || 0}
          icon={<Server className="w-12 h-12" />}
        />
      </div>

      {/* System Health */}
      <Card title="System Health" subtitle="Open5GS 4G EPC operational status">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="font-body text-gray-dark">Core Status:</span>
            <Badge variant={status?.health.core_operational ? 'success' : 'error'}>
              {status?.health.core_operational ? 'Operational' : 'Down'}
            </Badge>
          </div>
          <div className="flex items-center justify-between">
            <span className="font-body text-gray-dark">eNodeB Connection:</span>
            <Badge variant={status?.health.enodebs_connected ? 'success' : 'warning'}>
              {status?.health.enodebs_connected ? 'Connected' : 'Waiting'}
            </Badge>
          </div>
          <div className="flex items-center justify-between">
            <span className="font-body text-gray-dark">Active Sessions:</span>
            <Badge variant={status?.health.has_active_connections ? 'success' : 'neutral'}>
              {status?.health.has_active_connections ? 'Active' : 'None'}
            </Badge>
          </div>
        </div>
      </Card>

      {/* Connected eNodeBs */}
      {status && status.enodebs.total > 0 && (
        <Card title="Connected eNodeBs" subtitle="LTE base stations currently connected">
          <div className="space-y-3">
            {status.enodebs.list.map((enb) => (
              <div
                key={enb.id}
                className="flex items-center justify-between p-4 bg-primary-light/10 rounded-lg"
              >
                <div>
                  <p className="font-body text-gray-charcoal">{enb.name}</p>
                  <p className="text-sm text-gray-medium font-body">ID: {enb.id}</p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-body text-gray-dark">{enb.ip}</p>
                  <Badge variant="success">Connected</Badge>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Active Connections */}
      <Card
        title="Active Connections"
        subtitle={`${connections?.total_active || 0} device(s) currently connected`}
      >
        {connections && connections.total_active > 0 ? (
          <Table
            data={connections.connections}
            columns={[
              { key: 'name', header: 'Device Name' },
              { key: 'imsi', header: 'IMSI' },
              {
                key: 'ip',
                header: 'IP Address',
                render: (value) => value || <span className="text-gray-400">N/A</span>,
              },
              {
                key: 'apn',
                header: 'APN',
                render: (value) => value || <span className="text-gray-400">N/A</span>,
              },
              {
                key: 'cm_state',
                header: 'Status',
                render: (value) => (
                  <Badge variant={value === 'CONNECTED' ? 'success' : 'neutral'}>{value}</Badge>
                ),
              },
            ]}
          />
        ) : (
          <p className="text-center text-gray-medium font-body py-8">
            No active connections
          </p>
        )}
      </Card>
    </div>
  );
};
