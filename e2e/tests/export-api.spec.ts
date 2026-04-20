/**
 * B76: 导出 API E2E 测试
 *
 * 覆盖 markdown/json 导出：
 * - 格式验证 / 类型过滤 / 日期范围
 * - 新类型导出（decision/reflection/question）
 * - 认证 / 异常场景
 */
import { test, expect } from '@playwright/test';
import { registerAndLogin } from './helpers/auth';
import { createEntry } from './helpers/api';
import { exportEntries } from './helpers/export';

test.describe.configure({ timeout: 30000 });

test.describe('导出 API', () => {
  // ========================
  // markdown 导出
  // ========================

  test('markdown 导出 → 200 + content-type=application/zip', async ({ request }) => {
    const { token } = await registerAndLogin(request, 'exp_md');

    await createEntry(request, { type: 'task', title: '导出测试任务' }, token);

    const resp = await exportEntries(request, { format: 'markdown' }, token);
    expect(resp.status()).toBe(200);
    const contentType = resp.headers()['content-type'];
    expect(contentType).toContain('application/zip');
  });

  // ========================
  // json 导出
  // ========================

  test('json 导出 → 200 + JSON 数组 + 包含已创建条目', async ({ request }) => {
    const { token } = await registerAndLogin(request, 'exp_json');

    const entry = await createEntry(request, {
      type: 'task',
      title: 'JSON 导出测试',
    }, token);

    const resp = await exportEntries(request, { format: 'json' }, token);
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    expect(Array.isArray(data)).toBe(true);
    const ids = data.map((e: any) => e.id);
    expect(ids).toContain(entry.id);
  });

  // ========================
  // 类型过滤
  // ========================

  test('type=task 过滤 → 只含 task', async ({ request }) => {
    const { token } = await registerAndLogin(request, 'exp_task');

    await createEntry(request, { type: 'task', title: '任务条目' }, token);
    await createEntry(request, { type: 'note', title: '笔记条目' }, token);

    const resp = await exportEntries(request, { format: 'json', type: 'task' }, token);
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    for (const e of data) {
      expect(e.category).toBe('task');
    }
  });

  test('type=decision 过滤 → 只含 decision（跨模块闭环）', async ({ request }) => {
    const { token } = await registerAndLogin(request, 'exp_dec');

    await createEntry(request, { type: 'decision', title: '决策导出' }, token);
    await createEntry(request, { type: 'task', title: '任务导出' }, token);

    const resp = await exportEntries(request, { format: 'json', type: 'decision' }, token);
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    for (const e of data) {
      expect(e.category).toBe('decision');
    }
    expect(data.length).toBeGreaterThanOrEqual(1);
  });

  test('type=reflection 过滤 → 只含 reflection', async ({ request }) => {
    const { token } = await registerAndLogin(request, 'exp_ref');

    await createEntry(request, { type: 'reflection', title: '复盘导出' }, token);

    const resp = await exportEntries(request, { format: 'json', type: 'reflection' }, token);
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    for (const e of data) {
      expect(e.category).toBe('reflection');
    }
  });

  test('type=question 过滤 → 只含 question', async ({ request }) => {
    const { token } = await registerAndLogin(request, 'exp_que');

    await createEntry(request, { type: 'question', title: '疑问导出' }, token);

    const resp = await exportEntries(request, { format: 'json', type: 'question' }, token);
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    for (const e of data) {
      expect(e.category).toBe('question');
    }
  });

  // ========================
  // 日期范围过滤
  // ========================

  test('日期范围过滤 → 只含范围内条目', async ({ request }) => {
    const { token } = await registerAndLogin(request, 'exp_date');

    await createEntry(request, { type: 'task', title: '今天任务' }, token);

    const today = new Date().toISOString().split('T')[0];
    const resp = await exportEntries(request, {
      format: 'json',
      start_date: today,
      end_date: today,
    }, token);
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    // 至少应该包含今天创建的条目
    expect(data.length).toBeGreaterThanOrEqual(1);
  });

  // ========================
  // 无效参数
  // ========================

  test('无效 format → 422', async ({ request }) => {
    const { token } = await registerAndLogin(request, 'exp_inv_fmt');

    const resp = await request.get('/api/entries/export?format=xml', {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(resp.status()).toBe(422);
  });

  test('无效 type → 422', async ({ request }) => {
    const { token } = await registerAndLogin(request, 'exp_inv_type');

    const resp = await request.get('/api/entries/export?format=json&type=invalid_type', {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(resp.status()).toBe(422);
  });

  // ========================
  // 空数据
  // ========================

  test('空数据 json 导出 → 空数组', async ({ request }) => {
    const { token } = await registerAndLogin(request, 'exp_empty');

    // 新用户无数据，type=decision 可能没条目
    const resp = await exportEntries(request, { format: 'json', type: 'decision' }, token);
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    expect(Array.isArray(data)).toBe(true);
    expect(data).toEqual([]);
  });

  // ========================
  // 未认证
  // ========================

  test('未认证 → 401', async ({ request }) => {
    const resp = await exportEntries(request, { format: 'json' });
    expect(resp.status()).toBe(401);
  });
});
