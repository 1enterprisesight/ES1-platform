import { Routes, Route } from 'react-router-dom'
import { MainLayout } from './design-system/layouts/MainLayout'
import { Dashboard } from './modules/dashboard/Dashboard'
import { GatewayModule } from './modules/gateway/GatewayModule'
import { WorkflowsModule } from './modules/workflows/WorkflowsModule'
import { AIModule } from './modules/ai/AIModule'
import { ObservabilityModule } from './modules/observability/ObservabilityModule'
import { AutomationModule } from './modules/automation/AutomationModule'
import { MonitoringModule } from './modules/monitoring/MonitoringModule'
import { SettingsModule } from './modules/settings/SettingsModule'

function App() {
  return (
    <Routes>
      <Route element={<MainLayout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/gateway/*" element={<GatewayModule />} />
        <Route path="/workflows/*" element={<WorkflowsModule />} />
        <Route path="/ai/*" element={<AIModule />} />
        <Route path="/observability/*" element={<ObservabilityModule />} />
        <Route path="/automation/*" element={<AutomationModule />} />
        <Route path="/monitoring/*" element={<MonitoringModule />} />
        <Route path="/settings" element={<SettingsModule />} />
      </Route>
    </Routes>
  )
}

export default App
