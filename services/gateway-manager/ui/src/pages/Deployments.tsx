import { useState } from 'react';
import { PageLayout } from '../components/layout';
import { StatusBadge, Card, Modal, LoadingSpinner, EmptyState } from '../components/common';
import { useBranding } from '../hooks/useBranding';
import { useDeployments } from '../hooks/useDeployments';
import type { Deployment } from '../types';
import { format, formatDistanceToNow, differenceInSeconds } from 'date-fns';

export const Deployments = () => {
  const branding = useBranding();
  const [selectedDeployment, setSelectedDeployment] = useState<Deployment | null>(null);

  // Fetch deployments from API
  const { data: deployments, isLoading, error } = useDeployments(50);

  const getDuration = (deployment: Deployment) => {
    if (!deployment.completed_at) return null;
    const seconds = differenceInSeconds(
      new Date(deployment.completed_at),
      new Date(deployment.deployed_at)
    );
    return seconds;
  };

  // Loading state
  if (isLoading) {
    return (
      <PageLayout title="Deployments">
        <div className="flex items-center justify-center py-20">
          <LoadingSpinner size="lg" />
        </div>
      </PageLayout>
    );
  }

  // Error state
  if (error) {
    return (
      <PageLayout title="Deployments">
        <EmptyState
          icon={<span className="text-6xl">⚠️</span>}
          title="Failed to load deployments"
          description={error instanceof Error ? error.message : 'Unknown error occurred'}
        />
      </PageLayout>
    );
  }

  const deploymentsList = deployments || [];
  const inProgressCount = deploymentsList.filter(d => d.status === 'in_progress').length;

  return (
    <PageLayout title="Deployments">
      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="flex space-x-8">
          <button className="py-4 px-1 border-b-2 border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 font-medium text-sm">
            In Progress ({inProgressCount})
          </button>
          <button className="py-4 px-1 border-b-2 border-primary text-primary font-medium text-sm">
            History ({deploymentsList.length})
          </button>
        </nav>
      </div>

      {/* Search */}
      <div className="mb-6">
        <input
          type="text"
          placeholder="Search deployments..."
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
        />
      </div>

      {/* Deployments Table */}
      {deploymentsList.length === 0 ? (
        <EmptyState
          icon={<span className="text-6xl">📋</span>}
          title="No deployments yet"
          description="Deployments will appear here once you deploy configurations to the gateway"
        />
      ) : (
        <Card>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Date
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Deployed By
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Version
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Duration
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Health Check
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {deploymentsList.map((deployment) => (
                  <tr
                    key={deployment.id}
                    className="hover:bg-gray-50 cursor-pointer"
                    onClick={() => setSelectedDeployment(deployment)}
                  >
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900">
                        {formatDistanceToNow(new Date(deployment.deployed_at))} ago
                      </div>
                      <div className="text-xs text-gray-500">
                        {format(new Date(deployment.deployed_at), 'MMM dd, HH:mm')}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {deployment.deployed_by}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <StatusBadge status={deployment.status} />
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {deployment.version_id}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {getDuration(deployment) ? `${getDuration(deployment)}s` : '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {deployment.health_check_passed === true ? (
                        <span className="text-green-600 text-sm">✓ Passed</span>
                      ) : deployment.health_check_passed === false ? (
                        <span className="text-red-600 text-sm">✗ Failed</span>
                      ) : (
                        <span className="text-gray-400 text-sm">-</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Deployment Details Modal */}
      {selectedDeployment && (
        <Modal
          isOpen={!!selectedDeployment}
          onClose={() => setSelectedDeployment(null)}
          title={`${branding.terminology.deployment} Details`}
          size="lg"
        >
          <div className="space-y-6">
            {/* Status */}
            <div>
              <p className="text-sm font-medium text-gray-500 mb-2">Status</p>
              <StatusBadge status={selectedDeployment.status} />
            </div>

            {/* Version */}
            <div>
              <p className="text-sm font-medium text-gray-500 mb-2">Version</p>
              <p className="text-sm text-gray-900">{selectedDeployment.version_id}</p>
            </div>

            {/* Timeline */}
            <div>
              <p className="text-sm font-medium text-gray-500 mb-2">Timeline</p>
              <div className="text-sm text-gray-700 space-y-1">
                <p>
                  Started:{' '}
                  {format(
                    new Date(selectedDeployment.deployed_at),
                    'MMM dd, yyyy HH:mm:ss'
                  )}
                </p>
                {selectedDeployment.completed_at && (
                  <p>
                    Completed:{' '}
                    {format(
                      new Date(selectedDeployment.completed_at),
                      'MMM dd, yyyy HH:mm:ss'
                    )}
                  </p>
                )}
                {getDuration(selectedDeployment) && (
                  <p>Duration: {getDuration(selectedDeployment)} seconds</p>
                )}
                <p>Deployed by: {selectedDeployment.deployed_by}</p>
              </div>
            </div>

            {/* Health Check */}
            <div>
              <p className="text-sm font-medium text-gray-500 mb-2">Health Check</p>
              <div className="text-sm text-gray-700">
                {selectedDeployment.health_check_passed === true ? (
                  <span className="text-green-600">✓ Passed</span>
                ) : selectedDeployment.health_check_passed === false ? (
                  <span className="text-red-600">✗ Failed</span>
                ) : (
                  <span className="text-gray-400">Not available</span>
                )}
              </div>
            </div>

            {/* Error Message */}
            {selectedDeployment.error_message && (
              <div className="p-4 bg-red-50 rounded-lg">
                <p className="text-sm font-medium text-red-800 mb-1">Error</p>
                <p className="text-sm text-red-700">
                  {selectedDeployment.error_message}
                </p>
              </div>
            )}
          </div>
        </Modal>
      )}
    </PageLayout>
  );
};
