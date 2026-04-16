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
import { authFetch, buildAuthHeaders } from "@/lib/authFetch";
import createClient from "openapi-fetch";
import type { paths, components } from "@/types/api.generated";

// === 类型安全的 OpenAPI client ===
const client = createClient<paths>({
  baseUrl: API_BASE,
  fetch: async (request) => authFetch(request),
});

/**
 * 处理 openapi-fetch 返回值，统一错误处理
 * 与 handleApiResponse 保持一致的错误抛出行为
 */
function handleOpenApiResponse<T>(data: T | undefined, error: unknown, response: Response): T {
  if (error !== undefined && error !== null) {
    const errorObj = error as { detail?: string; message?: string };
    const message = errorObj.detail || errorObj.message || `HTTP ${response.status}`;
    throw new ApiError(response.status, message, error);
  }
  return data as T;
}

// === 项目进度响应类型 ===
export interface ProjectProgressResponse {
  project_id: string;
  total_tasks: number;
  completed_tasks: number;
  progress_percentage: number;
  status_distribution: Record<string, number>;
}

export type FeedbackSeverity = "low" | "medium" | "high" | "critical";

export interface FeedbackPayload {
  title: string;
  description?: string;
  severity: FeedbackSeverity;
}

export interface FeedbackItem {
  id: number;
  title: string;
  severity: string;
  status: string;
  log_service_issue_id: number | null;
  created_at: string;
}

export interface FeedbackListResponse {
  items: FeedbackItem[];
  total: number;
}

export interface FeedbackSubmitResponse {
  success: boolean;
  feedback: FeedbackItem;
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
  const { data, error, response } = await client.GET("/entries", {
    params: {
      query: {
        type: params?.type,
        status: params?.status,
        parent_id: params?.parent_id,
        tags: params?.tags && params.tags.length > 0 ? params.tags.join(",") : undefined,
        start_date: params?.start_date,
        end_date: params?.end_date,
        limit: params?.limit,
      },
    },
    fetchOptions: {
      cache: 'no-store',  // 禁用缓存，确保获取最新数据
    },
  });

  handleOpenApiResponse(data, error, response);

  // api.generated.ts 的 EntryListResponse 多了 total 字段，适配为现有 EntryListResponse
  return { entries: (data as components["schemas"]["EntryListResponse"])?.entries ?? [] } as EntryListResponse;
}

/**
 * 获取单个条目
 */
export async function getEntry(id: string): Promise<Task> {
  const { data, error, response } = await client.GET("/entries/{entry_id}", {
    params: { path: { entry_id: id } },
  });
  return handleOpenApiResponse<Task>(data as Task | undefined, error, response);
}

/**
 * 创建条目
 */
export async function createEntry(data: EntryCreate): Promise<Task> {
  // EntryCreate.type 映射为 api.generated.ts EntryCreate.category
  const body = { ...data, category: data.type };
  const { data: responseData, error, response } = await client.POST("/entries", {
    body: body as unknown as components["schemas"]["EntryCreate"],
  });
  return handleOpenApiResponse<Task>(responseData as Task | undefined, error, response);
}

/**
 * 更新条目
 */
export async function updateEntry(id: string, data: EntryUpdate): Promise<{ success: boolean; message: string }> {
  const { data: responseData, error, response } = await client.PUT("/entries/{entry_id}", {
    params: { path: { entry_id: id } },
    body: data as unknown as components["schemas"]["EntryUpdate"],
  });
  return handleOpenApiResponse<{ success: boolean; message: string }>(
    responseData as { success: boolean; message: string } | undefined,
    error,
    response,
  );
}

/**
 * 删除条目
 */
export async function deleteEntry(id: string): Promise<{ success: boolean; message: string }> {
  const { data, error, response } = await client.DELETE("/entries/{entry_id}", {
    params: { path: { entry_id: id } },
  });
  return handleOpenApiResponse<{ success: boolean; message: string }>(
    data as { success: boolean; message: string } | undefined,
    error,
    response,
  );
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
    headers: buildAuthHeaders({
      headers: { "Content-Type": "application/json" },
    }),
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
  const response = await fetch(`${API_BASE}/entries/search/query?q=${encodeURIComponent(query)}&limit=${limit}`, {
    headers: buildAuthHeaders(),
  });

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
  const response = await fetch(`${API_BASE}/knowledge-graph/${encodeURIComponent(concept)}?depth=${depth}`, {
    headers: buildAuthHeaders(),
  });
  return handleApiResponse<KnowledgeGraphResponse>(response);
}

