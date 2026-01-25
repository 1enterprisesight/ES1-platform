import { useNavigate } from 'react-router-dom';
import { PageLayout } from '../components/layout';
import { MetricCard, Card, CardHeader, CardBody, Button, LoadingSpinner, EmptyState } from '../components/common';
import { useBranding } from '../hooks/useBranding';
import { useDashboardMetrics, useGatewayHealth } from '../hooks/useDashboard';
import { useEvents } from '../hooks/useEvents';
import { useGatewayHealth as useKrakenDHealth, useGatewayRequests, useTopEndpoints } from '../hooks/useMetrics';
import { formatDistanceToNow } from 'date-fns';

// Helper function to format event messages with icons and colors
const formatEvent = (event: any) => {
  const { event_type, user_id, event_metadata } = event;

  let icon = '•';
  let color = 'text-blue-600';
  let message = '';

  switch (event_type) {
    // Resource Discovery & Library
    case 'resource_discovered':
      icon = '🔍';
      color = 'text-blue-600';
      message = `discovered ${event_metadata?.resource_type || 'resource'} "${event_metadata?.resource_name || 'unknown'}" from ${event_metadata?.source || 'source'}`;
      break;
    case 'resource_pushed':
      icon = '📤';
      color = 'text-blue-600';
      message = `pushed ${event_metadata?.resource_type || 'resource'} "${event_metadata?.resource_name || 'unknown'}" to gateway`;
      break;

    // Config Workflow
    case 'config_submitted':
      icon = '📝';
      color = 'text-blue-600';
      message = `submitted config v${event_metadata?.version || '?'} for approval (${event_metadata?.endpoint_count || 0} endpoints, ${event_metadata?.changes_count || 0} changes)`;
      break;
    case 'config_approved':
      icon = '✅';
      color = 'text-green-600';
      message = `approved config v${event_metadata?.version || '?'}`;
      break;
    case 'config_rejected':
      icon = '❌';
      color = 'text-red-600';
      message = `rejected config v${event_metadata?.version || '?'}`;
      if (event_metadata?.reason) {
        message += ` - ${event_metadata.reason}`;
      }
      break;

    // Deployment
    case 'deployment_succeeded':
      icon = '🚀';
      color = 'text-green-600';
      message = `deployed config v${event_metadata?.version || '?'} to gateway`;
      break;
    case 'deployment_failed':
      icon = '✗';
      color = 'text-red-600';
      message = `deployment failed`;
      if (event_metadata?.error) {
        message += ` - ${event_metadata.error}`;
      }
      break;

    default:
      message = `${event_type.replace(/_/g, ' ')} (${event.entity_type})`;
  }

  return { icon, color, message, user: user_id || 'System' };
};

