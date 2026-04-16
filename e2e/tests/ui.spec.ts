/**
 * B42: 浏览器级 UI 测试
 *
 * 补充真实浏览器渲染验证（非 API smoke）：
 * - Review 页面：Tab 切换、recharts 图表 SVG 渲染
 * - Chat：FloatingChat 输入框存在且可输入
 * - Review 空数据状态页面不崩溃
 */
import { test, expect } from '@playwright/test';
import { createEntry, deleteEntry } from './helpers/api';

const BASE = '/growth';

test.describe.configure({ timeout: 120000 });

test.describe('浏览器级 UI 测试', () => {
  /** 注册用户 + API onboarding + UI 登录，返回 token */
  async function setupUser(request: any, page: any, username: string, password: string) {
    await request.post('/api/auth/register', {
      data: { username, email: `${username}@e2e.test`, password },
    });
    const loginResp = await request.post('/api/auth/login', {
      data: { username, password },
    });
    const loginData = await loginResp.json();
    const token = loginData.access_token;

    await request.put('/api/auth/me', {
      headers: { Authorization: `Bearer ${token}` },
      data: { onboarding_completed: true },
    });

    // UI 登录
    await page.goto(`${BASE}/login`);
    await page.getByPlaceholder('请输入用户名').fill(username);
    await page.getByPlaceholder('请输入密码').fill(password);
    await page.getByRole('button', { name: '登录' }).click();
    await page.waitForURL(`**${BASE}/`, { timeout: 30000 });

    return token;
  }

  test('Review 页面 Tab 切换渲染 recharts SVG', async ({ page, request }) => {
    const username = `e2e_review_ui_${Date.now().toString(36)}`;
    const token = await setupUser(request, page, username, 'testpass123');

    // 创建一条完成的任务以产生统计数据
    const entry = await createEntry(request, {
      type: 'task',
      title: 'UI测试-回顾图表',
      status: 'completed',
    }, token);

    try {
      // 导航到回顾页
      await page.getByRole('link', { name: '回顾' }).click();
      await expect(page.getByRole('heading', { name: /成长回顾/ })).toBeVisible({ timeout: 15000 });

      // 点击趋势 Tab
      await page.getByText('趋势', { exact: true }).click();

      // recharts 渲染为 SVG — 验证 .recharts-surface 元素存在
      const chartSurface = page.locator('.recharts-surface').first();
      await expect(chartSurface).toBeVisible({ timeout: 10000 });

      // 切换回报表 Tab
      await page.getByText('日报', { exact: true }).click();
      // 页面仍然正常（不崩溃）
      await expect(page.getByRole('heading', { name: /成长回顾/ })).toBeVisible();
    } finally {
      await deleteEntry(request, entry.id, token);
    }
  });

  test('Review 页面活动热力图反映 seed 数据', async ({ page, request }) => {
    const username = `e2e_heatmap_ui_${Date.now().toString(36)}`;
    const token = await setupUser(request, page, username, 'testpass123');

    const entry = await createEntry(request, {
      type: 'task',
      title: 'UI测试-热力图',
      status: 'completed',
    }, token);

    try {
      await page.getByRole('link', { name: '回顾' }).click();
      await expect(page.getByRole('heading', { name: /成长回顾/ })).toBeVisible({ timeout: 15000 });

      // 等待 ActivityHeatmap 数据加载，找一个有数据的格子（data-count > 0）
      // 使用 CSS :not 选择器排除 count=0 的格子
      const activeCell = page.locator('[data-count]:not([data-count="0"])').first();
      await expect(activeCell).toBeVisible({ timeout: 10000 });

      // 验证选中的格子确实有数据
      const countVal = await activeCell.getAttribute('data-count');
      expect(Number(countVal)).toBeGreaterThan(0);

      // Hover 该格子，验证 tooltip 显示日期和记录数
      await activeCell.hover();
      const tooltip = page.locator('.bg-popover.text-popover-foreground');
      await expect(tooltip).toBeVisible({ timeout: 5000 });
      // 断言 tooltip 包含预期的记录数
      const tooltipText = await tooltip.textContent();
      expect(tooltipText).toContain(`${countVal} 条记录`);
    } finally {
      await deleteEntry(request, entry.id, token);
    }
  });

  test('FloatingChat 输入框在首页可输入', async ({ page, request }) => {
    const username = `e2e_chat_ui_${Date.now().toString(36)}`;
    await setupUser(request, page, username, 'testpass123');

    // 首页应有 FloatingChat 的 Input（placeholder 含 "输入内容"）
    const chatInput = page.getByPlaceholder(/输入内容|帮我搜索/);
    await expect(chatInput).toBeVisible({ timeout: 15000 });

    // 可输入文字
    await chatInput.fill('测试消息');
    await expect(chatInput).toHaveValue('测试消息');
  });

  test('Review 页面空数据时不崩溃', async ({ page, request }) => {
    const username = `e2e_review_empty_${Date.now().toString(36)}`;
    await setupUser(request, page, username, 'testpass123');

    // 新用户无数据，导航到回顾页
    await page.getByRole('link', { name: '回顾' }).click();
    await expect(page.getByRole('heading', { name: /成长回顾/ })).toBeVisible({ timeout: 15000 });

    // 页面加载完成，所有 Tab 可点击不崩溃
    for (const tab of ['周报', '月报', '趋势']) {
      await page.getByText(tab, { exact: true }).click();
      await expect(page.getByRole('heading', { name: /成长回顾/ })).toBeVisible({ timeout: 5000 });
    }
  });
});
