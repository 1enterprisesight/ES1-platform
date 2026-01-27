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
} from 'lucide-react'
import { useTheme } from '@/shared/contexts/ThemeContext'
import { useEventBus } from '@/shared/contexts/EventBusContext'
import { useBranding } from '@/shared/contexts/BrandingContext'
import { useKeyboardShortcuts } from '@/shared/hooks/useKeyboardShortcuts'
import { cn } from '@/shared/utils/cn'
import { Button } from '../components/Button'
import { ActivityFeed } from '../components/ActivityFeed'
import { KeyboardShortcutsHelp } from '../components/KeyboardShortcutsHelp'

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/gateway', icon: Network, label: 'Gateway' },
  { to: '/workflows', icon: Workflow, label: 'Workflows' },
  { to: '/automation', icon: Zap, label: 'Automation' },
  { to: '/ai', icon: Brain, label: 'AI Flows' },
  { to: '/agents', icon: Bot, label: 'Agents' },
  { to: '/knowledge', icon: Database, label: 'Knowledge' },
  { to: '/traffic', icon: Activity, label: 'API Traffic' },
  { to: '/models', icon: Box, label: 'Models' },
  { to: '/observability', icon: LineChart, label: 'Observability' },
  { to: '/monitoring', icon: BarChart3, label: 'Monitoring' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

export function MainLayout() {
  const { setTheme, resolvedTheme } = useTheme()
  const { events, connected, clearEvents } = useEventBus()
  const { branding } = useBranding()
  const [showShortcuts, setShowShortcuts] = useState(false)

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
      {/* Sidebar */}
      <aside className="w-64 border-r bg-card flex flex-col">
        {/* Logo */}
        <div className="h-14 flex items-center px-4 border-b gap-3">
          {branding.logo_url && (
            <img
              src={resolvedTheme === 'dark' && branding.logo_dark_url ? branding.logo_dark_url : branding.logo_url}
              alt={branding.name}
              className="h-8 w-auto"
            />
          )}
          <h1 className="text-lg font-semibold truncate">{branding.name}</h1>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors',
                  isActive
                    ? 'bg-primary text-primary-foreground'
                    : 'hover:bg-accent hover:text-accent-foreground'
                )
              }
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </NavLink>
          ))}
        </nav>

        {/* Theme Toggle */}
        <div className="p-4 border-t">
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-start"
            onClick={() => setTheme(resolvedTheme === 'dark' ? 'light' : 'dark')}
          >
            {resolvedTheme === 'dark' ? (
              <>
                <Sun className="h-4 w-4 mr-2" />
                Light Mode
              </>
            ) : (
              <>
                <Moon className="h-4 w-4 mr-2" />
                Dark Mode
              </>
            )}
          </Button>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Bar */}
        <header className="h-14 border-b bg-card flex items-center justify-between px-6">
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
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowShortcuts(true)}
            className="text-muted-foreground"
          >
            <Keyboard className="h-4 w-4 mr-2" />
            <span className="text-xs">Ctrl+/</span>
          </Button>
        </header>

        {/* Page Content with Activity Feed */}
        <div className="flex-1 flex overflow-hidden">
          {/* Main Content Area */}
          <main className="flex-1 overflow-auto p-6">
            <Outlet />
          </main>

          {/* Activity Feed Sidebar */}
          <aside className="w-80 border-l bg-card overflow-hidden">
            <ActivityFeed events={events} onClear={clearEvents} />
          </aside>
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
