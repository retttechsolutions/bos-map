import { defineConfig } from 'vite'

export default defineConfig({
  root: '.',
  build: {
    outDir: '../docs',
    emptyOutDir: false, // don't delete api/ and data/ subdirs
    assetsDir: 'assets',
  },
  server: {
    port: 5173,
    // Proxy data files to docs/ during development
    proxy: {
      '/data': {
        target: 'http://localhost:5174',
        changeOrigin: false,
      },
      '/api': {
        target: 'http://localhost:5174',
        changeOrigin: false,
      },
    },
  },
  test: {
    environment: 'jsdom',
  },
})
