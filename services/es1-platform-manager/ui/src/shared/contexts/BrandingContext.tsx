import { createContext, useContext, useEffect, ReactNode } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'

export interface BrandingConfig {
  name: string
  tagline: string | null
  logo_url: string | null
  logo_dark_url: string | null
  favicon_url: string | null
  primary_color: string
  secondary_color: string
  accent_color: string
  custom_css: string | null
  footer_text: string | null
  support_email: string | null
  support_url: string | null
  docs_url: string | null
}

const defaultBranding: BrandingConfig = {
  name: 'ES1 Platform',
  tagline: null,
  logo_url: null,
  logo_dark_url: null,
  favicon_url: null,
  primary_color: '#3B82F6',
  secondary_color: '#10B981',
  accent_color: '#8B5CF6',
  custom_css: null,
  footer_text: null,
  support_email: null,
  support_url: null,
  docs_url: null,
}

interface BrandingContextType {
  branding: BrandingConfig
  isLoading: boolean
  updateBranding: (updates: Partial<BrandingConfig>) => Promise<void>
  isUpdating: boolean
}

const BrandingContext = createContext<BrandingContextType | undefined>(undefined)

async function fetchBranding(): Promise<BrandingConfig> {
  const res = await fetch('/api/v1/settings/branding/config')
  if (!res.ok) throw new Error('Failed to fetch branding')
  return res.json()
}

async function updateBrandingApi(updates: Partial<BrandingConfig>): Promise<BrandingConfig> {
  const res = await fetch('/api/v1/settings/branding/config', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates),
  })
  if (!res.ok) throw new Error('Failed to update branding')
  return res.json()
}

export function BrandingProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()

  const { data: branding, isLoading } = useQuery({
    queryKey: ['branding'],
    queryFn: fetchBranding,
    staleTime: 1000 * 60 * 5, // 5 minutes
  })

  const mutation = useMutation({
    mutationFn: updateBrandingApi,
    onSuccess: (data) => {
      queryClient.setQueryData(['branding'], data)
    },
  })

  const currentBranding = branding || defaultBranding

  // Apply CSS custom properties for branding colors
  useEffect(() => {
    const root = document.documentElement
    root.style.setProperty('--brand-primary', currentBranding.primary_color)
    root.style.setProperty('--brand-secondary', currentBranding.secondary_color)
    root.style.setProperty('--brand-accent', currentBranding.accent_color)

    // Update page title
    document.title = currentBranding.name

    // Update favicon if provided
    if (currentBranding.favicon_url) {
      const link = document.querySelector("link[rel~='icon']") as HTMLLinkElement
      if (link) {
        link.href = currentBranding.favicon_url
      }
    }

    // Apply custom CSS if provided
    let styleEl = document.getElementById('custom-branding-css')
    if (currentBranding.custom_css) {
      if (!styleEl) {
        styleEl = document.createElement('style')
        styleEl.id = 'custom-branding-css'
        document.head.appendChild(styleEl)
      }
      styleEl.textContent = currentBranding.custom_css
    } else if (styleEl) {
      styleEl.remove()
    }
  }, [currentBranding])

  const updateBranding = async (updates: Partial<BrandingConfig>) => {
    await mutation.mutateAsync(updates)
  }

  return (
    <BrandingContext.Provider
      value={{
        branding: currentBranding,
        isLoading,
        updateBranding,
        isUpdating: mutation.isPending,
      }}
    >
      {children}
    </BrandingContext.Provider>
  )
}

export function useBranding() {
  const context = useContext(BrandingContext)
  if (context === undefined) {
    throw new Error('useBranding must be used within a BrandingProvider')
  }
  return context
}
