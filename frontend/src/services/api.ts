import type {
  Task, EntryCreate, EntryUpdate, EntryListResponse,
  SearchResponse, SearchResult, KnowledgeGraphResponse,
} from "@/types/task";
import { API_BASE } from "@/config/api";
import { ApiError } from "@/lib/errors";
import { authFetch } from "@/lib/authFetch";
import createClient from "openapi-fetch";
import type { paths, components } from "@/types/api.generated";
import { detectIntent as detectIntentLocal } from "@/lib/intentDetection";
const client = createClient<paths>({
  baseUrl: API_BASE,
  fetch: async (request) => authFetch(request),
});

// === 类型别名：从 api.generated.ts 映射（保持导出名不变，调用者无感知） ===
type S = components["schemas"];
// 以下类型需手动定义（generated 中结构不同：optional 字段、unknown、宽泛 string 等）
export interface ProjectProgressResponse {
  project_id: string; total_tasks: number; completed_tasks: number;
  progress_percentage: number; status_distribution: Record<string, number>;
}
export type FeedbackSeverity = S["FeedbackRequest"]["severity"];
export type FeedbackPayload = Omit<S["FeedbackRequest"], "severity"> & { severity: FeedbackSeverity };
export type FeedbackItem = S["FeedbackItem"];
export type FeedbackListResponse = S["FeedbackListResponse"];
export type FeedbackSubmitResponse = S["FeedbackResponse"];
export type MapNode = S["MapNode"];
export type MapEdge = S["MapEdge"];
export type KnowledgeMapResponse = S["KnowledgeMapResponse"];
export interface ConceptStatsResponse {
  concept_count: number; relation_count: number;
  category_distribution: Record<string, number>;
  top_concepts: Array<{ name: string; entry_count: number; category: string | null }>;
}
export type TaskStats = S["TaskStats"];
export interface NoteStats { total: number; recent_titles: string[] }
export interface VsLastPeriod { delta_completion_rate: number | null; delta_total: number | null }
export interface DailyReport {
  date: string; task_stats: TaskStats; note_stats: NoteStats;
  completed_tasks: Array<{ id: string; title: string; status: string }>;
  ai_summary?: string | null;
}
export interface WeeklyReport {
  start_date: string; end_date: string; task_stats: TaskStats; note_stats: NoteStats;
  daily_breakdown: DailyBreakdown[]; ai_summary?: string | null; vs_last_week?: VsLastPeriod | null;
}
export interface MonthlyReport {
  month: string; task_stats: TaskStats; note_stats: NoteStats;
  weekly_breakdown: WeeklyBreakdown[]; ai_summary?: string | null; vs_last_month?: VsLastPeriod | null;
}
export type BehaviorPattern = S["BehaviorPattern"];
export type GrowthSuggestion = S["GrowthSuggestion"];
export type CapabilityChange = S["CapabilityChange"];
export interface DeepInsights {
  behavior_patterns: BehaviorPattern[];
  growth_suggestions: GrowthSuggestion[];
  capability_changes: CapabilityChange[];
}
export interface InsightsResponse {
  period: "weekly" | "monthly"; start_date: string; end_date: string;
  insights: DeepInsights; source: "llm" | "rule_based";
}
export type HeatmapItem = S["HeatmapItem"];
export type HeatmapResponse = S["HeatmapResponse"];
export type GrowthCurvePoint = S["GrowthCurvePoint"];
export type GrowthCurveResponse = S["GrowthCurveResponse"];
export type MorningDigestTodo = S["MorningDigestTodo"];
export type MorningDigestOverdue = S["MorningDigestOverdue"];
export type MorningDigestStaleInbox = S["MorningDigestStaleInbox"];
export type MorningDigestWeeklySummary = S["MorningDigestWeeklySummary"];
export type DailyFocus = S["DailyFocus"];
export interface MorningDigestResponse {
  date: string; ai_suggestion: string;
  todos: MorningDigestTodo[]; overdue: MorningDigestOverdue[]; stale_inbox: MorningDigestStaleInbox[];
  weekly_summary: MorningDigestWeeklySummary; learning_streak?: number;
  daily_focus?: DailyFocus | null; pattern_insights?: string[]; cached_at?: string | null;
}
export type EntrySummaryResponse = S["EntrySummaryResponse"];
export type NotificationPreferences = S["NotificationPreferences"];
export type CapabilityConcept = S["CapabilityConcept"];
export type CapabilityDomain = S["CapabilityDomain"];
export type CapabilityMapResponse = S["CapabilityMapResponse"];
export type ActivityHeatmapItem = S["ActivityHeatmapItem"];
export type ActivityHeatmapResponse = S["ActivityHeatmapResponse"];
export type ProgressItem = S["ProgressItem"];
export type ProgressSummaryResponse = S["ProgressSummaryResponse"];
export type FeedbackSyncResponse = S["FeedbackSyncResponse"];
export type RelatedEntry = S["RelatedEntry"];
export interface KnowledgeContextNode {
  id: string; name: string; category: string | null;
  mastery: "new" | "beginner" | "intermediate" | "advanced"; entry_count: number;
}
export type KnowledgeContextEdge = S["KnowledgeContextEdge"];
export interface KnowledgeContextResponse {
  nodes: KnowledgeContextNode[]; edges: KnowledgeContextEdge[]; center_concepts: string[];
}
export type EntryLinkItem = S["EntryLinkItem"];
export type EntryLinkListResponse = S["EntryLinkListResponse"];
export type MasteryDistributionResponse = S["MasteryDistributionResponse"];
export type ConceptTimelineResponse = S["ConceptTimelineResponse"];
export type RelationType = S["EntryLinkCreate"]["relation_type"];
export type EntryLinkTarget = S["LinkTargetEntry"];
export type EntryLinkCreateResponse = S["EntryLinkResponse"];
export type KnowledgeSearchItem = S["ConceptSearchItem"];
export type KnowledgeSearchResponse = S["ConceptSearchResponse"];
export type ConceptTimelineEntry = S["TimelineEntry"];
export type ConceptTimelineDay = S["TimelineDay"];
export type TrendPeriod = S["TrendPeriod"];
export interface ReviewTrendResponse { periods: TrendPeriod[] }
export type IntentResponse = S["IntentResponse"];
export type ChecklistItem = S["ChecklistItem"];
export interface Goal {
  id: string; title: string; description: string | null;
  metric_type: MetricType; target_value: number; current_value: number;
  progress_percentage: number; status: GoalStatus;
  start_date: string | null; end_date: string | null;
  auto_tags: string[] | null; checklist_items: ChecklistItem[] | null;
  linked_entries_count: number; created_at: string; updated_at: string;
}
export interface GoalDetailResponse extends Goal { entries?: GoalEntry[] }
export type GoalListResponse = { goals: Goal[] };
export type GoalEntry = S["GoalEntryResponse"];
export type GoalEntryListResponse = S["GoalEntryListResponse"];
export type MetricType = "count" | "checklist" | "tag_auto";
export type GoalStatus = "active" | "completed" | "abandoned";
// === 手动保留的类型（api.generated.ts 中不存在） ===
export interface SearchFilterOptions { startTime?: string; endTime?: string; tags?: string[] }
export interface AIChatContext {
  page?: string; is_new_user?: boolean; selected_items?: string[];
  filters?: Record<string, string>; page_data?: Record<string, string | number>;
  messages?: Array<{ role: string; content: string }>;
}
export interface ExportOptions { format: "markdown" | "json"; type?: string; startDate?: string; endDate?: string }
export interface DailyBreakdown { date: string; total: number; completed: number }
export interface WeeklyBreakdown { week: string; start_date: string; end_date: string; total: number; completed: number }
export interface NotificationItem {
  id: string; type: string; title: string; message: string;
  ref_id: string | null; created_at: string; dismissed: boolean;
}
export interface NotificationResponse { items: NotificationItem[]; unread_count: number }
// === 错误处理工具 ===
function handleOpenApiResponse<T>(data: T | undefined, error: unknown, response: Response): T {
  if (error !== undefined && error !== null) {
    const e = error as { detail?: string; message?: string };
    throw new ApiError(response.status, e.detail || e.message || `HTTP ${response.status}`, error);
  }
  return data as T;
}
// === 条目 CRUD ===
export async function getEntries(params?: {
  type?: string; status?: string; parent_id?: string; tags?: string[];
  start_date?: string; end_date?: string; limit?: number;
}): Promise<EntryListResponse> {
  const { data, error, response } = await client.GET("/entries", {
    params: { query: {
      type: params?.type, status: params?.status, parent_id: params?.parent_id,
      tags: params?.tags && params.tags.length > 0 ? params.tags.join(",") : undefined,
      start_date: params?.start_date, end_date: params?.end_date, limit: params?.limit,
    }},
    fetchOptions: { cache: 'no-store' },
  });
  handleOpenApiResponse(data, error, response);
  return { entries: (data as S["EntryListResponse"])?.entries ?? [] } as EntryListResponse;
}

