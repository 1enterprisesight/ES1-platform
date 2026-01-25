import { useState } from 'react';
import { PageLayout } from '../components/layout';
import { Card, LoadingSpinner, EmptyState } from '../components/common';
import { useEvents } from '../hooks/useEvents';
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

export const Activity = () => {
  const [searchTerm, setSearchTerm] = useState('');

  // Fetch all events (increased limit for full history)
  const { data: events = [], isLoading, error } = useEvents(100);

  // Filter events based on search term and exclude batch events
  const filteredEvents = events.filter((event) => {
    // Exclude legacy batch events
    if (event.event_type.includes('batch_')) {
      return false;
    }

    if (!searchTerm) return true;

    const formatted = formatEvent(event);
    const searchLower = searchTerm.toLowerCase();

    return (
      event.event_type.toLowerCase().includes(searchLower) ||
      formatted.message.toLowerCase().includes(searchLower) ||
      formatted.user.toLowerCase().includes(searchLower) ||
      event.entity_type.toLowerCase().includes(searchLower)
    );
  });

  // Loading state
  if (isLoading) {
    return (
      <PageLayout title="Activity History">
        <div className="flex items-center justify-center py-20">
          <LoadingSpinner size="lg" />
        </div>
      </PageLayout>
    );
  }

  // Error state
  if (error) {
    return (
      <PageLayout title="Activity History">
        <EmptyState
          icon={<span className="text-6xl">⚠️</span>}
          title="Failed to load activity"
          description={error instanceof Error ? error.message : 'Unknown error occurred'}
        />
      </PageLayout>
    );
  }

  return (
    <PageLayout title="Activity History">
      <p className="text-sm text-gray-600 mb-4">
        Showing {filteredEvents.length} of {events.length} events
      </p>

      {/* Search */}
      <div className="mb-6">
        <input
          type="text"
          placeholder="Search activity by event type, user, or message..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
        />
      </div>

      {/* Activity Feed */}
      {filteredEvents.length === 0 ? (
        <EmptyState
          icon={<span className="text-6xl">📋</span>}
          title={searchTerm ? "No matching events" : "No activity yet"}
          description={searchTerm ? "Try adjusting your search terms" : "Activity events will appear here as you use the system"}
        />
      ) : (
        <Card>
          <div className="divide-y divide-gray-200">
            {filteredEvents.map((event) => {
              const formatted = formatEvent(event);
              return (
                <div
                  key={event.id}
                  className="p-4 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-start space-x-3">
                    <div className={`flex-shrink-0 text-2xl ${formatted.color}`}>
                      {formatted.icon}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-baseline justify-between">
                        <p className="text-sm text-gray-900">
                          <span className="font-medium">{formatted.user}</span>{' '}
                          <span className="text-gray-700">{formatted.message}</span>
                        </p>
                        <p className="text-xs text-gray-500 ml-4 flex-shrink-0">
                          {formatDistanceToNow(new Date(event.created_at))} ago
                        </p>
                      </div>

                      {/* Show entity type and ID if available */}
                      <div className="mt-1 flex items-center space-x-3 text-xs text-gray-500">
                        <span className="font-mono bg-gray-100 px-2 py-0.5 rounded">
                          {event.entity_type}
                        </span>
                        {event.event_metadata && Object.keys(event.event_metadata).length > 0 && (
                          <details className="cursor-pointer">
                            <summary className="hover:text-gray-700">
                              View details
                            </summary>
                            <pre className="mt-2 p-2 bg-gray-50 rounded text-xs overflow-x-auto">
                              {JSON.stringify(event.event_metadata, null, 2)}
                            </pre>
                          </details>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      )}
    </PageLayout>
  );
};
