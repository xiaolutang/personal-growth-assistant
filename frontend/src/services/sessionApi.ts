/**
 * 会话管理 API
 *
 * 提供会话列表、消息历史、标题更新等功能
 */

import { API_BASE } from "@/config/api";
import { handleApiResponse } from "@/lib/errors";
import { authFetch } from "@/lib/authFetch";

// === 类型定义 ===

export interface SessionInfo {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface MessageInfo {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

export interface SessionUpdate {
  title: string;
}

// === API 函数 ===

/**
 * 获取所有会话列表
 */
export async function listSessions(): Promise<SessionInfo[]> {
  const response = await authFetch(`${API_BASE}/sessions`);
  return handleApiResponse<SessionInfo[]>(response);
}

/**
 * 获取指定会话的消息历史
 */
export async function getSessionMessages(sessionId: string): Promise<MessageInfo[]> {
  const response = await authFetch(`${API_BASE}/sessions/${sessionId}/messages`);
  return handleApiResponse<MessageInfo[]>(response);
}

/**
 * 更新会话标题
 */
export async function updateSessionTitle(
  sessionId: string,
  title: string
): Promise<SessionInfo> {
  const response = await authFetch(`${API_BASE}/sessions/${sessionId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  return handleApiResponse<SessionInfo>(response);
}

/**
 * 删除会话
 */
export async function deleteSession(sessionId: string): Promise<void> {
  const response = await authFetch(`${API_BASE}/sessions/${sessionId}`, {
    method: "DELETE",
  });
  await handleApiResponse<void>(response as any);
}

// 导出统一的 API 对象
export const sessionApi = {
  list: listSessions,
  getMessages: getSessionMessages,
  updateTitle: updateSessionTitle,
  delete: deleteSession,
};
