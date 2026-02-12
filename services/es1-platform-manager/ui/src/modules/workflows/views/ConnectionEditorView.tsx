import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import {
  Plus,
  Save,
  Trash2,
  RefreshCw,
  Cable,
  Eye,
  EyeOff,
} from 'lucide-react'
import { Button, Card, Badge } from '@/design-system/components'
import { useToast } from '@/shared/contexts/ToastContext'

// ── Types ──────────────────────────────────────────────────────────────

interface Connection {
  connection_id: string
  conn_type: string | null
  description: string | null
  host: string | null
  port: number | null
  schema_name: string | null
}

interface ConnectionDetail {
  connection_id: string
  conn_type: string | null
  description: string | null
  host: string | null
  port: number | null
  schema_name: string | null
  login: string | null
  extra: string | null
}

interface TemplateField {
  name: string
  label: string
  type: string
  required: boolean
  placeholder?: string
}

interface ConnectionTemplate {
  conn_type: string
  display_name: string
  description: string
  category: string
  default_port: number | null
  fields: TemplateField[]
  extra_schema: Record<string, unknown>
}

interface TemplatesResponse {
  templates: ConnectionTemplate[]
  categories: Record<string, string>
}

// ── Form state ─────────────────────────────────────────────────────────

interface FormState {
  connection_id: string
  conn_type: string
  description: string
  host: string
  port: string
  schema_name: string
  login: string
  password: string
  extra: string
}

const emptyForm: FormState = {
  connection_id: '',
  conn_type: '',
  description: '',
  host: '',
  port: '',
  schema_name: '',
  login: '',
  password: '',
  extra: '',
}

// Generic fallback fields when no template matches
const GENERIC_FIELDS: TemplateField[] = [
  { name: 'host', label: 'Host', type: 'text', required: false, placeholder: 'hostname' },
  { name: 'port', label: 'Port', type: 'number', required: false, placeholder: '0' },
  { name: 'schema', label: 'Schema', type: 'text', required: false },
  { name: 'login', label: 'Username', type: 'text', required: false },
  { name: 'password', label: 'Password', type: 'password', required: false },
  { name: 'extra', label: 'Extra (JSON)', type: 'textarea', required: false, placeholder: '{"key": "value"}' },
]

// ── Component ──────────────────────────────────────────────────────────