export async function getEntry(id: string): Promise<Task> {
  const { data, error, response } = await client.GET("/entries/{entry_id}", { params: { path: { entry_id: id } } });
  return handleOpenApiResponse<Task>(data as Task | undefined, error, response);
}

export async function createEntry(data: EntryCreate): Promise<Task> {
  const { data: rd, error, response } = await client.POST("/entries", {
    body: { category: data.type, title: data.title, content: data.content ?? "", tags: data.tags,
      parent_id: data.parent_id ?? null, status: data.status ?? null, priority: data.priority ?? null,
      planned_date: data.planned_date ?? null, time_spent: data.time_spent },
  });
  return handleOpenApiResponse<Task>(rd as Task | undefined, error, response);
}

export async function updateEntry(id: string, data: EntryUpdate): Promise<{ success: boolean; message: string }> {
  const { data: rd, error, response } = await client.PUT("/entries/{entry_id}", {
    params: { path: { entry_id: id } },
    body: { title: data.title ?? null, content: data.content ?? null, category: data.category ?? null,
      status: data.status ?? null, priority: data.priority ?? null, tags: data.tags ?? null,
      parent_id: data.parent_id ?? null, planned_date: data.planned_date ?? null,
      time_spent: data.time_spent, completed_at: data.completed_at ?? null },
  });
  return handleOpenApiResponse<{ success: boolean; message: string }>(rd as { success: boolean; message: string } | undefined, error, response);
}

