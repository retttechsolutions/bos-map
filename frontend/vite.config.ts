import { defineConfig } from 'vite'

export default defineConfig({
  root: '.',
  build: {
    // Output goes to docs/ when building for the data repo (pipeline CI).
    // When building for bos-map.github.io the workflow sets outDir via env.
    outDir: process.env.VITE_OUT_DIR ?? '../docs',
    emptyOutDir: false,
    assetsDir: 'assets',
  },
  server: {
    port: 5173,
    // Local dev: proxy data requests to a locally served docs/ folder
    proxy: {
      '/data': { target: 'http://localhost:5174', changeOrigin: false },
      '/api':  { target: 'http://localhost:5174', changeOrigin: false },
    },
  },
  test: {
    environment: 'jsdom',
  },
})
