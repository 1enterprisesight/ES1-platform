import { useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTheme } from '../contexts/ThemeContext'
import { useEventBus } from '../contexts/EventBusContext'

interface ShortcutDefinition {
  key: string
  ctrl?: boolean
  shift?: boolean
  alt?: boolean
  description: string
  action: () => void
}

export const SHORTCUTS: Omit<ShortcutDefinition, 'action'>[] = [
  { key: 'g', description: 'Go to Dashboard', ctrl: true },
  { key: '1', description: 'Go to Gateway', ctrl: true },
  { key: '2', description: 'Go to Workflows', ctrl: true },
  { key: '3', description: 'Go to Automation', ctrl: true },
  { key: '4', description: 'Go to AI Flows', ctrl: true },
  { key: '5', description: 'Go to Observability', ctrl: true },
  { key: '6', description: 'Go to Monitoring', ctrl: true },
  { key: 'd', description: 'Toggle dark mode', ctrl: true, shift: true },
  { key: 'k', description: 'Clear activity feed', ctrl: true, shift: true },
  { key: '/', description: 'Show keyboard shortcuts', ctrl: true },
]

export function useKeyboardShortcuts(onShowHelp?: () => void) {
  const navigate = useNavigate()
  const { setTheme, resolvedTheme } = useTheme()
  const { clearEvents } = useEventBus()

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      // Don't trigger shortcuts when typing in inputs
      const target = event.target as HTMLElement
      if (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable
      ) {
        return
      }

      const { key, ctrlKey, shiftKey, metaKey } = event
      const ctrl = ctrlKey || metaKey // Support both Ctrl and Cmd (Mac)

      // Ctrl+G - Go to Dashboard
      if (ctrl && key.toLowerCase() === 'g' && !shiftKey) {
        event.preventDefault()
        navigate('/')
        return
      }

      // Ctrl+1 through Ctrl+6 - Navigation
      if (ctrl && !shiftKey) {
        const routes: Record<string, string> = {
          '1': '/gateway',
          '2': '/workflows',
          '3': '/automation',
          '4': '/ai',
          '5': '/observability',
          '6': '/monitoring',
        }
        if (routes[key]) {
          event.preventDefault()
          navigate(routes[key])
          return
        }
      }

      // Ctrl+Shift+D - Toggle dark mode
      if (ctrl && shiftKey && key.toLowerCase() === 'd') {
        event.preventDefault()
        setTheme(resolvedTheme === 'dark' ? 'light' : 'dark')
        return
      }

      // Ctrl+Shift+K - Clear activity feed
      if (ctrl && shiftKey && key.toLowerCase() === 'k') {
        event.preventDefault()
        clearEvents()
        return
      }

      // Ctrl+/ - Show help
      if (ctrl && key === '/') {
        event.preventDefault()
        onShowHelp?.()
        return
      }
    },
    [navigate, setTheme, resolvedTheme, clearEvents, onShowHelp]
  )

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])
}

export function formatShortcut(shortcut: Omit<ShortcutDefinition, 'action'>): string {
  const parts: string[] = []

  // Use ⌘ for Mac, Ctrl for others
  const isMac = typeof navigator !== 'undefined' && /Mac|iPod|iPhone|iPad/.test(navigator.platform)

  if (shortcut.ctrl) parts.push(isMac ? '⌘' : 'Ctrl')
  if (shortcut.shift) parts.push('Shift')
  if (shortcut.alt) parts.push(isMac ? '⌥' : 'Alt')

  // Format key nicely
  let keyDisplay = shortcut.key.toUpperCase()
  if (shortcut.key === '/') keyDisplay = '/'

  parts.push(keyDisplay)

  return parts.join(isMac ? '' : '+')
}
