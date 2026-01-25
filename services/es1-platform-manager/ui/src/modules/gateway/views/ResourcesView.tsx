import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, RefreshCw, ExternalLink } from 'lucide-react'
import { Button, Card, Badge } from '@/design-system/components'
import { useToast } from '@/shared/contexts/ToastContext'

interface Resource {
  id: string
  type: string
  source: string
  source_id: string
  metadata: Record<string, unknown>
  status: string
  discovered_at: string
}

interface ResourceListResponse {
  items: Resource[]
  total: number
  page: number
  page_size: number
}

export function ResourcesView() {
  const [page, setPage] = useState(1)
  const queryClient = useQueryClient()
  const { addToast } = useToast()

  const { data, isLoading, refetch } = useQuery<ResourceListResponse>({
    queryKey: ['resources', page],
    queryFn: async () => {
      const res = await fetch(`/api/v1/resources?page=${page}&page_size=20`)
      if (!res.ok) throw new Error('Failed to fetch resources')
      return res.json()
    },
  })

  const createExposure = useMutation({
    mutationFn: async (resourceId: string) => {
      const res = await fetch('/api/v1/exposures', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          resource_id: resourceId,
          settings: { rate_limit: 100 },
          created_by: 'admin',
        }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Failed to create exposure')
      }
      return res.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['exposures'] })
      addToast({ type: 'success', title: 'Exposure created', description: 'Resource is now pending approval' })
    },
    onError: (err: Error) => {
      addToast({ type: 'error', title: 'Failed to create exposure', description: err.message })
    },
  })

  const typeColors: Record<string, 'default' | 'secondary' | 'success' | 'warning' | 'info'> = {
    workflow: 'success',
    service: 'info',
    connection: 'warning',
    flow: 'secondary',
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-semibold">Discovered Resources</h2>
        <Button variant="outline" size="sm" onClick={() => refetch()}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {isLoading ? (
        <div className="text-center py-8 text-muted-foreground">Loading...</div>
      ) : data?.items.length === 0 ? (
        <Card className="p-8 text-center">
          <p className="text-muted-foreground">No resources discovered yet.</p>
          <p className="text-sm text-muted-foreground mt-2">
            Resources from Airflow, Langflow, and other integrations will appear here.
          </p>
        </Card>
      ) : (
        <div className="space-y-2">
          {data?.items.map((resource) => (
            <Card key={resource.id} className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <Badge variant={typeColors[resource.type] || 'default'}>
                    {resource.type}
                  </Badge>
                  <div>
                    <p className="font-medium">
                      {String(resource.metadata.name || resource.metadata.dag_id || resource.source_id)}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      Source: {resource.source} | ID: {resource.source_id}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={resource.status === 'active' ? 'success' : 'secondary'}>
                    {resource.status}
                  </Badge>
                  <Button
                    size="sm"
                    onClick={() => createExposure.mutate(resource.id)}
                    disabled={createExposure.isPending}
                  >
                    <Plus className="h-4 w-4 mr-1" />
                    Expose
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Pagination */}
      {data && data.total > data.page_size && (
        <div className="flex justify-center gap-2 mt-4">
          <Button
            variant="outline"
            size="sm"
            disabled={page === 1}
            onClick={() => setPage(page - 1)}
          >
            Previous
          </Button>
          <span className="px-4 py-2 text-sm">
            Page {page} of {Math.ceil(data.total / data.page_size)}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={page >= Math.ceil(data.total / data.page_size)}
            onClick={() => setPage(page + 1)}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  )
}
