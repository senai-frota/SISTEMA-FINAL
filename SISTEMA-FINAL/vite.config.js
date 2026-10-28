import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Permite acesso pelo IP da rede local (ex.: celular → http://192.168.x.x:5173)
    host: true,
  },
})
