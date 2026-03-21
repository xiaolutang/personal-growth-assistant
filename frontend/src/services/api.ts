import type {
  Task,
  EntryCreate,
  EntryUpdate,
  EntryListResponse,
  SearchResponse,
  SearchResult,
  KnowledgeGraphResponse,
  RelatedConceptsResponse,
} from "@/types/task";
import { API_BASE } from "@/config/api";
import { handleApiResponse, ApiError } from "@/lib/errors";

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
  tags?: string[];
  start_date?: string;
  end_date?: string;
  limit?: number;
}): Promise<EntryListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.type) searchParams.append("type", params.type);
  if (params?.status) searchParams.append("status", params.status);
  if (params?.parent_id) searchParams.append("parent_id", params.parent_id);
  if (params?.tags && params.tags.length > 0) {
    searchParams.append("tags", params.tags.join(","));
  }
  if (params?.start_date) searchParams.append("start_date", params.start_date);
  if (params?.end_date) searchParams.append("end_date", params.end_date);
  if (params?.limit) searchParams.append("limit", params.limit.toString());

  const response = await fetch(`${API_BASE}/entries?${searchParams.toString()}`, {
    cache: 'no-store',  // 禁用缓存，确保获取最新数据
  });
  return handleApiResponse<EntryListResponse>(response);
}

/**
 * 获取单个条目
 */
export async function getEntry(id: string): Promise<Task> {
  const response = await fetch(`${API_BASE}/entries/${id}`);
  return handleApiResponse<Task>(response);
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
  return handleApiResponse<Task>(response);
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
  return handleApiResponse<{ success: boolean; message: string }>(response);
}

/**
 * 删除条目
 */
export async function deleteEntry(id: string): Promise<{ success: boolean; message: string }> {
  const response = await fetch(`${API_BASE}/entries/${id}`, {
    method: "DELETE",
  });
  return handleApiResponse<{ success: boolean; message: string }>(response);
}

// === 搜索 API ===

// 使用 types/task.ts 中的 SearchResult 类型
type SearchResultItem = SearchResult;

/**
 * 归一化搜索结果项
 */
function normalizeSearchItem(e: any, defaultScore = 1): SearchResultItem {
  return {
    id: e.id,
    title: e.title,
    score: e.score ?? defaultScore,
    type: e.type ?? e.category,
    category: e.category ?? e.type ?? "note",
    status: e.status ?? "doing",
    tags: e.tags || [],
    created_at: e.created_at ?? "",
    file_path: e.file_path || "",
  };
}

/**
 * 向量搜索（Qdrant）
 */
