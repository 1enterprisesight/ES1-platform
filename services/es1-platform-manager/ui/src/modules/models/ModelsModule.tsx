import { Routes, Route, NavLink } from 'react-router-dom'
import { InventoryView } from './views/InventoryView'
import { OllamaView } from './views/OllamaView'
import { MLflowView } from './views/MLflowView'
import { InferenceView } from './views/InferenceView'

export function ModelsModule() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Model Management</h1>
        <p className="text-muted-foreground">
          View and manage LLM and ML models across Ollama and MLflow
        </p>
      </div>

      {/* Navigation Tabs */}
      <nav className="flex space-x-4 border-b border-border">
        <NavLink
          to="/models"
          end
          className={({ isActive }) =>
            `pb-2 px-1 text-sm font-medium border-b-2 transition-colors ${
              isActive
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`
          }
        >
          Inventory
        </NavLink>
        <NavLink
          to="/models/ollama"
          className={({ isActive }) =>
            `pb-2 px-1 text-sm font-medium border-b-2 transition-colors ${
              isActive
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`
          }
        >
          Ollama (LLM)
        </NavLink>
        <NavLink
          to="/models/mlflow"
          className={({ isActive }) =>
            `pb-2 px-1 text-sm font-medium border-b-2 transition-colors ${
              isActive
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`
          }
        >
          MLflow Registry
        </NavLink>
        <NavLink
          to="/models/inference"
          className={({ isActive }) =>
            `pb-2 px-1 text-sm font-medium border-b-2 transition-colors ${
              isActive
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`
          }
        >
          Inference Metrics
        </NavLink>
      </nav>

      {/* Content */}
      <Routes>
        <Route path="/" element={<InventoryView />} />
        <Route path="/ollama" element={<OllamaView />} />
        <Route path="/mlflow" element={<MLflowView />} />
        <Route path="/inference" element={<InferenceView />} />
      </Routes>
    </div>
  )
}
