import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Plus,
  Save,
  Trash2,
  RefreshCw,
  File,
  FileCode,
  Upload,
  Download,
} from 'lucide-react'
import { Button, Card, Badge } from '@/design-system/components'
import { useToast } from '@/shared/contexts/ToastContext'

interface DAGFile {
  filename: string
  dag_id: string
  path: string
  size: number
  modified_at: string
  created_at: string
}

interface DAGFileListResponse {
  files: DAGFile[]
  total: number
  dags_path: string
}

interface DAGTemplate {
  id: string
  name: string
  description: string
}

export function DagEditorView() {
  const [selectedFile, setSelectedFile] = useState<string | null>(null)
  const [editorContent, setEditorContent] = useState('')
  const [originalContent, setOriginalContent] = useState('')
  const [newDagDialogOpen, setNewDagDialogOpen] = useState(false)
  const [newDagId, setNewDagId] = useState('')
  const [newDagTemplate, setNewDagTemplate] = useState('basic')
  const [newDagDescription, setNewDagDescription] = useState('')
  const [newDagSchedule, setNewDagSchedule] = useState('')
  const queryClient = useQueryClient()
  const { addToast } = useToast()

  const hasUnsavedChanges = editorContent !== originalContent

  const { data: filesData, isLoading: filesLoading, refetch: refetchFiles } = useQuery<DAGFileListResponse>({
    queryKey: ['dag-files'],
    queryFn: async () => {
      const res = await fetch('/api/v1/airflow/dag-files')
      if (!res.ok) throw new Error('Failed to fetch DAG files')
      return res.json()
    },
  })

  const { data: templates } = useQuery<{ templates: DAGTemplate[] }>({
    queryKey: ['dag-templates'],
    queryFn: async () => {
      const res = await fetch('/api/v1/airflow/dag-templates')
      if (!res.ok) throw new Error('Failed to fetch templates')
      return res.json()
    },
  })

  const { data: fileContent, isLoading: contentLoading } = useQuery<{ content: string }>({
    queryKey: ['dag-file-content', selectedFile],
    queryFn: async () => {
      const res = await fetch(`/api/v1/airflow/dag-files/${selectedFile}`)
      if (!res.ok) throw new Error('Failed to fetch DAG file')
      return res.json()
    },
    enabled: !!selectedFile,
  })

  useEffect(() => {
    if (fileContent) {
      setEditorContent(fileContent.content)
      setOriginalContent(fileContent.content)
    }
  }, [fileContent])

  const saveMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch('/api/v1/airflow/dag-files', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: selectedFile, content: editorContent }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Failed to save')
      }
      return res.json()
    },
    onSuccess: () => {
      setOriginalContent(editorContent)
      queryClient.invalidateQueries({ queryKey: ['dag-files'] })
      addToast({ type: 'success', title: 'DAG saved', description: `${selectedFile} saved successfully` })
    },
    onError: (err: Error) => {
      addToast({ type: 'error', title: 'Save failed', description: err.message })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async (filename: string) => {
      const res = await fetch(`/api/v1/airflow/dag-files/${filename}`, { method: 'DELETE' })
      if (!res.ok) throw new Error('Failed to delete')
      return res.json()
    },
    onSuccess: () => {
      setSelectedFile(null)
      setEditorContent('')
      setOriginalContent('')
      queryClient.invalidateQueries({ queryKey: ['dag-files'] })
      addToast({ type: 'success', title: 'DAG deleted' })
    },
    onError: (err: Error) => {
      addToast({ type: 'error', title: 'Delete failed', description: err.message })
    },
  })

  const createMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch('/api/v1/airflow/dag-files/from-template', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          dag_id: newDagId,
          template: newDagTemplate,
          description: newDagDescription,
          schedule: newDagSchedule || null,
          tags: [],
        }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Failed to create DAG')
      }
      return res.json()
    },
    onSuccess: (data) => {
      setNewDagDialogOpen(false)
      setNewDagId('')
      setNewDagDescription('')
      setNewDagSchedule('')
      setSelectedFile(data.filename)
      queryClient.invalidateQueries({ queryKey: ['dag-files'] })
      addToast({ type: 'success', title: 'DAG created', description: `${data.filename} created` })
    },
    onError: (err: Error) => {
      addToast({ type: 'error', title: 'Create failed', description: err.message })
    },
  })

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    const content = await file.text()
    const filename = file.name.endsWith('.py') ? file.name : `${file.name}.py`

    try {
      const res = await fetch('/api/v1/airflow/dag-files', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename, content }),
      })
      if (!res.ok) throw new Error('Failed to upload')

      queryClient.invalidateQueries({ queryKey: ['dag-files'] })
      setSelectedFile(filename)
      addToast({ type: 'success', title: 'DAG uploaded', description: `${filename} uploaded` })
    } catch (err) {
      addToast({ type: 'error', title: 'Upload failed', description: String(err) })
    }

    e.target.value = ''
  }

  const handleDownload = () => {
    if (!selectedFile || !editorContent) return
    const blob = new Blob([editorContent], { type: 'text/x-python' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = selectedFile
    a.click()
    URL.revokeObjectURL(url)
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString()
  }

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`
  }

  return (
    <div className="flex h-[calc(100vh-16rem)] gap-4">
      {/* File List Sidebar */}
      <Card className="w-72 flex flex-col">
        <div className="p-3 border-b flex items-center justify-between">
          <h3 className="font-medium flex items-center gap-2">
            <FileCode className="h-4 w-4" />
            DAG Files
          </h3>
          <div className="flex gap-1">
            <Button variant="ghost" size="sm" onClick={() => refetchFiles()}>
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </div>
        <div className="p-2 border-b flex gap-2">
          <Button size="sm" className="flex-1" onClick={() => setNewDagDialogOpen(true)}>
            <Plus className="h-4 w-4 mr-1" />
            New
          </Button>
          <label className="cursor-pointer">
            <input type="file" accept=".py" className="hidden" onChange={handleFileUpload} />
            <Button size="sm" variant="outline" asChild>
              <span>
                <Upload className="h-4 w-4" />
              </span>
            </Button>
          </label>
        </div>
        <div className="flex-1 overflow-auto">
          {filesLoading ? (
            <div className="p-4 text-center text-muted-foreground">Loading...</div>
          ) : filesData?.files.length === 0 ? (
            <div className="p-4 text-center text-muted-foreground text-sm">
              No DAG files found. Create or upload one to get started.
            </div>
          ) : (
            <div className="divide-y">
              {filesData?.files.map((file) => (
                <button
                  key={file.filename}
                  onClick={() => {
                    if (hasUnsavedChanges) {
                      if (!confirm('You have unsaved changes. Discard?')) return
                    }
                    setSelectedFile(file.filename)
                  }}
                  className={`w-full p-3 text-left hover:bg-accent/50 transition-colors ${
                    selectedFile === file.filename ? 'bg-accent' : ''
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <File className="h-4 w-4 text-muted-foreground" />
                    <span className="font-medium text-sm truncate">{file.filename}</span>
                  </div>
                  <div className="mt-1 text-xs text-muted-foreground">
                    {formatSize(file.size)} - {formatDate(file.modified_at)}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
        {filesData && (
          <div className="p-2 border-t text-xs text-muted-foreground">
            Path: {filesData.dags_path}
          </div>
        )}
      </Card>

      {/* Editor Area */}
      <Card className="flex-1 flex flex-col">
        {selectedFile ? (
          <>
            <div className="p-3 border-b flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FileCode className="h-4 w-4" />
                <span className="font-medium">{selectedFile}</span>
                {hasUnsavedChanges && (
                  <Badge variant="warning">Unsaved</Badge>
                )}
              </div>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleDownload}
                >
                  <Download className="h-4 w-4 mr-1" />
                  Download
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    if (confirm(`Delete ${selectedFile}?`)) {
                      deleteMutation.mutate(selectedFile)
                    }
                  }}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
                <Button
                  size="sm"
                  disabled={!hasUnsavedChanges || saveMutation.isPending}
                  onClick={() => saveMutation.mutate()}
                >
                  <Save className="h-4 w-4 mr-1" />
                  Save
                </Button>
              </div>
            </div>
            <div className="flex-1 overflow-hidden">
              {contentLoading ? (
                <div className="p-8 text-center text-muted-foreground">Loading...</div>
              ) : (
                <textarea
                  value={editorContent}
                  onChange={(e) => setEditorContent(e.target.value)}
                  className="w-full h-full p-4 font-mono text-sm bg-muted/30 border-0 resize-none focus:outline-none"
                  spellCheck={false}
                />
              )}
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-muted-foreground">
            <div className="text-center">
              <FileCode className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>Select a DAG file to edit</p>
              <p className="text-sm mt-1">or create a new one</p>
            </div>
          </div>
        )}
      </Card>

      {/* New DAG Dialog */}
      {newDagDialogOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <Card className="w-[480px] p-6">
            <h2 className="text-lg font-semibold mb-4">Create New DAG</h2>
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium block mb-1">DAG ID *</label>
                <input
                  type="text"
                  value={newDagId}
                  onChange={(e) => setNewDagId(e.target.value)}
                  placeholder="my_dag"
                  className="w-full px-3 py-2 border rounded bg-background"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Must start with a letter, only letters, numbers, and underscores
                </p>
              </div>
              <div>
                <label className="text-sm font-medium block mb-1">Template</label>
                <select
                  value={newDagTemplate}
                  onChange={(e) => setNewDagTemplate(e.target.value)}
                  className="w-full px-3 py-2 border rounded bg-background"
                >
                  {templates?.templates.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name} - {t.description}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-sm font-medium block mb-1">Description</label>
                <input
                  type="text"
                  value={newDagDescription}
                  onChange={(e) => setNewDagDescription(e.target.value)}
                  placeholder="What this DAG does..."
                  className="w-full px-3 py-2 border rounded bg-background"
                />
              </div>
              <div>
                <label className="text-sm font-medium block mb-1">Schedule</label>
                <select
                  value={newDagSchedule}
                  onChange={(e) => setNewDagSchedule(e.target.value)}
                  className="w-full px-3 py-2 border rounded bg-background"
                >
                  <option value="">None (manual trigger only)</option>
                  <option value="@once">@once - Run once</option>
                  <option value="@hourly">@hourly - Every hour</option>
                  <option value="@daily">@daily - Every day at midnight</option>
                  <option value="@weekly">@weekly - Every week</option>
                  <option value="@monthly">@monthly - Every month</option>
                </select>
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <Button variant="outline" onClick={() => setNewDagDialogOpen(false)}>
                Cancel
              </Button>
              <Button
                disabled={!newDagId || createMutation.isPending}
                onClick={() => createMutation.mutate()}
              >
                Create DAG
              </Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  )
}
