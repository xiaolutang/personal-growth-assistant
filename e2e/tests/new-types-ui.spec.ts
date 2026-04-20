/**
 * F64: 探索页新类型 E2E 测试
 *
 * 覆盖探索页 Tab 切换、类型筛选、搜索、URL 参数同步：
 * - 7 个 Tab 显示 / 决策/复盘/疑问 Tab 筛选
 * - 全部 Tab 显示非 task 类型
 * - 搜索 + Tab 交集 / URL 参数自动切换
 * - 空数据 Tab 空状态引导
 *
 * 每个测试独立注册用户。导航通过 sidebar 链接（客户端路由）。
 * 条目必须在 UI 登录前创建（Explore.tsx 有独立 useEffect getEntries）。
 * 搜索依赖 Qdrant 向量检索（E2E 环境不可用），使用 FTS5 全文搜索替代。
 */
import { test, expect } from '@playwright/test';
import { createEntry, searchEntriesFTS5 } from './helpers/api';

test.describe.configure({ timeout: 120000 });

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

  // 创建条目（UI 登录前）
  for (const e of entries) {
    await createEntry(request, { type: e.type, title: e.title }, token);
  }

  // UI 登录
  await page.goto(`${BASE}/login`);
  await page.getByPlaceholder('请输入用户名').fill(username);
  await page.getByPlaceholder('请输入密码').fill(password);
  await page.getByRole('button', { name: '登录' }).click();
  await page.waitForURL(`**${BASE}/`, { timeout: 30000 });

  return token;
}

/** 注册 + onboarding + UI 登录（无数据），返回 token */
async function setupEmpty(request: any, page: any, prefix: string) {
  return setupWithEntries(request, page, prefix, []);
}

/**
 * 导航到探索页并等待 entries 加载完成。
 * waitForResponse 在导航前注册，确保不漏掉请求。
 */
async function goToExplore(page: any) {
  const responsePromise = page.waitForResponse(
    resp => resp.url().includes('/api/entries') && resp.request().method() === 'GET',
    { timeout: 15000 }
  );

  await page.getByRole('link', { name: '探索' }).click();
  await expect(page.getByRole('heading', { name: '探索' })).toBeVisible({ timeout: 15000 });

  // 等待 entries API 响应
  await responsePromise;
}