export async function deleteEntry(id: string): Promise<{ success: boolean; message: string }> {
  const { data, error, response } = await client.DELETE("/entries/{entry_id}", { params: { path: { entry_id: id } } });
  return handleOpenApiResponse<{ success: boolean; message: string }>(data as { success: boolean; message: string } | undefined, error, response);
}

// === 搜索 ===
type SearchResultItem = SearchResult;

function normalizeSearchItem(e: { id?: string; title?: string; score?: number; type?: string; category?: string; status?: string; tags?: string[]; created_at?: string; file_path?: string; content_snippet?: string }, defaultScore = 1): SearchResultItem {
  return { id: e.id ?? "", title: e.title ?? "", score: e.score ?? defaultScore,
    type: e.type ?? e.category ?? "note", category: e.category ?? e.type ?? "note",
    status: (e.status ?? "doing") as SearchResult["status"], tags: e.tags || [],
    created_at: e.created_at ?? "", file_path: e.file_path || "", content_snippet: e.content_snippet || "" };
}

export async function searchEntries(query: string, limit: number = 10, filterType?: string, filters?: SearchFilterOptions): Promise<SearchResponse> {
  const body: { query: string | null; limit: number; filter_type?: string | null; start_time?: string | null; end_time?: string | null; tags?: string[] | null } = { query: query || null, limit };
  if (filterType) body.filter_type = filterType;
  if (filters?.startTime) body.start_time = filters.startTime;
  if (filters?.endTime) body.end_time = filters.endTime;
  if (filters?.tags && filters.tags.length > 0) body.tags = filters.tags;
  const { data, error, response } = await client.POST("/search", { body });
  handleOpenApiResponse(data, error, response);
  return { results: ((data as { results?: unknown[] })?.results ?? []).map((e: unknown) => normalizeSearchItem(e as Record<string, unknown>)) };
}

