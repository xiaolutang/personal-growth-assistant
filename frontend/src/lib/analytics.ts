/**
 * Analytics — 成功指标前端埋点
 *
 * best-effort: 失败静默，不影响用户体验。
 * 离线时直接丢弃（navigator.onLine===false），不做缓存回放。
 */

import { API_BASE } from "@/config/api";
import { authFetch } from "@/lib/authFetch";

export type AnalyticsEventType =
  | "entry_created"
  | "entry_viewed"
  | "chat_message_sent"
  | "search_performed"
  | "page_viewed"
  | "onboarding_completed";

/**
 * 发送一个埋点事件到后端 POST /analytics/event。
 * 任何异常均静默吞掉。
 */
export async function trackEvent(
  eventType: AnalyticsEventType,
  metadata?: Record<string, unknown>,
): Promise<void> {
  // 离线时直接丢弃
  if (typeof navigator !== "undefined" && !navigator.onLine) return;

  try {
    await authFetch(`${API_BASE}/analytics/event`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        event_type: eventType,
        metadata: metadata ?? null,
      }),
    });
    // 不检查 response.ok — best-effort
  } catch {
    // 静默忽略
  }
}
