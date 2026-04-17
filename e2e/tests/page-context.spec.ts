/**
 * F39: 页面快捷建议 Chips + 页面状态同步 E2E 测试
 *
 * 覆盖验收条件：
 * - 各页面显示对应的快捷建议 chips
 * - 点击 chip 自动填入输入框
 * - 对话有消息时隐藏 chips
 * - Explore 页 tab/query 同步到 chatStore.pageExtra
 * - FloatingChat 合并 pageExtra 到 pageContext.extra 发送 API
 * - 路由切换后 pageExtra 被清空
 * - Chat API 接受 page_context 参数并透传
 */
import { test, expect } from '@playwright/test';
import { registerAndLogin } from './helpers/auth';
import { createEntry } from './helpers/api';

const BASE = '/growth';

test.describe.configure({ timeout: 120000, mode: 'serial' });

test.describe('页面上下文 AI (F39)', () => {
  /** 注册+登录+跳过 onboarding */
  async function setupUser(request: any, page: any) {
    const user = await registerAndLogin(request);

    // 跳过 onboarding
    await request.put('/api/auth/me', {
      headers: { Authorization: `Bearer ${user.token}` },
      data: { onboarding_completed: true },
    });

    // UI 登录
    await page.goto(`${BASE}/login`);
    await page.getByPlaceholder('请输入用户名').fill(user.username);
    await page.getByPlaceholder('请输入密码').fill(user.password);
    await page.getByRole('button', { name: '登录' }).click();
    await page.waitForURL(`**${BASE}/`, { timeout: 30000 });

    return user;
  }

  /** 通过侧边栏导航（React Router 客户端导航，避免 Vite base path 问题） */
  async function navigateViaSidebar(page: any, label: string) {
    await page.getByRole('link', { name: new RegExp(label) }).first().click();
    // 等待路由切换和页面渲染
    await page.waitForTimeout(500);
  }

  test('首页显示快捷建议 chips（今日有哪些任务 / 帮我记个想法 / 整理待办）', async ({ page, request }) => {
    await setupUser(request, page);

    // 首页应显示 chips
    await expect(page.getByText('今日有哪些任务?')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('帮我记个想法')).toBeVisible();
    await expect(page.getByText('整理待办')).toBeVisible();
  });

  test('点击 chip 自动填入输入框', async ({ page, request }) => {
    await setupUser(request, page);

    // 点击 chip
    await page.getByText('帮我记个想法').click();

    // 验证输入框被填充
    const input = page.getByPlaceholder(/输入内容|帮我搜索|改为/);
    await expect(input).toHaveValue('帮我记个想法');
  });

  test('发送消息后 chips 被隐藏', async ({ page, request }) => {
    await setupUser(request, page);

    // 确认 chips 可见
    await expect(page.getByText('帮我记个想法')).toBeVisible({ timeout: 10000 });

    const input = page.getByPlaceholder(/输入内容|帮我搜索|改为/);

    // 第一次发送：创建会话（首次 currentSessionId 闭包为 null，消息不会被添加，但会话已创建）
    await input.fill('第一条消息');
    await input.press('Enter');
    // 等待 SSE 错误（fake LLM 会快速失败：connection refused）
    await page.waitForTimeout(3000);

    // 第二次发送：React 已重渲染，currentSessionId 已设置，消息会被添加到 store
    await input.fill('第二条消息');
    await input.press('Enter');

    // chips 应该被隐藏（hasMessages=true）
    await expect(page.getByText('帮我记个想法')).not.toBeVisible({ timeout: 5000 });
  });

  test('探索页显示对应 chips（最近学了什么 / 搜索相关笔记）', async ({ page, request }) => {
    await setupUser(request, page);

    // 通过侧边栏导航到探索页
    await navigateViaSidebar(page, '探索');

    // 验证探索页 chips
    await expect(page.getByText('最近学了什么?')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('搜索相关笔记')).toBeVisible();
  });

  test('Chat API 接受 page_context 参数', async ({ request }) => {
    const user = await registerAndLogin(request);

    // 创建一个条目用于上下文测试
    const entry = await createEntry(request, {
      type: 'note',
      title: 'E2E上下文测试笔记',
      content: '测试页面上下文传递',
    }, user.token);

    try {
      // 发送带 page_context 的聊天请求（force_intent=read，不触发 LLM）
      const resp = await request.post('/api/chat', {
        headers: { Authorization: `Bearer ${user.token}` },
        data: {
          text: '上下文测试',
          session_id: 'e2e-page-ctx-test',
          force_intent: 'read',
          page_context: {
            page_type: 'entry',
            entry_id: entry.id,
            extra: { current_tab: 'note', search_query: '测试' },
          },
        },
      });

      expect(resp.ok()).toBeTruthy();
      expect(resp.headers()['content-type']).toContain('text/event-stream');

      const raw = await resp.text();
      expect(raw).toContain('intent');
      expect(raw).toContain('read');
    } finally {
      try {
        await request.delete(`/api/entries/${entry.id}`, {
          headers: { Authorization: `Bearer ${user.token}` },
        });
      } catch {}
    }
  });

  test('Explore 页面状态同步到 API 请求', async ({ page, request }) => {
    const user = await setupUser(request, page);

    // 创建 seed 数据
    await createEntry(request, {
      type: 'note',
      title: 'E2E探索同步测试笔记',
      content: '测试内容',
    }, user.token);

    // 拦截 chat API 请求
    let capturedContext: any = null;
    page.on('request', (req) => {
      if (req.url().includes('/api/chat') && req.method() === 'POST') {
        try {
          const body = req.postDataJSON();
          if (body?.page_context) {
            capturedContext = body.page_context;
          }
        } catch {}
      }
    });

    // 通过侧边栏导航到探索页
    await navigateViaSidebar(page, '探索');

    // 点击笔记 Tab（exact 避免"搜索相关笔记" chip 干扰）
    const noteTab = page.getByRole('button', { name: '笔记', exact: true });
    await noteTab.click();
    await page.waitForTimeout(500); // 等待 pageExtra 同步

    // 输入搜索查询（精确匹配探索页搜索框，排除 chat 输入框）
    const searchInput = page.getByPlaceholder(/试试搜索/);
    if (await searchInput.isVisible()) {
      await searchInput.fill('测试关键词');
      await page.waitForTimeout(400); // 等待 debounce + pageExtra 同步
    }

    // 在 chat 输入框输入并发送
    const chatInput = page.getByPlaceholder(/输入内容|帮我搜索|改为/);
    await chatInput.fill('搜索测试');
    await chatInput.press('Enter');

    // 等待请求发出
    await page.waitForTimeout(3000);

    // 验证 page_context 包含 explore 类型和 extra 信息
    expect(capturedContext).toBeTruthy();
    expect(capturedContext.page_type).toBe('explore');
    // extra 应包含 current_tab
    if (capturedContext.extra) {
      expect(capturedContext.extra.current_tab).toBeDefined();
    }
  });

  test('路由切换后 chips 更新', async ({ page, request }) => {
    await setupUser(request, page);

    // 首页 chips
    await expect(page.getByText('整理待办')).toBeVisible({ timeout: 10000 });

    // 通过侧边栏切换到探索页
    await navigateViaSidebar(page, '探索');

    // 首页 chips 应消失，探索页 chips 应出现
    await expect(page.getByText('整理待办')).not.toBeVisible({ timeout: 5000 });
    await expect(page.getByText('最近学了什么?')).toBeVisible({ timeout: 10000 });

    // 通过侧边栏切换到回顾页
    await navigateViaSidebar(page, '回顾');

    // 探索页 chips 消失，回顾页 chips 出现
    await expect(page.getByText('最近学了什么?')).not.toBeVisible({ timeout: 5000 });
    await expect(page.getByText('本周完成率?')).toBeVisible({ timeout: 10000 });
  });

  test('离开 Explore 后 pageExtra 被清空，后续 chat 请求不含旧 extra', async ({ page, request }) => {
    const user = await setupUser(request, page);

    // 创建 seed 数据
    await createEntry(request, {
      type: 'note',
      title: 'E2E pageExtra 清空测试笔记',
      content: '测试内容',
    }, user.token);

    // 拦截 chat API 请求
    const capturedContexts: any[] = [];
    page.on('request', (req) => {
      if (req.url().includes('/api/chat') && req.method() === 'POST') {
        try {
          const body = req.postDataJSON();
          capturedContexts.push(body?.page_context || null);
        } catch {}
      }
    });

    // Step 1: 导航到探索页，触发 pageExtra 设置
    await navigateViaSidebar(page, '探索');
    const noteTab = page.getByRole('button', { name: '笔记', exact: true });
    await noteTab.click();
    await page.waitForTimeout(500);

    // 在 Explore 页发送消息，捕获带 extra 的请求
    const chatInput = page.getByPlaceholder(/输入内容|帮我搜索|改为/);
    await chatInput.fill('探索页消息');
    await chatInput.press('Enter');
    await page.waitForTimeout(3000);

    // 验证 Explore 页请求包含 extra
    const exploreRequest = capturedContexts.find(ctx => ctx?.page_type === 'explore');
    expect(exploreRequest).toBeTruthy();
    expect(exploreRequest.extra).toBeDefined();

    // Step 2: 离开探索页，导航到首页
    await navigateViaSidebar(page, '今天');
    await page.waitForTimeout(500);

    // 在首页发送消息，捕获请求
    await chatInput.fill('首页消息');
    await chatInput.press('Enter');
    await page.waitForTimeout(3000);

    // 验证首页请求的 pageExtra 已被清空（不包含旧的 current_tab/search_query）
    const homeRequest = capturedContexts.find(ctx => ctx?.page_type === 'home');
    expect(homeRequest).toBeTruthy();
    // 首页请求的 extra 不应包含 Explore 页的 current_tab
    if (homeRequest.extra) {
      expect(homeRequest.extra.current_tab).toBeUndefined();
      expect(homeRequest.extra.search_query).toBeUndefined();
    }
  });
});
