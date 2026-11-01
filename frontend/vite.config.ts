import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react-swc';
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', '');
  return { plugins: [react()], server: { host: '127.0.0.1', port: 8082, strictPort: false, proxy: { '/api': { target: env.VIBE_DIRECTOR_API_PROXY || 'http://127.0.0.1:3020', changeOrigin: false } } } };
});
