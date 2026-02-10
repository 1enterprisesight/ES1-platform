import { Routes, Route, Navigate } from 'react-router-dom'
import { MainLayout } from './design-system/layouts/MainLayout'
import { Dashboard } from './modules/dashboard/Dashboard'
import { GatewayModule } from './modules/gateway/GatewayModule'
import { WorkflowsModule } from './modules/workflows/WorkflowsModule'
import { AIModule } from './modules/ai/AIModule'
import { AgentsModule } from './modules/agents/AgentsModule'
import { KnowledgeModule } from './modules/knowledge/KnowledgeModule'
import { TrafficModule } from './modules/traffic/TrafficModule'
import { ModelsModule } from './modules/models/ModelsModule'
import { ObservabilityModule } from './modules/observability/ObservabilityModule'
import { AutomationModule } from './modules/automation/AutomationModule'
import { MonitoringModule } from './modules/monitoring/MonitoringModule'
import { SettingsModule } from './modules/settings/SettingsModule'
import { LoginPage } from './modules/auth/LoginPage'
import { useAuth } from './shared/contexts/AuthContext'
import { Loader2 } from 'lucide-react'

function AuthGuard({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <AuthGuard>
            <MainLayout />
          </AuthGuard>
        }
      >
        <Route path="/" element={<Dashboard />} />
        <Route path="/gateway/*" element={<GatewayModule />} />
        <Route path="/workflows/*" element={<WorkflowsModule />} />
        <Route path="/ai/*" element={<AIModule />} />
        <Route path="/agents/*" element={<AgentsModule />} />
        <Route path="/knowledge/*" element={<KnowledgeModule />} />
        <Route path="/traffic/*" element={<TrafficModule />} />
        <Route path="/models/*" element={<ModelsModule />} />
        <Route path="/observability/*" element={<ObservabilityModule />} />
        <Route path="/automation/*" element={<AutomationModule />} />
        <Route path="/monitoring/*" element={<MonitoringModule />} />
        <Route path="/settings" element={<SettingsModule />} />
      </Route>
    </Routes>
  )
}

export default App
