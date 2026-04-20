/**
 * B75: 新类型条目 API E2E 测试
 *
 * 覆盖 decision/reflection/question 三种新类型：
 * - 创建 / 列表过滤 / 全文搜索（FTS5）/ 更新 / 删除
 * - 混合类型独立存在
 * - 认证 / 异常场景
 */
import { test, expect } from '@playwright/test';
import { registerAndLogin } from './helpers/auth';
import {
  createEntry,
  listEntries,
  updateEntry,
  deleteEntry,
  searchEntriesFTS5,
} from './helpers/api';

test.describe.configure({ timeout: 30000 });

test.describe('新类型条目 API', () => {
  // ========================
  // 创建 3 种新类型
  // ========================

  test('创建 decision → 201 + category=decision', async ({ request }) => {
    const { token } = await registerAndLogin(request, 'nt_decision');

    const entry = await createEntry(request, {
      type: 'decision',
      title: '采用 React 作为前端框架',
    }, token);

    expect(entry.id).toBeDefined();
    expect(entry.category).toBe('decision');
    expect(entry.title).toBe('采用 React 作为前端框架');
  });

  test('创建 reflection → 201 + category=reflection', async ({ request }) => {
    const { token } = await registerAndLogin(request, 'nt_reflection');

    const entry = await createEntry(request, {
      type: 'reflection',
      title: '本周学习复盘',
    }, token);

    expect(entry.id).toBeDefined();
    expect(entry.category).toBe('reflection');
    expect(entry.title).toBe('本周学习复盘');
  });

  test('创建 question → 201 + category=question', async ({ request }) => {
    const { token } = await registerAndLogin(request, 'nt_question');

    const entry = await createEntry(request, {
      type: 'question',
      title: '如何优化数据库查询性能',
    }, token);

    expect(entry.id).toBeDefined();
    expect(entry.category).toBe('question');
    expect(entry.title).toBe('如何优化数据库查询性能');
  });

  // ========================
  // 列表按类型过滤
  // ========================

  test('列表 type=decision 过滤 → 只含 decision', async ({ request }) => {
    const { token } = await registerAndLogin(request, 'nt_filter_dec');

    await createEntry(request, { type: 'decision', title: '决策 A' }, token);
    await createEntry(request, { type: 'reflection', title: '复盘 B' }, token);
    await createEntry(request, { type: 'question', title: '疑问 C' }, token);

    const data = await listEntries(request, token, 'decision');
    // EntryListResponse: { entries: [...], total: number }
    expect(Array.isArray(data.entries)).toBe(true);
    expect(typeof data.total).toBe('number');
    expect(data.total).toBeGreaterThanOrEqual(1);
    for (const e of data.entries) {
      expect(e.category).toBe('decision');
    }
  });

  test('列表 type=reflection 过滤 → 只含 reflection', async ({ request }) => {
    const { token } = await registerAndLogin(request, 'nt_filter_ref');

    await createEntry(request, { type: 'decision', title: '决策 D' }, token);
    await createEntry(request, { type: 'reflection', title: '复盘 E' }, token);

    const data = await listEntries(request, token, 'reflection');
    expect(Array.isArray(data.entries)).toBe(true);
    expect(typeof data.total).toBe('number');
    for (const e of data.entries) {
      expect(e.category).toBe('reflection');
    }
  });

  test('列表 type=question 过滤 → 只含 question', async ({ request }) => {
    const { token } = await registerAndLogin(request, 'nt_filter_q');

    await createEntry(request, { type: 'question', title: '疑问 F' }, token);
    await createEntry(request, { type: 'decision', title: '决策 G' }, token);

    const data = await listEntries(request, token, 'question');
    expect(Array.isArray(data.entries)).toBe(true);
    expect(typeof data.total).toBe('number');
    for (const e of data.entries) {
      expect(e.category).toBe('question');
    }
  });

  // ========================
  // 全文搜索（FTS5）
  // ========================

  test('全文搜索 decision 标题 → 结果命中', async ({ request }) => {
    const { token } = await registerAndLogin(request, 'nt_search');

    await createEntry(request, {
      type: 'decision',
      title: '微服务架构选型决策记录',
    }, token);

    const results = await searchEntriesFTS5(request, '微服务架构', token);
    // SearchResult: { entries: [...], query: string }
    expect(Array.isArray(results.entries)).toBe(true);
    expect(results.query).toBe('微服务架构');
    expect(results.entries.length).toBeGreaterThanOrEqual(1);
    const matched = results.entries.find((e: any) =>
      e.category === 'decision' && e.title?.includes('微服务架构')
    );
    expect(matched).toBeDefined();
  });

  test('搜索不匹配关键词 → 空结果', async ({ request }) => {
    const { token } = await registerAndLogin(request, 'nt_search_empty');

    await createEntry(request, {
      type: 'decision',
      title: '一个普通决策',
    }, token);

    const results = await searchEntriesFTS5(request, 'xyz完全不匹配的关键词abc', token);
    expect(Array.isArray(results.entries)).toBe(true);
    expect(results.entries.length).toBe(0);
  });

  // ========================
  // 更新
  // ========================

  test('更新 decision 标题 → 标题变更', async ({ request }) => {
    const { token } = await registerAndLogin(request, 'nt_update');

    const entry = await createEntry(request, {
      type: 'decision',
      title: '旧标题决策',
    }, token);

    // updateEntry 返回 SuccessResponse: {success, message}
    const resp = await request.put(`/api/entries/${entry.id}`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { title: '更新后的决策标题' },
    });
    expect(resp.ok()).toBeTruthy();
    const updateResult = await resp.json();
    expect(updateResult.success).toBe(true);

    const getResp = await request.get(`/api/entries/${entry.id}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(getResp.ok()).toBeTruthy();
    const updated = await getResp.json();
    expect(updated.title).toBe('更新后的决策标题');
    expect(updated.category).toBe('decision');
  });

  // ========================
  // 删除
  // ========================

  test('删除 reflection → 列表不再包含', async ({ request }) => {
    const { token } = await registerAndLogin(request, 'nt_delete');

    const entry = await createEntry(request, {
      type: 'reflection',
      title: '待删除的复盘',
    }, token);

    // deleteEntry 返回 SuccessResponse: {success, message}
    const delResp = await request.delete(`/api/entries/${entry.id}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(delResp.ok()).toBeTruthy();
    const delResult = await delResp.json();
    expect(delResult.success).toBe(true);

    const data = await listEntries(request, token, 'reflection');
    const ids = data.entries.map((e: any) => e.id);
    expect(ids).not.toContain(entry.id);
  });

  // ========================
  // 混合类型
  // ========================

  test('混合创建 3 种类型 → 各自独立存在', async ({ request }) => {
    const { token } = await registerAndLogin(request, 'nt_mixed');

    const decision = await createEntry(request, {
      type: 'decision',
      title: '混合决策',
    }, token);
    const reflection = await createEntry(request, {
      type: 'reflection',
      title: '混合复盘',
    }, token);
    const question = await createEntry(request, {
      type: 'question',
      title: '混合疑问',
    }, token);

    expect(decision.category).toBe('decision');
    expect(reflection.category).toBe('reflection');
    expect(question.category).toBe('question');
    expect(decision.id).not.toBe(reflection.id);
    expect(reflection.id).not.toBe(question.id);

    // 各自过滤确认独立
    const decList = await listEntries(request, token, 'decision');
    const decIds = decList.entries.map((e: any) => e.id);
    expect(decIds).toContain(decision.id);

    const refList = await listEntries(request, token, 'reflection');
    const refIds = refList.entries.map((e: any) => e.id);
    expect(refIds).toContain(reflection.id);

    const queList = await listEntries(request, token, 'question');
    const queIds = queList.entries.map((e: any) => e.id);
    expect(queIds).toContain(question.id);
  });

  // ========================
  // 未认证
  // ========================

  test('未认证创建 → 401', async ({ request }) => {
    const resp = await request.post('/api/entries', {
      data: {
        type: 'decision',
        title: '无认证',
        content: '',
      },
    });
    expect(resp.status()).toBe(401);
  });

  // ========================
  // 不存在条目
  // ========================

  test('更新/删除不存在条目 → 404', async ({ request }) => {
    const { token } = await registerAndLogin(request, 'nt_404');

    const fakeId = 'nonexistent_entry_xyz';
    const updateResp = await request.put(`/api/entries/${fakeId}`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { title: '不存在' },
    });
    expect(updateResp.status()).toBe(404);

    const deleteResp = await request.delete(`/api/entries/${fakeId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(deleteResp.status()).toBe(404);
  });

  // ========================
  // 边界: 特殊字符标题
  // ========================

  test('特殊字符标题创建 → 成功', async ({ request }) => {
    const { token } = await registerAndLogin(request, 'nt_special');

    const entry = await createEntry(request, {
      type: 'question',
      title: '如何处理 <script>alert("xss")</script> 攻击？',
    }, token);

    expect(entry.id).toBeDefined();
    expect(entry.title).toContain('<script>');
  });
});
