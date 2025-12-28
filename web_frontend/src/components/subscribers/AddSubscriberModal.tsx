import React, { useState } from 'react';
import { X, HelpCircle } from 'lucide-react';
import { Button } from '../ui';
import { api } from '../../services/api';
import type { AddSubscriberRequest } from '../../types/open5gs';

interface AddSubscriberModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

// IMSI prefix for Open5GS (PLMN 315-010)
const IMSI_PREFIX = '31501000000';

export const AddSubscriberModal: React.FC<AddSubscriberModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [formData, setFormData] = useState<AddSubscriberRequest>({
    device_number: '',
    name: '',
    ip: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Generate full IMSI from 4-digit device number
  const getFullImsi = (deviceNumber: string): string => {
    const padded = deviceNumber.padStart(4, '0');
    return `${IMSI_PREFIX}${padded}`;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);

    // Validate device number
    const deviceNum = parseInt(formData.device_number, 10);
    if (isNaN(deviceNum) || deviceNum < 1 || deviceNum > 9999) {
      setError('Device number must be between 0001 and 9999');
      setLoading(false);
      return;
    }

    try {
      const result = await api.addSubscriber(formData);
      if (result.success) {
        setSuccess(
          `Successfully added ${result.subscriber.name} (IMSI: ${result.subscriber.imsi}, IP: ${result.subscriber.ip})`
        );
        setTimeout(() => {
          onSuccess();
          onClose();
          // Reset form
          setFormData({
            device_number: '',
            name: '',
            ip: '',
          });
          setSuccess(null);
        }, 2000);
      } else {
        setError(result.error || 'Failed to add device');
      }
    } catch (err: unknown) {
      const error = err as { response?: { data?: { error?: string } }; message?: string };
      setError(error.response?.data?.error || error.message || 'Failed to add device');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setFormData({ device_number: '', name: '', ip: '' });
    setError(null);
    setSuccess(null);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h3 className="text-xl font-heading text-gray-charcoal">Add New Device</h3>
          <button onClick={handleClose} className="text-gray-400 hover:text-gray-600">
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
              Device Number (last 4 digits of IMSI)
            </label>
            <input
              type="text"
              pattern="[0-9]{1,4}"
              maxLength={4}
              required
              placeholder="e.g., 0001"
              value={formData.device_number}
              onChange={(e) => {
                const value = e.target.value.replace(/\D/g, '').slice(0, 4);
                setFormData({ ...formData, device_number: value });
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary font-body font-mono text-lg"
            />
            <div className="flex items-start mt-2 text-xs text-gray-medium">
              <HelpCircle className="w-4 h-4 mr-1 flex-shrink-0 mt-0.5" />
              <span>
                Full IMSI will be: <span className="font-mono">{formData.device_number ? getFullImsi(formData.device_number) : `${IMSI_PREFIX}____`}</span>
              </span>
            </div>
          </div>

          <div>
            <label className="block text-sm font-body text-gray-dark mb-1">
              Device Name
            </label>
            <input
              type="text"
              required
              placeholder="e.g., CAM-01, TABLET-02"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary font-body"
            />
          </div>

          <div>
            <label className="block text-sm font-body text-gray-dark mb-1">
              IP Address (optional)
            </label>
            <input
              type="text"
              placeholder="e.g., 10.48.99.10"
              value={formData.ip || ''}
              onChange={(e) => setFormData({ ...formData, ip: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary font-body font-mono"
            />
            <p className="text-xs text-gray-medium mt-1">
              Leave blank for auto-assignment from 10.48.99.0/24 pool
            </p>
          </div>

          {/* APN Info (read-only for MVP) */}
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-sm font-body text-gray-dark">
              <strong>APN:</strong> internet (default)
            </p>
            <p className="text-sm font-body text-gray-dark">
              <strong>QoS:</strong> Best Effort (QCI 9)
            </p>
            <p className="text-xs text-gray-medium mt-1">
              Using default Open5GS settings for homelab use
            </p>
          </div>

          <div className="flex space-x-3 pt-4">
            <Button type="submit" variant="primary" disabled={loading} className="flex-1">
              {loading ? 'Adding Device...' : 'Add Device'}
            </Button>
            <Button type="button" variant="secondary" onClick={handleClose} disabled={loading}>
              Cancel
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};
