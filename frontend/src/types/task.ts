export type Category = "task" | "inbox" | "note" | "project";

export type TaskStatus = "waitStart" | "doing" | "complete";

export interface Task {
  id: number;
  name: string;
  description?: string;
  category: Category;
  status: TaskStatus;
  created_at?: string;
  planned_date?: string;
  completed_at?: string;
  updated_at?: string;
  parent_id?: number;
}

export interface ParseResponse {
  tasks: Task[];
}
