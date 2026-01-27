import { Routes, Route, NavLink } from 'react-router-dom'
import { OverviewView } from './views/OverviewView'
import { RequestsView } from './views/RequestsView'
import { EndpointsView } from './views/EndpointsView'
import { ErrorsView } from './views/ErrorsView'

export function TrafficModule() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">API Traffic</h1>
        <p className="text-muted-foreground">
          Monitor API requests, latency, and errors across all services
        </p>
      </div>

      {/* Navigation Tabs */}
      <nav className="flex space-x-4 border-b border-border">
        <NavLink
          to="/traffic"
          end
          className={({ isActive }) =>
            `pb-2 px-1 text-sm font-medium border-b-2 transition-colors ${
              isActive
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`
          }
        >
          Overview
        </NavLink>
        <NavLink
          to="/traffic/requests"
          className={({ isActive }) =>
            `pb-2 px-1 text-sm font-medium border-b-2 transition-colors ${
              isActive
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`
          }
        >
          Requests
        </NavLink>
        <NavLink
          to="/traffic/endpoints"
          className={({ isActive }) =>
            `pb-2 px-1 text-sm font-medium border-b-2 transition-colors ${
              isActive
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`
          }
        >
          Endpoints
        </NavLink>
        <NavLink
          to="/traffic/errors"
          className={({ isActive }) =>
            `pb-2 px-1 text-sm font-medium border-b-2 transition-colors ${
              isActive
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`
          }
        >
          Errors
        </NavLink>
      </nav>

      {/* Content */}
      <Routes>
        <Route path="/" element={<OverviewView />} />
        <Route path="/requests" element={<RequestsView />} />
        <Route path="/endpoints" element={<EndpointsView />} />
        <Route path="/errors" element={<ErrorsView />} />
      </Routes>
    </div>
  )
}
