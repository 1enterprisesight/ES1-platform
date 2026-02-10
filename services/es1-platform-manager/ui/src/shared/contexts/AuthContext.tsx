import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react'
import { getConfig } from '@/config'

interface AuthUser {
  api_key_id: string | null
  user_id: string | null
  username: string | null
  permissions: string[]
  is_admin: boolean
}

interface AuthContextType {
  user: AuthUser | null
  isAuthenticated: boolean
  isLoading: boolean
  authMode: string
  login: (apiKey: string) => Promise<{ success: boolean; error?: string }>
  logout: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

const API_KEY_STORAGE_KEY = 'platform_api_key'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const authMode = getConfig().auth?.mode || 'none'
  const authRequired = authMode !== 'none'

  // Try to restore session from stored API key on mount
  useEffect(() => {
    if (!authRequired) {
      // Auth disabled — everyone is anonymous admin
      setUser({
        api_key_id: null,
        user_id: 'anonymous',
        username: 'anonymous',
        permissions: ['*'],
        is_admin: true,
      })
      setIsLoading(false)
      return
    }

    const storedKey = localStorage.getItem(API_KEY_STORAGE_KEY)
    if (!storedKey) {
      setIsLoading(false)
      return
    }

    // Validate stored key
    fetch('/api/v1/auth/me', {
      headers: { 'X-API-Key': storedKey },
    })
      .then((res) => {
        if (res.ok) return res.json()
        throw new Error('Invalid key')
      })
      .then((data) => {
        setUser(data)
      })
      .catch(() => {
        localStorage.removeItem(API_KEY_STORAGE_KEY)
      })
      .finally(() => {
        setIsLoading(false)
      })
  }, [authRequired])

  const login = useCallback(
    async (apiKey: string): Promise<{ success: boolean; error?: string }> => {
      try {
        const res = await fetch('/api/v1/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ api_key: apiKey }),
        })

        if (!res.ok) {
          return { success: false, error: 'Server error' }
        }

        const data = await res.json()
        if (!data.authenticated) {
          return { success: false, error: 'Invalid API key' }
        }

        localStorage.setItem(API_KEY_STORAGE_KEY, apiKey)
        setUser(data.user)
        return { success: true }
      } catch {
        return { success: false, error: 'Connection failed' }
      }
    },
    []
  )

  const logout = useCallback(() => {
    localStorage.removeItem(API_KEY_STORAGE_KEY)
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !authRequired || user !== null,
        isLoading,
        authMode,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

/**
 * Get the stored API key for use in fetch headers.
 * Returns null if no key is stored or auth is disabled.
 */
export function getStoredApiKey(): string | null {
  return localStorage.getItem(API_KEY_STORAGE_KEY)
}
