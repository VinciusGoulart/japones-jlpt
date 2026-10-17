import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// API=http://127.0.0.1:8788 npm run dev — aponta o painel para uma API de teste (cópia do banco)
const API = process.env.API ?? 'http://127.0.0.1:8787'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { '@': path.resolve(import.meta.dirname, './src') },
  },
  server: {
    proxy: { '/api': API },
  },
  preview: {
    proxy: { '/api': API },
  },
  // O FastAPI serve sistema/web/dist com fallback de SPA (DESIGN §10).
  build: { outDir: 'dist' },
})
