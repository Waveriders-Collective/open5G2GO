import React, { useEffect, useState } from 'react';
import { Users, Activity, Radio, Server, RefreshCw, ChevronDown, ChevronUp } from 'lucide-react';
import { StatCard, Card, Badge, Table, LoadingSpinner } from '../components/ui';
import { api } from '../services/api';
import type { SystemStatusResponse, ActiveConnectionsResponse, EnodebStatusResponse, ENodeBStatus } from '../types/open5gs';

export const Dashboard: React.FC = () => {
  const [status, setStatus] = useState<SystemStatusResponse | null>(null);
  const [connections, setConnections] = useState<ActiveConnectionsResponse | null>(null);
  const [enodebStatus, setEnodebStatus] = useState<EnodebStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedEnodebs, setExpandedEnodebs] = useState<Set<string>>(new Set());
  const [refreshingSas, setRefreshingSas] = useState(false);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [statusData, connectionsData, enodebStatusData] = await Promise.all([
        api.getSystemStatus(),
        api.getActiveConnections(),
        api.getEnodebStatus().catch(() => null), // Gracefully handle if endpoint not available
      ]);
      setStatus(statusData);
      setConnections(connectionsData);
      setEnodebStatus(enodebStatusData);
    } catch (err: unknown) {
      const error = err as { response?: { data?: { error?: string } }; message?: string };
      setError(error.response?.data?.error || error.message || 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const handleRefreshSas = async () => {
    try {
      setRefreshingSas(true);
      await api.refreshSasStatus();
      // Refetch eNodeB status after refresh
      const enodebStatusData = await api.getEnodebStatus().catch(() => null);
      setEnodebStatus(enodebStatusData);
    } catch (err) {
      console.error('Failed to refresh SAS status:', err);
    } finally {
      setRefreshingSas(false);
    }
  };

  const toggleEnodebExpanded = (serial: string) => {
    setExpandedEnodebs(prev => {
      const next = new Set(prev);
      if (next.has(serial)) {
        next.delete(serial);
      } else {
        next.add(serial);
      }
      return next;
    });
  };

  const getSasStateBadgeVariant = (state: string): 'success' | 'warning' | 'error' | 'neutral' => {
    switch (state?.toUpperCase()) {
      case 'AUTHORIZED':
        return 'success';
      case 'REGISTERED':
        return 'warning';
      case 'SUSPENDED':
      case 'TERMINATED':
        return 'error';
      default:
        return 'neutral';
    }
  };

  const getGrantStateBadgeVariant = (state: string): 'success' | 'warning' | 'error' | 'neutral' => {
    switch (state?.toUpperCase()) {
      case 'AUTHORIZED':
        return 'success';
      case 'GRANTED':
        return 'warning';
      case 'SUSPENDED':
      case 'TERMINATED':
        return 'error';
      default:
        return 'neutral';
    }
  };

  // Merge S1AP and SAS data to get combined eNodeB view
  const getMergedEnodebs = (): ENodeBStatus[] => {
    if (!enodebStatus) return [];

    const merged = new Map<string, ENodeBStatus>();

    // Add S1AP connected eNodeBs
    enodebStatus.s1ap.enodebs.forEach(enb => {
      merged.set(enb.serial_number, { ...enb });
    });

    // Merge/add SAS eNodeBs
    enodebStatus.sas.enodebs.forEach(enb => {
      const existing = merged.get(enb.serial_number);
      if (existing) {
        merged.set(enb.serial_number, { ...existing, ...enb });
      } else {
        merged.set(enb.serial_number, { ...enb });
      }
    });

    return Array.from(merged.values());
  };

  const isEnodebConnected = (serial: string): boolean => {
    return enodebStatus?.s1ap.enodebs.some(e => e.serial_number === serial) ?? false;
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

      {/* eNodeB Status Card */}
      <Card
        title="eNodeB Status"
        subtitle="LTE base stations with S1AP and SAS status"
        action={
          enodebStatus?.sas.available ? (
            <button
              onClick={handleRefreshSas}
              disabled={refreshingSas}
              className="flex items-center gap-2 px-3 py-1.5 text-sm font-body text-primary-dark hover:bg-primary-light/20 rounded-md disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${refreshingSas ? 'animate-spin' : ''}`} />
              Refresh SAS
            </button>
          ) : null
        }
      >
        {!enodebStatus ? (
          <p className="text-center text-gray-medium font-body py-8">
            Loading eNodeB status...
          </p>
        ) : getMergedEnodebs().length === 0 ? (
          <p className="text-center text-gray-medium font-body py-8">
            No eNodeBs configured
          </p>
        ) : (
          <div className="space-y-4">
            {/* SAS availability notice */}
            {!enodebStatus.sas.available && (
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
                <p className="text-sm text-amber-800 font-body">
                  SAS not configured - Spectrum access information unavailable
                </p>
              </div>
            )}

            {/* eNodeB list */}
            {getMergedEnodebs().map((enb) => {
              const isConnected = isEnodebConnected(enb.serial_number);
              const isExpanded = expandedEnodebs.has(enb.serial_number);

              return (
                <div
                  key={enb.serial_number}
                  className="border border-gray-200 rounded-lg overflow-hidden"
                >
                  {/* Main row */}
                  <div className="flex items-center justify-between p-4 bg-primary-light/10">
                    <div className="flex-1">
                      <div className="flex items-center gap-3">
                        <p className="font-body font-semibold text-gray-charcoal">
                          {enb.config_name || enb.serial_number}
                        </p>
                        <Badge variant={isConnected ? 'success' : 'error'}>
                          {isConnected ? 'Connected' : 'Disconnected'}
                        </Badge>
                      </div>
                      <p className="text-sm text-gray-medium font-body mt-1">
                        {enb.location || 'Location not set'} | S/N: {enb.serial_number}
                      </p>
                    </div>

                    <div className="flex items-center gap-4">
                      {/* SAS State */}
                      {enodebStatus.sas.available && (
                        <div className="text-right">
                          <p className="text-xs text-gray-medium font-body mb-1">SAS State</p>
                          <Badge variant={getSasStateBadgeVariant(enb.sas_state)}>
                            {enb.sas_state || 'UNREGISTERED'}
                          </Badge>
                        </div>
                      )}

                      {/* Active Grant */}
                      {enb.active_grant && (
                        <div className="text-right">
                          <p className="text-xs text-gray-medium font-body mb-1">Active Grant</p>
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-body text-gray-dark">
                              {enb.active_grant.frequency_mhz} MHz
                            </span>
                            <Badge variant={enb.active_grant.channel_type === 'PAL' ? 'success' : 'neutral'}>
                              {enb.active_grant.channel_type}
                            </Badge>
                            <Badge variant={getGrantStateBadgeVariant(enb.active_grant.state)}>
                              {enb.active_grant.state}
                            </Badge>
                          </div>
                        </div>
                      )}

                      {/* Expand button for history */}
                      {enb.grants && enb.grants.length > 0 && (
                        <button
                          onClick={() => toggleEnodebExpanded(enb.serial_number)}
                          className="p-2 hover:bg-gray-100 rounded-md"
                          title="View grant history"
                        >
                          {isExpanded ? (
                            <ChevronUp className="w-5 h-5 text-gray-dark" />
                          ) : (
                            <ChevronDown className="w-5 h-5 text-gray-dark" />
                          )}
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Expanded grant history */}
                  {isExpanded && enb.grants && enb.grants.length > 0 && (
                    <div className="border-t border-gray-200 bg-gray-50 p-4">
                      <p className="text-sm font-body font-semibold text-gray-dark mb-3">
                        Grant History (24h)
                      </p>
                      <div className="space-y-2">
                        {enb.grants.map((grant, idx) => (
                          <div
                            key={grant.grant_id || idx}
                            className="flex items-center justify-between p-2 bg-white rounded border border-gray-100"
                          >
                            <div className="flex items-center gap-3">
                              <Badge variant={getGrantStateBadgeVariant(grant.state)}>
                                {grant.state}
                              </Badge>
                              <span className="text-sm font-body text-gray-dark">
                                {grant.frequency_mhz} MHz
                              </span>
                              <Badge variant={grant.channel_type === 'PAL' ? 'success' : 'neutral'}>
                                {grant.channel_type}
                              </Badge>
                            </div>
                            <div className="text-right text-sm text-gray-medium font-body">
                              <span>Max EIRP: {grant.max_eirp_dbm} dBm</span>
                              {grant.expire_time && (
                                <span className="ml-3">
                                  Expires: {new Date(grant.expire_time).toLocaleString()}
                                </span>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </Card>

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
