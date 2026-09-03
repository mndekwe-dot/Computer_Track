// @ts-check
import { defineConfig, devices } from '@playwright/test'

/**
 * End-to-end tests against the running application.
 *
 * These need both halves of the system up: Django on :8000 and the app on
 * :5173. The port matters. `CORS_ALLOWED_ORIGINS` lists only :5173, so served
 * anywhere else every request is blocked and every test fails on empty pages
 * rather than on anything real.
 *
 *   cd backend && .venv/Scripts/python manage.py runserver 8000
 *   cd frontend && npm run dev
 *   npx playwright test
 *
 * The frontend is started for you when it is not already running; the API is
 * not, because it needs a database and a Python environment this config has no
 * business guessing at.
 */
export default defineConfig({
  testDir: './tests',
  globalSetup: './tests/global-setup.js',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? [['html'], ['list']] : 'list',

  use: {
    baseURL: process.env.APP_URL || 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'] } },
    // A guard works from a phone at the gate, so it is a supported target
    // rather than a nice-to-have.
    { name: 'mobile', use: { ...devices['Pixel 5'] } },
  ],

  webServer: {
    command: 'npm run dev --prefix frontend -- --port 5173 --strictPort',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
})
