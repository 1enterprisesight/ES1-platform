import { Routes, Route, NavLink, useLocation } from 'react-router-dom'
import { cn } from '@/shared/utils/cn'
import { ResourcesView } from './views/ResourcesView'
import { ExposuresView } from './views/ExposuresView'
import { DeploymentsView } from './views/DeploymentsView'
import { HealthView } from './views/HealthView'

const tabs = [
  { path: '/gateway', label: 'Resources', exact: true },
  { path: '/gateway/exposures', label: 'Exposures' },
  { path: '/gateway/deployments', label: 'Deployments' },
  { path: '/gateway/health', label: 'Health' },
]

export function GatewayModule() {
  const location = useLocation()

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">API Gateway</h1>
        <p className="text-muted-foreground">Manage gateway resources, exposures, and deployments</p>
      </div>

      {/* Tab Navigation */}
      <div className="border-b">
        <nav className="flex gap-4">
          {tabs.map((tab) => {
            const isActive = tab.exact
              ? location.pathname === tab.path
              : location.pathname.startsWith(tab.path)

            return (
              <NavLink
                key={tab.path}
                to={tab.path}
                end={tab.exact}
                className={cn(
                  'px-1 py-2 text-sm font-medium border-b-2 -mb-px transition-colors',
                  isActive
                    ? 'border-primary text-primary'
                    : 'border-transparent text-muted-foreground hover:text-foreground'
                )}
              >
                {tab.label}
              </NavLink>
            )
          })}
        </nav>
      </div>

      {/* Tab Content */}
      <Routes>
        <Route index element={<ResourcesView />} />
        <Route path="exposures" element={<ExposuresView />} />
        <Route path="deployments" element={<DeploymentsView />} />
        <Route path="health" element={<HealthView />} />
      </Routes>
    </div>
  )
}
