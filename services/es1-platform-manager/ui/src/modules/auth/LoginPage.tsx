import { useState, FormEvent } from 'react'
import { KeyRound, AlertCircle, Loader2 } from 'lucide-react'
import { useAuth } from '@/shared/contexts/AuthContext'
import { useBranding } from '@/shared/contexts/BrandingContext'

export function LoginPage() {
  const { login } = useAuth()
  const { branding } = useBranding()
  const [apiKey, setApiKey] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!apiKey.trim()) {
      setError('API key is required')
      return
    }

    setError('')
    setIsSubmitting(true)

    const result = await login(apiKey.trim())
    if (!result.success) {
      setError(result.error || 'Authentication failed')
    }

    setIsSubmitting(false)
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          {branding.logo_url ? (
            <img
              src={branding.logo_url}
              alt={branding.name}
              className="h-12 mx-auto mb-4"
            />
          ) : (
            <div className="flex items-center justify-center mb-4">
              <KeyRound className="h-10 w-10 text-primary" />
            </div>
          )}
          <h1 className="text-2xl font-semibold text-foreground">
            {branding.name}
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Enter your API key to sign in
          </p>
        </div>

        <div className="rounded-lg border bg-card p-6 shadow-sm">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="api-key"
                className="block text-sm font-medium text-foreground mb-1.5"
              >
                API Key
              </label>
              <input
                id="api-key"
                type="password"
                value={apiKey}
                onChange={(e) => {
                  setApiKey(e.target.value)
                  if (error) setError('')
                }}
                placeholder="pk_..."
                autoFocus
                disabled={isSubmitting}
                className="w-full px-3 py-2 border rounded-md bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
              />
            </div>

            {error && (
              <div className="flex items-center gap-2 text-sm text-destructive">
                <AlertCircle className="h-4 w-4 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={isSubmitting || !apiKey.trim()}
              className="w-full h-9 px-4 rounded-md bg-primary text-primary-foreground font-medium text-sm hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50 disabled:pointer-events-none flex items-center justify-center"
            >
              {isSubmitting ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                'Sign In'
              )}
            </button>
          </form>
        </div>

        <p className="text-xs text-muted-foreground text-center mt-4">
          Contact your administrator to obtain an API key
        </p>
      </div>
    </div>
  )
}