/**
 * 获取相关概念
 */
export async function getRelatedConcepts(concept: string): Promise<RelatedConceptsResponse> {
  const response = await fetch(`${API_BASE}/related-concepts/${encodeURIComponent(concept)}`, {
    headers: buildAuthHeaders(),
  });
  return handleApiResponse<RelatedConceptsResponse>(response);
}

// === 全局图谱 API ===

export interface MapNode {
  id: string;
  name: string;
  category: string | null;
  mastery: "new" | "beginner" | "intermediate" | "advanced";
  entry_count: number;
}

export interface MapEdge {
  source: string;
  target: string;
  relationship: string;
}

export interface KnowledgeMapResponse {
  nodes: MapNode[];
  edges: MapEdge[];
}

export interface ConceptStatsResponse {
  concept_count: number;
  relation_count: number;
  category_distribution: Record<string, number>;
  top_concepts: Array<{ name: string; entry_count: number; category: string | null }>;
}

export async function getKnowledgeMap(
  depth: number = 2,
  view: string = "domain"
): Promise<KnowledgeMapResponse> {
  const response = await fetch(`${API_BASE}/knowledge-map?depth=${depth}&view=${view}`, {
    headers: buildAuthHeaders(),
  });
  return handleApiResponse<KnowledgeMapResponse>(response);
}

export async function getKnowledgeStats(): Promise<ConceptStatsResponse> {
  const response = await fetch(`${API_BASE}/knowledge/stats`, {
    headers: buildAuthHeaders(),
  });
  return handleApiResponse<ConceptStatsResponse>(response);
}

// === 解析 API (旧接口) ===

/**
 * 解析自然语言 (SSE 流式)
 */
export async function parseText(text: string, sessionId?: string): Promise<Response> {
  const response = await fetch(`${API_BASE}/parse`, {
    method: "POST",
    headers: buildAuthHeaders({
      headers: { "Content-Type": "application/json" },
    }),
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
    headers: buildAuthHeaders(),
  });
  await handleApiResponse<void>(response as any);
}

// === 项目进度 API ===

/**
 * 获取项目进度
 */
export async function getProjectProgress(projectId: string): Promise<ProjectProgressResponse> {
  const { data, error, response } = await client.GET("/entries/{entry_id}/progress", {
    params: { path: { entry_id: projectId } },
  });
  return handleOpenApiResponse<ProjectProgressResponse>(
    data as ProjectProgressResponse | undefined,
    error,
    response,
  );
}

/**
 * 提交用户反馈
 */
export async function submitFeedback(payload: FeedbackPayload): Promise<FeedbackSubmitResponse> {
  const response = await fetch(`${API_BASE}/feedback`, {
    method: "POST",
    headers: buildAuthHeaders({
      headers: { "Content-Type": "application/json" },
    }),
    body: JSON.stringify(payload),
  });
  return handleApiResponse<FeedbackSubmitResponse>(response);
}

/**
 * 获取反馈列表
 */
export async function getFeedbackList(): Promise<FeedbackListResponse> {
  const response = await fetch(`${API_BASE}/feedback`, {
    headers: buildAuthHeaders(),
  });
  return handleApiResponse<FeedbackListResponse>(response);
}

/**
 * 获取单条反馈详情
 */
export async function getFeedbackDetail(id: number): Promise<FeedbackItem> {
  const response = await fetch(`${API_BASE}/feedback/${id}`, {
    headers: buildAuthHeaders(),
  });
  return handleApiResponse<FeedbackItem>(response);
}

// === AI 对话 API ===

/**
 * AI 对话页面上下文
 */
export interface AIChatContext {
  page?: string;
  selected_items?: string[];
  filters?: Record<string, string>;
  page_data?: Record<string, string | number>;
  messages?: Array<{ role: string; content: string }>;
}

/**
 * 发送 AI 对话消息（SSE 流式响应）
 * 返回原始 Response 对象，调用方自行读取 ReadableStream
 */
