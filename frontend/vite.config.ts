import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Where the dev server forwards API and game-socket traffic. Locally the backend is on localhost;
// under Docker Compose it is the `backend` service, so compose sets BACKEND_URL=http://backend:8000.
const backendUrl = process.env.BACKEND_URL ?? 'http://localhost:8000'
const backendSocketUrl = backendUrl.replace(/^http/, 'ws')

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/ws': { target: backendSocketUrl, ws: true },
      '/api': backendUrl,
    },
  },
})
