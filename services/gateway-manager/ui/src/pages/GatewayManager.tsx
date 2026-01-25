import { useState, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { PageLayout } from '../components/layout';
import { Card, CardBody, Button, StatusBadge, EmptyState, Modal } from '../components/common';
import { ConfigView } from '../components/gateway';
import {
  useExposureChanges,
  useDeleteExposureChange,
} from '../hooks/useExposureChanges';
import { useDeployments, useRedeployConfig } from '../hooks/useDeployments';
import { useResources } from '../hooks/useResources';
import { useActiveConfig, useConfigVersion, usePendingConfigVersions, useApprovedConfigVersions } from '../hooks/useConfigVersions';
import { formatDistanceToNow } from 'date-fns';
import type { ExposureChange, Exposure, ActiveConfig } from '../types';

type TabType = 'active' | 'drafts' | 'pending' | 'approved' | 'history';

export const GatewayManager = () => {
  const queryClient = useQueryClient();

  // Get initial tab from URL or default to 'active'
  const getInitialTab = (): TabType => {
    const params = new URLSearchParams(window.location.search);
    const tab = params.get('tab') as TabType;
    return ['active', 'drafts', 'pending', 'approved', 'history'].includes(tab) ? tab : 'active';
  };

  const [activeTab, setActiveTab] = useState<TabType>(getInitialTab());
  const [viewConfigVersionId, setViewConfigVersionId] = useState<string | null>(null);

  // Draft config state (in-memory, not saved until submit)
  const [draftConfig, setDraftConfig] = useState<ActiveConfig | null>(null);
  const [draftExposures, setDraftExposures] = useState<Exposure[]>([]);

  // Fetch data for each tab
  const { data: draftsData } = useExposureChanges({ status: 'draft' });
  const { data: deploymentsData } = useDeployments(10);
  const { data: resourcesData } = useResources();
  const { data: activeConfig } = useActiveConfig();
  const { data: viewConfig } = useConfigVersion(viewConfigVersionId);
  const { data: pendingConfigVersions } = usePendingConfigVersions();
  const { data: approvedConfigVersions } = useApprovedConfigVersions();

  // Mutations
  const deleteChange = useDeleteExposureChange();
  const redeployConfig = useRedeployConfig();

  const drafts = draftsData?.items || [];
  const deployments = deploymentsData || [];
  const resources = resourcesData?.items || [];

  // Get active config exposures from metadata (source of truth for what's in active version)
  const activeConfigExposures = activeConfig?.config_snapshot?.__ui_metadata?.exposures || [];

  // Update URL when tab changes
  useEffect(() => {
    const url = new URL(window.location.href);
    url.searchParams.set('tab', activeTab);
    window.history.pushState({}, '', url);
  }, [activeTab]);

  // Refetch queries when tab changes
  useEffect(() => {
    queryClient.invalidateQueries({ queryKey: ['exposures'] });
    queryClient.invalidateQueries({ queryKey: ['exposure-changes'] });
    queryClient.invalidateQueries({ queryKey: ['deployments'] });
    queryClient.invalidateQueries({ queryKey: ['config-versions'] });
  }, [activeTab, queryClient]);

  // Helper function to get resource display name
  const getResourceName = (resourceId: string) => {
    const resource = resources.find(r => r.id === resourceId);
    if (!resource) return resourceId.slice(0, 8) + '...';

    const metadata = resource.resource_metadata || {};
    if (resource.type === 'workflow' && metadata.dag_id) {
      return metadata.dag_id;
    }
    if (resource.type === 'connection' && metadata.conn_id) {
      return metadata.conn_id;
    }
    return metadata.name || resource.source_id;
  };

  // Helper function to get resource details
  const getResourceDetails = (resourceId: string) => {
    const resource = resources.find(r => r.id === resourceId);
    if (!resource) return null;

    const metadata = resource.resource_metadata || {};
    return {
      name: getResourceName(resourceId),
      type: resource.type,
      description: metadata.description || 'No description',
      source: resource.source,
    };
  };

  const tabs = [
    { id: 'active' as TabType, name: 'Active', count: activeConfigExposures.length },
    { id: 'drafts' as TabType, name: 'Draft Changes', count: drafts.length },
    { id: 'pending' as TabType, name: 'Pending Approval', count: pendingConfigVersions?.length || 0 },
    { id: 'approved' as TabType, name: 'Approved', count: approvedConfigVersions?.length || 0 },
    { id: 'history' as TabType, name: 'Deployment History', count: deployments.length },
  ];

  // Handlers
  const handleDeleteDraft = async (changeId: string) => {
    if (confirm('Delete this draft change?')) {
      await deleteChange.mutateAsync(changeId);
    }
  };

  const handleSubmitDrafts = async () => {
    // Check if we have a draft config to submit
    if (!draftConfig) {
      alert('No draft configuration to submit. Add resources to create a draft first.');
      return;
    }

    const endpointCount = draftConfig.config_snapshot.endpoints?.length || 0;
    if (!confirm(`Submit draft configuration with ${endpointCount} endpoint(s) for approval?`)) {
      return;
    }

    try {
      // Submit draft config to create ConfigVersion
      // Include exposures metadata so it's available for display in all tabs
      const response = await fetch('/api/v1/config-versions/submit-draft', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          config: {
            ...draftConfig.config_snapshot,
            __ui_metadata: {
              exposures: draftExposures  // Store exposures for ConfigView
            }
          }
        })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to submit draft');
      }

      const result = await response.json();

      // Clear draft state
      setDraftConfig(null);
      setDraftExposures([]);

      // Switch to Pending Approval tab
      setActiveTab('pending');

      alert(`Draft submitted successfully! Version ${result.version} is pending approval.`);

    } catch (error) {
      console.error('Failed to submit draft:', error);
      alert(`Failed to submit draft: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  // Draft config handlers
  const handleAddToDraft = async (change: ExposureChange) => {
    // Find the resource for this change
    const resource = resources.find(r => r.id === change.resource_id);
    if (!resource) return;

    // Check if resource already exists in draft
    const existingInDraft = draftExposures.find(exp => exp.resource_id === change.resource_id);
    if (existingInDraft) {
      alert(`Resource "${getResourceName(change.resource_id)}" is already in the draft configuration. Cannot add duplicate resources.`);
      return;
    }

    // Check if resource already exists in active config (when initializing from active)
    if (draftExposures.length === 0 && activeConfigExposures.length > 0) {
      const existingInActive = activeConfigExposures.find((exp: any) => exp.resource_id === change.resource_id);
      if (existingInActive) {
        alert(`Resource "${getResourceName(change.resource_id)}" is already in the active configuration. Cannot add duplicate resources.`);
        return;
      }
    }

    try {
      // Fetch full KrakenD endpoint config from API
      const response = await fetch(`/api/v1/exposure-changes/${change.id}/generate-config`);
      if (!response.ok) {
        throw new Error(`Failed to generate config: ${response.statusText}`);
      }
      const fullEndpointConfig = await response.json();

      // Create a new exposure for the draft
      const newExposure: Exposure = {
        id: `draft-${change.id}`,
        resource_id: change.resource_id,
        settings: change.settings_after || {},
        generated_config: fullEndpointConfig,
        status: 'deployed', // Will show as deployed in preview
        created_by: change.requested_by,
        created_at: change.requested_at,
        approved_by: null,
        approved_at: null,
        rejection_reason: null,
        resource: {
          id: resource.id,
          type: resource.type,
          source: resource.source,
          source_id: resource.source_id,
          name: getResourceName(resource.id),
          metadata: resource.resource_metadata || {},
        },
      };

      // Initialize draft exposures if needed, then add new exposure
      setDraftExposures(prev => {
        if (prev.length === 0 && activeConfigExposures.length > 0) {
          // First add - initialize from active config exposures
          return [...activeConfigExposures, newExposure];
        }
        return [...prev, newExposure];
      });

      // Initialize draft config if needed, then add endpoint
      setDraftConfig(prev => {
        // If no draft config yet, initialize from active config
        const baseConfig = prev || (activeConfig ? {
          ...activeConfig,
          config_snapshot: {
            ...activeConfig.config_snapshot,
            endpoints: [...(activeConfig.config_snapshot.endpoints || [])]
          }
        } : null);

        if (!baseConfig) return null;

        // Add the new endpoint
        return {
          ...baseConfig,
          config_snapshot: {
            ...baseConfig.config_snapshot,
            endpoints: [
              ...(baseConfig.config_snapshot.endpoints || []),
              fullEndpointConfig
            ]
          }
        };
      });
    } catch (error) {
      console.error('Failed to add resource to draft:', error);
      alert(`Failed to add resource: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  const handleEditResource = (exposureId: string) => {
    // TODO: Implement edit modal
    alert(`Edit functionality for ${exposureId} coming soon!`);
  };

  const handleRemoveResource = (exposureId: string) => {
    // Find the exposure to get its endpoint
    const exposure = draftExposures.find(e => e.id === exposureId);
    if (!exposure) return;

    // Remove from draft exposures
    setDraftExposures(prev => prev.filter(e => e.id !== exposureId));

    // Remove endpoint from config_snapshot
    setDraftConfig(prev => {
      if (!prev) return prev;
      return {
        ...prev,
        config_snapshot: {
          ...prev.config_snapshot,
          endpoints: (prev.config_snapshot.endpoints || []).filter(
            (endpoint: any) => endpoint.endpoint !== exposure.generated_config.endpoint
          )
        }
      };
    });
  };

  const handleApproveConfigVersion = async (versionId: string) => {
    try {
      const response = await fetch(`/api/v1/config-versions/${versionId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approved_by: 'admin' }) // TODO: Get from auth
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to approve');
      }

      // Invalidate queries to refresh all config version lists
      queryClient.invalidateQueries({ queryKey: ['config-versions'] });

      alert('Configuration approved successfully!');
    } catch (error) {
      alert(`Failed to approve: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  const handleRejectConfigVersion = async (versionId: string) => {
    const reason = prompt('Please provide a reason for rejection:');
    if (!reason) return;

    try {
      const response = await fetch(`/api/v1/config-versions/${versionId}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          rejected_by: 'admin', // TODO: Get from auth
          reason
        })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to reject');
      }

      // Invalidate queries to refresh all config version lists
      queryClient.invalidateQueries({ queryKey: ['config-versions'] });

      alert('Configuration rejected successfully!');
    } catch (error) {
      alert(`Failed to reject: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  const handleRedeploy = async (versionId: string) => {
    if (!confirm('Deploy this configuration version to the gateway?')) {
      return;
    }

    try {
      await redeployConfig.mutateAsync({
        versionId,
        deployedBy: 'admin', // TODO: Get from auth
      });

      // Switch to history tab to see deployment result
      setActiveTab('history');
      alert('Deployment initiated successfully! Check the Deployment History tab for status.');
    } catch (error) {
      alert(`Failed to deploy: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  const handleUseAsDraft = async (versionId: string) => {
    if (!confirm('Load this version into draft? This will replace any current draft changes.')) {
      return;
    }

    try {
      // Fetch the config version
      const response = await fetch(`/api/v1/config-versions/${versionId}`);
      if (!response.ok) {
        throw new Error('Failed to fetch config version');
      }
      const configVersion = await response.json();

      // Load config_snapshot into draftConfig
      setDraftConfig(configVersion);

      // Load exposures from metadata into draftExposures
      const exposures = configVersion.config_snapshot.__ui_metadata?.exposures || [];
      setDraftExposures(exposures);

      // Switch to drafts tab
      setActiveTab('drafts');
      alert('Version loaded into draft successfully!');
    } catch (error) {
      alert(`Failed to load version: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  return (
    <PageLayout title="Gateway Manager">
      {/* Tab Navigation */}
      <div className="mb-6 border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`
                whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm
                ${
                  activeTab === tab.id
                    ? 'border-primary text-primary'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }
              `}
            >
              {tab.name}
              {tab.count > 0 && (
                <span
                  className={`ml-2 py-0.5 px-2 rounded-full text-xs ${
                    activeTab === tab.id
                      ? 'bg-primary text-white'
                      : 'bg-gray-100 text-gray-900'
                  }`}
                >
                  {tab.count}
                </span>
              )}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="mt-6">
        {/* Active Tab */}
        {activeTab === 'active' && activeConfig && (
          <ConfigView config={activeConfig} exposures={activeConfigExposures} mode="view" />
        )}

        {/* Draft Changes Tab */}
        {activeTab === 'drafts' && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <p className="text-sm text-gray-600">
                {drafts.length} draft change{drafts.length !== 1 ? 's' : ''} in your workspace
              </p>
              {draftConfig && (
                <Button onClick={handleSubmitDrafts}>
                  Submit for Approval
                </Button>
              )}
            </div>

            {drafts.length === 0 ? (
              <EmptyState
                icon={<span className="text-6xl">📝</span>}
                title="No draft changes"
                description="Create exposure changes from the Resource Library"
              />
            ) : (
              <div className="space-y-3">
                {drafts.map((change) => (
                  <Card key={change.id}>
                    <CardBody>
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="mb-2">
                            <StatusBadge status="draft" />
                          </div>
                          <p className="text-sm font-semibold text-gray-900">
                            {getResourceName(change.resource_id)}
                          </p>
                          {getResourceDetails(change.resource_id) && (
                            <p className="text-xs text-gray-500">
                              {getResourceDetails(change.resource_id)!.type} • {getResourceDetails(change.resource_id)!.source}
                            </p>
                          )}
                          <p className="text-xs text-gray-500 mt-1">
                            Created {formatDistanceToNow(new Date(change.requested_at))} ago
                          </p>
                        </div>
                        <div className="flex space-x-2">
                          <Button
                            size="sm"
                            onClick={() => handleAddToDraft(change)}
                          >
                            + Add
                          </Button>
                          <Button
                            size="sm"
                            variant="secondary"
                            onClick={() => handleDeleteDraft(change.id)}
                            disabled={deleteChange.isPending}
                          >
                            Delete
                          </Button>
                        </div>
                      </div>
                    </CardBody>
                  </Card>
                ))}
              </div>
            )}

            {/* Draft Config View - Always show */}
            <div className="mt-8">
              <div className="border-t border-gray-200 pt-6 mb-4">
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  Draft Configuration Preview
                </h3>
                <p className="text-sm text-gray-600">
                  {draftConfig
                    ? 'Editing draft configuration (changes not saved until submitted)'
                    : activeConfig
                      ? 'Showing active configuration (click + Add above to start editing)'
                      : 'No configuration yet. Click + Add above to start building a draft.'}
                </p>
              </div>
              {(draftConfig || activeConfig) ? (
                <ConfigView
                  config={draftConfig || activeConfig!}
                  exposures={draftExposures.length > 0 ? draftExposures : activeConfigExposures}
                  mode="edit"
                  onEditResource={handleEditResource}
                  onRemoveResource={handleRemoveResource}
                />
              ) : (
                <EmptyState
                  icon={<span className="text-6xl">📋</span>}
                  title="No configuration"
                  description="Add resources above to build your draft configuration"
                />
              )}
            </div>
          </div>
        )}

        {/* Pending Approval Tab */}
        {activeTab === 'pending' && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <p className="text-sm text-gray-600">
                {pendingConfigVersions?.length || 0} version{(pendingConfigVersions?.length || 0) !== 1 ? 's' : ''} awaiting approval
              </p>
            </div>

            {!pendingConfigVersions || pendingConfigVersions.length === 0 ? (
              <EmptyState
                icon={<span className="text-6xl">⏳</span>}
                title="No pending approvals"
                description="Config versions submitted for approval will appear here"
              />
            ) : (
              <div className="space-y-6">
                {pendingConfigVersions.map((configVersion) => (
                  <div key={configVersion.version_id} className="border border-gray-200 rounded-lg p-6">
                    {/* Version Header */}
                    <div className="flex items-center justify-between mb-4">
                      <div>
                        <h3 className="text-lg font-semibold text-gray-900">
                          Version {configVersion.version}
                        </h3>
                        <p className="text-sm text-gray-600">
                          Submitted by {configVersion.deployed_by} •
                          {formatDistanceToNow(new Date(configVersion.deployed_at))} ago
                        </p>
                      </div>
                      <StatusBadge status="pending_approval" />
                    </div>

                    {/* ConfigView (shows config info + JSON) */}
                    <ConfigView
                      config={configVersion}
                      exposures={configVersion.config_snapshot.__ui_metadata?.exposures || []}
                      mode="view"
                    />

                    {/* Action Buttons */}
                    <div className="flex space-x-2 mt-4">
                      <Button
                        onClick={() => handleApproveConfigVersion(configVersion.version_id)}
                        className="flex-1"
                      >
                        Approve Version
                      </Button>
                      <Button
                        variant="secondary"
                        onClick={() => handleRejectConfigVersion(configVersion.version_id)}
                        className="flex-1"
                      >
                        Reject Version
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Approved Tab */}
        {activeTab === 'approved' && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <p className="text-sm text-gray-600">
                {approvedConfigVersions?.length || 0} version{(approvedConfigVersions?.length || 0) !== 1 ? 's' : ''} ready to deploy
              </p>
            </div>

            {!approvedConfigVersions || approvedConfigVersions.length === 0 ? (
              <EmptyState
                icon={<span className="text-6xl">✅</span>}
                title="No approved versions"
                description="Approved config versions will appear here"
              />
            ) : (
              <div className="space-y-6">
                {approvedConfigVersions.map((configVersion) => (
                  <div key={configVersion.version_id} className="border border-gray-200 rounded-lg p-6">
                    {/* Version Header */}
                    <div className="flex items-center justify-between mb-4">
                      <div>
                        <h3 className="text-lg font-semibold text-gray-900">
                          Version {configVersion.version}
                        </h3>
                        <p className="text-sm text-gray-600">
                          Approved by {configVersion.deployed_by} •
                          {formatDistanceToNow(new Date(configVersion.deployed_at))} ago
                        </p>
                      </div>
                      <StatusBadge status="approved" />
                    </div>

                    {/* ConfigView (shows config info + resource cards + JSON) */}
                    <ConfigView
                      config={configVersion}
                      exposures={configVersion.config_snapshot.__ui_metadata?.exposures || []}
                      mode="view"
                    />

                    {/* Action Buttons */}
                    <div className="mt-4 flex space-x-3">
                      <Button
                        onClick={() => handleRedeploy(configVersion.version_id)}
                        disabled={redeployConfig.isPending}
                        className="flex-1"
                      >
                        {redeployConfig.isPending ? 'Deploying...' : 'Deploy Version'}
                      </Button>
                      <Button
                        onClick={() => handleRejectConfigVersion(configVersion.version_id)}
                        variant="secondary"
                        className="flex-1"
                      >
                        Reject
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Deployment History Tab */}
        {activeTab === 'history' && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <p className="text-sm text-gray-600">
                {deployments.length} recent deployment{deployments.length !== 1 ? 's' : ''}
              </p>
            </div>

            {deployments.length === 0 ? (
              <EmptyState
                icon={<span className="text-6xl">📜</span>}
                title="No deployment history"
                description="Past deployments will appear here"
              />
            ) : (
              <div className="space-y-3">
                {deployments.map((deployment) => (
                  <Card key={deployment.id}>
                    <CardBody>
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center space-x-3 mb-2">
                            <StatusBadge status={deployment.status} />
                            <span className="text-sm text-gray-600">
                              {deployment.health_check_passed ? '✓ Health check passed' : '✗ Health check failed'}
                            </span>
                          </div>
                          <p className="text-sm text-gray-900 font-medium">
                            Deployed by {deployment.deployed_by}
                          </p>
                          <p className="text-xs text-gray-500 mt-1">
                            {formatDistanceToNow(new Date(deployment.completed_at || deployment.deployed_at))} ago
                          </p>
                          {deployment.error_message && (
                            <p className="text-xs text-red-600 mt-2">
                              Error: {deployment.error_message}
                            </p>
                          )}
                        </div>
                        <div className="flex space-x-2 ml-4">
                          <Button
                            size="sm"
                            variant="secondary"
                            onClick={() => setViewConfigVersionId(deployment.version_id)}
                          >
                            View Config
                          </Button>
                          <Button
                            size="sm"
                            onClick={() => handleUseAsDraft(deployment.version_id)}
                          >
                            Use as Draft
                          </Button>
                        </div>
                      </div>
                    </CardBody>
                  </Card>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* View Config Modal */}
      {viewConfig && (
        <Modal
          isOpen={!!viewConfigVersionId}
          onClose={() => setViewConfigVersionId(null)}
          title={`Configuration Version ${viewConfig.version}`}
          size="full"
        >
          <ConfigView
            config={viewConfig}
            exposures={viewConfig.config_snapshot.__ui_metadata?.exposures || []}
            mode="view"
          />
        </Modal>
      )}
    </PageLayout>
  );
};