export async function sendAIChat(
  message: string,
  context?: AIChatContext,
): Promise<Response> {
  const response = await fetch(`${API_BASE}/ai/chat`, {
    method: "POST",
    headers: buildAuthHeaders({
      headers: { "Content-Type": "application/json" },
    }),
    body: JSON.stringify({ message, context }),
  });
  if (!response.ok) {
    throw new ApiError(response.status, `AI Chat error: ${response.status}`);
  }
  return response;
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
    headers: buildAuthHeaders({
      headers: { "Content-Type": "application/json" },
    }),
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

// === 回顾趋势 API ===

export interface TrendPeriod {
  date: string;
  total: number;
  completed: number;
  completion_rate: number;
  notes_count: number;
}

export interface ReviewTrendResponse {
  periods: TrendPeriod[];
}

/**
 * 获取回顾趋势数据
 * @param period - "daily" | "weekly"
 * @param count - daily 时传 days（默认 7），weekly 时传 weeks（默认 8）
 */
export async function getReviewTrend(
  period: "daily" | "weekly",
  count?: number
): Promise<ReviewTrendResponse> {
  const params = new URLSearchParams({ period });
  if (period === "daily") {
    params.set("days", String(count ?? 7));
  } else {
    params.set("weeks", String(count ?? 8));
  }
  const response = await fetch(`${API_BASE}/review/trend?${params}`, {
    headers: buildAuthHeaders(),
  });
  return handleApiResponse<ReviewTrendResponse>(response);
}

// === 知识热力图 API ===

export interface HeatmapItem {
  concept: string;
  mastery: "new" | "beginner" | "intermediate" | "advanced";
  entry_count: number;
  category: string | null;
}

export interface HeatmapResponse {
  items: HeatmapItem[];
}

export interface GrowthCurvePoint {
  week: string;
  total_concepts: number;
  advanced_count: number;
  intermediate_count: number;
  beginner_count: number;
}

export interface GrowthCurveResponse {
  points: GrowthCurvePoint[];
}

export async function getKnowledgeHeatmap(): Promise<HeatmapResponse> {
  const response = await fetch(`${API_BASE}/review/knowledge-heatmap`, {
    headers: buildAuthHeaders(),
  });
  return handleApiResponse<HeatmapResponse>(response);
}

export async function getGrowthCurve(weeks: number = 8): Promise<GrowthCurveResponse> {
  const response = await fetch(`${API_BASE}/review/growth-curve?weeks=${weeks}`, {
    headers: buildAuthHeaders(),
  });
  return handleApiResponse<GrowthCurveResponse>(response);
}

// === AI 晨报 ===

export interface MorningDigestTodo {
  id: string;
  title: string;
  priority: string;
  planned_date: string | null;
}

export interface MorningDigestOverdue {
  id: string;
  title: string;
  priority: string;
  planned_date: string | null;
}

export interface MorningDigestStaleInbox {
  id: string;
  title: string;
  created_at: string;
}

export interface MorningDigestWeeklySummary {
  new_concepts: string[];
  entries_count: number;
}

export interface DailyFocus {
  title: string;
  description: string;
  target_entry_id: string | null;
}

export interface MorningDigestResponse {
  date: string;
  ai_suggestion: string;
  todos: MorningDigestTodo[];
  overdue: MorningDigestOverdue[];
  stale_inbox: MorningDigestStaleInbox[];
  weekly_summary: MorningDigestWeeklySummary;
  learning_streak?: number;
  daily_focus?: DailyFocus | null;
  pattern_insights?: string[];
}

export async function getMorningDigest(): Promise<MorningDigestResponse> {
  const response = await fetch(`${API_BASE}/review/morning-digest`, {
    headers: buildAuthHeaders(),
  });
  return handleApiResponse<MorningDigestResponse>(response);
}

// 导出错误类供外部使用
export { ApiError } from "@/lib/errors";

/**
 * 导出条目 — markdown (zip) 或 json
 */
export interface ExportOptions {
  format: "markdown" | "json";
  type?: string;
  startDate?: string;
  endDate?: string;
}

export async function exportEntries(options: ExportOptions): Promise<Blob> {
  const params = new URLSearchParams();
  params.set("format", options.format);
  if (options.type) params.set("type", options.type);
  if (options.startDate) params.set("start_date", options.startDate);
  if (options.endDate) params.set("end_date", options.endDate);

  const response = await fetch(`${API_BASE}/entries/export?${params.toString()}`, {
    headers: buildAuthHeaders(),
  });
  if (!response.ok) {
    throw new Error(`导出失败: ${response.status}`);
  }
  return response.blob();
}

/**
 * 获取条目的关联推荐
 */
export interface RelatedEntry {
  id: string;
  title: string;
  category: string;
  relevance_reason: string;
}

export async function getRelatedEntries(entryId: string): Promise<RelatedEntry[]> {
  const response = await fetch(`${API_BASE}/entries/${encodeURIComponent(entryId)}/related`, {
    headers: buildAuthHeaders(),
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch related entries: ${response.status}`);
  }
  const data = await response.json();
  return data.related ?? [];
}

// === AI 条目摘要 API ===

export interface EntrySummaryResponse {
  summary: string | null;
  generated_at: string | null;
  cached: boolean;
}

/**
 * 生成/获取条目的 AI 摘要
 * POST /entries/{id}/ai-summary
 */
export async function generateEntrySummary(entryId: string): Promise<EntrySummaryResponse> {
  const response = await fetch(`${API_BASE}/entries/${encodeURIComponent(entryId)}/ai-summary`, {
    method: "POST",
    headers: buildAuthHeaders({
      headers: { "Content-Type": "application/json" },
    }),
  });
  return handleApiResponse<EntrySummaryResponse>(response);
}

// === 通知 API ===

export interface NotificationItem {
  id: string;
  type: string;
  title: string;
  message: string;
  ref_id: string | null;
  created_at: string;
  dismissed: boolean;
}

export interface NotificationResponse {
  items: NotificationItem[];
  unread_count: number;
}

export interface NotificationPreferences {
  overdue_task_enabled: boolean;
  stale_inbox_enabled: boolean;
  review_prompt_enabled: boolean;
}

export async function getNotifications(): Promise<NotificationResponse> {
  const response = await fetch(`${API_BASE}/notifications`, {
    headers: buildAuthHeaders(),
  });
  return handleApiResponse<NotificationResponse>(response);
}

export async function dismissNotification(id: string): Promise<void> {
  const response = await fetch(`${API_BASE}/notifications/${encodeURIComponent(id)}/dismiss`, {
    method: "POST",
    headers: buildAuthHeaders(),
  });
  if (!response.ok) throw new ApiError(response.status, `dismiss failed: ${response.status}`);
}

export async function getNotificationPreferences(): Promise<NotificationPreferences> {
  const response = await fetch(`${API_BASE}/notification-preferences`, {
    headers: buildAuthHeaders(),
  });
  return handleApiResponse<NotificationPreferences>(response);
}

export async function updateNotificationPreferences(prefs: NotificationPreferences): Promise<NotificationPreferences> {
  const response = await fetch(`${API_BASE}/notification-preferences`, {
    method: "PUT",
    headers: { ...buildAuthHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify(prefs),
  });
  return handleApiResponse<NotificationPreferences>(response);
}

// === 知识图谱增强 API (F27) ===

export interface KnowledgeSearchItem {
  name: string;
  entry_count: number;
  mastery: "new" | "beginner" | "intermediate" | "advanced" | null;
}

export interface KnowledgeSearchResponse {
  items: KnowledgeSearchItem[];
}

export interface ConceptTimelineEntry {
  id: string;
  title: string;
  type: string;
}

export interface ConceptTimelineDay {
  date: string;
  entries: ConceptTimelineEntry[];
}

export interface ConceptTimelineResponse {
  concept: string;
  items: ConceptTimelineDay[];
}

export interface MasteryDistributionResponse {
  new: number;
  beginner: number;
  intermediate: number;
  advanced: number;
  total: number;
}

/**
 * 搜索知识概念
 */
export async function getKnowledgeSearch(query: string, limit?: number): Promise<KnowledgeSearchResponse> {
  const params = new URLSearchParams({ q: query });
  if (limit !== undefined) params.set("limit", String(limit));
  const response = await fetch(`${API_BASE}/knowledge/search?${params}`, {
    headers: buildAuthHeaders(),
  });
  return handleApiResponse<KnowledgeSearchResponse>(response);
}

/**
 * 获取概念学习时间线
 */
export async function getConceptTimeline(concept: string, days?: number): Promise<ConceptTimelineResponse> {
  const params = new URLSearchParams();
  if (days !== undefined) params.set("days", String(days));
  const qs = params.toString();
  const url = `${API_BASE}/knowledge/concepts/${encodeURIComponent(concept)}/timeline${qs ? `?${qs}` : ""}`;
  const response = await fetch(url, {
    headers: buildAuthHeaders(),
  });
  return handleApiResponse<ConceptTimelineResponse>(response);
}

/**
 * 获取掌握度分布
 */
export async function getMasteryDistribution(): Promise<MasteryDistributionResponse> {
  const response = await fetch(`${API_BASE}/knowledge/mastery-distribution`, {
    headers: buildAuthHeaders(),
  });
  return handleApiResponse<MasteryDistributionResponse>(response);
}

// === 条目手动关联 API (F32) ===

export type RelationType = "related" | "depends_on" | "derived_from" | "references";

export interface EntryLinkTarget {
  id: string;
  title: string;
  category: string;
}

export interface EntryLinkItem {
  id: string;
  target_id: string;
  target_entry: EntryLinkTarget;
  relation_type: RelationType;
  direction: "out" | "in";
  created_at: string;
}

export interface EntryLinkListResponse {
  links: EntryLinkItem[];
}

export interface EntryLinkCreateResponse {
  id: string;
  source_id: string;
  target_id: string;
  relation_type: RelationType;
  created_at: string;
  target_entry: EntryLinkTarget;
}

export async function getEntryLinks(entryId: string, direction?: "out" | "in" | "both"): Promise<EntryLinkListResponse> {
  const params = new URLSearchParams();
  if (direction) params.set("direction", direction);
  const qs = params.toString();
  const url = `${API_BASE}/entries/${encodeURIComponent(entryId)}/links${qs ? `?${qs}` : ""}`;
  const response = await fetch(url, { headers: buildAuthHeaders() });
  return handleApiResponse<EntryLinkListResponse>(response);
}

export async function createEntryLink(
  entryId: string,
  targetId: string,
  relationType: RelationType
): Promise<EntryLinkCreateResponse> {
  const response = await fetch(`${API_BASE}/entries/${encodeURIComponent(entryId)}/links`, {
    method: "POST",
    headers: buildAuthHeaders({ headers: { "Content-Type": "application/json" } }),
    body: JSON.stringify({ target_id: targetId, relation_type: relationType }),
  });
  return handleApiResponse<EntryLinkCreateResponse>(response);
}

export async function deleteEntryLink(entryId: string, linkId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/entries/${encodeURIComponent(entryId)}/links/${encodeURIComponent(linkId)}`, {
    method: "DELETE",
    headers: buildAuthHeaders(),
  });
  if (!response.ok) throw new ApiError(response.status, `删除关联失败: ${response.status}`);
}

// === 条目知识上下文 API (F31) ===

export interface KnowledgeContextNode {
  id: string;
  name: string;
  category: string | null;
  mastery: "new" | "beginner" | "intermediate" | "advanced";
  entry_count: number;
}

export interface KnowledgeContextEdge {
  source: string;
  target: string;
  relationship: string;
}

export interface KnowledgeContextResponse {
  nodes: KnowledgeContextNode[];
  edges: KnowledgeContextEdge[];
  center_concepts: string[];
}

export async function getKnowledgeContext(entryId: string): Promise<KnowledgeContextResponse> {
  const response = await fetch(`${API_BASE}/entries/${encodeURIComponent(entryId)}/knowledge-context`, {
    headers: buildAuthHeaders(),
  });
  return handleApiResponse<KnowledgeContextResponse>(response);
}

// === 活动热力图 API ===

export interface ActivityHeatmapItem {
  date: string;
  count: number;
}

export interface ActivityHeatmapResponse {
  year: number;
  items: ActivityHeatmapItem[];
}

export async function getActivityHeatmap(year: number): Promise<ActivityHeatmapResponse> {
  const response = await fetch(`${API_BASE}/review/activity-heatmap?year=${year}`, {
    headers: buildAuthHeaders(),
  });
  return handleApiResponse<ActivityHeatmapResponse>(response);
}

// === Goals API ===

export type MetricType = "count" | "checklist" | "tag_auto";
export type GoalStatus = "active" | "completed" | "abandoned";

export interface ChecklistItem {
  id: string;
  title: string;
  checked: boolean;
}

export interface Goal {
  id: string;
  title: string;
  description: string | null;
  metric_type: MetricType;
  target_value: number;
  current_value: number;
  progress_percentage: number;
  status: GoalStatus;
  start_date: string | null;
  end_date: string | null;
  auto_tags: string[] | null;
  checklist_items: ChecklistItem[] | null;
  linked_entries_count: number;
  created_at: string;
  updated_at: string;
}

export interface GoalListResponse {
  goals: Goal[];
}

export interface GoalDetailResponse extends Goal {
  entries?: GoalEntry[];
}

export interface GoalEntry {
  id: string;
  goal_id: string;
  entry_id: string;
  created_at: string;
  entry: {
    id: string;
    title: string | null;
    status: string | null;
    category: string | null;
    created_at: string | null;
  };
}

export interface GoalEntryListResponse {
  entries: GoalEntry[];
}

export interface ProgressItem {
  id: string;
  title: string;
  progress_percentage: number;
  progress_delta: number | null;
}

export interface ProgressSummaryResponse {
  active_count: number;
  completed_count: number;
  goals: ProgressItem[];
}

export async function getGoals(status?: string): Promise<GoalListResponse> {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  const qs = params.toString();
  const response = await fetch(`${API_BASE}/goals${qs ? `?${qs}` : ""}`, {
    headers: buildAuthHeaders(),
  });
  return handleApiResponse<GoalListResponse>(response);
}

export async function getGoal(goalId: string): Promise<GoalDetailResponse> {
  const response = await fetch(`${API_BASE}/goals/${encodeURIComponent(goalId)}`, {
    headers: buildAuthHeaders(),
  });
  return handleApiResponse<GoalDetailResponse>(response);
}

export async function createGoal(data: {
  title: string;
  description?: string;
  metric_type: MetricType;
  target_value: number;
  start_date?: string;
  end_date?: string;
  auto_tags?: string[];
  checklist_items?: string[];
}): Promise<Goal> {
  const response = await fetch(`${API_BASE}/goals`, {
    method: "POST",
    headers: buildAuthHeaders({ headers: { "Content-Type": "application/json" } }),
    body: JSON.stringify(data),
  });
  return handleApiResponse<Goal>(response);
}

export async function updateGoal(goalId: string, data: {
  title?: string;
  description?: string;
  target_value?: number;
  status?: string;
  start_date?: string;
  end_date?: string;
}): Promise<Goal> {
  const response = await fetch(`${API_BASE}/goals/${encodeURIComponent(goalId)}`, {
    method: "PUT",
    headers: buildAuthHeaders({ headers: { "Content-Type": "application/json" } }),
    body: JSON.stringify(data),
  });
  return handleApiResponse<Goal>(response);
}

export async function deleteGoal(goalId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/goals/${encodeURIComponent(goalId)}`, {
    method: "DELETE",
    headers: buildAuthHeaders(),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new ApiError(response.status, data.detail || `删除失败: ${response.status}`);
  }
}

export async function linkGoalEntry(goalId: string, entryId: string): Promise<any> {
  const response = await fetch(`${API_BASE}/goals/${encodeURIComponent(goalId)}/entries`, {
    method: "POST",
    headers: buildAuthHeaders({ headers: { "Content-Type": "application/json" } }),
    body: JSON.stringify({ entry_id: entryId }),
  });
  return handleApiResponse<any>(response);
}

export async function unlinkGoalEntry(goalId: string, entryId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/goals/${encodeURIComponent(goalId)}/entries/${encodeURIComponent(entryId)}`, {
    method: "DELETE",
    headers: buildAuthHeaders(),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new ApiError(response.status, data.detail || `取消关联失败: ${response.status}`);
  }
}

export async function getGoalEntries(goalId: string): Promise<GoalEntryListResponse> {
  const response = await fetch(`${API_BASE}/goals/${encodeURIComponent(goalId)}/entries`, {
    headers: buildAuthHeaders(),
  });
  return handleApiResponse<GoalEntryListResponse>(response);
}

export async function toggleChecklistItem(goalId: string, itemId: string): Promise<Goal> {
  const response = await fetch(`${API_BASE}/goals/${encodeURIComponent(goalId)}/checklist/${encodeURIComponent(itemId)}`, {
    method: "PATCH",
    headers: buildAuthHeaders(),
  });
  return handleApiResponse<Goal>(response);
}

export async function getProgressSummary(period?: string): Promise<ProgressSummaryResponse> {
  const params = new URLSearchParams();
  if (period) params.set("period", period);
  const qs = params.toString();
  const response = await fetch(`${API_BASE}/goals/progress-summary${qs ? `?${qs}` : ""}`, {
    headers: buildAuthHeaders(),
  });
  return handleApiResponse<ProgressSummaryResponse>(response);
}
