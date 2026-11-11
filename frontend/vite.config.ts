import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Vite proxies /api and /webhooks to the FastAPI backend; one Cloudflare quick
// tunnel to :5173 exposes both to the phone (docs/11_ENV_SETUP.md).
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { '@': path.resolve(__dirname, './src') } },
  server: {
    port: 5173,
    allowedHosts: ['.trycloudflare.com'],
    proxy: {
      '/api': 'http://localhost:8000',
      '/webhooks': 'http://localhost:8000',
    },
  },
})
