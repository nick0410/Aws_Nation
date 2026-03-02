import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",   // force IPv4, fixes blank page on Windows
    port: 5173,
    strictPort: true,
  },
})
