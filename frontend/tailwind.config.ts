import type { Config } from 'tailwindcss';
export default { content: ['./index.html','./src/**/*.{ts,tsx}'], theme: { extend: { colors: { canvas: '#101114', panel: '#17181c', accent: '#c3f56a' }, fontFamily: { sans: ['DM Sans','sans-serif'], display: ['Manrope','sans-serif'] } } }, plugins: [] } satisfies Config;
