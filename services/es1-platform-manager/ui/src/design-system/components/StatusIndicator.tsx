import { cn } from '@/shared/utils/cn'

type Status =
  | 'healthy' | 'degraded' | 'unhealthy' | 'pending' | 'active' | 'inactive'
  | 'success' | 'error' | 'warning' | 'neutral'

interface StatusIndicatorProps {
  status: Status
  label?: string
  showPulse?: boolean
}

const statusColors: Record<Status, string> = {
  healthy: 'bg-green-500',
  degraded: 'bg-yellow-500',
  unhealthy: 'bg-red-500',
  pending: 'bg-blue-500',
  active: 'bg-green-500',
  inactive: 'bg-gray-500',
  success: 'bg-green-500',
  error: 'bg-red-500',
  warning: 'bg-yellow-500',
  neutral: 'bg-gray-500',
}

export function StatusIndicator({ status, label, showPulse = true }: StatusIndicatorProps) {
  const isPulsing = showPulse && !['inactive', 'neutral'].includes(status)

  return (
    <div className="flex items-center gap-2">
      <span className="relative flex h-2 w-2">
        {isPulsing && (
          <span
            className={cn(
              'animate-ping absolute inline-flex h-full w-full rounded-full opacity-75',
              statusColors[status]
            )}
          />
        )}
        <span
          className={cn(
            'relative inline-flex rounded-full h-2 w-2',
            statusColors[status]
          )}
        />
      </span>
      {label && (
        <span className="text-sm text-muted-foreground capitalize">{label || status}</span>
      )}
    </div>
  )
}
