// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (c) 2025 Waveriders Collective Inc.

import React, { useEffect, useState, useCallback } from 'react';
import { Users, Activity, Radio, Server, Wifi, WifiOff, AlertTriangle, Cpu, RefreshCw } from 'lucide-react';
import { StatCard, Card, Badge, Table, LoadingSpinner } from '../components/ui';
import { api } from '../services/api';
import type { SystemStatusResponse, ActiveConnectionsResponse, EnodebStatusResponse, ENodeBStatus, SNMPEnodebStatus } from '../types/open5gs';

// Individual section loading states
interface SectionState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

export const Dashboard: React.FC = () => {
  // Independent state for each section
  const [status, setStatus] = useState<SectionState<SystemStatusResponse>>({
    data: null, loading: true, error: null
  });
  const [connections, setConnections] = useState<SectionState<ActiveConnectionsResponse>>({
    data: null, loading: true, error: null
  });
  const [enodebStatus, setEnodebStatus] = useState<SectionState<EnodebStatusResponse>>({
    data: null, loading: true, error: null
  });

  // Fetch system status independently
  const fetchStatus = useCallback(async () => {
    setStatus(prev => ({ ...prev, loading: true, error: null }));
    try {
      const data = await api.getSystemStatus();
      setStatus({ data, loading: false, error: null });
    } catch (err: unknown) {
      const error = err as { response?: { data?: { error?: string } }; message?: string };
      setStatus(prev => ({
        ...prev,
        loading: false,
        error: error.response?.data?.error || error.message || 'Failed to load status'
      }));
    }
  }, []);

  // Fetch connections independently
  const fetchConnections = useCallback(async () => {
    setConnections(prev => ({ ...prev, loading: true, error: null }));
    try {
      const data = await api.getActiveConnections();
      setConnections({ data, loading: false, error: null });
    } catch (err: unknown) {
      const error = err as { response?: { data?: { error?: string } }; message?: string };
      setConnections(prev => ({
        ...prev,
        loading: false,
        error: error.response?.data?.error || error.message || 'Failed to load connections'
      }));
    }
  }, []);

  // Fetch eNodeB status independently (this is the slow one)
  const fetchEnodebStatus = useCallback(async () => {
    setEnodebStatus(prev => ({ ...prev, loading: true, error: null }));
    try {
      const data = await api.getEnodebStatus();
      setEnodebStatus({ data, loading: false, error: null });
    } catch (err: unknown) {
      const error = err as { response?: { data?: { error?: string } }; message?: string };
      setEnodebStatus(prev => ({
        ...prev,
        loading: false,
        error: error.response?.data?.error || error.message || 'Failed to load eNodeB status'
      }));
    }
  }, []);

  // Fetch all data (called on mount and refresh)
  const fetchAllData = useCallback(() => {
    // Fire all fetches in parallel - each updates independently
    fetchStatus();
    fetchConnections();
    fetchEnodebStatus();
  }, [fetchStatus, fetchConnections, fetchEnodebStatus]);

  // Get S1AP connected eNodeBs
  const getEnodebs = (): ENodeBStatus[] => {
    if (!enodebStatus.data) return [];
    return enodebStatus.data.s1ap.enodebs;
  };

  // Get SNMP data for an eNodeB by serial number or IP
  const getSNMPStatus = (serial: string, ip?: string): SNMPEnodebStatus | undefined => {
    if (!enodebStatus.data?.snmp?.enodebs) return undefined;
    return enodebStatus.data.snmp.enodebs.find(
      e => e.serial_number === serial || e.ip_address === ip
    );
  };

  // Format throughput for display
  const formatThroughput = (kbps?: number): string => {
    if (kbps === undefined || kbps === null) return 'N/A';
    if (kbps >= 1000) return `${(kbps / 1000).toFixed(1)} Mbps`;
    return `${kbps} kbps`;
  };

  // Calculate frequency from EARFCN (Band 48 CBRS)
  const earfcnToFrequency = (earfcn?: number, band?: number): string => {
    if (!earfcn) return 'N/A';
    // Band 48 (CBRS): 3550-3700 MHz, EARFCN 55240-56739
    if (band === 48 || (earfcn >= 55240 && earfcn <= 56739)) {
      const freqMhz = 3550 + 0.1 * (earfcn - 55240);
      return `${freqMhz.toFixed(1)} MHz`;
    }
    // Fallback: just show EARFCN
    return `EARFCN ${earfcn}`;
  };

  const isEnodebConnected = (serial: string): boolean => {
    return enodebStatus.data?.s1ap.enodebs.some(e => e.serial_number === serial) ?? false;
  };

  useEffect(() => {
    fetchAllData();
    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchAllData, 30000);
    return () => clearInterval(interval);
  }, [fetchAllData]);

  // Check if any section has data (to show something rather than full-page spinner)
  const hasAnyData = status.data || connections.data || enodebStatus.data;
  const allLoading = status.loading && connections.loading && enodebStatus.loading && !hasAnyData;

  // Show full-page spinner only on initial load when we have nothing
  if (allLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h2 className="text-3xl font-heading text-gray-charcoal">System Dashboard</h2>
        <div className="flex items-center gap-4">
          <div className="text-sm text-gray-medium font-body">
            Last updated: {status.data?.timestamp || 'N/A'}
          </div>
          <button
            onClick={fetchAllData}
            className="p-2 text-gray-medium hover:text-primary-default rounded-md hover:bg-gray-100"
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 ${(status.loading || connections.loading || enodebStatus.loading) ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Stats Grid - shows with loading state per-card if needed */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {status.loading && !status.data ? (
          <>
            <div className="bg-white rounded-lg border border-gray-200 p-6 animate-pulse">
              <div className="h-12 bg-gray-200 rounded w-1/2 mb-2"></div>
              <div className="h-8 bg-gray-200 rounded w-1/4"></div>
            </div>
            <div className="bg-white rounded-lg border border-gray-200 p-6 animate-pulse">
              <div className="h-12 bg-gray-200 rounded w-1/2 mb-2"></div>
              <div className="h-8 bg-gray-200 rounded w-1/4"></div>
            </div>
            <div className="bg-white rounded-lg border border-gray-200 p-6 animate-pulse">
              <div className="h-12 bg-gray-200 rounded w-1/2 mb-2"></div>
              <div className="h-8 bg-gray-200 rounded w-1/4"></div>
            </div>
            <div className="bg-white rounded-lg border border-gray-200 p-6 animate-pulse">
              <div className="h-12 bg-gray-200 rounded w-1/2 mb-2"></div>
              <div className="h-8 bg-gray-200 rounded w-1/4"></div>
            </div>
          </>
        ) : status.error ? (
          <div className="col-span-4 bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-800 font-body text-sm">Stats error: {status.error}</p>
          </div>
        ) : (
          <>
            <StatCard
              title="Provisioned Devices"
              value={status.data?.subscribers.provisioned || 0}
              icon={<Users className="w-12 h-12" />}
            />
            <StatCard
              title="Registered UEs"
              value={status.data?.subscribers.registered || 0}
              icon={<Activity className="w-12 h-12" />}
            />
            <StatCard
              title="Connected Devices"
              value={status.data?.subscribers.connected || 0}
              icon={<Radio className="w-12 h-12" />}
            />
            <StatCard
              title="Connected eNodeBs"
              value={status.data?.enodebs.total || 0}
              icon={<Server className="w-12 h-12" />}
            />
          </>
        )}
      </div>

      {/* System Health */}
      <Card title="System Health" subtitle="Open5GS 4G EPC operational status">
        {status.loading && !status.data ? (
          <div className="space-y-4 animate-pulse">
            <div className="h-6 bg-gray-200 rounded w-3/4"></div>
            <div className="h-6 bg-gray-200 rounded w-2/3"></div>
            <div className="h-6 bg-gray-200 rounded w-1/2"></div>
          </div>
        ) : status.error ? (
          <p className="text-red-600 font-body text-sm">{status.error}</p>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="font-body text-gray-dark">Core Status:</span>
              <Badge variant={status.data?.health.core_operational ? 'success' : 'error'}>
                {status.data?.health.core_operational ? 'Operational' : 'Down'}
              </Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="font-body text-gray-dark">eNodeB Connection:</span>
              <Badge variant={status.data?.health.enodebs_connected ? 'success' : 'warning'}>
                {status.data?.health.enodebs_connected ? 'Connected' : 'Waiting'}
              </Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="font-body text-gray-dark">Active Sessions:</span>
              <Badge variant={status.data?.health.has_active_connections ? 'success' : 'neutral'}>
                {status.data?.health.has_active_connections ? 'Active' : 'None'}
              </Badge>
            </div>
          </div>
        )}
      </Card>

      {/* eNodeB Status Card - loads independently */}
      <Card
        title="eNodeB Status"
        subtitle="LTE base stations with S1AP connection status"
        action={enodebStatus.loading ? <LoadingSpinner size="sm" /> : undefined}
      >
        {enodebStatus.loading && !enodebStatus.data ? (
          <div className="py-8 text-center">
            <LoadingSpinner size="md" />
            <p className="mt-2 text-sm text-gray-medium font-body">Loading eNodeB status...</p>
          </div>
        ) : enodebStatus.error ? (
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
            <p className="text-amber-800 font-body text-sm">{enodebStatus.error}</p>
            <button
              onClick={fetchEnodebStatus}
              className="mt-2 text-sm text-amber-700 hover:text-amber-900 underline"
            >
              Retry
            </button>
          </div>
        ) : getEnodebs().length === 0 ? (
          <p className="text-center text-gray-medium font-body py-8">
            No eNodeBs configured
          </p>
        ) : (
          <div className="space-y-4">
            {/* eNodeB list */}
            {getEnodebs().map((enb) => {
              const isConnected = isEnodebConnected(enb.serial_number);

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
                        {/* SNMP reachability indicator */}
                        {(() => {
                          const snmpData = getSNMPStatus(enb.serial_number, enb.ip_address);
                          if (snmpData) {
                            return (
                              <Badge variant={snmpData.reachable ? 'success' : 'warning'}>
                                {snmpData.reachable ? (
                                  <span className="flex items-center gap-1">
                                    <Wifi className="w-3 h-3" /> SNMP
                                  </span>
                                ) : (
                                  <span className="flex items-center gap-1">
                                    <WifiOff className="w-3 h-3" /> SNMP
                                  </span>
                                )}
                              </Badge>
                            );
                          }
                          return null;
                        })()}
                      </div>
                      <p className="text-sm text-gray-medium font-body mt-1">
                        {enb.location || 'Location not set'} | S/N: {enb.serial_number}
                      </p>
                      {/* S1AP Connection Details */}
                      {isConnected && enb.ip_address && (
                        <p className="text-xs text-gray-medium font-body mt-1">
                          S1AP: <span className="font-mono text-gray-dark">{enb.ip_address}:{enb.port || 36412}</span>
                        </p>
                      )}
                      {/* SNMP Monitoring Data */}
                      {(() => {
                        const snmpData = getSNMPStatus(enb.serial_number, enb.ip_address);
                        if (snmpData?.reachable) {
                          return (
                            <div className="mt-3 p-3 bg-white rounded border border-gray-100">
                              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs font-body">
                                {/* Cell - RF/Radio layer */}
                                <div>
                                  <p className="text-gray-medium mb-1">Cell</p>
                                  <div className="flex items-center gap-2 mb-1">
                                    <Badge variant={snmpData.connection.rf_enabled ? 'success' : 'error'}>
                                      RF {snmpData.connection.rf_enabled ? 'ON' : 'OFF'}
                                    </Badge>
                                  </div>
                                  <p className="text-gray-dark font-semibold">
                                    B{snmpData.cell.band_class} | {earfcnToFrequency(snmpData.cell.earfcn, snmpData.cell.band_class)}
                                  </p>
                                  <p className="text-gray-medium">
                                    {snmpData.cell.bandwidth} | {snmpData.tx_power.current_dbm ?? snmpData.tx_power.max_dbm ?? 'N/A'} dBm
                                  </p>
                                </div>
                                {/* Core - S1AP backhaul */}
                                <div>
                                  <p className="text-gray-medium mb-1">Core</p>
                                  <div className="flex items-center gap-2 mb-1">
                                    <Badge variant={snmpData.connection.s1_link_up ? 'success' : 'error'}>
                                      S1AP {snmpData.connection.s1_link_up ? 'UP' : 'DOWN'}
                                    </Badge>
                                  </div>
                                  <p className="text-gray-dark">
                                    TAC {snmpData.cell.tac} | Cell {snmpData.cell.cell_id}
                                  </p>
                                  <p className="text-gray-medium">
                                    PCI {snmpData.cell.pci}
                                  </p>
                                </div>
                                {/* Traffic */}
                                <div>
                                  <p className="text-gray-medium mb-1">Traffic</p>
                                  <p className="text-gray-dark font-semibold flex items-center gap-1">
                                    <Users className="w-3 h-3" />
                                    {snmpData.connection.ue_count} UE
                                  </p>
                                  <p className="text-gray-medium">
                                    ↓{formatThroughput(snmpData.performance.dl_throughput_kbps)} ↑{formatThroughput(snmpData.performance.ul_throughput_kbps)}
                                  </p>
                                  <p className="text-gray-medium">
                                    PRB: ↓{snmpData.performance.dl_prb_pct ?? 0}% ↑{snmpData.performance.ul_prb_pct ?? 0}%
                                  </p>
                                </div>
                                {/* Health */}
                                <div>
                                  <p className="text-gray-medium mb-1">Health</p>
                                  <div className="flex items-center gap-2 mb-1">
                                    {snmpData.alarms.count === 0 ? (
                                      <Badge variant="success">OK</Badge>
                                    ) : (
                                      <Badge variant="error">
                                        <AlertTriangle className="w-3 h-3 mr-1" />
                                        {snmpData.alarms.count} Alarm{snmpData.alarms.count > 1 ? 's' : ''}
                                      </Badge>
                                    )}
                                  </div>
                                  <p className="text-gray-dark">
                                    <Cpu className="w-3 h-3 inline" /> CPU {snmpData.performance.cpu_utilization ?? 0}%
                                  </p>
                                  <p className="text-gray-medium">
                                    RRC {snmpData.kpis.rrc_success_pct ?? 'N/A'}% | E-RAB {snmpData.kpis.erab_success_pct ?? 'N/A'}%
                                  </p>
                                </div>
                              </div>
                              {/* Device Info Row */}
                              <div className="mt-2 pt-2 border-t border-gray-100 text-xs text-gray-medium">
                                {snmpData.identity.product_type} | {snmpData.identity.software_version}
                              </div>
                            </div>
                          );
                        } else if (snmpData?.error) {
                          return (
                            <div className="mt-2 p-2 bg-amber-50 border border-amber-200 rounded text-xs text-amber-800">
                              SNMP: {snmpData.error}
                            </div>
                          );
                        }
                        return null;
                      })()}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </Card>

      {/* Active Connections - loads independently */}
      <Card
        title="Active Connections"
        subtitle={`${connections.data?.total_active || 0} device(s) currently connected`}
        action={connections.loading ? <LoadingSpinner size="sm" /> : undefined}
      >
        {connections.loading && !connections.data ? (
          <div className="py-8 text-center">
            <LoadingSpinner size="md" />
            <p className="mt-2 text-sm text-gray-medium font-body">Loading connections...</p>
          </div>
        ) : connections.error ? (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-800 font-body text-sm">{connections.error}</p>
          </div>
        ) : connections.data && connections.data.total_active > 0 ? (
          <Table
            data={connections.data.connections}
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
