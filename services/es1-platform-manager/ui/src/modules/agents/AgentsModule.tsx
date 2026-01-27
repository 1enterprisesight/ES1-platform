import { Routes, Route, NavLink } from 'react-router-dom'
import { AgentsView } from './views/AgentsView'
import { TasksView } from './views/TasksView'
import { FrameworksView } from './views/FrameworksView'
import { NetworksView } from './views/NetworksView'

export function AgentsModule() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Agent Management</h1>
      </div>

      <nav className="flex space-x-4 border-b border-border">
        <NavLink
          to="/agents"
          end
          className={({ isActive }) =>
            `pb-2 px-1 text-sm font-medium border-b-2 -mb-px transition-colors ${
              isActive
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`
          }
        >
          Frameworks
        </NavLink>
        <NavLink
          to="/agents/registry"
          className={({ isActive }) =>
            `pb-2 px-1 text-sm font-medium border-b-2 -mb-px transition-colors ${
              isActive
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`
          }
        >
          Registry
        </NavLink>
        <NavLink
          to="/agents/tasks"
          className={({ isActive }) =>
            `pb-2 px-1 text-sm font-medium border-b-2 -mb-px transition-colors ${
              isActive
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`
          }
        >
          Tasks
        </NavLink>
        <NavLink
          to="/agents/networks"
          className={({ isActive }) =>
            `pb-2 px-1 text-sm font-medium border-b-2 -mb-px transition-colors ${
              isActive
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`
          }
        >
          Networks
        </NavLink>
      </nav>

      <Routes>
        <Route path="/" element={<FrameworksView />} />
        <Route path="/registry" element={<AgentsView />} />
        <Route path="/tasks" element={<TasksView />} />
        <Route path="/networks" element={<NetworksView />} />
      </Routes>
    </div>
  )
}
