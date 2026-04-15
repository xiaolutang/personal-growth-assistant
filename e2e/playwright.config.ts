import { defineConfig, devices } from '@playwright/test';

/**
 * E2E 测试配置
 *
 * 双服务拓扑：
 * - 后端 uvicorn :18929（健康检查 GET /health）
 * - 前端 vite dev server :5173（/api 代理到后端）
 *
 * 测试通过前端 URL 访问页面，API 调用走 /api 代理。
 */
export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  timeout: 30000,
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

  webServer: [
    {
      // 后端：uvicorn，端口 18929
      command: 'mkdir -p /tmp/pga_e2e_data && cd ../backend && DATA_DIR=/tmp/pga_e2e_data JWT_SECRET=test_e2e_secret LLM_API_KEY=fake_e2e_key LLM_BASE_URL=http://localhost:19999 LLM_MODEL=fake-model uv run uvicorn app.main:app --host 0.0.0.0 --port 18929',
      url: 'http://localhost:18929/health',
      reuseExistingServer: !process.env.CI,
      timeout: 30000,
    },
    {
      // 前端：vite dev server，端口 5173
      command: 'cd ../frontend && npm run dev -- --port 5173',
      url: 'http://localhost:5173',
      reuseExistingServer: !process.env.CI,
      timeout: 30000,
    },
  ],
});
