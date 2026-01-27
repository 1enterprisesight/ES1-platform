import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Play,
  Pause,
  ExternalLink,
  RefreshCw,
  Zap,
  CheckCircle,
  XCircle,
  Clock,
} from 'lucide-react'

interface Workflow {
  id: string
  name: string
  active: boolean
  created_at: string | null
  updated_at: string | null
  tags: string[]
  nodes_count: number
}

interface WorkflowListResponse {
  workflows: Workflow[]
  total: number
}

async function fetchWorkflows(): Promise<WorkflowListResponse> {
  const res = await fetch('/api/v1/n8n/workflows')
  if (!res.ok) throw new Error('Failed to fetch workflows')
  return res.json()
}

async function activateWorkflow(id: string): Promise<Workflow> {
  const res = await fetch(`/api/v1/n8n/workflows/${id}/activate`, {
    method: 'POST',
  })
  if (!res.ok) throw new Error('Failed to activate workflow')
  return res.json()
}

async function deactivateWorkflow(id: string): Promise<Workflow> {
  const res = await fetch(`/api/v1/n8n/workflows/${id}/deactivate`, {
    method: 'POST',
  })
  if (!res.ok) throw new Error('Failed to deactivate workflow')
  return res.json()
}

async function executeWorkflow(id: string): Promise<void> {
  const res = await fetch(`/api/v1/n8n/workflows/${id}/execute`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  })
  if (!res.ok) throw new Error('Failed to execute workflow')
}

