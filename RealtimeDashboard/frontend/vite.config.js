import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000, // Same port as CRA for consistency
    open: true
  },
  // Ensure proper handling of public assets
  publicDir: 'public',
  // Enable support for absolute imports from src
  resolve: {
    alias: {
      '@': '/src'
    }
  }
});
