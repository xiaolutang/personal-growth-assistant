import type {
  Task,
  EntryCreate,
  EntryUpdate,
  EntryListResponse,
  SearchResponse,
  KnowledgeGraphResponse,
  RelatedConceptsResponse,
} from "@/types/task";
import { API_BASE } from "@/config/api";

// === 项目进度响应类型 ===
export interface ProjectProgressResponse {
  project_id: string;
  total_tasks: number;
  completed_tasks: number;
  progress_percentage: number;
  status_distribution: Record<string, number>;
}

// === 条目管理 API ===

/**
 * 获取条目列表
 */
export async function getEntries(params?: {
  type?: string;
  status?: string;
  parent_id?: string;
  limit?: number;
}): Promise<EntryListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.type) searchParams.append("type", params.type);
  if (params?.status) searchParams.append("status", params.status);
  if (params?.parent_id) searchParams.append("parent_id", params.parent_id);
  if (params?.limit) searchParams.append("limit", params.limit.toString());

  const response = await fetch(`${API_BASE}/entries?${searchParams.toString()}`);
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  return response.json();
}

/**
 * 获取单个条目
 */
export async function getEntry(id: string): Promise<Task> {
  const response = await fetch(`${API_BASE}/entries/${id}`);
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  return response.json();
}

/**
 * 创建条目
 */
export async function createEntry(data: EntryCreate): Promise<Task> {
  const response = await fetch(`${API_BASE}/entries`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  return response.json();
}

/**
 * 更新条目
 */
export async function updateEntry(id: string, data: EntryUpdate): Promise<{ success: boolean; message: string }> {
  const response = await fetch(`${API_BASE}/entries/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  return response.json();
}

/**
 * 删除条目
 */
export async function deleteEntry(id: string): Promise<{ success: boolean; message: string }> {
  const response = await fetch(`${API_BASE}/entries/${id}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  return response.json();
}

// === 搜索 API ===

/**
 * 全文搜索条目（使用 SQLite FTS5）
 */
export async function searchEntries(query: string, limit: number = 5): Promise<SearchResponse> {
  const response = await fetch(
    `${API_BASE}/entries/search/query?q=${encodeURIComponent(query)}&limit=${limit}`
  );
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  const data = await response.json();
  // 转换为前端期望的格式
  return {
    results: data.entries.map((e: any) => ({
      id: e.id,
      title: e.title,
      score: 1, // SQLite 搜索没有分数，默认为 1
      type: e.category,
      tags: e.tags || [],
      file_path: e.file_path || "",
    })),
  };
}

// === 知识图谱 API ===

/**
 * 获取知识图谱
 */
export async function getKnowledgeGraph(
  concept: string,
  depth: number = 2
): Promise<KnowledgeGraphResponse> {
  const response = await fetch(
    `${API_BASE}/knowledge-graph/${encodeURIComponent(concept)}?depth=${depth}`
  );
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  return response.json();
}

/**
 * 获取相关概念
 */
export async function getRelatedConcepts(concept: string): Promise<RelatedConceptsResponse> {
  const response = await fetch(
    `${API_BASE}/related-concepts/${encodeURIComponent(concept)}`
  );
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  return response.json();
}

// === 解析 API (旧接口) ===

/**
 * 解析自然语言 (SSE 流式)
 */
export async function parseText(text: string, sessionId?: string): Promise<Response> {
  const response = await fetch(`${API_BASE}/parse`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, session_id: sessionId }),
  });
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  return response;
}

/**
 * 清空会话历史
 */
export async function clearSession(sessionId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/session/${sessionId}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
}

// === 项目进度 API ===

/**
 * 获取项目进度
 */
export async function getProjectProgress(projectId: string): Promise<ProjectProgressResponse> {
  const response = await fetch(`${API_BASE}/entries/${projectId}/progress`);
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  return response.json();
}
