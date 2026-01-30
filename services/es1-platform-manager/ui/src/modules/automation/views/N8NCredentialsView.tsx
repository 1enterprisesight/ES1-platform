import { useQuery } from '@tanstack/react-query'
import {
  RefreshCw,
  XCircle,
  Key,
  ExternalLink,
  Plus,
} from 'lucide-react'
import { serviceUrl } from '@/config'

interface Credential {
  id: string
  name: string
  type: string
  created_at: string | null
  updated_at: string | null
}

interface CredentialListResponse {
  credentials: Credential[]
  total: number
}

async function fetchCredentials(): Promise<CredentialListResponse> {
  const res = await fetch('/api/v1/n8n/credentials')
  if (!res.ok) throw new Error('Failed to fetch credentials')
  return res.json()
}

function formatCredentialType(type: string): string {
  // Convert camelCase or snake_case to Title Case
  return type
    .replace(/([A-Z])/g, ' $1')
    .replace(/_/g, ' ')
    .replace(/api/gi, 'API')
    .replace(/oauth/gi, 'OAuth')
    .trim()
    .split(' ')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

export function N8NCredentialsView() {
  const n8nUrl = serviceUrl('n8n')

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['n8n-credentials'],
    queryFn: fetchCredentials,
    refetchInterval: 60000,
  })

  const openN8NCredentials = () => {
    window.open(`${n8nUrl}/credentials`, '_blank')
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4">
        <div className="flex items-center gap-2 text-destructive">
          <XCircle className="w-5 h-5" />
          <span>Failed to load credentials. Is n8n running?</span>
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

  const credentials = data?.credentials || []

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {credentials.length} credential{credentials.length !== 1 ? 's' : ''}{' '}
          configured
        </p>
        <div className="flex items-center gap-2">
          <button
            onClick={() => refetch()}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm border rounded-md hover:bg-accent"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
          <button
            onClick={openN8NCredentials}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
          >
            <Plus className="w-4 h-4" />
            Add Credential
          </button>
        </div>
      </div>

      <div className="rounded-lg border bg-amber-50/50 dark:bg-amber-900/10 p-3">
        <p className="text-sm text-amber-800 dark:text-amber-200">
          Credentials are managed securely in n8n. This view shows available
          credentials without exposing sensitive data.
        </p>
      </div>

      {credentials.length === 0 ? (
        <div className="rounded-lg border border-dashed p-8 text-center">
          <Key className="w-12 h-12 mx-auto text-muted-foreground/50" />
          <h3 className="mt-4 text-lg font-medium">No credentials configured</h3>
          <p className="mt-2 text-sm text-muted-foreground">
            Add credentials in n8n to connect workflows to external services.
          </p>
          <button
            onClick={openN8NCredentials}
            className="inline-flex items-center gap-1.5 mt-4 px-4 py-2 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
          >
            Add Credential
            <ExternalLink className="w-4 h-4" />
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {credentials.map((credential) => (
            <div
              key={credential.id}
              className="rounded-lg border p-4 hover:bg-muted/30 transition-colors"
            >
              <div className="flex items-start gap-3">
                <div className="p-2 rounded-lg bg-primary/10">
                  <Key className="w-5 h-5 text-primary" />
                </div>
                <div className="flex-1 min-w-0">
                  <h4 className="font-medium truncate">{credential.name}</h4>
                  <p className="text-sm text-muted-foreground">
                    {formatCredentialType(credential.type)}
                  </p>
                  <p className="text-xs text-muted-foreground mt-2">
                    Created:{' '}
                    {credential.created_at
                      ? new Date(credential.created_at).toLocaleDateString()
                      : '—'}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
