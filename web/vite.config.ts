import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 37233,
    host: 'localhost',
    proxy: {
      '/v1': {
        target: process.env.VITE_DEV_API_ORIGIN ?? 'https://tv.test71.xyz',
        changeOrigin: true,
        secure: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          videojs: ['@videojs/react', '@videojs/react/video', '@videojs/react/media/hls-video'],
        },
      },
    },
  },
});
