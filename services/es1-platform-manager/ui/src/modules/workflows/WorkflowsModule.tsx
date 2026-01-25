import { Routes, Route, NavLink } from 'react-router-dom'
import { DagsView } from './views/DagsView'
import { DagRunsView } from './views/DagRunsView'
import { ConnectionsView } from './views/ConnectionsView'

export function WorkflowsModule() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Workflows</h1>
      </div>

      <nav className="flex space-x-4 border-b border-border">
        <NavLink
          to="/workflows"
          end
          className={({ isActive }) =>
            `pb-2 px-1 text-sm font-medium border-b-2 -mb-px transition-colors ${
              isActive
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`
          }
        >
          DAGs
        </NavLink>
        <NavLink
          to="/workflows/runs"
          className={({ isActive }) =>
            `pb-2 px-1 text-sm font-medium border-b-2 -mb-px transition-colors ${
              isActive
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`
          }
        >
          DAG Runs
        </NavLink>
        <NavLink
          to="/workflows/connections"
          className={({ isActive }) =>
            `pb-2 px-1 text-sm font-medium border-b-2 -mb-px transition-colors ${
              isActive
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`
          }
        >
          Connections
        </NavLink>
      </nav>

      <Routes>
        <Route path="/" element={<DagsView />} />
        <Route path="/runs" element={<DagRunsView />} />
        <Route path="/connections" element={<ConnectionsView />} />
      </Routes>
    </div>
  )
}
