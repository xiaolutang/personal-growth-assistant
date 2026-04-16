import { APIRequestContext, expect } from '@playwright/test';

/**
 * API 辅助函数
 *
 * 封装条目 CRUD 操作，所有调用走前端 vite proxy（/api/* → 后端）。
 * 需要传入已认证的 APIRequestContext（带 Authorization header）。
 */

export interface CreateEntryParams {
  type: string;
  title: string;
  content?: string;
  status?: string;
  tags?: string[];
}

/** 创建带认证头的请求选项 */
function authHeaders(token?: string): Record<string, string> {
  if (!token) return {};
  return { Authorization: `Bearer ${token}` };
}

/**
 * 创建条目（任务/笔记/灵感）
 */
export async function createEntry(
  request: APIRequestContext,
  params: CreateEntryParams,
  token?: string
) {
  const resp = await request.post('/api/entries', {
    headers: authHeaders(token),
    data: {
      type: params.type,
      title: params.title,
      content: params.content || '',
      status: params.status || 'pending',
      tags: params.tags || [],
    },
  });
  expect(resp.ok()).toBeTruthy();
  return resp.json();
}

/**
 * 获取条目列表
 */
export async function listEntries(
  request: APIRequestContext,
  token?: string,
  type?: string
) {
  const url = type ? `/api/entries?type=${type}` : '/api/entries';
  const resp = await request.get(url, {
    headers: authHeaders(token),
  });
  expect(resp.ok()).toBeTruthy();
  return resp.json();
}

/**
 * 获取单个条目
 */
export async function getEntry(
  request: APIRequestContext,
  id: string,
  token?: string
) {
  const resp = await request.get(`/api/entries/${id}`, {
    headers: authHeaders(token),
  });
  expect(resp.ok()).toBeTruthy();
  return resp.json();
}

/**
 * 更新条目
 */
export async function updateEntry(
  request: APIRequestContext,
  id: string,
  data: Record<string, unknown>,
  token?: string
) {
  const resp = await request.put(`/api/entries/${id}`, {
    headers: authHeaders(token),
    data,
  });
  expect(resp.ok()).toBeTruthy();
  return resp.json();
}

/**
 * 删除条目
 */
export async function deleteEntry(
  request: APIRequestContext,
  id: string,
  token?: string
) {
  const resp = await request.delete(`/api/entries/${id}`, {
    headers: authHeaders(token),
  });
  expect(resp.ok()).toBeTruthy();
}

/**
 * 搜索条目
 */
export async function searchEntries(
  request: APIRequestContext,
  query: string,
  token?: string,
  limit = 10
) {
  const resp = await request.post('/api/search', {
    headers: authHeaders(token),
    data: { query, limit },
  });
  expect(resp.ok()).toBeTruthy();
  return resp.json();
}
