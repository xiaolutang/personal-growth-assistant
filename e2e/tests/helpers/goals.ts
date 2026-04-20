import { APIRequestContext } from '@playwright/test';

/**
 * Goals API 辅助函数
 *
 * 封装目标管理 CRUD 操作，所有调用走前端 vite proxy（/api/* → 后端）。
 * 需要传入已认证的 APIRequestContext（带 Authorization header）。
 */

/** 创建带认证头的请求选项 */
function authHeaders(token?: string): Record<string, string> {
  if (!token) return {};
  return { Authorization: `Bearer ${token}` };
}

export type MetricType = 'count' | 'checklist' | 'tag_auto';

export interface CreateGoalParams {
  title: string;
  metric_type: MetricType;
  target_value: number;
  auto_tags?: string[];
  checklist_items?: string[];
  start_date?: string;
  end_date?: string;
  description?: string;
}

/**
 * 创建目标
 * POST /api/goals
 */
export async function createGoal(
  request: APIRequestContext,
  params: CreateGoalParams,
  token?: string
) {
  const resp = await request.post('/api/goals', {
    headers: authHeaders(token),
    data: params,
  });
  return resp;
}

/**
 * 列出目标
 * GET /api/goals?status=active&limit=20
 */
export async function listGoals(
  request: APIRequestContext,
  token?: string,
  options?: { status?: 'active' | 'completed' | 'abandoned'; limit?: number }
) {
  const params = new URLSearchParams();
  if (options?.status) params.set('status', options.status);
  if (options?.limit) params.set('limit', String(options.limit));
  const qs = params.toString();
  const url = qs ? `/api/goals?${qs}` : '/api/goals';

  const resp = await request.get(url, {
    headers: authHeaders(token),
  });
  return resp;
}

/**
 * 获取目标详情（含 linked_entries_count）
 * GET /api/goals/{id}
 */
export async function getGoal(
  request: APIRequestContext,
  goalId: string,
  token?: string
) {
  const resp = await request.get(`/api/goals/${encodeURIComponent(goalId)}`, {
    headers: authHeaders(token),
  });
  return resp;
}

/**
 * 更新目标
 * PUT /api/goals/{id}
 */
export async function updateGoal(
  request: APIRequestContext,
  goalId: string,
  data: Record<string, unknown>,
  token?: string
) {
  const resp = await request.put(`/api/goals/${encodeURIComponent(goalId)}`, {
    headers: authHeaders(token),
    data,
  });
  return resp;
}

/**
 * 删除目标（仅 abandoned 可删）
 * DELETE /api/goals/{id}
 */
export async function deleteGoal(
  request: APIRequestContext,
  goalId: string,
  token?: string
) {
  const resp = await request.delete(`/api/goals/${encodeURIComponent(goalId)}`, {
    headers: authHeaders(token),
  });
  return resp;
}

/**
 * 关联条目到目标
 * POST /api/goals/{id}/entries
 */
export async function linkEntry(
  request: APIRequestContext,
  goalId: string,
  entryId: string,
  token?: string
) {
  const resp = await request.post(`/api/goals/${encodeURIComponent(goalId)}/entries`, {
    headers: authHeaders(token),
    data: { entry_id: entryId },
  });
  return resp;
}

/**
 * 取消关联条目
 * DELETE /api/goals/{id}/entries/{entry_id}
 */
export async function unlinkEntry(
  request: APIRequestContext,
  goalId: string,
  entryId: string,
  token?: string
) {
  const resp = await request.delete(`/api/goals/${encodeURIComponent(goalId)}/entries/${encodeURIComponent(entryId)}`, {
    headers: authHeaders(token),
  });
  return resp;
}

/**
 * 获取目标关联的条目列表
 * GET /api/goals/{id}/entries
 */
export async function listGoalEntries(
  request: APIRequestContext,
  goalId: string,
  token?: string
) {
  const resp = await request.get(`/api/goals/${encodeURIComponent(goalId)}/entries`, {
    headers: authHeaders(token),
  });
  return resp;
}

/**
 * 切换检查清单项
 * PATCH /api/goals/{id}/checklist/{item_id}
 */
export async function toggleChecklist(
  request: APIRequestContext,
  goalId: string,
  itemId: string,
  token?: string
) {
  const resp = await request.patch(`/api/goals/${encodeURIComponent(goalId)}/checklist/${encodeURIComponent(itemId)}`, {
    headers: authHeaders(token),
  });
  return resp;
}

/**
 * 获取进度概览
 * GET /api/goals/progress-summary?period=weekly
 */
export async function getProgressSummary(
  request: APIRequestContext,
  token?: string,
  period?: string
) {
  const params = new URLSearchParams();
  if (period) params.set('period', period);
  const qs = params.toString();
  const url = qs ? `/api/goals/progress-summary?${qs}` : '/api/goals/progress-summary';

  const resp = await request.get(url, {
    headers: authHeaders(token),
  });
  return resp;
}
