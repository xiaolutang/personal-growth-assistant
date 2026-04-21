/**
 * F63: Goals 页面 E2E 测试
 *
 * 覆盖目标追踪前端页面交互：
 * - 空状态引导 / 创建目标弹窗 / 列表展示
 * - 状态筛选 / 详情页 / 进度显示
 * - 关联/取消关联条目 / 归档 / 重新激活
 * - 首页目标卡片
 *
 * 每个测试独立注册用户。
 * 导航通过 sidebar 链接（客户端路由），避免 page.goto 全量刷新。
 */
import { test, expect } from '@playwright/test';
import { createEntry } from './helpers/api';
import { createGoal, updateGoal, linkEntry } from './helpers/goals';

test.describe.configure({ timeout: 120000 });

const BASE = '/growth';

/** 注册用户 + API onboarding + UI 登录，返回 token */
async function setupUser(request: any, page: any, prefix: string) {
  const username = `${prefix}_${Date.now().toString(36)}`;
  const password = 'testpass123';

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

  await page.goto(`${BASE}/login`);
  await page.getByPlaceholder('请输入用户名').fill(username);
  await page.getByPlaceholder('请输入密码').fill(password);
  await page.getByRole('button', { name: '登录' }).click();
  await page.waitForURL(`**${BASE}/`, { timeout: 30000 });

  return token;
}

/** 导航到目标列表页并等待加载 */
async function goToGoals(page: any) {
  await page.getByRole('link', { name: /目标/ }).click();
  await expect(page.getByRole('heading', { name: /目标追踪/ })).toBeVisible({ timeout: 15000 });
}


