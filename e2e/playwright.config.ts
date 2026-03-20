import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  // 如果需要自动启动后端服务
  // webServer: {
  //   command: 'cd ../backend && uvicorn app.main:app --port 8000',
  //   url: 'http://localhost:8000/api/health',
  //   reuseExistingServer: !process.env.CI,
  //   timeout: 120000,
  // },
});
