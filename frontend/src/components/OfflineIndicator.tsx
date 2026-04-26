import { useState, useEffect, useRef, useCallback } from "react";
import { useOnlineStatus } from "@/hooks/useOnlineStatus";
import {
  subscribeSyncProgress,
  sync as doSync,
  isSyncing,
  type SyncEvent,
  type SyncProgress,
} from "@/lib/offlineSync";
import * as queue from "@/lib/offlineQueue";

type IndicatorState = "online" | "offline" | "recovered" | "syncing" | "auth_failed";

/**
 * 全局离线提示组件。
 * - 离线时显示底部固定条：「同步队列：X 条待同步」
 * - 同步中状态条显示进度「同步中 (X/Y)」
 * - 同步失败时显示「重试」按钮，点击触发手动同步
 * - recovered 状态显示「已同步 X 条」
 * - 手动同步按钮不与自动 online 事件冲突
 */
export function OfflineIndicator() {
  const { isOnline } = useOnlineStatus();
  const [state, setState] = useState<IndicatorState>(
    navigator.onLine ? "online" : "offline"
  );
  const [syncProgress, setSyncProgress] = useState<SyncProgress | null>(null);
  const [pendingCount, setPendingCount] = useState(0);
  const [syncedCount, setSyncedCount] = useState(0);
  const manualSyncRef = useRef(false);
  // 用 ref 保存最新 state，避免订阅回调闭包陈旧
  const stateRef = useRef(state);
  stateRef.current = state;

  // 读取队列 pending 数量
  const refreshQueueCount = useCallback(async () => {
    try {
      const items = await queue.getAll();
      const pending = items.filter((i) => i.status === "pending");
      setPendingCount(pending.length);
    } catch {
      // IDB 不可用时忽略
    }
  }, []);

  useEffect(() => {
    if (!isOnline) {
      setState("offline");
      refreshQueueCount();
    } else {
      if (stateRef.current === "offline") {
        setState("recovered");
      } else if (stateRef.current !== "syncing" && stateRef.current !== "auth_failed") {
        setState("online");
      }
    }
  }, [isOnline, refreshQueueCount]);

  // 订阅同步进度
  useEffect(() => {
    return subscribeSyncProgress((event: SyncEvent) => {
      if (event.type === "progress" && event.progress) {
        setSyncProgress(event.progress);
        setState("syncing");
      } else if (event.type === "completed") {
        setSyncProgress(null);
        setSyncedCount((prev) => prev + (manualSyncRef.current ? 0 : 0));
        setState("recovered");
        manualSyncRef.current = false;
        refreshQueueCount();
      } else if (event.type === "auth_failed") {
        setSyncProgress(null);
        setState("auth_failed");
        manualSyncRef.current = false;
        refreshQueueCount();
      }
    });
  }, [refreshQueueCount]);

  // recovered/auth_failed 状态 3 秒后自动切回 online（隐藏提示）
  useEffect(() => {
    if (state !== "recovered" && state !== "auth_failed") return;
    const timer = setTimeout(() => setState("online"), 3000);
    return () => clearTimeout(timer);
  }, [state]);

  // 手动同步
  const handleManualSync = useCallback(() => {
    if (isSyncing()) return;
    manualSyncRef.current = true;
    doSync();
  }, []);

  // online 状态不渲染（除非有 pending 队列且不是 syncing 状态）
  if (state === "online") {
    // 如果有 pending 队列且在线，显示同步提示
    if (pendingCount > 0 && isOnline) {
      return (
        <div
          role="status"
          aria-live="polite"
          className="fixed bottom-0 left-0 right-0 z-50 flex items-center justify-center gap-2 bg-amber-500 px-4 py-2.5 text-sm font-medium text-white shadow-lg"
        >
          <span>同步队列：{pendingCount} 条待同步</span>
          <button
            onClick={handleManualSync}
            className="ml-2 rounded bg-white/20 px-2 py-0.5 text-xs font-medium hover:bg-white/30 transition-colors"
          >
            立即同步
          </button>
        </div>
      );
    }
    return null;
  }

  if (state === "offline") {
    return (
      <div
        role="alert"
        aria-live="polite"
        className="fixed bottom-0 left-0 right-0 z-50 flex items-center justify-center gap-2 bg-amber-500 px-4 py-2.5 text-sm font-medium text-white shadow-lg"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="h-4 w-4 shrink-0"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <line x1="1" y1="1" x2="23" y2="23" />
          <path d="M16.72 11.06A10.94 10.94 0 0 1 19 12.55" />
          <path d="M5 12.55a10.94 10.94 0 0 1 5.17-2.39" />
          <path d="M10.71 5.05A16 16 0 0 1 22.56 9" />
          <path d="M1.42 9a15.91 15.91 0 0 1 4.7-2.88" />
          <path d="M8.53 16.11a6 6 0 0 1 6.95 0" />
          <line x1="12" y1="20" x2="12.01" y2="20" />
        </svg>
        <span>当前处于离线状态{pendingCount > 0 ? `，同步队列：${pendingCount} 条待同步` : "，部分功能不可用"}</span>
      </div>
    );
  }

  if (state === "auth_failed") {
    return (
      <div
        role="alert"
        aria-live="polite"
        className="fixed bottom-0 left-0 right-0 z-50 flex items-center justify-center gap-2 bg-red-500 px-4 py-2.5 text-sm font-medium text-white shadow-lg"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="h-4 w-4 shrink-0"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="8" x2="12" y2="12" />
          <line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
        <span>同步失败，请重新登录</span>
        <button
          onClick={handleManualSync}
          className="ml-2 rounded bg-white/20 px-2 py-0.5 text-xs font-medium hover:bg-white/30 transition-colors"
        >
          重试
        </button>
      </div>
    );
  }

  if (state === "syncing" && syncProgress && syncProgress.total > 0) {
    return (
      <div
        role="status"
        aria-live="polite"
        className="fixed bottom-0 left-0 right-0 z-50 flex items-center justify-center gap-2 bg-blue-500 px-4 py-2.5 text-sm font-medium text-white shadow-lg"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="h-4 w-4 shrink-0 animate-spin"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M21 12a9 9 0 1 1-6.219-8.56" />
        </svg>
        <span>同步中 ({syncProgress.current}/{syncProgress.total})</span>
      </div>
    );
  }

  // state === "recovered"
  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed bottom-0 left-0 right-0 z-50 flex items-center justify-center gap-2 bg-emerald-500 px-4 py-2.5 text-sm font-medium text-white shadow-lg"
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        className="h-4 w-4 shrink-0"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M5 12.55a11 11 0 0 1 14.08 0" />
        <path d="M1.42 9a16 16 0 0 1 21.16 0" />
        <path d="M8.53 16.11a6 6 0 0 1 6.95 0" />
        <line x1="12" y1="20" x2="12.01" y2="20" />
      </svg>
      <span>已恢复连接{syncedCount > 0 ? `，已同步 ${syncedCount} 条` : ""}</span>
    </div>
  );
}