// === 知识图谱 ===
export async function getKnowledgeGraph(concept: string, depth: number = 2): Promise<KnowledgeGraphResponse> {
  const { data, error, response } = await client.GET("/knowledge-graph/{concept}", { params: { path: { concept }, query: { depth } } });
  return handleOpenApiResponse<KnowledgeGraphResponse>(data as KnowledgeGraphResponse | undefined, error, response);
}

export async function getKnowledgeMap(depth: number = 2, view: string = "domain"): Promise<KnowledgeMapResponse> {
  const { data, error, response } = await client.GET("/knowledge-map", { params: { query: { depth, view } } });
  return handleOpenApiResponse<KnowledgeMapResponse>(data as KnowledgeMapResponse | undefined, error, response);
}

export async function getKnowledgeStats(): Promise<ConceptStatsResponse> {
  const { data, error, response } = await client.GET("/knowledge/stats");
  return handleOpenApiResponse<ConceptStatsResponse>(data as ConceptStatsResponse | undefined, error, response);
}

// === 解析/SSE（原始 fetch，无法用 openapi-fetch）===
export async function parseText(text: string, sessionId?: string): Promise<Response> {
  const response = await authFetch(`${API_BASE}/parse`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, session_id: sessionId }),
  });
  if (!response.ok) throw new ApiError(response.status, `Parse API error: ${response.status}`);
  return response;
}

export async function clearSession(sessionId: string): Promise<void> {
  const { error, response } = await client.DELETE("/session/{session_id}", { params: { path: { session_id: sessionId } } });
  handleOpenApiResponse(undefined, error, response);
}

// === 项目进度 ===
export async function getProjectProgress(projectId: string): Promise<ProjectProgressResponse> {
  const { data, error, response } = await client.GET("/entries/{entry_id}/progress", { params: { path: { entry_id: projectId } } });
  return handleOpenApiResponse<ProjectProgressResponse>(data as ProjectProgressResponse | undefined, error, response);
}

// === 反馈 ===
export async function submitFeedback(payload: FeedbackPayload): Promise<FeedbackSubmitResponse> {
  const { data, error, response } = await client.POST("/feedback", { body: payload });
  return handleOpenApiResponse<FeedbackSubmitResponse>(data as FeedbackSubmitResponse | undefined, error, response);
}

export async function getFeedbackList(): Promise<FeedbackListResponse> {
  const { data, error, response } = await client.GET("/feedback");
  return handleOpenApiResponse<FeedbackListResponse>(data as FeedbackListResponse | undefined, error, response);
}

export async function getFeedbackDetail(id: number): Promise<FeedbackItem> {
  const { data, error, response } = await client.GET("/feedback/{feedback_id}", { params: { path: { feedback_id: id } } });
  return handleOpenApiResponse<FeedbackItem>(data as FeedbackItem | undefined, error, response);
}

export async function syncFeedback(): Promise<FeedbackSyncResponse> {
  const { data, error, response } = await client.POST("/feedback/sync");
  return handleOpenApiResponse(data, error, response) as FeedbackSyncResponse;
}

// === AI 对话（SSE，原始 fetch）===
export async function sendAIChat(message: string, context?: AIChatContext): Promise<Response> {
  const response = await authFetch(`${API_BASE}/ai/chat`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, context }),
  });
  if (!response.ok) throw new ApiError(response.status, `AI Chat error: ${response.status}`);
  return response;
}

// === 意图识别（带回退）===
const localIntentFallback = (text: string): IntentResponse => ({
  intent: detectIntentLocal(text), confidence: 0.8, entities: {}, query: text,
});

export async function detectIntent(text: string): Promise<IntentResponse> {
  try {
    const { data, error, response } = await client.POST("/intent", { body: { text } });
    if (error || !response.ok) { console.warn("Intent API 不可用，回退到本地检测"); return localIntentFallback(text); }
    return handleOpenApiResponse<IntentResponse>(data as IntentResponse | undefined, error, response);
  } catch { console.warn("Intent API 不可用，回退到本地检测"); return localIntentFallback(text); }
}