test.describe('Goals 页面 E2E', () => {

  // ========================
  // AC 1 + AC 2: 空状态 → 创建 count 目标
  // ========================

  test('空状态引导 → 创建 count 目标 → 列表出现卡片', async ({ request, page }) => {
    await setupUser(request, page, 'goal_empty');

    // AC 1: 空目标列表 → 引导文案
    await goToGoals(page);
    await expect(page.getByText('设定一个目标开始追踪吧')).toBeVisible();
    await expect(page.getByText('创建第一个目标')).toBeVisible();

    // AC 2: 创建 count 目标
    await page.getByRole('button', { name: /新建/ }).click();
    await expect(page.getByText('创建目标')).toBeVisible();

    // 填写标题（默认 count 类型，目标值 5）
    await page.getByPlaceholder('如：完成 React 学习').fill('UI测试-count目标');

    // 提交
    await page.getByRole('button', { name: '创建', exact: true }).click();

    // 验证卡片出现 + 手动计数 badge
    await expect(page.getByText('UI测试-count目标')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('手动计数').first()).toBeVisible();
  });

  // ========================
  // AC 3: 创建 checklist 目标
  // ========================

  test('创建 checklist 目标 → 填写检查项 → 卡片显示', async ({ request, page }) => {
    await setupUser(request, page, 'goal_check');

    await goToGoals(page);

    // 打开创建弹窗
    await page.getByRole('button', { name: /新建/ }).click();
    await expect(page.getByText('创建目标')).toBeVisible();

    // 填写标题
    await page.getByPlaceholder('如：完成 React 学习').fill('UI测试-checklist目标');

    // 切换到检查清单类型（弹窗内 badge）
    const dialog = page.locator('.bg-card.rounded-xl.shadow-xl');
    await dialog.getByText('检查清单').click();

    // 填写第一个检查项
    await page.getByPlaceholder('检查项 1').fill('步骤一');

    // 添加第二个检查项
    await page.getByRole('button', { name: '+ 添加检查项' }).click();
    await page.getByPlaceholder('检查项 2').fill('步骤二');

    // 提交创建
    await page.getByRole('button', { name: '创建', exact: true }).click();

    // 验证卡片出现 + 检查清单 badge
    await expect(page.getByText('UI测试-checklist目标')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('检查清单').first()).toBeVisible();
  });

  // ========================
  // AC 4: tag_auto 目标（Neo4j 不可用，走 API + UI 验证）
  // ========================

  test('tag_auto 目标 → API 创建 → UI 显示 tag Badge', async ({ request, page }) => {
    const token = await setupUser(request, page, 'goal_tag');

    const resp = await createGoal(request, {
      title: 'API测试-tag目标',
      metric_type: 'tag_auto',
      target_value: 10,
      auto_tags: ['测试标签'],
    }, token);
    expect(resp.ok()).toBeTruthy();

    await goToGoals(page);

    // 验证卡片 + Tag 追踪 badge
    await expect(page.getByText('API测试-tag目标')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('Tag 追踪').first()).toBeVisible();
  });

  // ========================
  // AC 5: 状态筛选
  // ========================

  test('状态筛选 → 进行中/已完成/已归档', async ({ request, page }) => {
    const token = await setupUser(request, page, 'goal_filter');

    // 创建活跃目标
    await createGoal(request, {
      title: '筛选-活跃目标',
      metric_type: 'count',
      target_value: 5,
    }, token);

    // 创建已完成目标
    const cResp = await createGoal(request, {
      title: '筛选-已完成目标',
      metric_type: 'count',
      target_value: 1,
    }, token);
    const cGoal = await cResp.json();
    const entry = await createEntry(request, { type: 'task', title: '完成用条目' }, token);
    await linkEntry(request, cGoal.id, entry.id, token);
    await updateGoal(request, cGoal.id, { status: 'completed' }, token);

    // 创建已归档目标
    const aResp = await createGoal(request, {
      title: '筛选-已归档目标',
      metric_type: 'count',
      target_value: 1,
    }, token);
    const aGoal = await aResp.json();
    await updateGoal(request, aGoal.id, { status: 'abandoned' }, token);

    await goToGoals(page);

    // 默认"进行中"筛选
    await expect(page.getByText('筛选-活跃目标')).toBeVisible({ timeout: 10000 });

    // 切换"已完成"
    await page.getByText('已完成', { exact: true }).click();
    await expect(page.getByText('筛选-已完成目标')).toBeVisible({ timeout: 10000 });

    // 切换"已归档"
    await page.getByText('已归档', { exact: true }).click();
    await expect(page.getByText('筛选-已归档目标')).toBeVisible({ timeout: 10000 });

    // 切回"进行中"
    await page.getByText('进行中', { exact: true }).click();
    await expect(page.getByText('筛选-活跃目标')).toBeVisible({ timeout: 10000 });
  });

  // ========================
  // AC 6 + AC 7: 点击卡片 → 详情页 + 进度
  // ========================

  test('点击卡片 → 详情页 → 环形进度图 + 进度条', async ({ request, page }) => {
    const token = await setupUser(request, page, 'goal_detail');

    await createGoal(request, {
      title: '详情测试-count目标',
      metric_type: 'count',
      target_value: 5,
    }, token);

    await goToGoals(page);
    await expect(page.getByText('详情测试-count目标')).toBeVisible({ timeout: 10000 });

    // AC 6: 点击卡片 → 跳转详情页
    await page.getByText('详情测试-count目标').click();
    await expect(page).toHaveURL(/\/goals\/.+/, { timeout: 10000 });
    await expect(page.getByText('返回目标列表')).toBeVisible();
    await expect(page.getByRole('heading', { name: /目标详情/ })).toBeVisible();

    // AC 7: 验证环形进度图 SVG
    await expect(page.locator('svg').filter({ has: page.locator('circle') }).first()).toBeVisible();

    // 验证进度百分比
    await expect(page.getByText(/\d+%/).first()).toBeVisible();

    // 验证"当前值 / 目标值"
    await expect(page.getByText(/0 \/ 5/)).toBeVisible();

    // 验证"手动计数" badge
    await expect(page.getByText('手动计数').first()).toBeVisible();

    // 验证"归档"按钮（active 状态）
    await expect(page.getByRole('button', { name: '归档' })).toBeVisible();
  });

  // ========================
  // AC 8: 关联条目（搜索弹窗 → 输入关键词 → 搜索 → 点击关联 → 列表更新）
  // ========================

  test('详情页关联条目 → 搜索弹窗 → 搜索 → 关联 → 列表更新', async ({ request, page }) => {
    const token = await setupUser(request, page, 'goal_link');

    // 预创建可搜索条目（在 UI 登录前，确保数据已落库）
    await createEntry(request, { type: 'task', title: '关联搜索条目-E2E' }, token);

    const gResp = await createGoal(request, {
      title: '关联测试-count目标',
      metric_type: 'count',
      target_value: 5,
    }, token);
    const goal = await gResp.json();

    await goToGoals(page);
    await page.getByText('关联测试-count目标').click();
    await expect(page.getByRole('heading', { name: /目标详情/ })).toBeVisible({ timeout: 15000 });

    // 点击关联条目按钮 → 打开搜索弹窗
    await page.getByRole('button', { name: /关联条目/ }).click();
    await expect(page.getByPlaceholder('输入关键词搜索...')).toBeVisible({ timeout: 5000 });

    // 在搜索框输入预创建条目的唯一关键词
    await page.getByPlaceholder('输入关键词搜索...').fill('关联搜索条目');

    // 等待搜索结果出现（300ms debounce + 网络请求）
    await expect(page.getByText('关联搜索条目-E2E')).toBeVisible({ timeout: 10000 });

    // 点击搜索结果关联条目
    await page.getByText('关联搜索条目-E2E').click();

    // 验证关联成功 toast
    await expect(page.getByText('已关联')).toBeVisible({ timeout: 5000 });

    // 验证关联条目出现在列表中（刷新后）
    await expect(page.locator('div.rounded-lg.border', { hasText: '关联搜索条目-E2E' })).toBeVisible({ timeout: 10000 });
  });

  // ========================
  // AC 9: 取消关联
  // ========================

  test('详情页取消关联 → 条目消失', async ({ request, page }) => {
    const token = await setupUser(request, page, 'goal_unlink');

    const gResp = await createGoal(request, {
      title: '取消关联测试目标',
      metric_type: 'count',
      target_value: 5,
    }, token);
    const goal = await gResp.json();

    // 通过 API 创建并关联两个条目
    const entry1 = await createEntry(request, { type: 'note', title: '要取消关联-E2E' }, token);
    const entry2 = await createEntry(request, { type: 'task', title: '保留关联-E2E' }, token);
    await linkEntry(request, goal.id, entry1.id, token);
    await linkEntry(request, goal.id, entry2.id, token);

    // 通过客户端路由导航到详情页
    await goToGoals(page);
    await page.getByText('取消关联测试目标').click();
    await expect(page.getByRole('heading', { name: /目标详情/ })).toBeVisible({ timeout: 15000 });
    await expect(page.getByText('要取消关联-E2E')).toBeVisible({ timeout: 10000 });

    // 精确定位要取消的条目行中的 X 按钮
    const entryRow = page.locator('div.rounded-lg.border', { hasText: '要取消关联-E2E' });
    await entryRow.locator('button[title="取消关联"]').click();

    // 验证条目消失
    await expect(page.getByText('要取消关联-E2E')).not.toBeVisible({ timeout: 5000 });

    // 保留的条目仍在
    await expect(page.getByText('保留关联-E2E')).toBeVisible();
  });

  // ========================
  // AC 10: 归档目标
  // ========================

  test('归档目标 → 状态变 abandoned → 列表更新', async ({ request, page }) => {
    const token = await setupUser(request, page, 'goal_archive');

    await createGoal(request, {
      title: '归档测试目标',
      metric_type: 'count',
      target_value: 3,
    }, token);

    await goToGoals(page);
    await expect(page.getByText('归档测试目标')).toBeVisible({ timeout: 10000 });

    // 进入详情页
    await page.getByText('归档测试目标').click();
    await expect(page.getByRole('heading', { name: /目标详情/ })).toBeVisible({ timeout: 15000 });

    // 点击归档
    await page.getByRole('button', { name: '归档' }).click();

    // 验证返回目标列表
    await expect(page).toHaveURL(/\/goals$/, { timeout: 10000 });
    await expect(page.getByRole('heading', { name: /目标追踪/ })).toBeVisible({ timeout: 10000 });

    // 切换到"已归档"筛选
    await page.getByText('已归档', { exact: true }).click();

    // 验证目标出现在已归档列表
    await expect(page.getByText('归档测试目标')).toBeVisible({ timeout: 10000 });
  });

  // ========================
  // AC 11: 重新激活 completed → active
  // ========================

  test('重新激活 completed → active → 列表更新', async ({ request, page }) => {
    const token = await setupUser(request, page, 'goal_react');

    // 创建已完成目标
    const gResp = await createGoal(request, {
      title: '重新激活测试目标',
      metric_type: 'count',
      target_value: 1,
    }, token);
    const goal = await gResp.json();
    const entry = await createEntry(request, { type: 'task', title: '完成用' }, token);
    await linkEntry(request, goal.id, entry.id, token);
    await updateGoal(request, goal.id, { status: 'completed' }, token);

    // 通过客户端路由导航到已完成目标详情
    await goToGoals(page);
    await page.getByText('已完成', { exact: true }).click();
    await expect(page.getByText('重新激活测试目标')).toBeVisible({ timeout: 10000 });
    await page.getByText('重新激活测试目标').click();
    await expect(page.getByRole('heading', { name: /目标详情/ })).toBeVisible({ timeout: 15000 });

    // 验证当前状态为已完成
    await expect(page.getByText('已完成').first()).toBeVisible();

    // 点击重新激活按钮
    await page.getByRole('button', { name: /重新激活/ }).click();

    // 验证 toast + 按钮变化
    await expect(page.getByText('已重新激活')).toBeVisible({ timeout: 5000 });
    await expect(page.getByRole('button', { name: '归档' })).toBeVisible({ timeout: 5000 });

    // 返回列表验证
    await page.getByText('返回目标列表').click();
    await expect(page.getByRole('heading', { name: /目标追踪/ })).toBeVisible({ timeout: 10000 });

    // 切换到"进行中"
    await page.getByText('进行中', { exact: true }).click();

    // 验证出现在进行中列表
    await expect(page.getByText('重新激活测试目标')).toBeVisible({ timeout: 10000 });
  });

  // ========================
  // AC 12: 首页目标进度卡片
  // ========================

  test('首页目标进度卡片显示活跃目标', async ({ request, page }) => {
    // 先注册用户（不登录 UI），创建目标，再 UI 登录让首页首次加载就看到目标
    const username = `goal_home_${Date.now().toString(36)}`;
    const password = 'testpass123';

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

    // 创建一条 task 让首页 isEmpty=false（首页空状态会隐藏"我的目标"卡片）
    await createEntry(request, { type: 'task', title: '首页目标任务' }, token);

    // 在 UI 登录前创建目标
    await createGoal(request, {
      title: '首页展示目标',
      metric_type: 'count',
      target_value: 5,
    }, token);

    // UI 登录 → 自动跳转首页 → 首页 mount 时 fetch goals
    await page.goto(`${BASE}/login`);
    await page.getByPlaceholder('请输入用户名').fill(username);
    await page.getByPlaceholder('请输入密码').fill(password);
    await page.getByRole('button', { name: '登录' }).click();
    await page.waitForURL(`**${BASE}/`, { timeout: 30000 });

    // 首页加载后应显示目标卡片
    await expect(page.getByText('我的目标')).toBeVisible({ timeout: 15000 });
    await expect(page.getByText('首页展示目标')).toBeVisible({ timeout: 10000 });
  });
});
