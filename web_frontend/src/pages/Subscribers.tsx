// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (c) 2025 Waveriders Collective Inc.

import React, { useEffect, useState } from 'react';
import { UserPlus, RefreshCw, Pencil, Trash2, Eye } from 'lucide-react';
import { Button, Card, Table, LoadingSpinner, Badge } from '../components/ui';
import { AddSubscriberModal, EditSubscriberModal, DeleteSubscriberModal, ViewSubscriberModal } from '../components/subscribers';
import { api } from '../services/api';
import type { ListSubscribersResponse, Subscriber } from '../types/open5gs';

export const Subscribers: React.FC = () => {
  const [data, setData] = useState<ListSubscribersResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedSubscriber, setSelectedSubscriber] = useState<Subscriber | null>(null);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [isViewModalOpen, setIsViewModalOpen] = useState(false);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await api.listSubscribers();
      setData(result);
    } catch (err: unknown) {
      const error = err as { response?: { data?: { error?: string } }; message?: string };
      setError(error.response?.data?.error || error.message || 'Failed to load devices');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const filteredSubscribers = data?.subscribers.filter(
    (sub) =>
      sub.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      sub.imsi.includes(searchTerm) ||
      sub.ip.includes(searchTerm)
  );

  const handleView = (subscriber: Subscriber) => {
    setSelectedSubscriber(subscriber);
    setIsViewModalOpen(true);
  };

  const handleEdit = (subscriber: Subscriber) => {
    setSelectedSubscriber(subscriber);
    setIsEditModalOpen(true);
  };

  const handleDelete = (subscriber: Subscriber) => {
    setSelectedSubscriber(subscriber);
    setIsDeleteModalOpen(true);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-3xl font-heading text-gray-charcoal">Devices</h2>
        <div className="flex space-x-3">
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
          <Button
            variant="primary"
            size="md"
            onClick={() => setIsModalOpen(true)}
            className="flex items-center space-x-2"
          >
            <UserPlus className="w-4 h-4" />
            <span>Add Device</span>
          </Button>
        </div>
      </div>

      {loading && !data ? (
        <div className="flex items-center justify-center h-64">
          <LoadingSpinner size="lg" />
        </div>
      ) : error ? (
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <p className="text-red-800 font-body">Error: {error}</p>
          <Button variant="primary" onClick={fetchData} className="mt-4">
            Retry
          </Button>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card className="bg-primary-light/20">
              <div className="text-center">
                <p className="text-sm font-body text-gray-medium">Total Devices</p>
                <p className="text-3xl font-heading text-gray-charcoal mt-2">{data?.total || 0}</p>
              </div>
            </Card>
            <Card className="bg-primary-light/20">
              <div className="text-center">
                <p className="text-sm font-body text-gray-medium">Last Updated</p>
                <p className="text-lg font-body text-gray-dark mt-2">
                  {data?.timestamp ? new Date(data.timestamp).toLocaleTimeString() : 'N/A'}
                </p>
              </div>
            </Card>
            <Card className="bg-primary-light/20">
              <div className="text-center">
                <p className="text-sm font-body text-gray-medium">Mobile Network</p>
                <p className="text-lg font-body text-gray-dark mt-2">{data?.host || 'N/A'}</p>
              </div>
            </Card>
          </div>

          <Card>
            <div className="mb-4">
              <input
                type="text"
                placeholder="Search by name, IMSI, or IP address..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary font-body"
              />
            </div>

            {filteredSubscribers && filteredSubscribers.length > 0 ? (
              <Table
                data={filteredSubscribers}
                columns={[
                  { key: 'name', header: 'Device Name' },
                  { key: 'imsi', header: 'IMSI' },
                  { key: 'ip', header: 'Static IP' },
                  {
                    key: 'apn',
                    header: 'APN',
                    render: (value) => (
                      <Badge variant="info">{(value || 'internet').toUpperCase()}</Badge>
                    ),
                  },
                  {
                    key: 'actions',
                    header: 'Actions',
                    render: (_: unknown, row: Subscriber) => (
                      <div className="flex space-x-2">
                        <button
                          onClick={() => handleView(row)}
                          className="p-1 text-gray-500 hover:text-primary"
                          title="View details"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleEdit(row)}
                          className="p-1 text-gray-500 hover:text-primary"
                          title="Edit device"
                        >
                          <Pencil className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDelete(row)}
                          className="p-1 text-gray-500 hover:text-red-600"
                          title="Delete device"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    ),
                  },
                ]}
              />
            ) : (
              <p className="text-center text-gray-medium font-body py-8">
                {searchTerm ? 'No devices match your search' : 'No devices provisioned'}
              </p>
            )}
          </Card>
        </>
      )}

      <AddSubscriberModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSuccess={fetchData}
      />

      <EditSubscriberModal
        isOpen={isEditModalOpen}
        subscriber={selectedSubscriber}
        onClose={() => setIsEditModalOpen(false)}
        onSuccess={fetchData}
      />

      <DeleteSubscriberModal
        isOpen={isDeleteModalOpen}
        subscriber={selectedSubscriber}
        onClose={() => setIsDeleteModalOpen(false)}
        onSuccess={fetchData}
      />

      <ViewSubscriberModal
        isOpen={isViewModalOpen}
        subscriber={selectedSubscriber}
        onClose={() => setIsViewModalOpen(false)}
      />
    </div>
  );
};
