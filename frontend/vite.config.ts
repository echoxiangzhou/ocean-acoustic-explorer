import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import cesium from 'vite-plugin-cesium'

export default defineConfig({
  plugins: [react(), cesium()],
  optimizeDeps: {
    include: ['resium', 'cesium', 'react', 'react-dom', 'react-plotly.js', 'plotly.js-dist-min'],
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://backend:8000',
        changeOrigin: true,
      },
      '/wms': {
        target: 'http://wms-server:8090',
        changeOrigin: true,
      },
    },
  },
})
