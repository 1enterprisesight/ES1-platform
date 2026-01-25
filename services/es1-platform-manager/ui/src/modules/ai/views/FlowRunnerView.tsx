import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { Card, Button, Badge } from '../../../design-system/components'
import { useToast } from '../../../shared/contexts/ToastContext'

interface Flow {
  id: string
  name: string
  description: string | null
  endpoint_name: string | null
}

interface FlowsResponse {
  flows: Flow[]
  total: number
}

interface FlowRunResponse {
  outputs: any[]
  session_id: string | null
}

async function fetchFlows(): Promise<FlowsResponse> {
  const res = await fetch('/api/v1/langflow/flows')
  if (!res.ok) throw new Error('Failed to fetch flows')
  return res.json()
}

async function runFlow(
  flowId: string,
  input: string
): Promise<FlowRunResponse> {
  const res = await fetch(`/api/v1/langflow/flows/${flowId}/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      input_value: input,
      input_type: 'chat',
      output_type: 'chat',
    }),
  })
  if (!res.ok) throw new Error('Failed to run flow')
  return res.json()
}

export function FlowRunnerView() {
  const { addToast } = useToast()
  const [selectedFlowId, setSelectedFlowId] = useState<string>('')
  const [input, setInput] = useState('')
  const [output, setOutput] = useState<string | null>(null)

  const { data: flowsData, isLoading: flowsLoading } = useQuery({
    queryKey: ['langflow', 'flows'],
    queryFn: fetchFlows,
  })

  const runMutation = useMutation({
    mutationFn: ({ flowId, input }: { flowId: string; input: string }) =>
      runFlow(flowId, input),
    onSuccess: (result) => {
      // Extract output from the response
      const outputText =
        result.outputs?.[0]?.outputs?.[0]?.results?.message?.text ||
        result.outputs?.[0]?.outputs?.[0]?.messages?.[0]?.message ||
        JSON.stringify(result.outputs, null, 2)
      setOutput(outputText)
      addToast({ type: 'success', message: 'Flow executed successfully' })
    },
    onError: (error: Error) => {
      addToast({ type: 'error', message: error.message })
      setOutput(`Error: ${error.message}`)
    },
  })

  const flows = flowsData?.flows || []
  const selectedFlow = flows.find((f) => f.id === selectedFlowId)

  return (
    <div className="space-y-6">
      <Card className="p-4">
        <h3 className="font-medium mb-4">Select a Flow</h3>
        {flowsLoading ? (
          <p className="text-muted-foreground">Loading flows...</p>
        ) : flows.length === 0 ? (
          <p className="text-muted-foreground">No flows available</p>
        ) : (
          <div className="grid gap-2 md:grid-cols-2 lg:grid-cols-3">
            {flows.map((flow) => (
              <button
                key={flow.id}
                onClick={() => setSelectedFlowId(flow.id)}
                className={`text-left p-3 rounded-lg border transition-colors ${
                  selectedFlowId === flow.id
                    ? 'border-primary bg-primary/5'
                    : 'border-border hover:border-primary/50'
                }`}
              >
                <p className="font-medium truncate">{flow.name}</p>
                {flow.description && (
                  <p className="text-sm text-muted-foreground truncate">
                    {flow.description}
                  </p>
                )}
              </button>
            ))}
          </div>
        )}
      </Card>

      {selectedFlow && (
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-4">
            <h3 className="font-medium">Running: {selectedFlow.name}</h3>
            {selectedFlow.endpoint_name && (
              <Badge variant="outline" className="font-mono text-xs">
                /{selectedFlow.endpoint_name}
              </Badge>
            )}
          </div>

          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium text-muted-foreground block mb-2">
                Input
              </label>
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Enter your message or input..."
                className="w-full h-32 px-3 py-2 rounded-md border border-input bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring resize-none"
              />
            </div>

            <Button
              onClick={() =>
                runMutation.mutate({ flowId: selectedFlowId, input })
              }
              disabled={!input.trim() || runMutation.isPending}
            >
              {runMutation.isPending ? 'Running...' : 'Run Flow'}
            </Button>

            {output && (
              <div>
                <label className="text-sm font-medium text-muted-foreground block mb-2">
                  Output
                </label>
                <div className="p-4 rounded-md border border-border bg-muted/30 font-mono text-sm whitespace-pre-wrap">
                  {output}
                </div>
              </div>
            )}
          </div>
        </Card>
      )}
    </div>
  )
}