export const Dashboard = () => {
  const branding = useBranding();
  const navigate = useNavigate();

  // Fetch real data from API
  const { data: metrics, isLoading: metricsLoading } = useDashboardMetrics();
  const { data: gatewayHealth, isLoading: healthLoading } = useGatewayHealth();
  const { data: events = [], isLoading: eventsLoading } = useEvents(5);
  const { data: krakenDHealth } = useKrakenDHealth();
  const { data: requestMetrics } = useGatewayRequests();
  const { data: topEndpoints } = useTopEndpoints(5);

  // Show loading state
  if (metricsLoading || healthLoading || eventsLoading) {
    return (
      <PageLayout title="Dashboard">
        <div className="flex items-center justify-center py-20">
          <LoadingSpinner size="lg" />
        </div>
      </PageLayout>
    );
  }

  // Show error state if metrics failed to load
  if (!metrics) {
    return (
      <PageLayout title="Dashboard">
        <EmptyState
          icon={<span className="text-6xl">⚠️</span>}
          title="Failed to load dashboard"
          description="Unable to fetch dashboard metrics"
        />
      </PageLayout>
    );
  }

  return (
    <PageLayout title="Dashboard">
      {/* Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
        <MetricCard
          title="Total Endpoints"
          value={metrics.total_endpoints}
        />
        <MetricCard
          title="Active Endpoints"
          value={metrics.active_endpoints}
        />
        <MetricCard
          title="Pending Approvals"
          value={metrics.pending_approvals}
          onClick={() => navigate('/gateway')}
        />
        <MetricCard
          title="Failed Deployments"
          value={metrics.failed_deployments}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Gateway Health */}
        <Card>
          <CardHeader>
            <h3 className="text-lg font-semibold">
              {branding.terminology.gateway} Health
            </h3>
          </CardHeader>
          <CardBody>
            <div className="space-y-4">
              <div className="flex items-center space-x-2">
                <div
                  className={`w-3 h-3 rounded-full ${
                    gatewayHealth?.status === 'healthy'
                      ? 'bg-green-500'
                      : gatewayHealth?.status === 'degraded'
                      ? 'bg-yellow-500'
                      : 'bg-red-500'
                  }`}
                ></div>
                <span className="text-gray-900 font-medium">
                  {gatewayHealth?.status === 'healthy' && 'All systems operational'}
                  {gatewayHealth?.status === 'degraded' && 'System degraded'}
                  {gatewayHealth?.status === 'unhealthy' && 'System unhealthy'}
                  {!gatewayHealth && 'Status unknown'}
                </span>
              </div>

              {gatewayHealth && (
                <div className="space-y-2 text-sm text-gray-600">
                  <p>
                    <span className="font-medium">KrakenD Gateway</span>
                  </p>
                  <ul className="list-disc list-inside pl-4 space-y-1">
                    <li>
                      {gatewayHealth.running_pods} / {gatewayHealth.pod_count} pods running
                    </li>
                    {gatewayHealth.last_deploy && (
                      <li>
                        Last deploy:{' '}
                        {formatDistanceToNow(new Date(gatewayHealth.last_deploy))}{' '}
                        ago
                      </li>
                    )}
                    <li>
                      {gatewayHealth.failed_health_checks} failed health checks
                    </li>
                  </ul>
                </div>
              )}
            </div>
          </CardBody>
        </Card>

        {/* Recent Activity */}
        <Card>
          <CardHeader>
            <h3 className="text-lg font-semibold">Recent Activity</h3>
          </CardHeader>
          <CardBody>
            <div className="space-y-4">
              {events.length === 0 ? (
                <p className="text-sm text-gray-500 text-center py-4">
                  No recent activity
                </p>
              ) : (
                events
                  .filter((event) => !event.event_type.includes('batch_'))  // Exclude legacy batch events
                  .map((event) => {
                    const formatted = formatEvent(event);
                    return (
                      <div key={event.id} className="flex items-start space-x-3 pb-3 border-b border-gray-100 last:border-0 last:pb-0">
                        <div className={`flex-shrink-0 text-lg ${formatted.color}`}>
                          {formatted.icon}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-gray-900">
                            <span className="font-medium">{formatted.user}</span>{' '}
                            <span className="text-gray-700">{formatted.message}</span>
                          </p>
                          <p className="text-xs text-gray-500 mt-0.5">
                            {formatDistanceToNow(new Date(event.created_at))} ago
                          </p>
                        </div>
                      </div>
                    );
                  })
              )}

              <Button
                variant="secondary"
                size="sm"
                className="w-full"
                onClick={() => navigate('/activity')}
              >
                View All Activity
              </Button>
            </div>
          </CardBody>
        </Card>
      </div>

      {/* Gateway Application Metrics */}
      <Card className="mb-6">
        <CardHeader>
          <h3 className="text-lg font-semibold">Gateway Metrics</h3>
        </CardHeader>
        <CardBody>
          {krakenDHealth?.status === 'healthy' ? (
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <div>
                <p className="text-xs text-gray-500">Status</p>
                <p className="text-sm font-medium text-green-600">✓ Healthy</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Memory</p>
                <p className="text-sm font-medium">
                  {((krakenDHealth.memory_bytes || 0) / 1024 / 1024).toFixed(1)} MB
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Goroutines</p>
                <p className="text-sm font-medium">{krakenDHealth.goroutines || 0}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Total Requests</p>
                <p className="text-sm font-medium">{krakenDHealth.total_requests || 0}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Success Rate</p>
                <p className="text-sm font-medium">
                  {requestMetrics?.success_rate !== null && requestMetrics?.success_rate !== undefined
                    ? `${requestMetrics.success_rate.toFixed(1)}%`
                    : 'N/A'}
                </p>
              </div>
            </div>
          ) : (
            <p className="text-sm text-gray-500">Gateway metrics unavailable</p>
          )}
        </CardBody>
      </Card>

      {/* Top Endpoints */}
      <Card className="mb-6">
        <CardHeader>
          <h3 className="text-lg font-semibold">Top Endpoints</h3>
        </CardHeader>
        <CardBody>
          {topEndpoints?.endpoints && topEndpoints.endpoints.length > 0 ? (
            <div className="space-y-3">
              {topEndpoints.endpoints.map((endpoint, idx) => (
                <div key={idx} className="border-b border-gray-100 pb-3 last:border-0 last:pb-0">
                  <div className="flex items-center justify-between mb-1">
                    <p className="text-sm font-medium text-gray-900 truncate flex-1">
                      {endpoint.endpoint}
                    </p>
                    <p className="text-xs text-gray-500 ml-2">
                      {endpoint.total_requests} requests
                    </p>
                  </div>
                  <div className="flex items-center space-x-4 text-xs text-gray-600">
                    <span className="text-green-600">
                      ✓ {endpoint.success_requests} success
                    </span>
                    <span className="text-red-600">
                      ✗ {endpoint.error_requests} errors
                    </span>
                    <span className={endpoint.error_rate > 5 ? 'text-red-600 font-medium' : 'text-gray-500'}>
                      {endpoint.error_rate.toFixed(1)}% error rate
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-500 text-center py-4">
              No endpoint metrics available
            </p>
          )}
        </CardBody>
      </Card>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <h3 className="text-lg font-semibold">Quick Actions</h3>
        </CardHeader>
        <CardBody>
          <div className="flex flex-wrap gap-3">
            <Button onClick={() => navigate('/resources')}>
              📦 View {branding.terminology.workflows}
            </Button>
            <Button
              onClick={() => navigate('/gateway')}
              variant="secondary"
            >
              ✅ {branding.terminology.approve} Pending
            </Button>
            <Button onClick={() => navigate('/deployments')} variant="secondary">
              🚀 {branding.terminology.deploy}
            </Button>
          </div>
        </CardBody>
      </Card>
    </PageLayout>
  );
};
