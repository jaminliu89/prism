import { defineConfig } from '@playwright/test'

const macChrome = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
const browser = process.env.CI
  ? { browserName: 'chromium' as const }
  : { browserName: 'chromium' as const, launchOptions: { executablePath: macChrome } }

export default defineConfig({
  testDir: 'tests',
  fullyParallel: false,
  workers: 1,
  reporter: [['list'], ['json', { outputFile: '../work/v03-browser-results.json' }]],
  use: {
    baseURL: 'http://127.0.0.1:8774',
    viewport: { width: 1440, height: 1000 },
    ...browser,
  },
  webServer: {
    command: `python3 ../scripts/foundry_web.py --workspace ../work/browser-projects-${Date.now()} --port 8774`,
    url: 'http://127.0.0.1:8774/api/projects',
    reuseExistingServer: false,
    timeout: 30_000,
  },
  timeout: 60_000,
})
