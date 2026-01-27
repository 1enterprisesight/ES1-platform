import { AlertCircle, RefreshCw, ExternalLink, Copy, ChevronDown, ChevronUp } from 'lucide-react'
import { useState } from 'react'
import { cn } from '@/shared/utils/cn'
import { Button } from './Button'

interface ErrorDisplayProps {
  title?: string
  message: string
  error?: Error | string | null
  onRetry?: () => void
  retryLabel?: string
  suggestion?: string
  helpLink?: { label: string; url: string }
  className?: string
  variant?: 'default' | 'inline' | 'card'
}

export function ErrorDisplay({
  title = 'Something went wrong',
  message,
  error,
  onRetry,
  retryLabel = 'Try again',
  suggestion,
  helpLink,
  className,
  variant = 'default',
}: ErrorDisplayProps) {
  const [showDetails, setShowDetails] = useState(false)
  const [copied, setCopied] = useState(false)

  const errorDetails = error instanceof Error ? error.message : error

  const copyError = async () => {
    const textToCopy = `${title}\n${message}${errorDetails ? `\n\nDetails: ${errorDetails}` : ''}`
    await navigator.clipboard.writeText(textToCopy)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (variant === 'inline') {
    return (
      <div className={cn('flex items-center gap-2 text-destructive', className)}>
        <AlertCircle className="h-4 w-4 flex-shrink-0" />
        <span className="text-sm">{message}</span>
        {onRetry && (
          <button
            onClick={onRetry}
            className="text-sm underline hover:no-underline ml-2"
          >
            {retryLabel}
          </button>
        )}
      </div>
    )
  }

  return (
    <div
      className={cn(
        'rounded-lg border border-destructive/50 bg-destructive/5 p-4',
        variant === 'card' && 'shadow-sm',
        className
      )}
    >
      <div className="flex items-start gap-3">
        <div className="p-2 rounded-full bg-destructive/10">
          <AlertCircle className="h-5 w-5 text-destructive" />
        </div>

        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-destructive">{title}</h3>
          <p className="text-sm text-muted-foreground mt-1">{message}</p>

          {suggestion && (
            <p className="text-sm text-muted-foreground mt-2 p-2 bg-muted/50 rounded">
              <strong>Suggestion:</strong> {suggestion}
            </p>
          )}

          {/* Error Details (expandable) */}
          {errorDetails && (
            <div className="mt-3">
              <button
                onClick={() => setShowDetails(!showDetails)}
                className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
              >
                {showDetails ? (
                  <ChevronUp className="h-3 w-3" />
                ) : (
                  <ChevronDown className="h-3 w-3" />
                )}
                {showDetails ? 'Hide' : 'Show'} technical details
              </button>

              {showDetails && (
                <div className="mt-2 p-2 bg-muted rounded text-xs font-mono overflow-x-auto">
                  <pre className="whitespace-pre-wrap break-all">{errorDetails}</pre>
                </div>
              )}
            </div>
          )}

          {/* Actions */}
          <div className="flex flex-wrap items-center gap-2 mt-4">
            {onRetry && (
              <Button size="sm" onClick={onRetry}>
                <RefreshCw className="h-3 w-3 mr-1.5" />
                {retryLabel}
              </Button>
            )}

            {helpLink && (
              <Button size="sm" variant="outline" asChild>
                <a href={helpLink.url} target="_blank" rel="noopener noreferrer">
                  <ExternalLink className="h-3 w-3 mr-1.5" />
                  {helpLink.label}
                </a>
              </Button>
            )}

            <Button size="sm" variant="ghost" onClick={copyError}>
              <Copy className="h-3 w-3 mr-1.5" />
              {copied ? 'Copied!' : 'Copy error'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}

// Specialized error displays for common scenarios

interface ServiceErrorProps {
  serviceName: string
  onRetry?: () => void
  setupUrl?: string
}

export function ServiceConnectionError({
  serviceName,
  onRetry,
  setupUrl,
}: ServiceErrorProps) {
  return (
    <ErrorDisplay
      title={`Cannot connect to ${serviceName}`}
      message={`The ${serviceName} service is not responding. This could be because the service is not running or is still starting up.`}
      suggestion={`Check if ${serviceName} is running with 'docker ps' or view the logs with 'docker logs <container-name>'.`}
      onRetry={onRetry}
      retryLabel="Retry connection"
      helpLink={setupUrl ? { label: `Open ${serviceName}`, url: setupUrl } : undefined}
    />
  )
}

export function ServiceSetupRequired({
  serviceName,
  setupUrl,
  instructions,
}: {
  serviceName: string
  setupUrl: string
  instructions?: string[]
}) {
  return (
    <div className="rounded-lg border border-amber-500/50 bg-amber-50 dark:bg-amber-900/20 p-4">
      <div className="flex items-start gap-3">
        <div className="p-2 rounded-full bg-amber-100 dark:bg-amber-900/50">
          <AlertCircle className="h-5 w-5 text-amber-600 dark:text-amber-400" />
        </div>

        <div className="flex-1">
          <h3 className="font-semibold text-amber-800 dark:text-amber-200">
            {serviceName} Setup Required
          </h3>
          <p className="text-sm text-amber-700 dark:text-amber-300 mt-1">
            {serviceName} needs to be configured before it can be managed from this dashboard.
          </p>

          {instructions && instructions.length > 0 && (
            <ol className="text-sm text-amber-700 dark:text-amber-300 list-decimal list-inside space-y-1 mt-3">
              {instructions.map((instruction, i) => (
                <li key={i}>{instruction}</li>
              ))}
            </ol>
          )}

          <div className="mt-4">
            <Button size="sm" asChild>
              <a href={setupUrl} target="_blank" rel="noopener noreferrer">
                <ExternalLink className="h-3 w-3 mr-1.5" />
                Open {serviceName} Setup
              </a>
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
}: {
  icon: React.ComponentType<{ className?: string }>
  title: string
  description: string
  action?: { label: string; onClick?: () => void; href?: string }
}) {
  return (
    <div className="rounded-lg border border-dashed p-8 text-center">
      <Icon className="h-12 w-12 mx-auto text-muted-foreground/50" />
      <h3 className="mt-4 text-lg font-medium">{title}</h3>
      <p className="mt-2 text-sm text-muted-foreground max-w-md mx-auto">
        {description}
      </p>
      {action && (
        <div className="mt-4">
          {action.href ? (
            <Button asChild>
              <a href={action.href} target="_blank" rel="noopener noreferrer">
                {action.label}
                <ExternalLink className="h-4 w-4 ml-1.5" />
              </a>
            </Button>
          ) : (
            <Button onClick={action.onClick}>{action.label}</Button>
          )}
        </div>
      )}
    </div>
  )
}
