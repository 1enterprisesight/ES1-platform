import { X, Keyboard } from 'lucide-react'
import { SHORTCUTS, formatShortcut } from '@/shared/hooks/useKeyboardShortcuts'
import { Button } from './Button'

interface KeyboardShortcutsHelpProps {
  isOpen: boolean
  onClose: () => void
}

export function KeyboardShortcutsHelp({ isOpen, onClose }: KeyboardShortcutsHelpProps) {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-card border rounded-lg shadow-lg w-full max-w-md mx-4">
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex items-center gap-2">
            <Keyboard className="h-5 w-5" />
            <h2 className="font-semibold">Keyboard Shortcuts</h2>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>

        <div className="p-4 space-y-4 max-h-[60vh] overflow-auto">
          {/* Navigation */}
          <div>
            <h3 className="text-sm font-medium text-muted-foreground mb-2">Navigation</h3>
            <div className="space-y-1">
              {SHORTCUTS.filter(s =>
                s.description.startsWith('Go to') || s.description === 'Show keyboard shortcuts'
              ).map((shortcut) => (
                <ShortcutRow key={shortcut.key + shortcut.description} shortcut={shortcut} />
              ))}
            </div>
          </div>

          {/* Actions */}
          <div>
            <h3 className="text-sm font-medium text-muted-foreground mb-2">Actions</h3>
            <div className="space-y-1">
              {SHORTCUTS.filter(s =>
                !s.description.startsWith('Go to') && s.description !== 'Show keyboard shortcuts'
              ).map((shortcut) => (
                <ShortcutRow key={shortcut.key + shortcut.description} shortcut={shortcut} />
              ))}
            </div>
          </div>
        </div>

        <div className="p-4 border-t bg-muted/30">
          <p className="text-xs text-muted-foreground text-center">
            Press <kbd className="px-1.5 py-0.5 bg-muted rounded text-xs">Esc</kbd> to close
          </p>
        </div>
      </div>
    </div>
  )
}

function ShortcutRow({ shortcut }: { shortcut: typeof SHORTCUTS[number] }) {
  return (
    <div className="flex items-center justify-between py-1.5">
      <span className="text-sm">{shortcut.description}</span>
      <kbd className="px-2 py-1 bg-muted rounded text-xs font-mono">
        {formatShortcut(shortcut)}
      </kbd>
    </div>
  )
}
