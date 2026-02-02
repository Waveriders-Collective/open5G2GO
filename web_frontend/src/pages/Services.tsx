// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (c) 2025 Waveriders Collective Inc.

import React, { useEffect, useState, useCallback } from 'react';
import { Server, RefreshCw, AlertCircle, CheckCircle, XCircle, HelpCircle } from 'lucide-react';
import { Card, Badge, LoadingSpinner } from '../components/ui';
import { api } from '../services/api';
import type { ServicesResponse, ServiceInfo } from '../types/open5gs';

export const Services: React.FC = () => {
  const [data, setData] = useState<ServicesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setError(null);
      const result = await api.getServices();
      setData(result);
      setLastRefresh(new Date());
    } catch (err: unknown) {
      const error = err as { response?: { data?: { error?: string } }; message?: string };
      setError(error.response?.data?.error || error.message || 'Failed to load services');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'stopped':
        return <XCircle className="w-5 h-5 text-red-500" />;
      case 'error':
        return <AlertCircle className="w-5 h-5 text-red-500" />;
      default:
        return <HelpCircle className="w-5 h-5 text-gray-500" />;
    }
  };

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'running':
        return 'bg-green-500';
      case 'stopped':
      case 'error':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  const getBadgeVariant = (status: string): 'success' | 'error' | 'warning' | 'neutral' => {
    switch (status) {
      case 'running':
        return 'success';
      case 'stopped':
      case 'error':
        return 'error';
      default:
        return 'neutral';
    }
  };

  const groupServicesByCategory = (services: ServiceInfo[]) => {
    const grouped: Record<string, ServiceInfo[]> = {};
    services.forEach((service) => {
      const category = service.category || 'Other';
      if (!grouped[category]) {
        grouped[category] = [];
      }
      grouped[category].push(service);
    });
    return grouped;
  };

  if (loading && !data) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner />
      </div>
    );
  }

  const groupedServices = data ? groupServicesByCategory(data.services) : {};

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-heading text-accent-charcoal">Services</h1>
          <p className="text-gray-medium font-body mt-1">
            Open5GS Core Network Services Status
          </p>
        </div>
        <button
          onClick={fetchData}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-deep transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Error Alert */}
      {error && (
        <Card className="bg-red-50 border border-red-200">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-500" />
            <div>
              <h3 className="font-semibold text-red-800">Error Loading Services</h3>
              <p className="text-sm text-red-700">{error}</p>
            </div>
          </div>
        </Card>
      )}

      {/* Summary Cards */}
      {data && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <Card className="text-center">
            <div className="text-3xl font-heading text-accent-charcoal">{data.summary.total}</div>
            <div className="text-sm text-gray-medium">Total</div>
          </Card>
          <Card className="text-center bg-green-50">
            <div className="text-3xl font-heading text-green-600">{data.summary.running}</div>
            <div className="text-sm text-gray-medium">Running</div>
          </Card>
          <Card className="text-center bg-red-50">
            <div className="text-3xl font-heading text-red-600">{data.summary.stopped}</div>
            <div className="text-sm text-gray-medium">Stopped</div>
          </Card>
          <Card className="text-center bg-red-50">
            <div className="text-3xl font-heading text-red-600">{data.summary.error}</div>
            <div className="text-sm text-gray-medium">Error</div>
          </Card>
          <Card className="text-center bg-gray-50">
            <div className="text-3xl font-heading text-gray-600">{data.summary.unknown}</div>
            <div className="text-sm text-gray-medium">Unknown</div>
          </Card>
        </div>
      )}

      {/* Services by Category */}
      {Object.entries(groupedServices).map(([category, services]) => (
        <Card key={category}>
          <div className="flex items-center gap-2 mb-4">
            <Server className="w-5 h-5 text-primary" />
            <h2 className="text-xl font-heading text-accent-charcoal">{category}</h2>
            <span className="text-sm text-gray-medium">({services.length} services)</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {services.map((service) => (
              <div
                key={service.name}
                className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow bg-white"
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <div className={`w-2.5 h-2.5 rounded-full ${getStatusColor(service.status)}`} />
                    <h3 className="font-semibold text-accent-charcoal uppercase">{service.name}</h3>
                  </div>
                  {getStatusIcon(service.status)}
                </div>

                <p className="text-sm text-gray-medium mb-3">{service.display_name}</p>

                <div className="flex items-center justify-between">
                  <Badge variant={getBadgeVariant(service.status)}>
                    {service.status.charAt(0).toUpperCase() + service.status.slice(1)}
                  </Badge>
                  {service.details && (
                    <span className="text-xs text-gray-medium">{service.details}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </Card>
      ))}

      {/* Info Footer */}
      <Card className="bg-gray-50">
        <div className="flex items-center justify-between text-sm text-gray-medium">
          <div className="flex items-center gap-4">
            <span>Check Method: <strong>{data?.check_method || 'N/A'}</strong></span>
            <span>Host: <strong>{data?.host || 'N/A'}</strong></span>
          </div>
          {lastRefresh && (
            <span>Last updated: {lastRefresh.toLocaleTimeString()}</span>
          )}
        </div>
      </Card>
    </div>
  );
};