// === 回顾报告 ===
export async function getDailyReport(): Promise<DailyReport> {
  const { data, error, response } = await client.GET("/review/daily");
  return handleOpenApiResponse<DailyReport>(data as DailyReport | undefined, error, response);
}
export async function getWeeklyReport(): Promise<WeeklyReport> {
  const { data, error, response } = await client.GET("/review/weekly");
  return handleOpenApiResponse<WeeklyReport>(data as WeeklyReport | undefined, error, response);
}
export async function getMonthlyReport(): Promise<MonthlyReport> {
  const { data, error, response } = await client.GET("/review/monthly");
  return handleOpenApiResponse<MonthlyReport>(data as MonthlyReport | undefined, error, response);
}

export async function getReviewTrend(period: "daily" | "weekly", count?: number): Promise<ReviewTrendResponse> {
  const { data, error, response } = await client.GET("/review/trend", {
    params: { query: period === "daily" ? { period, days: count ?? 7 } : { period, weeks: count ?? 8 } },
  });
  return handleOpenApiResponse<ReviewTrendResponse>(data as ReviewTrendResponse | undefined, error, response);
}

// === AI 深度洞察 ===
export async function getInsights(period: "weekly" | "monthly"): Promise<InsightsResponse> {
  const { data, error, response } = await client.GET("/review/insights", { params: { query: { period } } });
  return handleOpenApiResponse<InsightsResponse>(data as InsightsResponse | undefined, error, response);
}

// === 知识热力图 ===
export async function getKnowledgeHeatmap(): Promise<HeatmapResponse> {
  const { data, error, response } = await client.GET("/review/knowledge-heatmap");
  return handleOpenApiResponse<HeatmapResponse>(data as HeatmapResponse | undefined, error, response);
}
export async function getGrowthCurve(weeks: number = 8): Promise<GrowthCurveResponse> {
  const { data, error, response } = await client.GET("/review/growth-curve", { params: { query: { weeks } } });
  return handleOpenApiResponse<GrowthCurveResponse>(data as GrowthCurveResponse | undefined, error, response);
}

// === AI 晨报 ===
export async function getMorningDigest(): Promise<MorningDigestResponse> {
  const { data, error, response } = await client.GET("/review/morning-digest");
  return handleOpenApiResponse<MorningDigestResponse>(data as MorningDigestResponse | undefined, error, response);
}

// === 导出（原始 fetch）===
export async function exportEntries(options: ExportOptions): Promise<Blob> {
  const params = new URLSearchParams();
  params.set("format", options.format);
  if (options.type) params.set("type", options.type);
  if (options.startDate) params.set("start_date", options.startDate);
  if (options.endDate) params.set("end_date", options.endDate);
  const response = await authFetch(`${API_BASE}/entries/export?${params.toString()}`);
  if (!response.ok) throw new Error(`导出失败: ${response.status}`);
  return response.blob();
}
export async function exportSingleEntry(entryId: string): Promise<Blob> {
  const response = await authFetch(`${API_BASE}/entries/${entryId}/export`);
  if (!response.ok) throw new Error(`导出失败: ${response.status}`);
  return response.blob();
}
export async function exportGrowthReport(): Promise<Blob> {
  const response = await authFetch(`${API_BASE}/review/growth-report`);
  if (!response.ok) throw new Error(`导出成长报告失败: ${response.status}`);
  return response.blob();
}

// === 关联推荐 ===
export async function getRelatedEntries(entryId: string): Promise<RelatedEntry[]> {
  const { data, error, response } = await client.GET("/entries/{entry_id}/related", { params: { path: { entry_id: entryId } } });
  handleOpenApiResponse(data, error, response);
  return ((data as { related?: unknown[] })?.related ?? []) as RelatedEntry[];
}