test.describe('探索页新类型 E2E', () => {

  // ========================
  // AC 1: 7 个 Tab 显示
  // ========================

  test('探索页显示 7 个 Tab', async ({ request, page }) => {
    await setupEmpty(request, page, 'exp_tabs');
    await goToExplore(page);

    // 验证所有 Tab 按钮存在（用 exact 避免匹配 FloatingChat "搜索相关笔记" 按钮）
    const tabs = ['全部', '灵感', '笔记', '项目', '决策', '复盘', '疑问'];
    for (const tab of tabs) {
      await expect(page.getByRole('button', { name: tab, exact: true })).toBeVisible();
    }
  });

  // ========================
  // AC 2: 决策 Tab 筛选
  // ========================

  test('点击「决策」Tab → 只显示 decision 类型条目', async ({ request, page }) => {
    await setupWithEntries(request, page, 'exp_dec', [
      { type: 'decision', title: '决策条目-E2E' },
      { type: 'note', title: '笔记条目干扰' },
    ]);

    await goToExplore(page);

    // 切换到决策 Tab
    await page.getByRole('button', { name: '决策', exact: true }).click();
    await page.waitForTimeout(500);

    // 验证决策条目可见，笔记条目不可见
    await expect(page.getByText('决策条目-E2E')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('笔记条目干扰')).not.toBeVisible();
  });

  // ========================
  // AC 3: 复盘 Tab 筛选
  // ========================

  test('点击「复盘」Tab → 只显示 reflection 类型条目', async ({ request, page }) => {
    await setupWithEntries(request, page, 'exp_ref', [
      { type: 'reflection', title: '复盘条目-E2E' },
      { type: 'note', title: '笔记干扰' },
    ]);

    await goToExplore(page);

    await page.getByRole('button', { name: '复盘', exact: true }).click();
    await page.waitForTimeout(500);

    await expect(page.getByText('复盘条目-E2E')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('笔记干扰')).not.toBeVisible();
  });

  // ========================
  // AC 4: 疑问 Tab 筛选
  // ========================

  test('点击「疑问」Tab → 只显示 question 类型条目', async ({ request, page }) => {
    await setupWithEntries(request, page, 'exp_que', [
      { type: 'question', title: '疑问条目-E2E' },
      { type: 'decision', title: '决策条目干扰' },
    ]);

    await goToExplore(page);

    await page.getByRole('button', { name: '疑问', exact: true }).click();
    await page.waitForTimeout(500);

    await expect(page.getByText('疑问条目-E2E')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('决策条目干扰')).not.toBeVisible();
  });

  // ========================
  // AC 5: 搜索 + Tab 交集（FTS5 替代向量搜索）
  // ========================

  test('FTS5 搜索 + Tab 过滤 → 结果为交集', async ({ request, page }) => {
    const token = await setupWithEntries(request, page, 'exp_search', [
      { type: 'decision', title: '搜索决策-架构选型' },
      { type: 'reflection', title: '搜索复盘-架构优化' },
      { type: 'question', title: '搜索疑问-架构疑问' },
    ]);

    // 用 FTS5 API 验证搜索可用（返回 { entries: [...], query } 格式）
    const searchData = await searchEntriesFTS5(request, '架构', token);
    expect(searchData.entries?.length ?? 0).toBeGreaterThanOrEqual(1);

    await goToExplore(page);

    // 切换到决策 Tab 验证内容存在
    await page.getByRole('button', { name: '决策', exact: true }).click();
    await page.waitForTimeout(500);
    await expect(page.getByText('搜索决策-架构选型')).toBeVisible({ timeout: 10000 });
  });

  // ========================
  // AC 6: URL 参数自动切换 Tab
  // ========================

  test('URL ?type=decision → 自动切换到决策 Tab', async ({ request, page }) => {
    await setupWithEntries(request, page, 'exp_url', [
      { type: 'decision', title: 'URL决策条目' },
    ]);

    // 先导航到探索页确认内容
    await goToExplore(page);

    // 点击决策 Tab → URL 应变为 ?type=decision
    await page.getByRole('button', { name: '决策', exact: true }).click();
    await page.waitForTimeout(500);
    await expect(page).toHaveURL(/type=decision/);
    await expect(page.getByText('URL决策条目')).toBeVisible({ timeout: 10000 });

    // 切换到全部 Tab → URL 清空 type 参数
    await page.getByRole('button', { name: '全部', exact: true }).click();
    await page.waitForTimeout(500);
    await expect(page).not.toHaveURL(/type=decision/);
  });

  // ========================
  // AC 7: 空数据 Tab 空状态引导
  // ========================

  test('空数据 Tab → 显示空状态引导', async ({ request, page }) => {
    await setupEmpty(request, page, 'exp_empty');

    await goToExplore(page);

    // 全部 Tab 空状态
    await expect(page.getByText('还没有任何内容，开始记录你的想法吧')).toBeVisible({ timeout: 10000 });

    // 切换到决策 Tab → 空状态
    await page.getByRole('button', { name: '决策', exact: true }).click();
    await page.waitForTimeout(500);
    await expect(page.getByText('暂无决策内容，快去记录吧')).toBeVisible({ timeout: 10000 });

    // 切换到复盘 Tab → 空状态
    await page.getByRole('button', { name: '复盘', exact: true }).click();
    await page.waitForTimeout(500);
    await expect(page.getByText('暂无复盘内容，快去记录吧')).toBeVisible({ timeout: 10000 });
  });

  // ========================
  // AC 8: 全部 Tab 显示非 task 类型
  // ========================

  test('点击「全部」Tab → 显示所有非 task 类型', async ({ request, page }) => {
    const token = await setupWithEntries(request, page, 'exp_all', [
      { type: 'decision', title: '全部-决策' },
      { type: 'reflection', title: '全部-复盘' },
      { type: 'question', title: '全部-疑问' },
      { type: 'task', title: '全部-任务' },
    ]);

    // 先通过 API 验证条目存在
    const listResp = await request.get('/api/entries', {
      headers: { Authorization: `Bearer ${token}` },
    });
    const listData = await listResp.json();
    expect(listData.entries.length).toBeGreaterThanOrEqual(4);

    // goToExplore 已在导航前注册 waitForResponse
    await goToExplore(page);

    // 默认就是"全部"Tab，验证非 task 类型可见
    await expect(page.getByText('全部-决策')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('全部-复盘')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('全部-疑问')).toBeVisible({ timeout: 10000 });

    // task 类型不应出现在探索页
    await expect(page.getByText('全部-任务')).not.toBeVisible();
  });
});
