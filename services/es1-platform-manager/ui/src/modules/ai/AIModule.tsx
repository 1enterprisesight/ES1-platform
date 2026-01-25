import { Routes, Route, NavLink } from 'react-router-dom'
import { FlowsView } from './views/FlowsView'
import { FlowRunnerView } from './views/FlowRunnerView'

export function AIModule() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">AI Flows</h1>
      </div>

      <nav className="flex space-x-4 border-b border-border">
        <NavLink
          to="/ai"
          end
          className={({ isActive }) =>
            `pb-2 px-1 text-sm font-medium border-b-2 -mb-px transition-colors ${
              isActive
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`
          }
        >
          Flows
        </NavLink>
        <NavLink
          to="/ai/runner"
          className={({ isActive }) =>
            `pb-2 px-1 text-sm font-medium border-b-2 -mb-px transition-colors ${
              isActive
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`
          }
        >
          Flow Runner
        </NavLink>
      </nav>

      <Routes>
        <Route path="/" element={<FlowsView />} />
        <Route path="/runner" element={<FlowRunnerView />} />
      </Routes>
    </div>
  )
}