// === AI 条目摘要 ===
export async function generateEntrySummary(entryId: string): Promise<EntrySummaryResponse> {
  const { data, error, response } = await client.POST("/entries/{entry_id}/ai-summary", { params: { path: { entry_id: entryId } } });
  return handleOpenApiResponse<EntrySummaryResponse>(data as EntrySummaryResponse | undefined, error, response);
}

// === 通知 ===
export async function getNotifications(): Promise<NotificationResponse> {
  const { data, error, response } = await client.GET("/notifications");
  return handleOpenApiResponse<NotificationResponse>(data as NotificationResponse | undefined, error, response);
}
export async function dismissNotification(id: string): Promise<void> {
  const { error, response } = await client.POST("/notifications/{notification_id}/dismiss", { params: { path: { notification_id: id } } });
  handleOpenApiResponse(undefined, error, response);
}
export async function getNotificationPreferences(): Promise<NotificationPreferences> {
  const { data, error, response } = await client.GET("/notification-preferences");
  return handleOpenApiResponse<NotificationPreferences>(data as NotificationPreferences | undefined, error, response);
}
export async function updateNotificationPreferences(prefs: NotificationPreferences): Promise<NotificationPreferences> {
  const { data, error, response } = await client.PUT("/notification-preferences", { body: prefs });
  return handleOpenApiResponse<NotificationPreferences>(data as NotificationPreferences | undefined, error, response);
}

// === 知识图谱增强 ===
export async function getKnowledgeSearch(query: string, limit?: number): Promise<KnowledgeSearchResponse> {
  const { data, error, response } = await client.GET("/knowledge/search", { params: { query: { q: query, limit } } });
  return handleOpenApiResponse<KnowledgeSearchResponse>(data as KnowledgeSearchResponse | undefined, error, response);
}
export async function getConceptTimeline(concept: string, days?: number): Promise<ConceptTimelineResponse> {
  const { data, error, response } = await client.GET("/knowledge/concepts/{name}/timeline", {
    params: { path: { name: concept }, query: days !== undefined ? { days } : undefined },
  });
  return handleOpenApiResponse<ConceptTimelineResponse>(data as ConceptTimelineResponse | undefined, error, response);
}
export async function getMasteryDistribution(): Promise<MasteryDistributionResponse> {
  const { data, error, response } = await client.GET("/knowledge/mastery-distribution");
  return handleOpenApiResponse<MasteryDistributionResponse>(data as MasteryDistributionResponse | undefined, error, response);
}

// === 能力地图 ===
export async function getCapabilityMap(masteryLevel?: string): Promise<CapabilityMapResponse> {
  const { data, error, response } = await client.GET("/knowledge/capability-map", { params: { query: masteryLevel ? { mastery_level: masteryLevel } : undefined } });
  return handleOpenApiResponse<CapabilityMapResponse>(data as CapabilityMapResponse | undefined, error, response);
}

// === 条目手动关联 ===
export async function getEntryLinks(entryId: string, direction?: "out" | "in" | "both"): Promise<EntryLinkListResponse> {
  const { data, error, response } = await client.GET("/entries/{entry_id}/links", {
    params: { path: { entry_id: entryId }, query: direction ? { direction } : undefined },
  });
  return handleOpenApiResponse<EntryLinkListResponse>(data as EntryLinkListResponse | undefined, error, response);
}
export async function createEntryLink(entryId: string, targetId: string, relationType: RelationType): Promise<EntryLinkCreateResponse> {
  const { data, error, response } = await client.POST("/entries/{entry_id}/links", {
    params: { path: { entry_id: entryId } }, body: { target_id: targetId, relation_type: relationType },
  });
  return handleOpenApiResponse<EntryLinkCreateResponse>(data as EntryLinkCreateResponse | undefined, error, response);
}
export async function deleteEntryLink(entryId: string, linkId: string): Promise<void> {
  const { error, response } = await client.DELETE("/entries/{entry_id}/links/{link_id}", { params: { path: { entry_id: entryId, link_id: linkId } } });
  handleOpenApiResponse(undefined, error, response);
}

