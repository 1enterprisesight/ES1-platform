import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3001,
    proxy: {
      // Platform Manager API proxy
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      // Agent Router API proxy
      '/agent-router': {
        target: 'http://localhost:8102',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/agent-router/, ''),
      },
    },
  },
})
