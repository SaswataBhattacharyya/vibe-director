import { defineConfig } from '@playwright/test';

const port = process.env.VIBE_DIRECTOR_TEST_PORT || '5180';
const configuredUiUrl = process.env.VIBE_DIRECTOR_UI_URL || `http://127.0.0.1:${port}`;
process.env.VIBE_UI_BASE_URL ||= configuredUiUrl;

export default defineConfig({
  testDir: './tests',
  outputDir: process.env.PLAYWRIGHT_OUTPUT_DIR || '/tmp/vibe-director-playwright-results',
  webServer: process.env.VIBE_DIRECTOR_UI_URL ? undefined : {
    // Keep pagehide/keepalive requests from escaping mocks into the owner's backend.
    env: { VIBE_DIRECTOR_API_PROXY: 'http://127.0.0.1:1' },
    command: `npm run dev -- --host 127.0.0.1 --port ${port} --strictPort --configLoader runner`,
    url: `http://127.0.0.1:${port}`,
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
  },
  use: {
    baseURL: configuredUiUrl,
    browserName: 'chromium',
    launchOptions: {
      executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE || undefined,
    },
  },
  reporter: 'line',
});
