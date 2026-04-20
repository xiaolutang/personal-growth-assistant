/**
 * F65: 导出 UI E2E 测试
 *
 * 覆盖导出对话框的完整交互流程：
 * - Sidebar 导出按钮 → 打开对话框
 * - 选择 markdown/json 格式 → 触发下载
 * - 类型过滤 + 导出 → 下载内容正确
 * - 关闭对话框 → 不触发下载
 *
 * 每个测试独立注册用户并创建条目。
 * 下载检测使用 page.waitForEvent('download')。
 */
import { test, expect } from '@playwright/test';
import { createEntry } from './helpers/api';
import fs from 'fs';

const BASE = '/growth';

/** 注册 + onboarding + 创建条目 + UI 登录，返回 token */
async function setupWithEntries(request: any, page: any, prefix: string, entries: { type: string; title: string }[]) {
  const username = `${prefix}_${Date.now().toString(36)}`;
  const password = 'testpass123';

  await request.post('/api/auth/register', {
    data: { username, email: `${username}@e2e.test`, password },
  });
  const loginResp = await request.post('/api/auth/login', {
    data: { username, password },
  });
  const { access_token: token } = await loginResp.json();

  await request.put('/api/auth/me', {
    headers: { Authorization: `Bearer ${token}` },
    data: { onboarding_completed: true },
  });

  for (const e of entries) {
    await createEntry(request, { type: e.type, title: e.title }, token);
  }

  await page.goto(`${BASE}/login`);
  await page.getByPlaceholder('请输入用户名').fill(username);
  await page.getByPlaceholder('请输入密码').fill(password);
  await page.getByRole('button', { name: '登录' }).click();
  await page.waitForURL(`**${BASE}/`, { timeout: 30000 });

  return token;
}

/** 点击 Sidebar 导出按钮，打开导出对话框 */
async function openExportDialog(page: any) {
  await page.getByRole('button', { name: '导出数据', exact: true }).click();
  await expect(page.getByRole('heading', { name: '导出数据' })).toBeVisible({ timeout: 10000 });
}

/** 对话框内的导出按钮（exact true 避免 Sidebar "导出数据" 按钮冲突） */
function exportButton(page: any) {
  return page.getByRole('button', { name: '导出', exact: true });
}

test.describe('导出 UI E2E', () => {
  test.describe.configure({ timeout: 120000 });

  // ========================
  // AC 1: Sidebar 导出按钮 → 打开对话框
  // ========================

  test('Sidebar 导出按钮 → 点击打开导出对话框', async ({ request, page }) => {
    await setupWithEntries(request, page, 'exp_ui_open', [
      { type: 'note', title: '导出测试笔记' },
    ]);

    await openExportDialog(page);

    // 验证对话框内容
    await expect(page.getByText('导出格式')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Markdown (ZIP)' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'JSON', exact: true })).toBeVisible();
    await expect(page.getByRole('combobox')).toBeVisible();
    await expect(exportButton(page)).toBeVisible();
    await expect(page.getByRole('button', { name: '取消' })).toBeVisible();
  });

  // ========================
  // AC 2: 选择 markdown → 触发下载
  // ========================

  test('选择 markdown → 点击导出 → 触发 ZIP 下载', async ({ request, page }) => {
    await setupWithEntries(request, page, 'exp_ui_md', [
      { type: 'note', title: 'MD导出笔记' },
    ]);

    await openExportDialog(page);

    const [download] = await Promise.all([
      page.waitForEvent('download', { timeout: 15000 }),
      exportButton(page).click(),
    ]);

    expect(download.suggestedFilename()).toContain('entries_export.zip');
    const path = await download.path();
    expect(path).toBeTruthy();
  });

  // ========================
  // AC 3: 选择 json → 触发下载
  // ========================

  test('选择 json → 点击导出 → 触发 JSON 下载', async ({ request, page }) => {
    await setupWithEntries(request, page, 'exp_ui_json', [
      { type: 'note', title: 'JSON导出笔记' },
    ]);

    await openExportDialog(page);

    // 切换到 JSON 格式
    await page.getByRole('button', { name: 'JSON', exact: true }).click();

    const [download] = await Promise.all([
      page.waitForEvent('download', { timeout: 15000 }),
      exportButton(page).click(),
    ]);

    expect(download.suggestedFilename()).toContain('entries_export.json');

    // 验证 JSON 内容
    const path = await download.path();
    const content = fs.readFileSync(path!, 'utf-8');
    const data = JSON.parse(content);
    expect(Array.isArray(data)).toBeTruthy();
    expect(data.length).toBeGreaterThanOrEqual(1);
    expect(data.some((e: any) => e.title === 'JSON导出笔记')).toBeTruthy();
  });

  // ========================
  // AC 4: 类型过滤 + 导出 → 只含该类型
  // ========================

  test('选择类型过滤 + 导出 → 下载只含该类型', async ({ request, page }) => {
    await setupWithEntries(request, page, 'exp_ui_filter', [
      { type: 'note', title: '过滤-笔记' },
      { type: 'task', title: '过滤-任务' },
    ]);

    await openExportDialog(page);

    // 切换到 JSON 格式
    await page.getByRole('button', { name: 'JSON', exact: true }).click();

    // 选择类型：笔记（用 combobox role）
    await page.getByRole('combobox').selectOption({ label: '笔记' });

    const [download] = await Promise.all([
      page.waitForEvent('download', { timeout: 15000 }),
      exportButton(page).click(),
    ]);

    // 验证 JSON 只包含 note 类型
    const path = await download.path();
    const content = fs.readFileSync(path!, 'utf-8');
    const data = JSON.parse(content);
    expect(Array.isArray(data)).toBeTruthy();
    expect(data.some((e: any) => e.title === '过滤-笔记')).toBeTruthy();
    expect(data.some((e: any) => e.title === '过滤-任务')).toBeFalsy();
  });

  // ========================
  // AC 5: 关闭对话框 → 不触发下载
  // ========================

  test('关闭对话框 → 不触发下载', async ({ request, page }) => {
    await setupWithEntries(request, page, 'exp_ui_close', [
      { type: 'note', title: '关闭测试笔记' },
    ]);

    await openExportDialog(page);

    // 点击取消
    await page.getByRole('button', { name: '取消' }).click();
    await expect(page.getByRole('heading', { name: '导出数据' })).not.toBeVisible({ timeout: 5000 });

    // 确认没有下载
    let downloadTriggered = false;
    page.on('download', () => { downloadTriggered = true; });
    await page.waitForTimeout(2000);
    expect(downloadTriggered).toBeFalsy();
  });
});