// === 条目知识上下文 ===
export async function getKnowledgeContext(entryId: string): Promise<KnowledgeContextResponse> {
  const { data, error, response } = await client.GET("/entries/{entry_id}/knowledge-context", { params: { path: { entry_id: entryId } } });
  return handleOpenApiResponse<KnowledgeContextResponse>(data as KnowledgeContextResponse | undefined, error, response);
}

// === 活动热力图 ===
export async function getActivityHeatmap(year: number): Promise<ActivityHeatmapResponse> {
  const { data, error, response } = await client.GET("/review/activity-heatmap", { params: { query: { year } } });
  return handleOpenApiResponse<ActivityHeatmapResponse>(data as ActivityHeatmapResponse | undefined, error, response);
}

// === Goals ===
export async function getGoals(status?: string): Promise<GoalListResponse> {
  const { data, error, response } = await client.GET("/goals", { params: { query: status ? { status } : undefined } });
  return handleOpenApiResponse<GoalListResponse>(data as GoalListResponse | undefined, error, response);
}
export async function getGoal(goalId: string): Promise<GoalDetailResponse> {
  const { data, error, response } = await client.GET("/goals/{goal_id}", { params: { path: { goal_id: goalId } } });
  return handleOpenApiResponse<GoalDetailResponse>(data as GoalDetailResponse | undefined, error, response);
}
export async function createGoal(data: {
  title: string; description?: string; metric_type: MetricType; target_value: number;
  start_date?: string; end_date?: string; auto_tags?: string[]; checklist_items?: string[];
}): Promise<Goal> {
  const { data: rd, error, response } = await client.POST("/goals", { body: data });
  return handleOpenApiResponse<Goal>(rd as Goal | undefined, error, response);
}
export async function updateGoal(goalId: string, data: {
  title?: string; description?: string; target_value?: number;
  status?: string; start_date?: string; end_date?: string;
}): Promise<Goal> {
  const { data: rd, error, response } = await client.PUT("/goals/{goal_id}", {
    params: { path: { goal_id: goalId } }, body: data as S["GoalUpdate"],
  });
  return handleOpenApiResponse<Goal>(rd as Goal | undefined, error, response);
}
export async function deleteGoal(goalId: string): Promise<void> {
  const { error, response } = await client.DELETE("/goals/{goal_id}", { params: { path: { goal_id: goalId } } });
  handleOpenApiResponse(undefined, error, response);
}
export async function linkGoalEntry(goalId: string, entryId: string): Promise<S["GoalEntryLinkResponse"]> {
  const { data, error, response } = await client.POST("/goals/{goal_id}/entries", {
    params: { path: { goal_id: goalId } }, body: { entry_id: entryId },
  });
  return handleOpenApiResponse(data, error, response);
}
export async function unlinkGoalEntry(goalId: string, entryId: string): Promise<void> {
  const { error, response } = await client.DELETE("/goals/{goal_id}/entries/{entry_id}", { params: { path: { goal_id: goalId, entry_id: entryId } } });
  handleOpenApiResponse(undefined, error, response);
}
export async function getGoalEntries(goalId: string): Promise<GoalEntryListResponse> {
  const { data, error, response } = await client.GET("/goals/{goal_id}/entries", { params: { path: { goal_id: goalId } } });
  return handleOpenApiResponse<GoalEntryListResponse>(data as GoalEntryListResponse | undefined, error, response);
}
export async function toggleChecklistItem(goalId: string, itemId: string): Promise<Goal> {
  const { data, error, response } = await client.PATCH("/goals/{goal_id}/checklist/{item_id}", { params: { path: { goal_id: goalId, item_id: itemId } } });
  return handleOpenApiResponse<Goal>(data as Goal | undefined, error, response);
}
export async function getProgressSummary(period?: string): Promise<ProgressSummaryResponse> {
  const { data, error, response } = await client.GET("/goals/progress-summary", { params: { query: period ? { period } : undefined } });
  return handleOpenApiResponse<ProgressSummaryResponse>(data as ProgressSummaryResponse | undefined, error, response);
}

// 导出错误类供外部使用
export { ApiError } from "@/lib/errors";
