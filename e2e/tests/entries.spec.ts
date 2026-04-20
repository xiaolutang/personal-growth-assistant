/**
 * B37: 条目 CRUD E2E 测试
 *
 * 覆盖条目管理的核心用户路径：创建 → 列表查看 → 状态切换 → 删除 → 空状态。
 * 每个 test 独立完成 setup（注册+登录+onboarding），通过任务页验证。
 */
import { test, expect } from '@playwright/test';
import { createEntry, deleteEntry } from './helpers/api';

const BASE = '/growth';

test.describe.configure({ timeout: 120000 });

test.describe('条目 CRUD', () => {
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

  /** 导航到任务页并等待加载完成 */
  async function goToTasks(page: any) {
    await page.getByRole('link', { name: '任务' }).click();
    await expect(page.getByRole('heading', { name: /任务列表/ })).toBeVisible({ timeout: 15000 });
    await expect(page.getByText('加载中')).not.toBeVisible({ timeout: 15000 });
  }

  test('创建任务后任务列表可见', async ({ page, request }) => {
    const username = `e2e_tlist_${Date.now().toString(36)}`;
    const token = await setupUser(request, page, username, 'testpass123');

    const entry = await createEntry(request, {
      type: 'task',
      title: 'E2E测试任务-列表可见',
    }, token);

    try {
      await goToTasks(page);
      await expect(page.locator('p', { hasText: 'E2E测试任务-列表可见' })).toBeVisible({ timeout: 10000 });
    } finally {
      await deleteEntry(request, entry.id, token);
    }
  });

  test('更新状态后 UI 保持可见', async ({ page, request }) => {
    const username = `e2e_status_${Date.now().toString(36)}`;
    const token = await setupUser(request, page, username, 'testpass123');

    const entry = await createEntry(request, {
      type: 'task',
      title: 'E2E测试-状态切换',
    }, token);

    try {
      await goToTasks(page);
      await expect(page.locator('p', { hasText: 'E2E测试-状态切换' })).toBeVisible({ timeout: 10000 });
      const toggleBtn = page.getByRole('button', { name: '切换状态' }).first();
      await toggleBtn.click();
      // 等待状态更新 API 响应并验证条目仍然可见
      await expect(page.locator('p', { hasText: 'E2E测试-状态切换' })).toBeVisible({ timeout: 10000 });
    } finally {
      await deleteEntry(request, entry.id, token);
    }
  });

  test('删除后 API 不再返回该条目', async ({ page, request }) => {
    const username = `e2e_del_${Date.now().toString(36)}`;
    const token = await setupUser(request, page, username, 'testpass123');

    const entry = await createEntry(request, {
      type: 'task',
      title: 'E2E测试-待删除任务',
    }, token);

    // 导航到任务页确认条目存在
    await goToTasks(page);
    await expect(page.locator('p', { hasText: 'E2E测试-待删除任务' })).toBeVisible({ timeout: 10000 });

    // 通过 API 删除
    await deleteEntry(request, entry.id, token);

    // 通过 API 验证条目已不存在（404）
    const getResp = await request.get(`/api/entries/${entry.id}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(getResp.status()).toBe(404);
  });

  test('空列表显示空状态提示', async ({ page, request }) => {
    const username = `e2e_empty_${Date.now().toString(36)}`;
    await setupUser(request, page, username, 'testpass123');

    await goToTasks(page);
    await expect(page.getByText(/还没有任务/)).toBeVisible({ timeout: 10000 });
  });
});
