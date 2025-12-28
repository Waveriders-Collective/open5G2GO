import React, { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import { Button } from '../ui';
import { api } from '../../services/api';
import type { Subscriber, UpdateSubscriberRequest } from '../../types/attocore';

interface EditSubscriberModalProps {
  isOpen: boolean;
  subscriber: Subscriber | null;
  onClose: () => void;
  onSuccess: () => void;
}

export const EditSubscriberModal: React.FC<EditSubscriberModalProps> = ({
  isOpen,
  subscriber,
  onClose,
  onSuccess,
}) => {
  const [formData, setFormData] = useState<UpdateSubscriberRequest>({
    name: '',
    ip: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Populate form when subscriber changes
  useEffect(() => {
    if (subscriber) {
      setFormData({
        name: subscriber.name,
        ip: subscriber.ip,
      });
      setError(null);
      setSuccess(null);
    }
  }, [subscriber]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!subscriber) return;

    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const result = await api.updateSubscriber(subscriber.imsi, formData);
      if (result.success) {
        setSuccess(result.message || 'Subscriber updated successfully');
        setTimeout(() => {
          onSuccess();
          onClose();
          setSuccess(null);
        }, 1500);
      } else {
        setError(result.error || 'Failed to update subscriber');
      }
    } catch (err: any) {
      setError(err.response?.data?.error || err.message || 'Failed to update subscriber');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen || !subscriber) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h3 className="text-xl font-heading text-gray-charcoal">Edit Subscriber</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3">
              <p className="text-sm text-red-800 font-body">{error}</p>
            </div>
          )}

          {success && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-3">
              <p className="text-sm text-green-800 font-body">{success}</p>
            </div>
          )}

          <div>
            <label className="block text-sm font-body text-gray-dark mb-1">
              IMSI (read-only)
            </label>
            <input
              type="text"
              value={subscriber.imsi}
              disabled
              className="w-full px-3 py-2 border border-gray-200 rounded-md bg-gray-50 text-gray-500 font-body font-mono"
            />
          </div>

          <div>
            <label className="block text-sm font-body text-gray-dark mb-1">
              Device Name
            </label>
            <input
              type="text"
              value={formData.name || ''}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary font-body"
            />
          </div>

          <div>
            <label className="block text-sm font-body text-gray-dark mb-1">
              Static IP Address
            </label>
            <input
              type="text"
              value={formData.ip || ''}
              onChange={(e) => setFormData({ ...formData, ip: e.target.value })}
              placeholder="e.g., 10.48.100.11"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary font-body font-mono"
            />
          </div>

          <div className="flex space-x-3 pt-4">
            <Button type="submit" variant="primary" disabled={loading} className="flex-1">
              {loading ? 'Saving...' : 'Save Changes'}
            </Button>
            <Button type="button" variant="secondary" onClick={onClose} disabled={loading}>
              Cancel
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};
