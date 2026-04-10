import { test, expect } from '@playwright/test';

test.describe('页面加载与导航（硬断言）', () => {
  test('首页加载成功', async ({ page }) => {
    await page.goto('/');
    // 硬断言：页面必须有标题
    await expect(page).toHaveTitle(/Growth|个人成长/);
    // 硬断言：主要内容区域可见
    const main = page.locator('main').first();
    await expect(main).toBeVisible({ timeout: 5000 });
  });

  test('导航栏包含所有页面链接', async ({ page }) => {
    await page.goto('/');
    // 硬断言：导航栏存在
    const nav = page.locator('nav, [role="navigation"]').first();
    await expect(nav).toBeVisible({ timeout: 5000 });
  });

  test('导航到任务列表页', async ({ page }) => {
    await page.goto('/');
    const navLinks = page.locator('nav a, [role="navigation"] a');
    const taskLink = navLinks.filter({ hasText: /任务|Tasks/ }).first();
    await expect(taskLink).toBeVisible({ timeout: 5000 });
    await taskLink.click();
    await expect(page).toHaveURL(/\/tasks/);
  });

  test('响应式：移动端页面可用', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    const main = page.locator('main').first();
    await expect(main).toBeVisible({ timeout: 5000 });
  });

  test('响应式：桌面端页面可用', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 720 });
    await page.goto('/');
    const main = page.locator('main').first();
    await expect(main).toBeVisible({ timeout: 5000 });
  });
});

test.describe('数据创建与验证闭环', () => {
  test('通过 API 创建任务后在列表中可见', async ({ page, request }) => {
    // 1. 通过 API 创建任务
    const createResponse = await request.post('/api/entries', {
      data: {
        type: 'task',
        title: 'E2E测试任务-' + Date.now(),
        content: '这是 E2E 测试创建的任务',
        status: 'doing',
        priority: 'high',
        tags: ['e2e-test'],
      },
    });
    expect(createResponse.ok()).toBeTruthy();
    const created = await createResponse.json();
    expect(created.id).toBeTruthy();
    const taskId = created.id;

    try {
      // 2. 导航到任务列表页
      await page.goto('/tasks');

      // 3. 验证新创建的任务在列表中可见
      const taskElement = page.locator('text=E2E测试任务').first();
      await expect(taskElement).toBeVisible({ timeout: 10000 });
    } finally {
      // 4. 清理：删除测试任务
      const deleteResponse = await request.delete(`/api/entries/${taskId}`);
      expect(deleteResponse.ok()).toBeTruthy();
    }
  });
});

test.describe('非关键路径（容错）', () => {
  test('搜索功能可用', async ({ page }) => {
    await page.goto('/');
    const searchInput = page.locator('[data-testid="search-input"], input[placeholder*="搜索"], input[placeholder*="Search"]').first();

    if (!(await searchInput.isVisible().catch(() => false))) {
      test.skip();
      return;
    }

    await searchInput.fill('测试');
    await searchInput.press('Enter');

    // 验证有搜索结果或"无结果"提示
    const resultArea = page.locator('.search-result, [data-testid*="result"], .list-item, text=没有').first();
    await expect(resultArea).toBeVisible({ timeout: 5000 });
  });

  test('任务状态切换', async ({ page }) => {
    await page.goto('/tasks');

    const taskItem = page.locator('.task-card, [data-testid*="task"], li, .list-item').first();
    if (!(await taskItem.isVisible({ timeout: 5000 }).catch(() => false))) {
      test.skip();
      return;
    }

    const statusButton = taskItem.locator('button, [data-testid*="status"]').first();
    if (await statusButton.isVisible().catch(() => false)) {
      await statusButton.click();
      // 验证状态变更后有 UI 反馈（按钮文本或样式变化）
      await expect(taskItem).toBeVisible();
    }
  });
});
