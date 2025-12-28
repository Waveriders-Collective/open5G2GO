import React, { useState } from 'react';
import { X, AlertTriangle } from 'lucide-react';
import { Button } from '../ui';
import { api } from '../../services/api';
import type { Subscriber } from '../../types/open5gs';

interface DeleteSubscriberModalProps {
  isOpen: boolean;
  subscriber: Subscriber | null;
  onClose: () => void;
  onSuccess: () => void;
}

export const DeleteSubscriberModal: React.FC<DeleteSubscriberModalProps> = ({
  isOpen,
  subscriber,
  onClose,
  onSuccess,
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDelete = async () => {
    if (!subscriber) return;

    setLoading(true);
    setError(null);

    try {
      const result = await api.deleteSubscriber(subscriber.imsi);
      if (result.success) {
        onSuccess();
        onClose();
      } else {
        setError(result.error || 'Failed to delete device');
      }
    } catch (err: unknown) {
      const error = err as { response?: { data?: { error?: string } }; message?: string };
      setError(error.response?.data?.error || error.message || 'Failed to delete device');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen || !subscriber) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h3 className="text-xl font-heading text-gray-charcoal">Delete Device</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-4">
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3">
              <p className="text-sm text-red-800 font-body">{error}</p>
            </div>
          )}

          <div className="flex items-start space-x-3">
            <AlertTriangle className="w-6 h-6 text-red-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-body text-gray-dark">
                Are you sure you want to delete this device?
              </p>
              <div className="mt-3 bg-gray-50 rounded-lg p-3">
                <p className="text-sm font-body text-gray-dark">
                  <span className="font-semibold">Name:</span> {subscriber.name}
                </p>
                <p className="text-sm font-body text-gray-dark">
                  <span className="font-semibold">IMSI:</span> {subscriber.imsi}
                </p>
                <p className="text-sm font-body text-gray-dark">
                  <span className="font-semibold">IP:</span> {subscriber.ip}
                </p>
              </div>
              <p className="text-sm text-red-600 mt-3 font-body">
                This action cannot be undone.
              </p>
            </div>
          </div>

          <div className="flex space-x-3 pt-4">
            <Button
              type="button"
              variant="primary"
              onClick={handleDelete}
              disabled={loading}
              className="flex-1 bg-red-600 hover:bg-red-700"
            >
              {loading ? 'Deleting...' : 'Delete Device'}
            </Button>
            <Button type="button" variant="secondary" onClick={onClose} disabled={loading}>
              Cancel
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};
