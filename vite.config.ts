import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => ({
  plugins: [react()],
  base: mode === 'github-pages' ? '/multiagent-bias-output-browser/' : '/',
  server: {
    host: true,
    port: 5173,
  },
}))
