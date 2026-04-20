import { APIRequestContext } from '@playwright/test';

/**
 * Export API 辅助函数
 *
 * 封装条目导出操作，所有调用走前端 vite proxy（/api/* → 后端）。
 * 需要传入已认证的 APIRequestContext（带 Authorization header）。
 */

export type ExportFormat = 'markdown' | 'json';
export type EntryCategory = 'task' | 'note' | 'inbox' | 'project' | 'decision' | 'reflection' | 'question';

export interface ExportParams {
  format: ExportFormat;
  type?: EntryCategory;
  start_date?: string;
  end_date?: string;
}

/** 创建带认证头的请求选项 */
function authHeaders(token?: string): Record<string, string> {
  if (!token) return {};
  return { Authorization: `Bearer ${token}` };
}

/**
 * 导出条目
 * GET /api/entries/export?format=json&type=task&start_date=2026-01-01&end_date=2026-12-31
 *
 * format=markdown 返回 application/zip（原始 Response）
 * format=json 返回 JSON 数组（原始 Response）
 */
export async function exportEntries(
  request: APIRequestContext,
  params: ExportParams,
  token?: string
) {
  const searchParams = new URLSearchParams();
  searchParams.set('format', params.format);
  if (params.type) searchParams.set('type', params.type);
  if (params.start_date) searchParams.set('start_date', params.start_date);
  if (params.end_date) searchParams.set('end_date', params.end_date);

  const resp = await request.get(`/api/entries/export?${searchParams.toString()}`, {
    headers: authHeaders(token),
  });
  return resp;
}
