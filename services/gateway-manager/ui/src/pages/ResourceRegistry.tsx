import { useState } from 'react';
import { PageLayout } from '../components/layout';
import { Card, CardBody, CardFooter, Button, EmptyState, LoadingSpinner } from '../components/common';
import { ExposeResourceModal } from '../components/resources/ExposeResourceModal';
import { useBranding } from '../hooks/useBranding';
import { useResources, useSyncAirflow } from '../hooks/useResources';
import { useExposureChanges } from '../hooks/useExposureChanges';
import { useActiveConfig } from '../hooks/useConfigVersions';
import type { ResourceType, Resource } from '../types';
import { formatDistanceToNow } from 'date-fns';

export const ResourceRegistry = () => {
  const branding = useBranding();
  const [filter, setFilter] = useState<ResourceType | 'all'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedResource, setSelectedResource] = useState<Resource | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Fetch resources from API
  const { data, isLoading, error } = useResources();
  const syncAirflow = useSyncAirflow();

  // Fetch active config and exposure changes
  const { data: activeConfig } = useActiveConfig();
  const { data: changesData } = useExposureChanges({ status: 'draft,pending_approval,approved' });

  const resources = data?.items || [];
  const changes = changesData?.items || [];

  // Get active config exposures from metadata (source of truth for what's deployed)
  const activeConfigExposures = activeConfig?.config_snapshot?.__ui_metadata?.exposures || [];

  const filteredResources = resources.filter((resource) => {
    const matchesFilter = filter === 'all' || resource.type === filter;
    const description = resource.resource_metadata?.description || '';
    const matchesSearch =
      searchQuery === '' ||
      resource.source_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      description.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  // Get resource status (deployed, pending, or available)
  // Uses activeConfig.config_snapshot.__ui_metadata.exposures as source of truth (version-specific)
  const getResourceStatus = (resourceId: string) => {
    // Check if resource is in the currently deployed active config
    const isDeployed = activeConfigExposures.some(
      (exp: any) => exp.resource_id === resourceId
    );
    if (isDeployed) {
      return { type: 'deployed' as const, label: 'Deployed', color: 'green' };
    }

    // Check if resource has pending change (draft, pending_approval, or approved but not deployed)
    const pendingChange = changes.find((change) => change.resource_id === resourceId);
    if (pendingChange) {
      if (pendingChange.status === 'approved') {
        return { type: 'pending' as const, label: 'Approved', color: 'blue' };
      }
      if (pendingChange.status === 'pending_approval') {
        return { type: 'pending' as const, label: 'Pending Approval', color: 'yellow' };
      }
      if (pendingChange.status === 'draft') {
        return { type: 'pending' as const, label: 'Draft', color: 'gray' };
      }
    }

    return { type: 'available' as const, label: 'Available', color: 'gray' };
  };

  const handleExposeResource = (resource: Resource) => {
    setSelectedResource(resource);
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedResource(null);
  };

  const getResourceIcon = (type: ResourceType) => {
    switch (type) {
      case 'workflow':
        return '🔵';
      case 'connection':
        return '🟢';
      case 'service':
        return '🟣';
    }
  };

  const getResourceTypeName = (type: ResourceType) => {
    switch (type) {
      case 'workflow':
        return branding.terminology.workflow;
      case 'connection':
        return branding.terminology.connection;
      case 'service':
        return branding.terminology.service;
    }
  };

  const getResourceDisplayName = (resource: Resource) => {
    // Try to get a human-readable name from metadata
    const metadata = resource.resource_metadata || {};

    // For workflows, use dag_id if available
    if (resource.type === 'workflow' && metadata.dag_id) {
      return metadata.dag_id;
    }

    // For connections, use conn_id if available
    if (resource.type === 'connection' && metadata.conn_id) {
      return metadata.conn_id;
    }

    // Fall back to name field or source_id
    return metadata.name || resource.source_id;
  };

  // Loading state
  if (isLoading) {
    return (
      <PageLayout title="Resource Registry">
        <div className="flex items-center justify-center py-20">
          <LoadingSpinner size="lg" />
        </div>
      </PageLayout>
    );
  }

  // Error state
  if (error) {
    return (
      <PageLayout title="Resource Registry">
        <EmptyState
          icon={<span className="text-6xl">⚠️</span>}
          title="Failed to load resources"
          description={error instanceof Error ? error.message : 'Unknown error occurred'}
        />
      </PageLayout>
    );
  }

  return (
    <PageLayout title="Resource Registry">
      {/* Search and Filters */}
      <div className="mb-6 space-y-4">
        <div className="flex items-center space-x-3">
          <input
            type="text"
            placeholder="Search resources..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
          />
          <Button
            onClick={() => syncAirflow.mutate()}
            disabled={syncAirflow.isPending}
          >
            {syncAirflow.isPending ? 'Syncing...' : '🔄 Sync from Airflow'}
          </Button>
        </div>

        <div className="flex items-center space-x-3">
          <span className="text-sm font-medium text-gray-700">Filters:</span>
          <div className="flex space-x-2">
            {(['all', 'workflow', 'connection', 'service'] as const).map(
              (type) => (
                <button
                  key={type}
                  onClick={() => setFilter(type)}
                  className={`px-3 py-1 text-sm font-medium rounded-lg transition-colors ${
                    filter === type
                      ? 'bg-primary text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {type === 'all'
                    ? 'All Types'
                    : getResourceTypeName(type as ResourceType)}
                </button>
              )
            )}
          </div>
        </div>

        <div className="flex items-center justify-between">
          <p className="text-sm text-gray-600">
            Showing {filteredResources.length} of {resources.length}{' '}
            resources
          </p>
        </div>
      </div>

      {/* Resource Cards Grid */}
      {filteredResources.length === 0 ? (
        <EmptyState
          icon={<span className="text-6xl">📦</span>}
          title="No resources found"
          description="Try adjusting your filters or search query"
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredResources.map((resource) => {
            const status = getResourceStatus(resource.id);

            return (
              <Card key={resource.id} hover>
                <CardBody>
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center space-x-2">
                      <span className="text-2xl">{getResourceIcon(resource.type as ResourceType)}</span>
                      <span className="text-xs font-medium text-gray-500 uppercase">
                        {getResourceTypeName(resource.type as ResourceType)}
                      </span>
                    </div>
                    {/* Status Badge */}
                    <span
                      className={`px-2 py-1 text-xs font-medium rounded-full ${
                        status.color === 'green'
                          ? 'bg-green-100 text-green-800'
                          : status.color === 'blue'
                          ? 'bg-blue-100 text-blue-800'
                          : status.color === 'yellow'
                          ? 'bg-yellow-100 text-yellow-800'
                          : 'bg-gray-100 text-gray-800'
                      }`}
                    >
                      {status.label}
                    </span>
                  </div>

                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    {getResourceDisplayName(resource)}
                  </h3>
                  <p className="text-sm text-gray-600 mb-4">
                    {resource.resource_metadata?.description || 'No description available'}
                  </p>

                  <div className="text-xs text-gray-500 space-y-1">
                    <p>Source: {resource.source}</p>
                    {resource.resource_metadata?.owner && (
                      <p>Owner: {resource.resource_metadata.owner}</p>
                    )}
                    <p>
                      Discovered:{' '}
                      {formatDistanceToNow(new Date(resource.discovered_at))} ago
                    </p>
                  </div>
                </CardBody>

                <CardFooter>
                  <Button
                    size="sm"
                    className="w-full"
                    onClick={() => handleExposeResource(resource)}
                    disabled={status.type === 'deployed'}
                  >
                    {status.type === 'deployed' ? (
                      `✓ ${status.label}`
                    ) : (
                      `🚀 ${branding.terminology.pushToGateway}`
                    )}
                  </Button>
                </CardFooter>
              </Card>
            );
          })}
        </div>
      )}

      {/* Expose Resource Modal */}
      <ExposeResourceModal
        isOpen={isModalOpen}
        onClose={handleCloseModal}
        resource={selectedResource}
      />
    </PageLayout>
  );
};
