import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The desk runs at http://localhost:5173 (or the next free port if that one is busy)
// and talks to the FastAPI backend at http://localhost:8000 (see src/api.ts).
// PORT lets an outside launcher pick the port.
export default defineConfig({
  plugins: [react()],
  server: {
    port: Number(process.env.PORT) || 5173,
    open: !process.env.PORT,
  },
})
