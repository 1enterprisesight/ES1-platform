import { useState } from 'react';
import { Card, CardBody, StatusBadge, EmptyState, Button } from '../common';
import { formatDistanceToNow } from 'date-fns';
import type { ActiveConfig, Exposure } from '../../types';

interface ConfigViewProps {
  config: ActiveConfig;
  exposures: Exposure[];
  mode?: 'view' | 'edit';
  actions?: React.ReactNode;
  onEditResource?: (exposureId: string) => void;
  onRemoveResource?: (exposureId: string) => void;
}

export const ConfigView = ({
  config,
  exposures,
  mode = 'view',
  actions,
  onEditResource,
  onRemoveResource,
}: ConfigViewProps) => {
  const [showConfigJson, setShowConfigJson] = useState(false);

  return (
    <div>
      {/* Section 1: Active Config Info Card - EXTRACTED FROM Active Tab */}
      {config && (
        <div className="mb-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-3">
            Current Active Configuration
          </h3>
          <div className="text-sm text-gray-700 space-y-1 mb-3">
            <p>
              <span className="font-medium">Version:</span> v{config.version}
            </p>
            <p>
              <span className="font-medium">Endpoints:</span> {exposures.length} active
            </p>
            <p>
              <span className="font-medium">Last Deployed:</span>{' '}
              {formatDistanceToNow(new Date(config.deployed_at))} ago by {config.deployed_by}
            </p>
            <p>
              <span className="font-medium">Status:</span>{' '}
              <span className="text-green-600 font-medium">✓ Healthy</span>
            </p>
          </div>
          <div className="flex space-x-2">
            <Button
              size="sm"
              onClick={() => setShowConfigJson(!showConfigJson)}
            >
              {showConfigJson ? 'Hide' : 'View'} Complete Config JSON
            </Button>
            {actions}
          </div>
        </div>
      )}

      {/* Section 2: Resource Count - EXTRACTED FROM Active Tab */}
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-gray-600">
          {exposures.length} resource{exposures.length !== 1 ? 's' : ''} active on gateway
        </p>
      </div>

      {/* Section 2: Resource Cards Grid - EXTRACTED FROM Active Tab */}
      {exposures.length === 0 ? (
        <EmptyState
          icon={<span className="text-6xl">🚀</span>}
          title="No active exposures"
          description="Deploy some resources to see them here"
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {exposures.map((exposure) => (
            <Card key={exposure.id}>
              <CardBody>
                <div className="flex items-start justify-between mb-3">
                  <StatusBadge status="deployed" />
                  <span className="text-xs text-gray-500">
                    {exposure.resource?.type.toUpperCase()}
                  </span>
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  {exposure.resource?.name || exposure.resource?.source_id}
                </h3>
                <div className="text-sm text-gray-600 space-y-1">
                  <p>Endpoint: {exposure.generated_config.endpoint}</p>
                  <p>Rate Limit: {exposure.settings.rate_limit} req/min</p>
                </div>
                {mode === 'edit' && (
                  <div className="flex space-x-2 mt-3">
                    <button
                      onClick={() => onEditResource?.(exposure.id)}
                      className="text-sm text-primary hover:underline"
                    >
                      [Edit]
                    </button>
                    <button
                      onClick={() => onRemoveResource?.(exposure.id)}
                      className="text-sm text-red-600 hover:underline"
                    >
                      [Remove]
                    </button>
                  </div>
                )}
              </CardBody>
            </Card>
          ))}
        </div>
      )}

      {/* Section 3: Config JSON - EXTRACTED FROM Active Tab Modal */}
      {showConfigJson && config && (
        <div className="mt-6">
          <div className="bg-gray-900 text-green-400 p-4 rounded-lg overflow-x-auto max-h-[70vh]">
            <pre className="text-xs font-mono">
              {JSON.stringify(config.config_snapshot, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
};
