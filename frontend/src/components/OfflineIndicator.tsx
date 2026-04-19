import { useState, useEffect, useCallback } from "react";
import { useOnlineStatus } from "@/hooks/useOnlineStatus";
import {
  subscribeSyncProgress,
  type SyncProgress,
} from "@/lib/offlineSync";

type IndicatorState = "online" | "offline" | "recovered" | "syncing";

/**
 * 全局离线提示组件。
 * - 离线时显示底部固定条：「当前处于离线状态，部分功能不可用」
 * - 上线时切换为同步进度或「已恢复连接」，3 秒后自动消失
 */
export function OfflineIndicator() {
  const { isOnline } = useOnlineStatus();
  const [state, setState] = useState<IndicatorState>(
    navigator.onLine ? "online" : "offline"
  );
  const [syncProgress, setSyncProgress] = useState<SyncProgress | null>(null);

  const handleRecovered = useCallback(() => {
    setState("recovered");
  }, []);

  useEffect(() => {
    if (!isOnline) {
      setState("offline");
    } else {
      // 从离线恢复到在线
      if (state === "offline") {
        handleRecovered();
      } else {
        setState("online");
      }
    }
    // 只依赖 isOnline 变化来触发
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOnline]);

  // 订阅同步进度
  useEffect(() => {
    return subscribeSyncProgress((progress) => {
      setSyncProgress(progress);
      if (progress && progress.total > 0) {
        setState("syncing");
      } else if (progress === null && state === "syncing") {
        setState("recovered");
      }
      // progress {current: -1, total: -1} means 401 auth error
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // recovered 状态 3 秒后自动切回 online（隐藏提示）
  useEffect(() => {
    if (state !== "recovered") return;
    const timer = setTimeout(() => setState("online"), 3000);
    return () => clearTimeout(timer);
  }, [state]);

  // online 状态不渲染
  if (state === "online") return null;

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
        <span>当前处于离线状态，部分功能不可用</span>
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
        <span>正在同步 {syncProgress.current}/{syncProgress.total}...</span>
      </div>
    );
  }

  // state === "recovered" (or syncing done)
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
      <span>已恢复连接</span>
    </div>
  );
}
