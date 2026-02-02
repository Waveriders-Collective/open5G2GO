// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (c) 2025 Waveriders Collective Inc.

import React, { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import { Button } from '../ui';
import { LoadingSpinner } from '../ui';
import { api } from '../../services/api';
import type { Subscriber, GetSubscriberResponse } from '../../types/open5gs';

interface ViewSubscriberModalProps {
  isOpen: boolean;
  subscriber: Subscriber | null;
  onClose: () => void;
}

export const ViewSubscriberModal: React.FC<ViewSubscriberModalProps> = ({
  isOpen,
  subscriber,
  onClose,
}) => {
  const [details, setDetails] = useState<GetSubscriberResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && subscriber) {
      fetchDetails();
    } else {
      setDetails(null);
      setError(null);
    }
  }, [isOpen, subscriber]);

  const fetchDetails = async () => {
    if (!subscriber) return;

    setLoading(true);
    setError(null);

    try {
      const result = await api.getSubscriber(subscriber.imsi);
      if (result.success) {
        setDetails(result);
      } else {
        setError(result.error || 'Failed to fetch device details');
      }
    } catch (err: unknown) {
      const error = err as { response?: { data?: { error?: string } }; message?: string };
      setError(error.response?.data?.error || error.message || 'Failed to fetch device details');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen || !subscriber) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-lg w-full mx-4 max-h-[80vh] overflow-hidden flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h3 className="text-xl font-heading text-gray-charcoal">Device Details</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 overflow-y-auto flex-1">
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
              <p className="text-sm text-red-800 font-body">{error}</p>
            </div>
          )}

          {loading ? (
            <div className="flex items-center justify-center py-12">
              <LoadingSpinner size="lg" />
            </div>
          ) : (
            <div className="space-y-4">
              {/* Basic Info */}
              <div className="bg-gray-50 rounded-lg p-4">
                <h4 className="text-sm font-semibold text-gray-dark mb-3">Basic Information</h4>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <p className="text-xs text-gray-medium font-body">Device Name</p>
                    <p className="text-sm font-body text-gray-dark">{subscriber.name}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-medium font-body">IMSI</p>
                    <p className="text-sm font-body font-mono text-gray-dark">{subscriber.imsi}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-medium font-body">Static IP</p>
                    <p className="text-sm font-body font-mono text-gray-dark">{subscriber.ip}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-medium font-body">APN</p>
                    <p className="text-sm font-body text-gray-dark">{subscriber.apn}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-medium font-body">Max Downlink</p>
                    <p className="text-sm font-body font-mono text-gray-dark">
                      {details?.ambr?.downlink || 'N/A'}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-medium font-body">Max Uplink</p>
                    <p className="text-sm font-body font-mono text-gray-dark">
                      {details?.ambr?.uplink || 'N/A'}
                    </p>
                  </div>
                </div>
              </div>

              {/* Extended Details from API */}
              {details?.data && (
                <div className="bg-gray-50 rounded-lg p-4">
                  <h4 className="text-sm font-semibold text-gray-dark mb-3">Open5GS Configuration</h4>
                  <pre className="text-xs font-mono text-gray-dark bg-white p-3 rounded border overflow-x-auto">
                    {JSON.stringify(details.data, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="px-6 py-4 border-t border-gray-200">
          <Button type="button" variant="secondary" onClick={onClose} className="w-full">
            Close
          </Button>
        </div>
      </div>
    </div>
  );
};