export function ConnectionEditorView() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [selectedConnection, setSelectedConnection] = useState<string | null>(searchParams.get('connection'))
  const [form, setForm] = useState<FormState>(emptyForm)
  const [originalForm, setOriginalForm] = useState<FormState>(emptyForm)
  const [isNew, setIsNew] = useState(false)
  const [newDialogOpen, setNewDialogOpen] = useState(false)
  const [newConnId, setNewConnId] = useState('')
  const [newConnType, setNewConnType] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [changePassword, setChangePassword] = useState(false)
  const queryClient = useQueryClient()
  const { addToast } = useToast()

  const hasUnsavedChanges = JSON.stringify(form) !== JSON.stringify(originalForm)

  // URL sync
  useEffect(() => {
    const param = searchParams.get('connection')
    if (param && param !== selectedConnection) {
      setSelectedConnection(param)
    }
  }, [searchParams])

  useEffect(() => {
    if (selectedConnection) {
      setSearchParams({ connection: selectedConnection }, { replace: true })
    } else {
      setSearchParams({}, { replace: true })
    }
  }, [selectedConnection])

  // ── Queries ────────────────────────────────────────────────────────

  const { data: connectionsData, isLoading: connectionsLoading, refetch: refetchConnections } = useQuery<{
    connections: Connection[]
    total_entries: number
  }>({
    queryKey: ['airflow', 'connections'],
    queryFn: async () => {
      const res = await fetch('/api/v1/airflow/connections')
      if (!res.ok) throw new Error('Failed to fetch connections')
      return res.json()
    },
  })

  const { data: templatesData } = useQuery<TemplatesResponse>({
    queryKey: ['connection-templates'],
    queryFn: async () => {
      const res = await fetch('/api/v1/airflow/connection-templates')
      if (!res.ok) throw new Error('Failed to fetch templates')
      return res.json()
    },
  })

  const { data: connectionDetail, isLoading: detailLoading } = useQuery<ConnectionDetail>({
    queryKey: ['airflow', 'connection', selectedConnection],
    queryFn: async () => {
      const res = await fetch(`/api/v1/airflow/connections/${selectedConnection}`)
      if (!res.ok) throw new Error('Failed to fetch connection')
      return res.json()
    },
    enabled: !!selectedConnection && !isNew,
  })

  // Load connection detail into form
  useEffect(() => {
    if (connectionDetail && !isNew) {
      const loaded: FormState = {
        connection_id: connectionDetail.connection_id,
        conn_type: connectionDetail.conn_type || '',
        description: connectionDetail.description || '',
        host: connectionDetail.host || '',
        port: connectionDetail.port != null ? String(connectionDetail.port) : '',
        schema_name: connectionDetail.schema_name || '',
        login: connectionDetail.login || '',
        password: '', // never displayed
        extra: connectionDetail.extra || '',
      }
      setForm(loaded)
      setOriginalForm(loaded)
      setChangePassword(false)
      setShowPassword(false)
    }
  }, [connectionDetail, isNew])

  // ── Mutations ──────────────────────────────────────────────────────

  const saveMutation = useMutation({
    mutationFn: async () => {
      const payload: Record<string, unknown> = {
        conn_type: form.conn_type,
      }
      if (form.description) payload.description = form.description
      if (form.host) payload.host = form.host
      if (form.port) payload.port = parseInt(form.port, 10)
      if (form.schema_name) payload.schema_name = form.schema_name
      if (form.login) payload.login = form.login
      if (form.extra) payload.extra = form.extra

      if (isNew) {
        payload.connection_id = form.connection_id
        if (form.password) payload.password = form.password
        const res = await fetch('/api/v1/airflow/connections', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        })
        if (!res.ok) {
          const err = await res.json()
          throw new Error(err.detail || 'Failed to create connection')
        }
        return res.json()
      } else {
        // PATCH — only send password if user chose to change it
        if (changePassword && form.password) {
          payload.password = form.password
        }
        const res = await fetch(`/api/v1/airflow/connections/${selectedConnection}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        })
        if (!res.ok) {
          const err = await res.json()
          throw new Error(err.detail || 'Failed to update connection')
        }
        return res.json()
      }
    },
    onSuccess: (data) => {
      const connId = data.connection_id || form.connection_id
      setIsNew(false)
      setSelectedConnection(connId)
      setChangePassword(false)
      setShowPassword(false)
      // Reset the password field so it shows "unchanged" state
      const updated: FormState = {
        ...form,
        connection_id: connId,
        password: '',
      }
      setForm(updated)
      setOriginalForm(updated)
      queryClient.invalidateQueries({ queryKey: ['airflow', 'connections'] })
      queryClient.invalidateQueries({ queryKey: ['airflow', 'connection', connId] })
      queryClient.invalidateQueries({ queryKey: ['resources'] })
      addToast({ type: 'success', title: 'Connection saved', description: `${connId} saved successfully` })
    },
    onError: (err: Error) => {
      addToast({ type: 'error', title: 'Save failed', description: err.message })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async (connectionId: string) => {
      const res = await fetch(`/api/v1/airflow/connections/${connectionId}`, { method: 'DELETE' })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Failed to delete')
      }
      return res.json()
    },
    onSuccess: () => {
      setSelectedConnection(null)
      setForm(emptyForm)
      setOriginalForm(emptyForm)
      setIsNew(false)
      queryClient.invalidateQueries({ queryKey: ['airflow', 'connections'] })
      queryClient.invalidateQueries({ queryKey: ['resources'] })
      addToast({ type: 'success', title: 'Connection deleted' })
    },
    onError: (err: Error) => {
      addToast({ type: 'error', title: 'Delete failed', description: err.message })
    },
  })

  // ── New connection dialog handler ──────────────────────────────────

  const handleCreateNew = () => {
    if (!newConnId || !newConnType) return

    // Find matching template for defaults
    const template = templatesData?.templates.find(t => t.conn_type === newConnType)

    const newForm: FormState = {
      connection_id: newConnId,
      conn_type: newConnType,
      description: '',
      host: '',
      port: template?.default_port != null ? String(template.default_port) : '',
      schema_name: '',
      login: '',
      password: '',
      extra: template?.extra_schema && Object.keys(template.extra_schema).length > 0
        ? JSON.stringify(template.extra_schema, null, 2)
        : '',
    }
    setForm(newForm)
    setOriginalForm(newForm)
    setIsNew(true)
    setSelectedConnection(newConnId)
    setChangePassword(true)
    setShowPassword(false)
    setNewDialogOpen(false)
    setNewConnId('')
    setNewConnType('')
  }

  // ── Template lookup for current conn_type ──────────────────────────

  const currentTemplate = templatesData?.templates.find(t => t.conn_type === form.conn_type)
  const fields = currentTemplate?.fields || GENERIC_FIELDS

  // ── Form field update helper ───────────────────────────────────────

  const updateField = (name: string, value: string) => {
    // Map template field name "schema" to our form field "schema_name"
    const formKey = name === 'schema' ? 'schema_name' : name
    setForm(prev => ({ ...prev, [formKey]: value }))
  }

  const getFieldValue = (name: string): string => {
    const key = name === 'schema' ? 'schema_name' : name
    return form[key as keyof FormState] || ''
  }

  // ── Group templates by category for new dialog ─────────────────────

  const templatesByCategory: Record<string, ConnectionTemplate[]> = {}
  if (templatesData) {
    for (const t of templatesData.templates) {
      if (!templatesByCategory[t.category]) {
        templatesByCategory[t.category] = []
      }
      templatesByCategory[t.category].push(t)
    }
  }

  // ── Render ─────────────────────────────────────────────────────────

  return (
    <div className="flex h-[calc(100vh-16rem)] gap-4">
      {/* Sidebar — Connection list */}
      <Card className="w-72 flex flex-col">
        <div className="p-3 border-b flex items-center justify-between">
          <h3 className="font-medium flex items-center gap-2">
            <Cable className="h-4 w-4" />
            Connections
          </h3>
          <Button variant="ghost" size="sm" onClick={() => refetchConnections()}>
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
        <div className="p-2 border-b">
          <Button size="sm" className="w-full" onClick={() => setNewDialogOpen(true)}>
            <Plus className="h-4 w-4 mr-1" />
            New Connection
          </Button>
        </div>
        <div className="flex-1 overflow-auto">
          {connectionsLoading ? (
            <div className="p-4 text-center text-muted-foreground">Loading...</div>
          ) : !connectionsData?.connections.length ? (
            <div className="p-4 text-center text-muted-foreground text-sm">
              No connections found. Create one to get started.
            </div>
          ) : (
            <div className="divide-y">
              {connectionsData.connections.map((conn) => (
                <button
                  key={conn.connection_id}
                  onClick={() => {
                    if (hasUnsavedChanges) {
                      if (!confirm('You have unsaved changes. Discard?')) return
                    }
                    setIsNew(false)
                    setSelectedConnection(conn.connection_id)
                  }}
                  className={`w-full p-3 text-left hover:bg-accent/50 transition-colors ${
                    selectedConnection === conn.connection_id ? 'bg-accent' : ''
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium text-sm truncate">{conn.connection_id}</span>
                    {conn.conn_type && (
                      <Badge variant="secondary" className="text-xs shrink-0">{conn.conn_type}</Badge>
                    )}
                  </div>
                  {conn.host && (
                    <div className="mt-1 text-xs text-muted-foreground truncate">
                      {conn.host}{conn.port ? `:${conn.port}` : ''}
                    </div>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>
      </Card>

      {/* Main — Form editor */}
      <Card className="flex-1 flex flex-col">
        {selectedConnection ? (
          <>
            <div className="p-3 border-b flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Cable className="h-4 w-4" />
                <span className="font-medium">{form.connection_id}</span>
                {form.conn_type && <Badge variant="secondary">{form.conn_type}</Badge>}
                {isNew && <Badge variant="warning">New</Badge>}
                {hasUnsavedChanges && !isNew && <Badge variant="warning">Unsaved</Badge>}
              </div>
              <div className="flex gap-2">
                {!isNew && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      if (confirm(`Delete connection "${selectedConnection}"?`)) {
                        deleteMutation.mutate(selectedConnection)
                      }
                    }}
                    disabled={deleteMutation.isPending}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                )}
                <Button
                  size="sm"
                  disabled={(!hasUnsavedChanges && !isNew) || saveMutation.isPending || !form.connection_id || !form.conn_type}
                  onClick={() => saveMutation.mutate()}
                >
                  <Save className="h-4 w-4 mr-1" />
                  {isNew ? 'Create' : 'Save'}
                </Button>
              </div>
            </div>

            <div className="flex-1 overflow-auto p-4 space-y-4">
              {detailLoading && !isNew ? (
                <div className="text-center text-muted-foreground py-8">Loading connection details...</div>
              ) : (
                <>
                  {/* Connection ID (read-only for existing) */}
                  <div>
                    <label className="text-sm font-medium block mb-1">Connection ID</label>
                    <input
                      type="text"
                      value={form.connection_id}
                      disabled={!isNew}
                      onChange={(e) => updateField('connection_id', e.target.value)}
                      className="w-full px-3 py-2 border rounded bg-background disabled:bg-muted disabled:cursor-not-allowed"
                    />
                  </div>

                  {/* Connection Type (read-only — set at creation) */}
                  <div>
                    <label className="text-sm font-medium block mb-1">Connection Type</label>
                    <input
                      type="text"
                      value={form.conn_type}
                      disabled
                      className="w-full px-3 py-2 border rounded bg-muted cursor-not-allowed"
                    />
                  </div>

                  {/* Description */}
                  <div>
                    <label className="text-sm font-medium block mb-1">Description</label>
                    <input
                      type="text"
                      value={form.description}
                      onChange={(e) => updateField('description', e.target.value)}
                      placeholder="Optional description"
                      className="w-full px-3 py-2 border rounded bg-background"
                    />
                  </div>

                  <hr className="border-border" />

                  {/* Dynamic fields from template */}
                  {fields.map((field) => {
                    // Password gets special handling below
                    if (field.type === 'password') return null

                    if (field.type === 'textarea') {
                      return (
                        <div key={field.name}>
                          <label className="text-sm font-medium block mb-1">
                            {field.label}
                            {field.required && <span className="text-destructive ml-1">*</span>}
                          </label>
                          <textarea
                            value={getFieldValue(field.name)}
                            onChange={(e) => updateField(field.name, e.target.value)}
                            placeholder={field.placeholder}
                            rows={4}
                            className="w-full px-3 py-2 border rounded bg-background font-mono text-sm resize-y"
                          />
                        </div>
                      )
                    }

                    return (
                      <div key={field.name}>
                        <label className="text-sm font-medium block mb-1">
                          {field.label}
                          {field.required && <span className="text-destructive ml-1">*</span>}
                        </label>
                        <input
                          type={field.type === 'number' ? 'number' : 'text'}
                          value={getFieldValue(field.name)}
                          onChange={(e) => updateField(field.name, e.target.value)}
                          placeholder={field.placeholder}
                          className="w-full px-3 py-2 border rounded bg-background"
                        />
                      </div>
                    )
                  })}

                  {/* Password field — special handling */}
                  {fields.some(f => f.type === 'password') && (
                    <div>
                      <label className="text-sm font-medium block mb-1">
                        {fields.find(f => f.type === 'password')?.label || 'Password'}
                      </label>
                      {!isNew && !changePassword ? (
                        <div className="flex items-center gap-2">
                          <input
                            type="password"
                            value="••••••••"
                            disabled
                            className="flex-1 px-3 py-2 border rounded bg-muted cursor-not-allowed"
                          />
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => setChangePassword(true)}
                          >
                            Change
                          </Button>
                        </div>
                      ) : (
                        <div className="flex items-center gap-2">
                          <div className="relative flex-1">
                            <input
                              type={showPassword ? 'text' : 'password'}
                              value={form.password}
                              onChange={(e) => updateField('password', e.target.value)}
                              placeholder={isNew ? 'Enter password' : 'Enter new password'}
                              className="w-full px-3 py-2 border rounded bg-background pr-10"
                            />
                            <button
                              type="button"
                              onClick={() => setShowPassword(!showPassword)}
                              className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                            >
                              {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                            </button>
                          </div>
                          {!isNew && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => {
                                setChangePassword(false)
                                setForm(prev => ({ ...prev, password: '' }))
                              }}
                            >
                              Cancel
                            </Button>
                          )}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Extra field if not already in template fields */}
                  {!fields.some(f => f.name === 'extra') && (
                    <div>
                      <label className="text-sm font-medium block mb-1">Extra (JSON)</label>
                      <textarea
                        value={form.extra}
                        onChange={(e) => updateField('extra', e.target.value)}
                        placeholder='{"key": "value"}'
                        rows={4}
                        className="w-full px-3 py-2 border rounded bg-background font-mono text-sm resize-y"
                      />
                    </div>
                  )}
                </>
              )}
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-muted-foreground">
            <div className="text-center">
              <Cable className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>Select a connection to edit</p>
              <p className="text-sm mt-1">or create a new one</p>
            </div>
          </div>
        )}
      </Card>

      {/* New Connection Dialog */}
      {newDialogOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <Card className="w-[520px] max-h-[80vh] flex flex-col p-6">
            <h2 className="text-lg font-semibold mb-4">New Connection</h2>
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium block mb-1">Connection ID *</label>
                <input
                  type="text"
                  value={newConnId}
                  onChange={(e) => setNewConnId(e.target.value)}
                  placeholder="my_postgres_conn"
                  className="w-full px-3 py-2 border rounded bg-background"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Unique identifier for this connection
                </p>
              </div>
              <div>
                <label className="text-sm font-medium block mb-1">Connection Type *</label>
                <select
                  value={newConnType}
                  onChange={(e) => setNewConnType(e.target.value)}
                  className="w-full px-3 py-2 border rounded bg-background"
                >
                  <option value="">Select a type...</option>
                  {Object.entries(templatesByCategory).map(([category, templates]) => (
                    <optgroup key={category} label={templatesData?.categories[category] || category}>
                      {templates.map((t) => (
                        <option key={`${t.conn_type}-${t.display_name}`} value={t.conn_type}>
                          {t.display_name} — {t.description}
                        </option>
                      ))}
                    </optgroup>
                  ))}
                </select>
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <Button variant="outline" onClick={() => { setNewDialogOpen(false); setNewConnId(''); setNewConnType('') }}>
                Cancel
              </Button>
              <Button
                disabled={!newConnId || !newConnType}
                onClick={handleCreateNew}
              >
                Continue
              </Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  )
}
