// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (c) 2025 Waveriders Collective Inc.

import React, { useEffect, useState } from 'react';
import { Users, Activity, Radio, Server, Wifi, WifiOff, AlertTriangle, Cpu } from 'lucide-react';
import { StatCard, Card, Badge, Table, LoadingSpinner } from '../components/ui';
import { api } from '../services/api';
import type { SystemStatusResponse, ActiveConnectionsResponse, EnodebStatusResponse, ENodeBStatus, SNMPEnodebStatus } from '../types/open5gs';

export const Dashboard: React.FC = () => {
  const [status, setStatus] = useState<SystemStatusResponse | null>(null);
  const [connections, setConnections] = useState<ActiveConnectionsResponse | null>(null);
  const [enodebStatus, setEnodebStatus] = useState<EnodebStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

  // Get S1AP connected eNodeBs
  const getEnodebs = (): ENodeBStatus[] => {
    if (!enodebStatus) return [];
    return enodebStatus.s1ap.enodebs;
  };

  // Get SNMP data for an eNodeB by serial number or IP
  const getSNMPStatus = (serial: string, ip?: string): SNMPEnodebStatus | undefined => {
    if (!enodebStatus?.snmp?.enodebs) return undefined;
    return enodebStatus.snmp.enodebs.find(
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
        subtitle="LTE base stations with S1AP connection status"
      >
        {!enodebStatus ? (
          <p className="text-center text-gray-medium font-body py-8">
            Loading eNodeB status...
          </p>
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
