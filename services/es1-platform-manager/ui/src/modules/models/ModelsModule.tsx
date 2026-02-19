import { Routes, Route, NavLink, Navigate } from 'react-router-dom'
import { InventoryView } from './views/InventoryView'
import { OllamaView } from './views/OllamaView'
import { MLflowView } from './views/MLflowView'
import { InferenceView } from './views/InferenceView'
import { isFeatureEnabled } from '@/config'

const tabClass = ({ isActive }: { isActive: boolean }) =>
  `pb-2 px-1 text-sm font-medium border-b-2 transition-colors ${
    isActive
      ? 'border-primary text-primary'
      : 'border-transparent text-muted-foreground hover:text-foreground'
  }`

export function ModelsModule() {
  const ollamaEnabled = isFeatureEnabled('enableOllama')
  const mlflowEnabled = isFeatureEnabled('enableMlflow')

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Model Management</h1>
        <p className="text-muted-foreground">
          View and manage LLM and ML models{ollamaEnabled && mlflowEnabled ? ' across Ollama and MLflow' : ollamaEnabled ? ' via Ollama' : ' via MLflow'}
        </p>
      </div>

      {/* Navigation Tabs */}
      <nav className="flex space-x-4 border-b border-border">
        <NavLink to="/models" end className={tabClass}>
          Inventory
        </NavLink>
        {ollamaEnabled && (
          <NavLink to="/models/ollama" className={tabClass}>
            Ollama (LLM)
          </NavLink>
        )}
        {mlflowEnabled && (
          <NavLink to="/models/mlflow" className={tabClass}>
            MLflow Registry
          </NavLink>
        )}
        <NavLink to="/models/inference" className={tabClass}>
          Inference Metrics
        </NavLink>
      </nav>

      {/* Content */}
      <Routes>
        <Route path="/" element={<InventoryView />} />
        {ollamaEnabled && <Route path="/ollama" element={<OllamaView />} />}
        {mlflowEnabled && <Route path="/mlflow" element={<MLflowView />} />}
        <Route path="/inference" element={<InferenceView />} />
        <Route path="*" element={<Navigate to="/models" replace />} />
      </Routes>
    </div>
  )
}
