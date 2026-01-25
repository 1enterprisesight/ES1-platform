import { useState } from 'react';
import { apiFetch } from '../lib/api';

export interface ColorConfig {
  primary: string;
  primaryHover: string;
  secondary: string;
  secondaryHover: string;
  accent: string;
  danger: string;
  success: string;
  warning: string;
  info: string;
}

export interface FontConfig {
  heading: string;
  body: string;
  mono: string;
}

export interface TerminologyConfig {
  workflow: string;
  workflows: string;
  connection: string;
  connections: string;
  service: string;
  services: string;
  gateway: string;
  orchestrator: string;
  exposure: string;
  exposures: string;
  pushToGateway: string;
  approve: string;
  reject: string;
  deploy: string;
  deployment: string;
  rollback: string;
}

export interface BrandingConfig {
  companyName: string;
  productName: string;
  logoUrl: string;
  faviconUrl: string;
  colors: ColorConfig;
  fonts: FontConfig;
  terminology: TerminologyConfig;
}

export const useBrandingConfig = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const getBranding = async (): Promise<BrandingConfig | null> => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiFetch<BrandingConfig>('/branding');
      return data;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);
      return null;
    } finally {
      setIsLoading(false);
    }
  };

  const updateBranding = async (branding: BrandingConfig): Promise<{ success: boolean; message?: string }> => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiFetch<{ success: boolean; message: string; branding: BrandingConfig }>('/branding', {
        method: 'PUT',
        body: JSON.stringify(branding),
      });
      return { success: true, message: data.message };
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);
      return { success: false, message: errorMessage };
    } finally {
      setIsLoading(false);
    }
  };

  return {
    getBranding,
    updateBranding,
    isLoading,
    error,
  };
};
