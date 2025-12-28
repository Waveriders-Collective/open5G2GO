import React, { useState } from 'react';
import { X } from 'lucide-react';
import { Button } from '../ui';
import { api } from '../../services/api';
import type { AddSubscriberRequest } from '../../types/attocore';

interface AddSubscriberModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const AddSubscriberModal: React.FC<AddSubscriberModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [formData, setFormData] = useState<AddSubscriberRequest>({
    device_number: 1,
    name_prefix: 'WR-VIDEO',
    dnn: 'video',
    ip_mode: 'old',
    imsi: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const result = await api.addSubscriber(formData);
      if (result.success) {
        setSuccess(
          `Successfully provisioned ${result.subscriber.name} (IMSI: ${result.subscriber.imsi}, IP: ${result.subscriber.ip})`
        );
        setTimeout(() => {
          onSuccess();
          onClose();
          // Reset form
          setFormData({
            device_number: 1,
            name_prefix: 'WR-VIDEO',
            dnn: 'video',
            ip_mode: 'old',
            imsi: '',
          });
          setSuccess(null);
        }, 2000);
      } else {
        setError(result.error || 'Failed to provision subscriber');
      }
    } catch (err: any) {
      setError(err.response?.data?.error || err.message || 'Failed to provision subscriber');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h3 className="text-xl font-heading text-gray-charcoal">Add New Subscriber</h3>
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
              IMSI (15 digits)
            </label>
            <input
              type="text"
              pattern="[0-9]{15}"
              maxLength={15}
              required
              placeholder="e.g., 315010123456789"
              value={formData.imsi || ''}
              onChange={(e) => {
                const value = e.target.value.replace(/\D/g, '').slice(0, 15);
                setFormData({ ...formData, imsi: value });
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary font-body font-mono"
            />
          </div>

          <div>
            <label className="block text-sm font-body text-gray-dark mb-1">
              Device Number (1-999)
            </label>
            <input
              type="number"
              min="1"
              max="999"
              required
              value={formData.device_number}
              onChange={(e) =>
                setFormData({ ...formData, device_number: parseInt(e.target.value) })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary font-body"
            />
            <p className="text-xs text-gray-medium mt-1">
              Used for IP address calculation and subscriber name
            </p>
          </div>

          <div>
            <label className="block text-sm font-body text-gray-dark mb-1">Name Prefix</label>
            <select
              value={formData.name_prefix}
              onChange={(e) => setFormData({ ...formData, name_prefix: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary font-body"
            >
              <option value="WR-VIDEO">WR-VIDEO (Standard Android/Video)</option>
              <option value="WR-iVIDEO">WR-iVIDEO (iPhone)</option>
              <option value="WR-VIDEO-e">WR-VIDEO-e (eSIM)</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-body text-gray-dark mb-1">
              Data Network Name (DNN)
            </label>
            <select
              value={formData.dnn}
              onChange={(e) => setFormData({ ...formData, dnn: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary font-body"
            >
              <option value="video">video</option>
              <option value="internet">internet</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-body text-gray-dark mb-1">IP Address Mode</label>
            <div className="space-y-2">
              <label className="flex items-center">
                <input
                  type="radio"
                  name="ip_mode"
                  value="old"
                  checked={formData.ip_mode === 'old'}
                  onChange={() => setFormData({ ...formData, ip_mode: 'old' })}
                  className="mr-2"
                />
                <span className="text-sm font-body text-gray-dark">
                  Old (10.48.100.x, offset +10)
                </span>
              </label>
              <label className="flex items-center">
                <input
                  type="radio"
                  name="ip_mode"
                  value="new"
                  checked={formData.ip_mode === 'new'}
                  onChange={() => setFormData({ ...formData, ip_mode: 'new' })}
                  className="mr-2"
                />
                <span className="text-sm font-body text-gray-dark">
                  New (10.48.98.x, direct)
                </span>
              </label>
            </div>
          </div>

          <div className="flex space-x-3 pt-4">
            <Button type="submit" variant="primary" disabled={loading} className="flex-1">
              {loading ? 'Provisioning...' : 'Add Subscriber'}
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