async function vectorSearch(query: string, limit: number): Promise<SearchResponse> {
  const response = await fetch(`${API_BASE}/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, limit }),
  });

  if (!response.ok) {
    throw new ApiError(response.status, `Vector search failed: ${response.status}`);
  }

  const data = await response.json();
  return {
    results: data.results.map((e: any) => normalizeSearchItem(e)),
  };
}

/**
 * SQLite 全文搜索（FTS5）
 */
async function sqliteSearch(query: string, limit: number): Promise<SearchResponse> {
  const response = await fetch(
    `${API_BASE}/entries/search/query?q=${encodeURIComponent(query)}&limit=${limit}`
  );

  if (!response.ok) {
    throw new ApiError(response.status, `SQLite search failed: ${response.status}`);
  }

  const data = await response.json();
  return {
    results: data.entries.map((e: any) => normalizeSearchItem(e)),
  };
}

/**
 * SQLite 分数归一化
 */
function normalizeSqliteScore(score: number): number {
  return Math.min(1, Math.max(0, score));
}

/**
 * 合并向量搜索和全文搜索结果
 * 权重：向量 70% + BM25 30%
 */
function mergeSearchResults(
  vecResults: SearchResultItem[],
  sqlResults: SearchResultItem[],
  limit: number
): SearchResponse {
  const VECTOR_WEIGHT = 0.7;
  const SQLITE_WEIGHT = 0.3;

  // 用 Map 存储合并后的结果（按 id 去重）
  const merged = new Map<string, SearchResultItem>();

  // 添加向量搜索结果
  for (const item of vecResults) {
    merged.set(item.id, { ...item, score: item.score * VECTOR_WEIGHT });
  }

  // 合并 SQL 搜索结果
  for (const item of sqlResults) {
    if (merged.has(item.id)) {
      // 已存在，累加分数
      const existing = merged.get(item.id)!;
      existing.score += normalizeSqliteScore(item.score) * SQLITE_WEIGHT;
    } else {
      // 新增
      merged.set(item.id, {
        ...item,
        score: normalizeSqliteScore(item.score) * SQLITE_WEIGHT,
      });
    }
  }

  // 按分数排序，返回 top N
  const results = Array.from(merged.values())
    .sort((a, b) => b.score - a.score)
    .slice(0, limit);

  return { results };
}

/**
 * 混合搜索：并行执行向量搜索和全文搜索，合并结果
 * 权重：向量 70% + BM25 30%
 *
 * 优势：
 * - 向量搜索擅长语义理解（如 "mcp" 能找到相关概念）
 * - 全文搜索擅长精确匹配（如专有名词、代码）
 * - 并行执行 + 结果融合，取长补短
 */
export async function searchEntries(query: string, limit: number = 5): Promise<SearchResponse> {
  // 并行执行两个搜索
  const [vectorResults, sqliteResults] = await Promise.allSettled([
    vectorSearch(query, limit * 2), // 多取一些用于合并
    sqliteSearch(query, limit * 2),
  ]);

  // 提取成功的结果
  const vecHits = vectorResults.status === 'fulfilled' ? vectorResults.value.results : [];
  const sqlHits = sqliteResults.status === 'fulfilled' ? sqliteResults.value.results : [];

  // 如果两个都失败，抛出错误
  if (vecHits.length === 0 && sqlHits.length === 0) {
    // 尝试获取具体的错误信息
    const vecError = vectorResults.status === 'rejected' ? vectorResults.reason : null;
    const sqlError = sqliteResults.status === 'rejected' ? sqliteResults.reason : null;

    console.warn("Both search methods failed:", { vecError, sqlError });
    throw new Error("搜索服务暂时不可用，请稍后重试");
  }

  // 合并结果
  return mergeSearchResults(vecHits, sqlHits, limit);
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
  return handleApiResponse<KnowledgeGraphResponse>(response);
}

/**
 * 获取相关概念
 */
export async function getRelatedConcepts(concept: string): Promise<RelatedConceptsResponse> {
  const response = await fetch(
    `${API_BASE}/related-concepts/${encodeURIComponent(concept)}`
  );
  return handleApiResponse<RelatedConceptsResponse>(response);
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
    throw new ApiError(response.status, `Parse API error: ${response.status}`);
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
  await handleApiResponse<void>(response as any);
}

// === 项目进度 API ===

/**
 * 获取项目进度
 */
export async function getProjectProgress(projectId: string): Promise<ProjectProgressResponse> {
  const response = await fetch(`${API_BASE}/entries/${projectId}/progress`);
  return handleApiResponse<ProjectProgressResponse>(response);
}

// === 意图识别 API ===

import { detectIntent as detectIntentLocal, type Intent } from "@/lib/intentDetection";

export interface IntentResponse {
  intent: Intent;
  confidence: number;
  entities: Record<string, string>;
  query?: string;
  response_hint?: string;
}

/**
 * 检测用户输入的意图（调用后端 LLM，失败时回退到本地）
 */
export async function detectIntent(text: string): Promise<IntentResponse> {
  const response = await fetch(`${API_BASE}/intent`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });

  if (!response.ok) {
    // 如果后端 API 不可用，回退到本地检测
    console.warn("Intent API 不可用，回退到本地检测");
    return {
      intent: detectIntentLocal(text),
      confidence: 0.8,
      entities: {},
      query: text,
    };
  }

  return response.json();
}

// 导出错误类供外部使用
export { ApiError } from "@/lib/errors";
