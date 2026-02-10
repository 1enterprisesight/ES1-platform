import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App'
import { ThemeProvider } from './shared/contexts/ThemeContext'
import { AuthProvider } from './shared/contexts/AuthContext'
import { EventBusProvider } from './shared/contexts/EventBusContext'
import { ToastProvider } from './shared/contexts/ToastContext'
import { BrandingProvider } from './shared/contexts/BrandingContext'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60, // 1 minute
      retry: 1,
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ThemeProvider>
          <AuthProvider>
            <BrandingProvider>
              <EventBusProvider>
                <ToastProvider>
                  <App />
                </ToastProvider>
              </EventBusProvider>
            </BrandingProvider>
          </AuthProvider>
        </ThemeProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
)
