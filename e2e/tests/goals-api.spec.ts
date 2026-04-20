/**
 * B74: Goals API E2E 测试
 *
 * 覆盖目标管理 API 的完整路径：
 * - 创建 3 种 metric_type 目标
 * - 列出 / 详情 / 更新 / 删除
 * - 关联 / 取消关联条目
 * - Checklist 切换
 * - 进度汇总
 * - 认证 / 校验异常
 */
import { test, expect } from '@playwright/test';
import { registerAndLogin } from './helpers/auth';
import { createEntry } from './helpers/api';
import {
  createGoal,
  listGoals,
  getGoal,
  updateGoal,
  deleteGoal,
  linkEntry,
  unlinkEntry,
  listGoalEntries,
  toggleChecklist,
  getProgressSummary,
} from './helpers/goals';

test.describe.configure({ timeout: 30000 });

test.describe('Goals API', () => {
  // ========================
  // 正常路径: 创建 3 种 metric_type
  // ========================

  test('创建 count 类型目标 → 201 + 正确字段', async ({ request }) => {
    const { token } = await registerAndLogin(request, 'goal_count');

    const resp = await createGoal(request, {
      title: '跑步 30 次',
      metric_type: 'count',
      target_value: 30,
    }, token);

    expect(resp.status()).toBe(201);
    const data = await resp.json();
    expect(data.id).toBeDefined();
    expect(data.title).toBe('跑步 30 次');
    expect(data.metric_type).toBe('count');
    expect(data.target_value).toBe(30);
    expect(data.current_value).toBe(0);
    expect(data.status).toBe('active');
    expect(data.progress_percentage).toBe(0.0);
    expect(data.auto_tags).toBeNull();
    expect(data.checklist_items).toBeNull();
    expect(data.created_at).toBeDefined();
    expect(data.updated_at).toBeDefined();
  });

  test('创建 checklist 类型目标 → 201 + checklist_items 有 id/title/checked', async ({ request }) => {
    const { token } = await registerAndLogin(request, 'goal_cl');

    const resp = await createGoal(request, {
      title: '学习清单',
      metric_type: 'checklist',
      target_value: 2,
      checklist_items: ['读一本书', '写一篇笔记'],
    }, token);

    expect(resp.status()).toBe(201);
    const data = await resp.json();
    expect(data.metric_type).toBe('checklist');
    expect(data.checklist_items).toHaveLength(2);
    expect(data.checklist_items[0]).toHaveProperty('id');
    expect(data.checklist_items[0]).toHaveProperty('title');
    expect(data.checklist_items[0]).toHaveProperty('checked');
    expect(data.checklist_items[0].checked).toBe(false);
    expect(data.checklist_items[0].title).toBe('读一本书');
    expect(data.checklist_items[1].title).toBe('写一篇笔记');
  });

  test('创建 tag_auto 类型目标 → 201 + auto_tags 字段', async ({ request }) => {
    const { token } = await registerAndLogin(request, 'goal_tag');

    const resp = await createGoal(request, {
      title: '跑步相关条目',
      metric_type: 'tag_auto',
      target_value: 5,
      auto_tags: ['跑步', '运动'],
    }, token);

    expect(resp.status()).toBe(201);
    const data = await resp.json();
    expect(data.metric_type).toBe('tag_auto');
    expect(data.auto_tags).toEqual(['跑步', '运动']);
  });

  // ========================
  // 列出目标
  // ========================

  test('列出目标 → 返回数组', async ({ request }) => {
    const { token } = await registerAndLogin(request, 'goal_list');

    await createGoal(request, {
      title: '目标 A',
      metric_type: 'count',
      target_value: 10,
    }, token);

    await createGoal(request, {
      title: '目标 B',
      metric_type: 'count',
      target_value: 5,
    }, token);

    const resp = await listGoals(request, token);
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    expect(data.goals).toBeDefined();
    expect(Array.isArray(data.goals)).toBe(true);
    expect(data.goals.length).toBeGreaterThanOrEqual(2);
  });

  test('按 status=active 过滤 → 只返回 active', async ({ request }) => {
    const { token } = await registerAndLogin(request, 'goal_filter');

    const resp1 = await createGoal(request, {
      title: '活跃目标',
      metric_type: 'count',
      target_value: 10,
    }, token);
    const goal1 = await resp1.json();

    // 创建第二个并设为 completed
    const resp2 = await createGoal(request, {
      title: '完成目标',
      metric_type: 'count',
      target_value: 1,
    }, token);
    const goal2 = await resp2.json();
    await updateGoal(request, goal2.id, { status: 'completed' }, token);

    const resp = await listGoals(request, token, { status: 'active' });
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    const activeGoals = data.goals;
    expect(activeGoals.length).toBeGreaterThanOrEqual(1);
    for (const g of activeGoals) {
      expect(g.status).toBe('active');
    }
  });

  // ========================
  // 获取目标详情
  // ========================

  test('获取目标详情 → 含 linked_entries_count', async ({ request }) => {
    const { token } = await registerAndLogin(request, 'goal_detail');

    const resp = await createGoal(request, {
      title: '详情测试',
      metric_type: 'count',
      target_value: 5,
    }, token);
    const goal = await resp.json();

    const detailResp = await getGoal(request, goal.id, token);
    expect(detailResp.status()).toBe(200);
    const detail = await detailResp.json();
    expect(detail.id).toBe(goal.id);
    expect(detail.linked_entries_count).toBe(0);
  });

  // ========================
  // 更新目标
  // ========================

  test('更新目标状态 active→completed → status 变为 completed', async ({ request }) => {
    const { token } = await registerAndLogin(request, 'goal_update');

    const resp = await createGoal(request, {
      title: '状态切换测试',
      metric_type: 'count',
      target_value: 10,
    }, token);
    const goal = await resp.json();
    expect(goal.status).toBe('active');

    const updateResp = await updateGoal(request, goal.id, { status: 'completed' }, token);
    expect(updateResp.status()).toBe(200);
    const updated = await updateResp.json();
    expect(updated.status).toBe('completed');
  });

  // ========================
  // 删除目标
  // ========================

  test('删除 active 目标 → 拒绝（仅 abandoned 可删）', async ({ request }) => {
    const { token } = await registerAndLogin(request, 'goal_del_active');

    const resp = await createGoal(request, {
      title: '不可删除的目标',
      metric_type: 'count',
      target_value: 10,
    }, token);
    const goal = await resp.json();

    const delResp = await deleteGoal(request, goal.id, token);
    expect(delResp.status()).toBe(400);
  });

  test('abandoned 目标删除成功 → 200 + GET 404', async ({ request }) => {
    const { token } = await registerAndLogin(request, 'goal_del_abandoned');

    const resp = await createGoal(request, {
      title: '可删除的目标',
      metric_type: 'count',
      target_value: 10,
    }, token);
    const goal = await resp.json();

    // 先设为 abandoned
    await updateGoal(request, goal.id, { status: 'abandoned' }, token);

    // 删除
    const delResp = await deleteGoal(request, goal.id, token);
    expect(delResp.status()).toBe(200);

    // 确认 GET 404
    const getResp = await getGoal(request, goal.id, token);
    expect(getResp.status()).toBe(404);
  });

  // ========================
  // 关联条目到 count 目标
  // ========================

  test('关联条目到 count 目标 → current_value +1', async ({ request }) => {
    const { token } = await registerAndLogin(request, 'goal_link');

    // 创建目标和条目
    const goalResp = await createGoal(request, {
      title: '关联测试',
      metric_type: 'count',
      target_value: 5,
    }, token);
    const goal = await goalResp.json();

    const entry = await createEntry(request, {
      type: 'task',
      title: '关联条目测试',
    }, token);

    // 关联
    const linkResp = await linkEntry(request, goal.id, entry.id, token);
    expect(linkResp.status()).toBe(201);
    const linkData = await linkResp.json();
    expect(linkData.goal_id).toBe(goal.id);
    expect(linkData.entry_id).toBe(entry.id);

    // 验证 current_value
    const detailResp = await getGoal(request, goal.id, token);
    const detail = await detailResp.json();
    expect(detail.current_value).toBe(1);
    expect(detail.linked_entries_count).toBe(1);
  });

  // ========================
  // 目标关联条目列表
  // ========================

  test('空关联列表 → 返回空数组', async ({ request }) => {
    const { token } = await registerAndLogin(request, 'goal_le_empty');

    const goalResp = await createGoal(request, {
      title: '关联列表空测试',
      metric_type: 'count',
      target_value: 5,
    }, token);
    const goal = await goalResp.json();

    const listResp = await listGoalEntries(request, goal.id, token);
    expect(listResp.status()).toBe(200);
    const data = await listResp.json();
    expect(data.entries).toBeDefined();
    expect(Array.isArray(data.entries)).toBe(true);
    expect(data.entries).toEqual([]);
  });

  test('关联后列出条目 → 包含已关联条目', async ({ request }) => {
    const { token } = await registerAndLogin(request, 'goal_le_filled');

    const goalResp = await createGoal(request, {
      title: '关联列表测试',
      metric_type: 'count',
      target_value: 5,
    }, token);
    const goal = await goalResp.json();

    const entry = await createEntry(request, {
      type: 'task',
      title: '关联列表条目',
    }, token);

    await linkEntry(request, goal.id, entry.id, token);

    const listResp = await listGoalEntries(request, goal.id, token);
    expect(listResp.status()).toBe(200);
    const data = await listResp.json();
    expect(data.entries).toHaveLength(1);
    expect(data.entries[0].entry_id).toBe(entry.id);
    expect(data.entries[0].entry.id).toBe(entry.id);
    expect(data.entries[0].entry.title).toBe('关联列表条目');
  });

  // ========================
  // 取消关联条目
  // ========================

  test('取消关联条目 → current_value -1', async ({ request }) => {
    const { token } = await registerAndLogin(request, 'goal_unlink');

    const goalResp = await createGoal(request, {
      title: '取消关联测试',
      metric_type: 'count',
      target_value: 5,
    }, token);
    const goal = await goalResp.json();

    const entry = await createEntry(request, {
      type: 'task',
      title: '取消关联条目',
    }, token);

    await linkEntry(request, goal.id, entry.id, token);

    // 取消关联
    const unlinkResp = await unlinkEntry(request, goal.id, entry.id, token);
    expect(unlinkResp.status()).toBe(204);

    // 验证 current_value 回到 0
    const detailResp = await getGoal(request, goal.id, token);
    const detail = await detailResp.json();
    expect(detail.current_value).toBe(0);
  });

  // ========================
  // 切换 checklist 项
  // ========================

  test('切换 checklist 项 → checked 翻转', async ({ request }) => {
    const { token } = await registerAndLogin(request, 'goal_toggle');

    const resp = await createGoal(request, {
      title: '切换测试',
      metric_type: 'checklist',
      target_value: 2,
      checklist_items: ['项 A', '项 B'],
    }, token);
    const goal = await resp.json();
    const itemId = goal.checklist_items[0].id;

    // 切换为 checked
    const toggleResp = await toggleChecklist(request, goal.id, itemId, token);
    expect(toggleResp.status()).toBe(200);
    const toggled = await toggleResp.json();
    const toggledItem = toggled.checklist_items.find((i: any) => i.id === itemId);
    expect(toggledItem.checked).toBe(true);
    expect(toggled.current_value).toBe(1);

    // 再次切换回 unchecked
    const toggleResp2 = await toggleChecklist(request, goal.id, itemId, token);
    expect(toggleResp2.status()).toBe(200);
    const toggled2 = await toggleResp2.json();
    const toggledItem2 = toggled2.checklist_items.find((i: any) => i.id === itemId);
    expect(toggledItem2.checked).toBe(false);
  });

  // ========================
  // 进度汇总
  // ========================

  test('进度汇总 → 精确断言 active_count/completed_count + goals 仅含活跃目标', async ({ request }) => {
    const { token } = await registerAndLogin(request, 'goal_progress');

    const resp1 = await createGoal(request, {
      title: '活跃汇总',
      metric_type: 'count',
      target_value: 10,
    }, token);
    const goal1 = await resp1.json();

    const resp2 = await createGoal(request, {
      title: '完成汇总',
      metric_type: 'count',
      target_value: 1,
    }, token);
    const goal2 = await resp2.json();
    await updateGoal(request, goal2.id, { status: 'completed' }, token);

    const summaryResp = await getProgressSummary(request, token);
    expect(summaryResp.status()).toBe(200);
    const summary = await summaryResp.json();
    // 精确断言数量
    expect(summary.active_count).toBe(1);
    expect(summary.completed_count).toBe(1);
    // goals 仅含活跃目标
    expect(summary.goals).toHaveLength(1);
    const goalItem = summary.goals[0];
    expect(goalItem.id).toBe(goal1.id);
    expect(goalItem.title).toBe('活跃汇总');
    expect(typeof goalItem.progress_percentage).toBe('number');
    // 不应包含 status 字段（ProgressItem schema 无此字段）
    expect(goalItem).not.toHaveProperty('status');
  });

  // ========================
  // 未认证请求
  // ========================

  test('未认证请求 → 401', async ({ request }) => {
    const resp = await createGoal(request, {
      title: '无认证',
      metric_type: 'count',
      target_value: 1,
    });
    expect(resp.status()).toBe(401);

    const listResp = await listGoals(request);
    expect(listResp.status()).toBe(401);
  });

  // ========================
  // 跨用户隔离
  // ========================

  test('跨用户隔离 → A 不能操作 B 的目标', async ({ request }) => {
    // 用户 A 创建目标
    const userA = await registerAndLogin(request, 'iso_user_a');
    const goalResp = await createGoal(request, {
      title: 'A 的目标',
      metric_type: 'count',
      target_value: 5,
    }, userA.token);
    const goal = await goalResp.json();

    // 用户 B 尝试访问 A 的目标
    const userB = await registerAndLogin(request, 'iso_user_b');

    const getResp = await getGoal(request, goal.id, userB.token);
    expect(getResp.status()).toBe(404);

    const updateResp = await updateGoal(request, goal.id, { title: 'B 篡改' }, userB.token);
    expect(updateResp.status()).toBe(404);

    const delResp = await deleteGoal(request, goal.id, userB.token);
    expect(delResp.status()).toBe(404);

    // B 的列表不含 A 的目标
    const listResp = await listGoals(request, userB.token);
    const listData = await listResp.json();
    const ids = listData.goals.map((g: any) => g.id);
    expect(ids).not.toContain(goal.id);
  });

  // ========================
  // 边界: 空目标列表
  // ========================

  test('空目标列表 → 返回空数组', async ({ request }) => {
    const { token } = await registerAndLogin(request, 'goal_empty');

    const resp = await listGoals(request, token);
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    expect(data.goals).toEqual([]);
  });

  // ========================
  // 边界: target_value=1 最小值
  // ========================

  test('target_value=1 最小值 → 创建成功', async ({ request }) => {
    const { token } = await registerAndLogin(request, 'goal_min');

    const resp = await createGoal(request, {
      title: '最小目标值',
      metric_type: 'count',
      target_value: 1,
    }, token);
    expect(resp.status()).toBe(201);
    const data = await resp.json();
    expect(data.target_value).toBe(1);
  });

  // ========================
  // 边界: 已完成目标不可删
  // ========================

  test('删除 completed 目标 → 拒绝', async ({ request }) => {
    const { token } = await registerAndLogin(request, 'goal_del_comp');

    const resp = await createGoal(request, {
      title: '已完成目标',
      metric_type: 'count',
      target_value: 1,
    }, token);
    const goal = await resp.json();

    await updateGoal(request, goal.id, { status: 'completed' }, token);

    const delResp = await deleteGoal(request, goal.id, token);
    expect(delResp.status()).toBe(400);
  });

  // ========================
  // 边界: tag_auto 必填校验
  // ========================

  test('tag_auto 缺少 auto_tags → 422', async ({ request }) => {
    const { token } = await registerAndLogin(request, 'goal_tag_val');

    const resp = await createGoal(request, {
      title: '缺少 auto_tags',
      metric_type: 'tag_auto',
      target_value: 5,
    }, token);
    expect(resp.status()).toBe(422);
  });

  // ========================
  // 边界: checklist 缺少 checklist_items
  // ========================

  test('checklist 缺少 checklist_items → 422', async ({ request }) => {
    const { token } = await registerAndLogin(request, 'goal_cl_val');

    const resp = await createGoal(request, {
      title: '缺少 checklist_items',
      metric_type: 'checklist',
      target_value: 2,
    }, token);
    expect(resp.status()).toBe(422);
  });

  // ========================
  // 异常: 不存在 goal_id → 404
  // ========================

  test('不存在 goal_id → 404', async ({ request }) => {
    const { token } = await registerAndLogin(request, 'goal_404');

    const fakeId = 'nonexistent_goal_id_12345';
    const detailResp = await getGoal(request, fakeId, token);
    expect(detailResp.status()).toBe(404);

    const updateResp = await updateGoal(request, fakeId, { title: '不存在' }, token);
    expect(updateResp.status()).toBe(404);

    const delResp = await deleteGoal(request, fakeId, token);
    expect(delResp.status()).toBe(404);
  });

  // ========================
  // 异常: 缺少必填字段 → 422
  // ========================

  test('缺少 title → 422', async ({ request }) => {
    const { token } = await registerAndLogin(request, 'goal_no_title');

    const resp = await createGoal(request, {
      metric_type: 'count',
      target_value: 1,
    } as any, token);
    expect(resp.status()).toBe(422);
  });

  // ========================
  // 异常: 重复关联 → 409
  // ========================

  test('重复关联同一条目 → 409', async ({ request }) => {
    const { token } = await registerAndLogin(request, 'goal_dup_link');

    const goalResp = await createGoal(request, {
      title: '重复关联测试',
      metric_type: 'count',
      target_value: 5,
    }, token);
    const goal = await goalResp.json();

    const entry = await createEntry(request, {
      type: 'task',
      title: '重复关联条目',
    }, token);

    // 第一次关联
    const linkResp1 = await linkEntry(request, goal.id, entry.id, token);
    expect(linkResp1.status()).toBe(201);

    // 第二次关联同一条目
    const linkResp2 = await linkEntry(request, goal.id, entry.id, token);
    expect(linkResp2.status()).toBe(409);
  });
});
