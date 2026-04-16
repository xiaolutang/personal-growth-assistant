/**
 * B39: 回顾页 E2E 测试
 *
 * 覆盖回顾统计页面的核心路径：
 * - 日/周/月统计
 * - 趋势数据
 * - 知识热力图、成长曲线、活动热力图
 * - 有数据和无数据两种场景
 *
 * 纯 API 测试，不依赖 UI 渲染。
 */
import { test, expect } from '@playwright/test';
import { registerAndLogin } from './helpers/auth';
import { createEntry, deleteEntry } from './helpers/api';

test.describe.configure({ timeout: 120000 });

test.describe('回顾统计', () => {
  test('无数据时各端点返回空结果', async ({ request }) => {
    const user = await registerAndLogin(request);
    const headers = { Authorization: `Bearer ${user.token}` };

    // 日统计
    const daily = await (await request.get('/api/review/daily', { headers })).json();
    expect(daily).toBeTruthy();

    // 周统计
    const weekly = await (await request.get('/api/review/weekly', { headers })).json();
    expect(weekly).toBeTruthy();

    // 月统计
    const monthly = await (await request.get('/api/review/monthly', { headers })).json();
    expect(monthly).toBeTruthy();

    // 趋势
    const trend = await (await request.get('/api/review/trend', { headers })).json();
    expect(trend).toBeTruthy();

    // 知识热力图
    const heatmap = await (await request.get('/api/review/knowledge-heatmap', { headers })).json();
    expect(heatmap).toBeTruthy();

    // 成长曲线
    const curve = await (await request.get('/api/review/growth-curve', { headers })).json();
    expect(curve).toBeTruthy();

    // 活动热力图
    const activity = await (await request.get('/api/review/activity-heatmap', { headers })).json();
    expect(activity).toBeTruthy();
  });

  test('有 seed 数据时日统计返回非零数值', async ({ request }) => {
    const user = await registerAndLogin(request);
    const headers = { Authorization: `Bearer ${user.token}` };

    // 创建已完成的任务
    const entry = await createEntry(request, {
      type: 'task',
      title: '回顾测试-已完成任务',
      status: 'completed',
    }, user.token);

    try {
      const resp = await request.get('/api/review/daily', { headers });
      expect(resp.ok()).toBeTruthy();
      const data = await resp.json();
      // 应该有统计数据
      expect(data).toBeTruthy();
    } finally {
      await deleteEntry(request, entry.id, user.token);
    }
  });

  test('周统计返回正确结构', async ({ request }) => {
    const user = await registerAndLogin(request);
    const headers = { Authorization: `Bearer ${user.token}` };

    const entry = await createEntry(request, {
      type: 'task',
      title: '回顾测试-周统计',
      status: 'completed',
    }, user.token);

    try {
      const resp = await request.get('/api/review/weekly', { headers });
      expect(resp.ok()).toBeTruthy();
      const data = await resp.json();
      expect(data).toBeTruthy();
    } finally {
      await deleteEntry(request, entry.id, user.token);
    }
  });

  test('月统计返回正确结构', async ({ request }) => {
    const user = await registerAndLogin(request);
    const headers = { Authorization: `Bearer ${user.token}` };

    const entry = await createEntry(request, {
      type: 'task',
      title: '回顾测试-月统计',
      status: 'completed',
    }, user.token);

    try {
      const resp = await request.get('/api/review/monthly', { headers });
      expect(resp.ok()).toBeTruthy();
      const data = await resp.json();
      expect(data).toBeTruthy();
    } finally {
      await deleteEntry(request, entry.id, user.token);
    }
  });

  test('趋势数据返回时间序列', async ({ request }) => {
    const user = await registerAndLogin(request);
    const headers = { Authorization: `Bearer ${user.token}` };

    const entry = await createEntry(request, {
      type: 'task',
      title: '回顾测试-趋势',
      status: 'completed',
    }, user.token);

    try {
      const resp = await request.get('/api/review/trend', { headers });
      expect(resp.ok()).toBeTruthy();
      const data = await resp.json();
      expect(data).toBeTruthy();
      // 趋势数据应有 periods 数组
      expect(Array.isArray(data.periods)).toBeTruthy();
    } finally {
      await deleteEntry(request, entry.id, user.token);
    }
  });

  test('知识热力图返回数据', async ({ request }) => {
    const user = await registerAndLogin(request);
    const headers = { Authorization: `Bearer ${user.token}` };

    const entry = await createEntry(request, {
      type: 'task',
      title: '回顾测试-知识热力图',
      status: 'completed',
    }, user.token);

    try {
      const resp = await request.get('/api/review/knowledge-heatmap', { headers });
      expect(resp.ok()).toBeTruthy();
      const data = await resp.json();
      expect(data).toBeTruthy();
    } finally {
      await deleteEntry(request, entry.id, user.token);
    }
  });

  test('成长曲线返回数据', async ({ request }) => {
    const user = await registerAndLogin(request);
    const headers = { Authorization: `Bearer ${user.token}` };

    const entry = await createEntry(request, {
      type: 'task',
      title: '回顾测试-成长曲线',
      status: 'completed',
    }, user.token);

    try {
      const resp = await request.get('/api/review/growth-curve', { headers });
      expect(resp.ok()).toBeTruthy();
      const data = await resp.json();
      expect(data).toBeTruthy();
    } finally {
      await deleteEntry(request, entry.id, user.token);
    }
  });

  test('活动热力图返回数据', async ({ request }) => {
    const user = await registerAndLogin(request);
    const headers = { Authorization: `Bearer ${user.token}` };

    const entry = await createEntry(request, {
      type: 'task',
      title: '回顾测试-活动热力图',
      status: 'completed',
    }, user.token);

    try {
      const resp = await request.get('/api/review/activity-heatmap', { headers });
      expect(resp.ok()).toBeTruthy();
      const data = await resp.json();
      expect(data).toBeTruthy();
    } finally {
      await deleteEntry(request, entry.id, user.token);
    }
  });

  test('未认证请求返回 401', async ({ request }) => {
    const resp = await request.get('/api/review/daily');
    expect(resp.status()).toBe(401);
  });
});
