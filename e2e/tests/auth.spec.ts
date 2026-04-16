/**
 * B36: 认证流程 E2E 测试
 *
 * 覆盖完整认证用户路径：注册 → 登录 → 访问受保护页面 → 登出 → 重定向到登录页。
 * 包括未认证访问拦截、重复注册、错误密码等边界场景。
 *
 * 注意：前端 base path 为 /growth/
 */
import { test, expect } from '@playwright/test';

const BASE = '/growth';

test.describe('认证流程', () => {
  test('注册 → 跳转到首页', async ({ page }) => {
    const username = `e2e_reg_${Date.now().toString(36)}`;
    await page.goto(`${BASE}/register`);

    await page.getByPlaceholder('请输入用户名').fill(username);
    await page.getByPlaceholder('请输入邮箱').fill(`${username}@e2e.test`);
    await page.getByPlaceholder('至少 6 个字符').fill('testpass123');
    await page.getByPlaceholder('再次输入密码').fill('testpass123');
    await page.getByRole('button', { name: '注册' }).click();

    // 注册成功后跳转到首页
    await page.waitForURL(`**${BASE}/`, { timeout: 10000 });
  });

  test('登录 → 跳转到首页', async ({ page, request }) => {
    // 先通过 API 注册用户
    const username = `e2e_login_${Date.now().toString(36)}`;
    await request.post('/api/auth/register', {
      data: { username, email: `${username}@e2e.test`, password: 'testpass123' },
    });

    // 通过 UI 登录
    await page.goto(`${BASE}/login`);
    await page.getByPlaceholder('请输入用户名').fill(username);
    await page.getByPlaceholder('请输入密码').fill('testpass123');
    await page.getByRole('button', { name: '登录' }).click();

    // 登录成功后跳转到首页
    await page.waitForURL(`**${BASE}/`, { timeout: 10000 });
  });

  test('登录 → 访问首页 → 登出 → 重定向到登录页', async ({ page, request }) => {
    // 先通过 API 注册用户并完成 onboarding
    const username = `e2e_logout_${Date.now().toString(36)}`;
    const regResp = await request.post('/api/auth/register', {
      data: { username, email: `${username}@e2e.test`, password: 'testpass123' },
    });
    const regData = await regResp.json();

    // 通过 API 标记 onboarding 完成
    const loginResp = await request.post('/api/auth/login', {
      data: { username, password: 'testpass123' },
    });
    const loginData = await loginResp.json();
    await request.put('/api/auth/me', {
      headers: { Authorization: `Bearer ${loginData.access_token}` },
      data: { onboarding_completed: true },
    });

    // 通过 UI 登录
    await page.goto(`${BASE}/login`);
    await page.getByPlaceholder('请输入用户名').fill(username);
    await page.getByPlaceholder('请输入密码').fill('testpass123');
    await page.getByRole('button', { name: '登录' }).click();
    await page.waitForURL(`**${BASE}/`, { timeout: 30000 });

    // 确认首页可访问（无 onboarding 遮罩）
    await expect(page.locator('main').first()).toBeVisible({ timeout: 10000 });

    // 点击登出按钮
    await page.getByTitle('登出').click();

    // 登出后重定向到登录页
    await page.waitForURL('**/login', { timeout: 10000 });
  });

  test('未认证访问受保护页面 → 重定向到登录页', async ({ page }) => {
    // 清除可能的残留 token
    await page.goto(`${BASE}/login`);

    // 直接访问受保护路径
    await page.goto(`${BASE}/tasks`);

    // 应被重定向到登录页
    await page.waitForURL('**/login', { timeout: 10000 });
    expect(page.url()).toContain('/login');
  });

  test('重复用户名注册失败', async ({ page, request }) => {
    // 先通过 API 注册用户
    const username = `e2e_dup_${Date.now().toString(36)}`;
    await request.post('/api/auth/register', {
      data: { username, email: `${username}@e2e.test`, password: 'testpass123' },
    });

    // 再通过 UI 尝试注册相同用户名
    await page.goto(`${BASE}/register`);
    await page.getByPlaceholder('请输入用户名').fill(username);
    await page.getByPlaceholder('请输入邮箱').fill(`${username}2@e2e.test`);
    await page.getByPlaceholder('至少 6 个字符').fill('testpass123');
    await page.getByPlaceholder('再次输入密码').fill('testpass123');
    await page.getByRole('button', { name: '注册' }).click();

    // 应该显示错误提示（红色文字）
    const errorEl = page.locator('.text-red-600, .text-red-400').first();
    await expect(errorEl).toBeVisible({ timeout: 5000 });
  });

  test('错误密码登录失败', async ({ page, request }) => {
    // 先通过 API 注册用户
    const username = `e2e_wrongpw_${Date.now().toString(36)}`;
    await request.post('/api/auth/register', {
      data: { username, email: `${username}@e2e.test`, password: 'testpass123' },
    });

    // 用错误密码登录
    await page.goto(`${BASE}/login`);
    await page.getByPlaceholder('请输入用户名').fill(username);
    await page.getByPlaceholder('请输入密码').fill('wrongpassword');
    await page.getByRole('button', { name: '登录' }).click();

    // 应该显示错误提示
    const errorEl = page.locator('.text-red-600, .text-red-400').first();
    await expect(errorEl).toBeVisible({ timeout: 5000 });
    // 仍然在登录页
    expect(page.url()).toContain('/login');
  });
});
