// 条目类型
export type Category = "task" | "inbox" | "note" | "project";

// 任务状态
export type TaskStatus = "waitStart" | "doing" | "complete" | "paused" | "cancelled";

// 任务优先级
export type Priority = "high" | "medium" | "low";

// 条目接口 (与后端 EntryResponse 对齐)
export interface Task {
  id: string;
  title: string;
  content: string;
  category: Category;
  status: TaskStatus;
  tags: string[];
  created_at: string;
  updated_at: string;
  planned_date?: string;
  completed_at?: string;
  time_spent?: number;
  parent_id?: string;
  file_path: string;
  priority?: Priority;
}

// 创建条目请求
export interface EntryCreate {
  type: string;
  title: string;
  content?: string;
  tags?: string[];
  parent_id?: string;
  status?: TaskStatus;
  priority?: Priority;
  planned_date?: string;
  time_spent?: number;
}

// 更新条目请求
export interface EntryUpdate {
  title?: string;
  content?: string;
  category?: Category;
  status?: TaskStatus;
  priority?: Priority;
  tags?: string[];
  parent_id?: string;
  planned_date?: string;
  time_spent?: number;
  completed_at?: string;
}

// 条目列表响应
export interface EntryListResponse {
  entries: Task[];
}

// 搜索结果
export interface SearchResult {
  id: string;
  title: string;
  score: number;
  type: string;
  category: string;        // 条目类型
  status: TaskStatus;     // 状态
  priority?: Priority;   // 优先级
  tags: string[];
  created_at: string;     // 创建时间
  file_path: string;
}

// 搜索响应
export interface SearchResponse {
  results: SearchResult[];
}

// 知识图谱节点
export interface ConceptNode {
  name: string;
  category?: string;
  description?: string;
}

// 概念关系
export interface ConceptRelation {
  name: string;
  relationship: string;
  category?: string;
}

// 知识图谱响应
export interface KnowledgeGraphResponse {
  center?: ConceptNode;
  connections: ConceptRelation[];
}

// 相关概念响应
export interface RelatedConceptsResponse {
  concept: string;
  related: ConceptNode[];
}

// 解析响应 (旧接口兼容)
export interface ParseResponse {
  tasks: Task[];
}
