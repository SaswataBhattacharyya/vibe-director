import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react-swc';
export default defineConfig({ plugins: [react()], server: { host: '127.0.0.1', port: 8082, strictPort: true, proxy: { '/api': { target: 'http://127.0.0.1:3020', changeOrigin: false } } } });
