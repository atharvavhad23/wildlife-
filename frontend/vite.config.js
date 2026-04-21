import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/features': 'http://127.0.0.1:8000',
      '/predict': 'http://127.0.0.1:8000',
      '/dashboard': 'http://127.0.0.1:8000',
      '/photos': 'http://127.0.0.1:8000',
      '/photo-proxy': 'http://127.0.0.1:8000',
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
