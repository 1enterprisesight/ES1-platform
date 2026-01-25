import { createContext, useContext, useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import type { BrandingConfig } from '../types';
import { apiFetch } from '../lib/api';

const BrandingContext = createContext<BrandingConfig | null>(null);

interface BrandingProviderProps {
  children: ReactNode;
}

export const BrandingProvider = ({ children }: BrandingProviderProps) => {
  const [branding, setBranding] = useState<BrandingConfig | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    apiFetch<BrandingConfig>('/branding')
      .then((data: BrandingConfig) => {
        setBranding(data);

        // Apply CSS variables for colors
        const colors = data.colors;
        Object.entries(colors).forEach(([key, value]) => {
          if (typeof value === 'string') {
            document.documentElement.style.setProperty(`--color-${key}`, value);
          }
        });

        // Update page title
        document.title = `${data.companyName} ${data.productName}`;

        // Update favicon if provided
        if (data.faviconUrl) {
          const link =
            document.querySelector("link[rel*='icon']") ||
            document.createElement('link');
          (link as HTMLLinkElement).type = 'image/x-icon';
          (link as HTMLLinkElement).rel = 'shortcut icon';
          (link as HTMLLinkElement).href = data.faviconUrl;
          document.getElementsByTagName('head')[0].appendChild(link);
        }

        setIsLoading(false);
      })
      .catch((error) => {
        console.error('Failed to load branding config:', error);
        setIsLoading(false);
      });
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  if (!branding) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <p className="text-red-600">Failed to load branding configuration</p>
        </div>
      </div>
    );
  }

  return (
    <BrandingContext.Provider value={branding}>
      {children}
    </BrandingContext.Provider>
  );
};

export const useBranding = (): BrandingConfig => {
  const context = useContext(BrandingContext);
  if (!context) {
    throw new Error('useBranding must be used within BrandingProvider');
  }
  return context;
};
