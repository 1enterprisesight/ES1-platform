import { useState, useEffect } from 'react'
import { Outlet, NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Network,
  Workflow,
  Brain,
  Bot,
  Database,
  Settings,
  Moon,
  Sun,
  Wifi,
  WifiOff,
  LineChart,
  Zap,
  BarChart3,
  Keyboard,
  Activity,
  Box,
  PanelRightOpen,
  PanelRightClose,
} from 'lucide-react'
import { useTheme } from '@/shared/contexts/ThemeContext'
import { useEventBus } from '@/shared/contexts/EventBusContext'
import { useBranding } from '@/shared/contexts/BrandingContext'
import { useKeyboardShortcuts } from '@/shared/hooks/useKeyboardShortcuts'
import { cn } from '@/shared/utils/cn'
import { isFeatureEnabled } from '@/config'
import type { RuntimeConfig } from '@/config'
import { Button } from '../components/Button'
import { ActivityFeed } from '../components/ActivityFeed'
import { KeyboardShortcutsHelp } from '../components/KeyboardShortcutsHelp'

function useMediaQuery(query: string) {
  const [matches, setMatches] = useState(() => window.matchMedia(query).matches)
  useEffect(() => {
    const mq = window.matchMedia(query)
    const handler = (e: MediaQueryListEvent) => setMatches(e.matches)
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [query])
  return matches
}

const allNavItems: Array<{
  to: string
  icon: typeof LayoutDashboard
  label: string
  featureFlag?: keyof RuntimeConfig['features']
  featureCheck?: () => boolean
}> = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/gateway', icon: Network, label: 'Gateway' },
  { to: '/workflows', icon: Workflow, label: 'Workflows', featureFlag: 'enableAirflow' },
  { to: '/automation', icon: Zap, label: 'Automation', featureFlag: 'enableN8n' },
  { to: '/ai', icon: Brain, label: 'AI Flows', featureFlag: 'enableLangflow' },
  { to: '/agents', icon: Bot, label: 'Agents' },
  { to: '/knowledge', icon: Database, label: 'Knowledge' },
  { to: '/traffic', icon: Activity, label: 'API Traffic' },
  { to: '/models', icon: Box, label: 'Models', featureCheck: () => isFeatureEnabled('enableOllama') || isFeatureEnabled('enableMlflow') },
  { to: '/observability', icon: LineChart, label: 'Observability', featureFlag: 'enableLangfuse' },
  { to: '/monitoring', icon: BarChart3, label: 'Monitoring', featureFlag: 'enableMonitoring' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

const navItems = allNavItems.filter(item => {
  if (item.featureFlag) return isFeatureEnabled(item.featureFlag)
  if (item.featureCheck) return item.featureCheck()
  return true
})

export function MainLayout() {
  const { setTheme, resolvedTheme } = useTheme()
  const { events, connected, clearEvents } = useEventBus()
  const { branding } = useBranding()
  const [showShortcuts, setShowShortcuts] = useState(false)
  const [activityOverride, setActivityOverride] = useState<boolean | null>(null)
  const hideActivity = useMediaQuery('(max-width: 1399px)')
  const collapseNav = useMediaQuery('(max-width: 1079px)')

  // Auto-show/hide activity when crossing breakpoint, unless user toggled manually
  useEffect(() => {
    setActivityOverride(null)
  }, [hideActivity])

  const showActivity = activityOverride ?? !hideActivity

  // Initialize keyboard shortcuts
  useKeyboardShortcuts(() => setShowShortcuts(true))

  // Close on Escape
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setShowShortcuts(false)
    }
    window.addEventListener('keydown', handleEscape)
    return () => window.removeEventListener('keydown', handleEscape)
  }, [])

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar — icons-only when collapseNav */}
      <aside className={cn(
        'border-r bg-card flex flex-col shrink-0 transition-[width] duration-200',
        collapseNav ? 'w-14' : 'w-48'
      )}>
        {/* Logo */}
        <div className="h-14 flex items-center px-3 border-b gap-3 overflow-hidden">
          {branding.logo_url && (
            <img
              src={resolvedTheme === 'dark' && branding.logo_dark_url ? branding.logo_dark_url : branding.logo_url}
              alt={branding.name}
              className="h-8 w-auto shrink-0"
            />
          )}
          {!collapseNav && (
            <h1 className="text-lg font-semibold truncate">{branding.name}</h1>
          )}
        </div>

        {/* Navigation */}
        <nav className={cn('flex-1 space-y-1', collapseNav ? 'p-2' : 'p-3')}>
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              title={collapseNav ? item.label : undefined}
              className={({ isActive }) =>
                cn(
                  'flex items-center rounded-md text-sm transition-colors',
                  collapseNav ? 'justify-center p-2' : 'gap-3 px-3 py-2',
                  isActive
                    ? 'bg-primary text-primary-foreground'
                    : 'hover:bg-accent hover:text-accent-foreground'
                )
              }
            >
              <item.icon className="h-4 w-4 shrink-0" />
              {!collapseNav && item.label}
            </NavLink>
          ))}
        </nav>

        {/* Theme Toggle */}
        <div className={cn('border-t', collapseNav ? 'p-2' : 'p-3')}>
          <Button
            variant="ghost"
            size="sm"
            className={cn(collapseNav ? 'w-full justify-center' : 'w-full justify-start')}
            title={collapseNav ? (resolvedTheme === 'dark' ? 'Light Mode' : 'Dark Mode') : undefined}
            onClick={() => setTheme(resolvedTheme === 'dark' ? 'light' : 'dark')}
          >
            {resolvedTheme === 'dark' ? (
              <>
                <Sun className="h-4 w-4 shrink-0" />
                {!collapseNav && <span className="ml-2">Light Mode</span>}
              </>
            ) : (
              <>
                <Moon className="h-4 w-4 shrink-0" />
                {!collapseNav && <span className="ml-2">Dark Mode</span>}
              </>
            )}
          </Button>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        {/* Top Bar */}
        <header className="h-14 border-b bg-card flex items-center justify-between px-6 shrink-0">
          <div className="flex items-center gap-2">
            {connected ? (
              <Wifi className="h-4 w-4 text-green-500" />
            ) : (
              <WifiOff className="h-4 w-4 text-red-500" />
            )}
            <span className="text-sm text-muted-foreground">
              {connected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowShortcuts(true)}
              className="text-muted-foreground"
            >
              <Keyboard className="h-4 w-4 mr-2" />
              <span className="text-xs">Ctrl+/</span>
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setActivityOverride(!showActivity)}
              className="text-muted-foreground"
              title={showActivity ? 'Hide activity' : 'Show activity'}
            >
              {showActivity ? (
                <PanelRightClose className="h-4 w-4" />
              ) : (
                <PanelRightOpen className="h-4 w-4" />
              )}
            </Button>
          </div>
        </header>

        {/* Page Content with Activity Feed */}
        <div className="flex-1 flex overflow-hidden">
          {/* Main Content Area */}
          <main className="flex-1 overflow-auto p-6 min-w-0">
            <Outlet />
          </main>

          {/* Activity Feed Sidebar — collapsible */}
          {showActivity && (
            <aside className="w-64 border-l bg-card overflow-hidden shrink-0">
              <ActivityFeed events={events} onClear={clearEvents} />
            </aside>
          )}
        </div>
      </div>

      {/* Keyboard Shortcuts Help Modal */}
      <KeyboardShortcutsHelp
        isOpen={showShortcuts}
        onClose={() => setShowShortcuts(false)}
      />
    </div>
  )
}
