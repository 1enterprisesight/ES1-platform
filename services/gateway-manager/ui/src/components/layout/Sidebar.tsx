import { Link, useLocation } from 'react-router-dom';
import {
  HomeIcon,
  Square3Stack3DIcon,
  RocketLaunchIcon,
  DocumentTextIcon,
  Cog6ToothIcon,
} from '@heroicons/react/24/outline';
import { useBranding } from '../../hooks/useBranding';
import { StatusBadge } from '../common';
import { useDashboardMetrics, useGatewayHealth } from '../../hooks/useDashboard';
import { formatDistanceToNow } from 'date-fns';

interface NavItem {
  name: string;
  path: string;
  icon: typeof HomeIcon;
  badge?: number;
}

export const Sidebar = () => {
  const location = useLocation();
  const branding = useBranding();

  // Fetch real-time data from API
  const { data: metrics } = useDashboardMetrics();
  const { data: gatewayHealth } = useGatewayHealth();

  const navItems: NavItem[] = [
    { name: 'Dashboard', path: '/', icon: HomeIcon },
    { name: 'Resource Registry', path: '/resources', icon: Square3Stack3DIcon },
    {
      name: `${branding.terminology.gateway} Manager`,
      path: '/gateway',
      icon: RocketLaunchIcon,
      badge: metrics?.pending_approvals || 0,
    },
    { name: 'Deployments', path: '/deployments', icon: DocumentTextIcon },
    { name: 'Settings', path: '/settings', icon: Cog6ToothIcon },
  ];

  return (
    <div className="flex flex-col w-64 bg-white border-r border-gray-200 h-screen">
      {/* Logo and branding */}
      <div className="flex items-center justify-center h-16 px-6 border-b border-gray-200">
        <div className="text-center">
          <h1 className="text-xl font-bold text-gray-900">
            {branding.companyName}
          </h1>
          <p className="text-sm text-gray-600">{branding.productName}</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-4 py-6 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const isActive = location.pathname === item.path;
          const Icon = item.icon;

          return (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center justify-between px-3 py-2 text-sm font-medium rounded-lg transition-colors ${
                isActive
                  ? 'bg-primary text-white'
                  : 'text-gray-700 hover:bg-gray-100'
              }`}
            >
              <div className="flex items-center">
                <Icon className="w-5 h-5 mr-3" />
                <span>{item.name}</span>
              </div>
              {item.badge && item.badge > 0 && (
                <span className="px-2 py-1 text-xs font-semibold text-white bg-red-500 rounded-full">
                  {item.badge}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Gateway status */}
      <div className="p-4 border-t border-gray-200 space-y-3">
        <div>
          <p className="text-xs font-medium text-gray-500 mb-2">
            {branding.terminology.gateway} Status
          </p>
          <StatusBadge status={(gatewayHealth?.status as 'healthy' | 'degraded' | 'unhealthy') || 'unhealthy'} />
        </div>
        {gatewayHealth && (
          <div className="text-xs text-gray-600 space-y-1">
            <p>
              {gatewayHealth.running_pods} / {gatewayHealth.pod_count} pods running
            </p>
            {gatewayHealth.last_deploy && (
              <p>
                Last deploy: {formatDistanceToNow(new Date(gatewayHealth.last_deploy))} ago
              </p>
            )}
            <p>{gatewayHealth.failed_health_checks} failed health checks</p>
          </div>
        )}
      </div>
    </div>
  );
};