export function N8NWorkflowsView() {
  const queryClient = useQueryClient()
  const [executingId, setExecutingId] = useState<string | null>(null)

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['n8n-workflows'],
    queryFn: fetchWorkflows,
    refetchInterval: 30000,
  })

  const activateMutation = useMutation({
    mutationFn: activateWorkflow,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['n8n-workflows'] })
    },
  })

  const deactivateMutation = useMutation({
    mutationFn: deactivateWorkflow,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['n8n-workflows'] })
    },
  })

  const executeMutation = useMutation({
    mutationFn: executeWorkflow,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['n8n-executions'] })
    },
    onSettled: () => {
      setExecutingId(null)
    },
  })

  const handleToggleActive = (workflow: Workflow) => {
    if (workflow.active) {
      deactivateMutation.mutate(workflow.id)
    } else {
      activateMutation.mutate(workflow.id)
    }
  }

  const handleExecute = (workflow: Workflow) => {
    setExecutingId(workflow.id)
    executeMutation.mutate(workflow.id)
  }

  const openInN8N = (workflowId: string) => {
    window.open(`http://localhost:5678/workflow/${workflowId}`, '_blank')
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (error) {
    const errorMessage = (error as Error).message || 'Unknown error'
    const isApiKeyMissing = errorMessage.includes('503') || errorMessage.includes('API key')

    if (isApiKeyMissing) {
      return (
        <div className="rounded-lg border border-amber-500/50 bg-amber-50 dark:bg-amber-900/20 p-6">
          <h3 className="font-semibold text-amber-800 dark:text-amber-200 mb-2">
            n8n API Key Required
          </h3>
          <p className="text-sm text-amber-700 dark:text-amber-300 mb-4">
            To manage workflows from this dashboard, you need to configure an n8n API key.
          </p>
          <ol className="text-sm text-amber-700 dark:text-amber-300 list-decimal list-inside space-y-2 mb-4">
            <li>Open n8n at <a href="http://localhost:5678" target="_blank" rel="noopener noreferrer" className="underline">http://localhost:5678</a></li>
            <li>Complete the initial setup (create owner account)</li>
            <li>Go to <strong>Settings &gt; API</strong></li>
            <li>Create a new API Key</li>
            <li>Add <code className="bg-amber-100 dark:bg-amber-800 px-1 rounded">N8N_API_KEY=your-key</code> to your environment</li>
            <li>Restart the Platform Manager API</li>
          </ol>
          <a
            href="http://localhost:5678"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 px-4 py-2 text-sm bg-amber-600 text-white rounded-md hover:bg-amber-700"
          >
            <ExternalLink className="w-4 h-4" />
            Open n8n Setup
          </a>
        </div>
      )
    }

    return (
      <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4">
        <div className="flex items-center gap-2 text-destructive">
          <XCircle className="w-5 h-5" />
          <span>Failed to load workflows. Is n8n running?</span>
        </div>
        <button
          onClick={() => refetch()}
          className="mt-2 text-sm text-primary hover:underline"
        >
          Try again
        </button>
      </div>
    )
  }

  const workflows = data?.workflows || []

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {workflows.length} workflow{workflows.length !== 1 ? 's' : ''} found
        </p>
        <div className="flex items-center gap-2">
          <button
            onClick={() => refetch()}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm border rounded-md hover:bg-accent"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
          <a
            href="http://localhost:5678"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
          >
            <ExternalLink className="w-4 h-4" />
            Open n8n
          </a>
        </div>
      </div>

      {workflows.length === 0 ? (
        <div className="rounded-lg border border-dashed p-8 text-center">
          <Zap className="w-12 h-12 mx-auto text-muted-foreground/50" />
          <h3 className="mt-4 text-lg font-medium">No workflows yet</h3>
          <p className="mt-2 text-sm text-muted-foreground">
            Create your first workflow in n8n to get started with automation.
          </p>
          <a
            href="http://localhost:5678/workflow/new"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 mt-4 px-4 py-2 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
          >
            Create Workflow
            <ExternalLink className="w-4 h-4" />
          </a>
        </div>
      ) : (
        <div className="rounded-lg border overflow-hidden">
          <table className="w-full">
            <thead className="bg-muted/50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Status
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Workflow
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Nodes
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Tags
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Updated
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {workflows.map((workflow) => (
                <tr key={workflow.id} className="hover:bg-muted/30">
                  <td className="px-4 py-3">
                    {workflow.active ? (
                      <span className="inline-flex items-center gap-1.5 text-green-600">
                        <CheckCircle className="w-4 h-4" />
                        <span className="text-sm">Active</span>
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 text-muted-foreground">
                        <Clock className="w-4 h-4" />
                        <span className="text-sm">Inactive</span>
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => openInN8N(workflow.id)}
                      className="font-medium hover:text-primary hover:underline"
                    >
                      {workflow.name}
                    </button>
                    <p className="text-xs text-muted-foreground">
                      ID: {workflow.id}
                    </p>
                  </td>
                  <td className="px-4 py-3 text-sm text-muted-foreground">
                    {workflow.nodes_count} node{workflow.nodes_count !== 1 ? 's' : ''}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1">
                      {workflow.tags.length > 0 ? (
                        workflow.tags.map((tag) => (
                          <span
                            key={tag}
                            className="px-2 py-0.5 text-xs rounded-full bg-primary/10 text-primary"
                          >
                            {tag}
                          </span>
                        ))
                      ) : (
                        <span className="text-xs text-muted-foreground">—</span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm text-muted-foreground">
                    {workflow.updated_at
                      ? new Date(workflow.updated_at).toLocaleDateString()
                      : '—'}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => handleExecute(workflow)}
                        disabled={executingId === workflow.id}
                        className="p-1.5 rounded hover:bg-accent disabled:opacity-50"
                        title="Execute workflow"
                      >
                        {executingId === workflow.id ? (
                          <RefreshCw className="w-4 h-4 animate-spin" />
                        ) : (
                          <Play className="w-4 h-4 text-green-600" />
                        )}
                      </button>
                      <button
                        onClick={() => handleToggleActive(workflow)}
                        disabled={
                          activateMutation.isPending || deactivateMutation.isPending
                        }
                        className="p-1.5 rounded hover:bg-accent disabled:opacity-50"
                        title={workflow.active ? 'Deactivate' : 'Activate'}
                      >
                        {workflow.active ? (
                          <Pause className="w-4 h-4 text-orange-500" />
                        ) : (
                          <Play className="w-4 h-4" />
                        )}
                      </button>
                      <button
                        onClick={() => openInN8N(workflow.id)}
                        className="p-1.5 rounded hover:bg-accent"
                        title="Edit in n8n"
                      >
                        <ExternalLink className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
