// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (c) 2025 Waveriders Collective Inc.

import React, { useEffect, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { Button, Card, Table, LoadingSpinner } from '../components/ui';
import { api } from '../services/api';
import type { NetworkConfigResponse } from '../types/open5gs';

export const NetworkConfig: React.FC = () => {
  const [data, setData] = useState<NetworkConfigResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await api.getNetworkConfig();
      setData(result);
    } catch (err: unknown) {
      const error = err as { response?: { data?: { error?: string } }; message?: string };
      setError(error.response?.data?.error || error.message || 'Failed to load network config');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
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
        <Button variant="primary" onClick={fetchData} className="mt-4">
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-3xl font-heading text-gray-charcoal">Network Configuration</h2>
        <Button
          variant="secondary"
          size="md"
          onClick={fetchData}
          disabled={loading}
          className="flex items-center space-x-2"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </Button>
      </div>

      {/* Network Identity */}
      <Card
        title="Network Identity"
        subtitle={`Last updated: ${data?.timestamp || 'N/A'}`}
        className="bg-gradient-to-br from-primary-light/10 to-primary/5"
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <p className="text-sm font-body text-gray-medium mb-1">PLMNID</p>
            <p className="text-2xl font-heading text-gray-charcoal">
              {data?.network_identity.plmnid || 'N/A'}
            </p>
          </div>
          <div>
            <p className="text-sm font-body text-gray-medium mb-1">Network Name</p>
            <p className="text-2xl font-heading text-gray-charcoal">
              {data?.network_identity.network_name || 'N/A'}
            </p>
          </div>
          <div>
            <p className="text-sm font-body text-gray-medium mb-1">MCC (Mobile Country Code)</p>
            <p className="text-xl font-body text-gray-dark">
              {data?.network_identity.mcc || 'N/A'}
            </p>
          </div>
          <div>
            <p className="text-sm font-body text-gray-medium mb-1">MNC (Mobile Network Code)</p>
            <p className="text-xl font-body text-gray-dark">
              {data?.network_identity.mnc || 'N/A'}
            </p>
          </div>
          <div>
            <p className="text-sm font-body text-gray-medium mb-1">Tracking Area Code (TAC)</p>
            <p className="text-xl font-body text-gray-dark">
              {data?.network_identity.tac || 'N/A'}
            </p>
          </div>
          <div>
            <p className="text-sm font-body text-gray-medium mb-1">Open5GS Host</p>
            <p className="text-xl font-body text-gray-dark">{data?.host || 'N/A'}</p>
          </div>
        </div>
      </Card>

      {/* eNodeB Configuration */}
      {data?.enodeb_config && (
        <Card
          title="eNodeB Configuration"
          subtitle="Use these settings when configuring your eNodeB"
          className="bg-gradient-to-br from-green-50 to-emerald-50 border-green-200"
        >
          <Table
            data={[
              { setting: 'MME IP Address', value: data.enodeb_config.mme_ip },
              { setting: 'MME Port', value: String(data.enodeb_config.mme_port) },
              { setting: 'PLMN ID', value: data.enodeb_config.plmn_id },
              { setting: 'TAC', value: String(data.enodeb_config.tac) },
            ]}
            columns={[
              {
                key: 'setting',
                header: 'Setting',
                render: (value) => (
                  <span className="font-heading text-gray-charcoal">{value}</span>
                ),
              },
              {
                key: 'value',
                header: 'Value',
                render: (value) => (
                  <span className="font-mono text-primary-deep font-semibold">{value}</span>
                ),
              },
            ]}
          />
        </Card>
      )}

      {/* Access Point Names */}
      <Card
        title="Access Point Names (APNs)"
        subtitle={`${data?.apns.total || 0} APN(s) configured`}
      >
        {data && data.apns.total > 0 ? (
          <Table
            data={data.apns.list}
            columns={[
              {
                key: 'name',
                header: 'APN Name',
                render: (value) => (
                  <span className="font-heading text-gray-charcoal">{value}</span>
                ),
              },
              {
                key: 'downlink_kbps',
                header: 'Downlink Bandwidth',
                render: (value) => (
                  <span className="font-body text-primary-deep">{value}</span>
                ),
              },
              {
                key: 'uplink_kbps',
                header: 'Uplink Bandwidth',
                render: (value) => (
                  <span className="font-body text-primary-deep">{value}</span>
                ),
              },
            ]}
          />
        ) : (
          <p className="text-center text-gray-medium font-body py-8">No APNs configured</p>
        )}
      </Card>

      {/* Network Details */}
      <Card title="Configuration Details" className="bg-gray-50">
        <div className="prose prose-sm max-w-none">
          <p className="text-gray-dark font-body">
            This network configuration is read from the Open5GS system and represents the current
            operational parameters. The configuration is stored in YAML files and MongoDB.
          </p>
          <div className="mt-4 space-y-2">
            <p className="text-sm text-gray-medium font-body">
              <strong>PLMNID Format:</strong> {data?.network_identity.mcc}
              {data?.network_identity.mnc} (MCC-MNC)
            </p>
            <p className="text-sm text-gray-medium font-body">
              <strong>Bandwidth Units:</strong> Kbps (Kilobits per second)
            </p>
            <p className="text-sm text-gray-medium font-body">
              <strong>Default APN:</strong> internet (best-effort QoS)
            </p>
            <p className="text-sm text-gray-medium font-body">
              <strong>UE IP Pool:</strong> 10.48.99.0/24
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
};
