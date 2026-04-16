/**
 * B35: E2E 基础设施验证
 *
 * 验证双服务启停、认证 fixture 和 API helper 可正常工作。
 * 这是其他 E2E 测试的前置依赖。
 */
import { test, expect } from '@playwright/test';
import { registerAndLogin } from './helpers/auth';
import { createEntry, deleteEntry, listEntries } from './helpers/api';

test.describe('E2E 基础设施', () => {
  test('后端健康检查通过', async ({ request }) => {
    const resp = await request.get('/api/health');
    expect(resp.ok()).toBeTruthy();
    const data = await resp.json();
    expect(['ok', 'degraded']).toContain(data.status);
    expect(data.services.sqlite).toBe('ok');
  });

  test('前端页面可访问', async ({ page }) => {
    await page.goto('/growth/');
    await expect(page).toHaveTitle(/Growth|个人成长/);
  });

  test('认证 fixture 成功注册+登录', async ({ request }) => {
    const user = await registerAndLogin(request);
    expect(user.token).toBeTruthy();
    expect(user.userId).toBeTruthy();

    // 验证 token 有效 — 调用 /auth/me
    const meResp = await request.get('/api/auth/me', {
      headers: { Authorization: `Bearer ${user.token}` },
    });
    expect(meResp.ok()).toBeTruthy();
    const meData = await meResp.json();
    expect(meData.username).toBe(user.username);
  });

  test('API helper 成功创建+删除条目', async ({ request }) => {
    // 先登录
    const user = await registerAndLogin(request);

    // 创建条目（带认证）
    const entry = await createEntry(
      request,
      { type: 'task', title: '基础设施测试任务' },
      user.token
    );
    expect(entry.id).toBeTruthy();

    // 列表可见
    const list = await listEntries(request, user.token);
    expect(list.entries.length).toBeGreaterThanOrEqual(1);

    // 删除
    await deleteEntry(request, entry.id, user.token);

    // 验证已删除
    const listAfter = await listEntries(request, user.token);
    const ids = listAfter.entries.map((e: { id: string }) => e.id);
    expect(ids).not.toContain(entry.id);
  });
});
