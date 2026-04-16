/**
 * B38: Chat 对话 E2E 测试（read/delete 路径）
 *
 * 覆盖 Chat SSE 的 read 和 delete 路径（不触发 LLM）：
 * - force_intent=read: 搜索已有条目 → 验证 results 事件
 * - force_intent=delete: 删除已有条目 → 验证 confirm/deleted 事件
 * - 会话列表展示
 * - 空输入/错误处理
 */
import { test, expect } from '@playwright/test';
import { registerAndLogin } from './helpers/auth';
import { createEntry, deleteEntry } from './helpers/api';

const BASE = '/growth';

test.describe.configure({ timeout: 120000 });

test.describe('Chat 对话', () => {
  /** 注册 + UI 登录 */
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

    await page.goto(`${BASE}/login`);
    await page.getByPlaceholder('请输入用户名').fill(username);
    await page.getByPlaceholder('请输入密码').fill(password);
    await page.getByRole('button', { name: '登录' }).click();
    await page.waitForURL(`**${BASE}/`, { timeout: 30000 });

    return token;
  }

  /** 解析 SSE 事件流为事件数组 */
  function parseSSEEvents(raw: string): Array<{ event: string; data: any }> {
    const events: Array<{ event: string; data: any }> = [];
    let currentEvent = '';
    let currentData = '';

    for (const line of raw.split('\n')) {
      if (line.startsWith('event: ')) {
        currentEvent = line.slice(7).trim();
      } else if (line.startsWith('data: ')) {
        currentData = line.slice(6).trim();
      } else if (line === '' && currentEvent) {
        try {
          events.push({ event: currentEvent, data: JSON.parse(currentData) });
        } catch {
          events.push({ event: currentEvent, data: currentData });
        }
        currentEvent = '';
        currentData = '';
      }
    }
    return events;
  }

  test('Chat read 搜索已有条目返回 results 事件', async ({ request }) => {
    const user = await registerAndLogin(request);

    // 创建 seed 条目
    const entry = await createEntry(request, {
      type: 'task',
      title: 'Chat搜索测试任务-独特关键词XYZ',
    }, user.token);

    try {
      // 调用 Chat API with force_intent=read
      const resp = await request.post('/api/chat', {
        headers: { Authorization: `Bearer ${user.token}` },
        data: {
          text: 'Chat搜索测试任务-独特关键词XYZ',
          session_id: 'e2e-read-test',
          force_intent: 'read',
        },
      });

      expect(resp.ok()).toBeTruthy();
      expect(resp.headers()['content-type']).toContain('text/event-stream');

      const raw = await resp.text();
      const events = parseSSEEvents(raw);

      // 验证有 intent 事件
      const intentEvent = events.find(e => e.event === 'intent');
      expect(intentEvent).toBeTruthy();
      expect(intentEvent!.data.intent).toBe('read');

      // 验证有 results 事件
      const resultsEvent = events.find(e => e.event === 'results');
      expect(resultsEvent).toBeTruthy();
      expect(resultsEvent!.data.items.length).toBeGreaterThanOrEqual(1);

      // 验证结果包含 seed 条目
      const found = resultsEvent!.data.items.some(
        (item: any) => item.title === 'Chat搜索测试任务-独特关键词XYZ'
      );
      expect(found).toBeTruthy();

      // 验证有 done 事件
      const doneEvent = events.find(e => e.event === 'done');
      expect(doneEvent).toBeTruthy();
    } finally {
      await deleteEntry(request, entry.id, user.token);
    }
  });

  test('Chat delete 删除已有条目返回 deleted 事件', async ({ request }) => {
    const user = await registerAndLogin(request);

    const entry = await createEntry(request, {
      type: 'task',
      title: 'Chat删除测试任务-唯一标识',
    }, user.token);

    try {
      // Step 1: 发送 delete 意图，期望返回 confirm 事件
      const resp1 = await request.post('/api/chat', {
        headers: { Authorization: `Bearer ${user.token}` },
        data: {
          text: 'Chat删除测试任务-唯一标识',
          session_id: 'e2e-delete-test',
          force_intent: 'delete',
        },
      });

      expect(resp1.ok()).toBeTruthy();
      const raw1 = await resp1.text();
      const events1 = parseSSEEvents(raw1);

      // 验证 confirm 事件（因为需要确认删除哪个）
      const confirmEvent = events1.find(e => e.event === 'confirm');
      expect(confirmEvent).toBeTruthy();
      expect(confirmEvent!.data.action).toBe('delete');
      expect(confirmEvent!.data.items.length).toBeGreaterThanOrEqual(1);

      // Step 2: 确认删除
      const itemId = confirmEvent!.data.items[0].id;
      expect(itemId).toBe(entry.id);

      const resp2 = await request.post('/api/chat', {
        headers: { Authorization: `Bearer ${user.token}` },
        data: {
          text: '确认删除',
          session_id: 'e2e-delete-test',
          force_intent: 'delete',
          confirm: { action: 'delete', item_id: itemId },
        },
      });

      expect(resp2.ok()).toBeTruthy();
      const raw2 = await resp2.text();
      const events2 = parseSSEEvents(raw2);

      // 验证 deleted 事件
      const deletedEvent = events2.find(e => e.event === 'deleted');
      expect(deletedEvent).toBeTruthy();
      expect(deletedEvent!.data.id).toBe(itemId);

      // 验证 done 事件
      const doneEvent = events2.find(e => e.event === 'done');
      expect(doneEvent).toBeTruthy();
    } finally {
      // 尝试清理（如果 delete 测试失败条目可能仍在）
      try { await deleteEntry(request, entry.id, user.token); } catch {}
    }
  });

  test('Chat 空输入返回验证错误', async ({ request }) => {
    const user = await registerAndLogin(request);

    const resp = await request.post('/api/chat', {
      headers: { Authorization: `Bearer ${user.token}` },
      data: {
        text: '',
        session_id: 'e2e-empty-test',
      },
    });

    // 空文本应该被 min_length=1 验证拒绝
    expect(resp.ok()).toBeFalsy();
    expect(resp.status()).toBe(422);
  });

  test('Chat 未认证请求返回 401', async ({ request }) => {
    const resp = await request.post('/api/chat', {
      data: {
        text: '测试消息',
        session_id: 'e2e-noauth-test',
      },
    });

    expect(resp.status()).toBe(401);
  });

  test('会话列表返回非空', async ({ request }) => {
    const user = await registerAndLogin(request);

    // 通过 PATCH /sessions/{session_id} 创建会话
    const saveResp = await request.patch('/api/sessions/e2e-session-list', {
      headers: { Authorization: `Bearer ${user.token}` },
      data: { title: 'E2E测试会话' },
    });
    expect(saveResp.ok()).toBeTruthy();

    // 获取会话列表
    const resp = await request.get('/api/sessions', {
      headers: { Authorization: `Bearer ${user.token}` },
    });

    expect(resp.ok()).toBeTruthy();
    const sessions = await resp.json();
    expect(Array.isArray(sessions)).toBeTruthy();
    expect(sessions.length).toBeGreaterThanOrEqual(1);
  });
});
