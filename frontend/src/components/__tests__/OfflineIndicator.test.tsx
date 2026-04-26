/**
 * OfflineIndicator 组件单元测试
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act } from "@testing-library/react";

// Mock subscribeSyncProgress to capture the callback
let syncCallback: ((event: any) => void) | null = null;
vi.mock("@/lib/offlineSync", () => ({
  subscribeSyncProgress: (cb: (event: any) => void) => {
    syncCallback = cb;
    return () => { syncCallback = null; };
  },
  sync: vi.fn(),
  isSyncing: () => false,
}));

vi.mock("@/lib/offlineQueue", () => ({
  getAll: () => Promise.resolve([]),
}));

import { OfflineIndicator } from "../OfflineIndicator";

describe("OfflineIndicator", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    syncCallback = null;
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("在线状态时不渲染任何内容", () => {
    vi.stubGlobal("navigator", { onLine: true });
    const { container } = render(<OfflineIndicator />);
    expect(container.innerHTML).toBe("");
  });

  it("离线时显示离线提示", () => {
    vi.stubGlobal("navigator", { onLine: false });
    render(<OfflineIndicator />);
    expect(screen.getByText("当前处于离线状态，部分功能不可用")).toBeInTheDocument();
  });

  it("离线 → 上线时显示恢复提示", () => {
    vi.stubGlobal("navigator", { onLine: false });
    render(<OfflineIndicator />);

    expect(screen.getByText("当前处于离线状态，部分功能不可用")).toBeInTheDocument();

    vi.stubGlobal("navigator", { onLine: true });
    act(() => {
      window.dispatchEvent(new Event("online"));
    });

    expect(screen.getByText("已恢复连接")).toBeInTheDocument();
  });

  it("恢复提示 3 秒后自动消失", () => {
    vi.stubGlobal("navigator", { onLine: false });
    const { container } = render(<OfflineIndicator />);

    vi.stubGlobal("navigator", { onLine: true });
    act(() => {
      window.dispatchEvent(new Event("online"));
    });
    expect(screen.getByText("已恢复连接")).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(3000);
    });

    expect(container.innerHTML).toBe("");
  });

  it("离线提示有 role=alert 属性", () => {
    vi.stubGlobal("navigator", { onLine: false });
    render(<OfflineIndicator />);
    const alert = screen.getByRole("alert");
    expect(alert).toBeInTheDocument();
  });

  it("恢复提示有 role=status 属性", () => {
    vi.stubGlobal("navigator", { onLine: false });
    render(<OfflineIndicator />);

    vi.stubGlobal("navigator", { onLine: true });
    act(() => {
      window.dispatchEvent(new Event("online"));
    });

    const status = screen.getByRole("status");
    expect(status).toBeInTheDocument();
  });

  it("sync completed 事件显示已恢复连接，3 秒后消失", () => {
    vi.stubGlobal("navigator", { onLine: true });
    const { container } = render(<OfflineIndicator />);

    // 模拟 sync progress 事件
    act(() => {
      syncCallback?.({ type: "progress", progress: { current: 1, total: 2 } });
    });
    expect(screen.getByText(/同步中/)).toBeInTheDocument();

    // 模拟 sync completed
    act(() => {
      syncCallback?.({ type: "completed" });
    });
    expect(screen.getByText("已恢复连接")).toBeInTheDocument();

    // 3 秒后消失
    act(() => {
      vi.advanceTimersByTime(3000);
    });
    expect(container.innerHTML).toBe("");
  });

  it("auth_failed 事件显示重新登录提示，3 秒后消失", () => {
    vi.stubGlobal("navigator", { onLine: true });
    const { container } = render(<OfflineIndicator />);

    // 模拟 sync progress → auth_failed
    act(() => {
      syncCallback?.({ type: "progress", progress: { current: 1, total: 1 } });
    });
    act(() => {
      syncCallback?.({ type: "auth_failed" });
    });
    expect(screen.getByText("同步失败，请重新登录")).toBeInTheDocument();

    // 3 秒后消失
    act(() => {
      vi.advanceTimersByTime(3000);
    });
    expect(container.innerHTML).toBe("");
  });
});
