import { Routes, Route, NavLink, useLocation } from 'react-router-dom'
import { cn } from '@/shared/utils/cn'
import { CurrentStateView } from './views/CurrentStateView'
import { EditConfigView } from './views/EditConfigView'
import { ReviewView } from './views/ReviewView'
import { HistoryView } from './views/HistoryView'
import { HealthView } from './views/HealthView'

const tabs = [
  { path: '/gateway', label: 'Overview', exact: true },
  { path: '/gateway/edit', label: 'Edit' },
  { path: '/gateway/review', label: 'Review' },
  { path: '/gateway/history', label: 'History' },
  { path: '/gateway/health', label: 'Health' },
]

export function GatewayModule() {
  const location = useLocation()

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">API Gateway</h1>
        <p className="text-muted-foreground">Manage gateway configuration, exposures, and deployments</p>
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
        <Route index element={<CurrentStateView />} />
        <Route path="edit" element={<EditConfigView />} />
        <Route path="review" element={<ReviewView />} />
        <Route path="history" element={<HistoryView />} />
        <Route path="health" element={<HealthView />} />
      </Routes>
    </div>
  )
}
