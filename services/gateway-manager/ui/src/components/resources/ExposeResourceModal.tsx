import { useState } from 'react';
import { Modal, Button } from '../common';
import { useCreateExposureChange } from '../../hooks/useExposureChanges';
import type { Resource } from '../../types';

interface ExposeResourceModalProps {
  isOpen: boolean;
  onClose: () => void;
  resource: Resource | null;
}

export const ExposeResourceModal = ({
  isOpen,
  onClose,
  resource,
}: ExposeResourceModalProps) => {
  const [rateLimit, setRateLimit] = useState<number>(100);
  const createChange = useCreateExposureChange();

  if (!resource) return null;

  const handleSubmit = async () => {
    try {
      await createChange.mutateAsync({
        resource_id: resource.id,
        change_type: 'add',
        settings_after: {
          rate_limit: rateLimit,
        },
        requested_by: 'admin', // TODO: Get from auth context
      });
      onClose();
    } catch (error) {
      console.error('Failed to create exposure change:', error);
    }
  };

  const getPreviewEndpoint = () => {
    if (resource.type === 'workflow') {
      return `/gateway/v1/workflows/trigger/${resource.source_id}`;
    } else if (resource.type === 'connection') {
      return `/gateway/v1/data/${resource.id}/{operation}`;
    }
    return `/gateway/v1/resources/${resource.id}`;
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Expose Resource to Gateway"
      size="lg"
      footer={
        <div className="flex items-center justify-end space-x-3">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={createChange.isPending}
          >
            {createChange.isPending ? 'Creating...' : 'Create Draft'}
          </Button>
        </div>
      }
    >
      <div className="space-y-6">
        {/* Resource Details */}
        <div>
          <h4 className="text-sm font-medium text-gray-900 mb-3">
            Resource Details
          </h4>
          <div className="bg-gray-50 rounded-lg p-4 space-y-2">
            <div className="flex justify-between">
              <span className="text-sm font-medium text-gray-600">Name:</span>
              <span className="text-sm text-gray-900">{resource.source_id}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm font-medium text-gray-600">Type:</span>
              <span className="text-sm text-gray-900 capitalize">{resource.type}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm font-medium text-gray-600">Source:</span>
              <span className="text-sm text-gray-900">{resource.source}</span>
            </div>
          </div>
        </div>

        {/* Endpoint Preview */}
        <div>
          <h4 className="text-sm font-medium text-gray-900 mb-2">
            Gateway Endpoint Preview
          </h4>
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
            <code className="text-sm text-blue-900 font-mono">
              POST {getPreviewEndpoint()}
            </code>
          </div>
          <p className="text-xs text-gray-500 mt-2">
            This endpoint will be created when the change is approved and deployed
          </p>
        </div>

        {/* Settings */}
        <div>
          <h4 className="text-sm font-medium text-gray-900 mb-3">
            Exposure Settings
          </h4>
          <div className="space-y-4">
            {/* Rate Limit */}
            <div>
              <label htmlFor="rateLimit" className="block text-sm font-medium text-gray-700 mb-2">
                Rate Limit (requests per minute)
              </label>
              <div className="flex items-center space-x-4">
                <input
                  type="range"
                  id="rateLimit"
                  min="10"
                  max="1000"
                  step="10"
                  value={rateLimit}
                  onChange={(e) => setRateLimit(Number(e.target.value))}
                  className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                />
                <input
                  type="number"
                  value={rateLimit}
                  onChange={(e) => setRateLimit(Number(e.target.value))}
                  min="10"
                  max="1000"
                  className="w-20 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
              <div className="flex justify-between mt-2">
                <span className="text-xs text-gray-500">Lower (10 req/min)</span>
                <span className="text-xs text-gray-500">Higher (1000 req/min)</span>
              </div>
            </div>

            {/* Info Box */}
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
              <p className="text-sm text-yellow-800">
                <strong>Note:</strong> This creates a draft change that requires approval before deployment.
                You can adjust these settings later in the Gateway Manager.
              </p>
            </div>
          </div>
        </div>

        {/* Error Display */}
        {createChange.isError && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3">
            <p className="text-sm text-red-800">
              Failed to create exposure change. Please try again.
            </p>
          </div>
        )}
      </div>
    </Modal>
  );
};
