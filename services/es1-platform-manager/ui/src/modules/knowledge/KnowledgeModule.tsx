import { Routes, Route, NavLink } from 'react-router-dom'
import { KnowledgeBasesView } from './views/KnowledgeBasesView'
import { DocumentsView } from './views/DocumentsView'
import { GraphExplorerView } from './views/GraphExplorerView'
import { SearchView } from './views/SearchView'

export function KnowledgeModule() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Knowledge Management</h1>
        <p className="text-muted-foreground">
          Manage knowledge bases, documents, and explore the knowledge graph
        </p>
      </div>

      {/* Navigation Tabs */}
      <nav className="flex space-x-4 border-b border-border">
        <NavLink
          to="/knowledge"
          end
          className={({ isActive }) =>
            `pb-2 px-1 text-sm font-medium border-b-2 transition-colors ${
              isActive
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`
          }
        >
          Knowledge Bases
        </NavLink>
        <NavLink
          to="/knowledge/documents"
          className={({ isActive }) =>
            `pb-2 px-1 text-sm font-medium border-b-2 transition-colors ${
              isActive
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`
          }
        >
          Documents
        </NavLink>
        <NavLink
          to="/knowledge/graph"
          className={({ isActive }) =>
            `pb-2 px-1 text-sm font-medium border-b-2 transition-colors ${
              isActive
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`
          }
        >
          Graph Explorer
        </NavLink>
        <NavLink
          to="/knowledge/search"
          className={({ isActive }) =>
            `pb-2 px-1 text-sm font-medium border-b-2 transition-colors ${
              isActive
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`
          }
        >
          Search
        </NavLink>
      </nav>

      {/* Content */}
      <Routes>
        <Route path="/" element={<KnowledgeBasesView />} />
        <Route path="/documents" element={<DocumentsView />} />
        <Route path="/graph" element={<GraphExplorerView />} />
        <Route path="/search" element={<SearchView />} />
      </Routes>
    </div>
  )
}
