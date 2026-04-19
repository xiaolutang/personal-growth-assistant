/**
 * OfflineIndicator 组件单元测试
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { OfflineIndicator } from "../OfflineIndicator";

describe("OfflineIndicator", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.stubGlobal("navigator", { onLine: true });
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

    // 确认离线状态
    expect(screen.getByText("当前处于离线状态，部分功能不可用")).toBeInTheDocument();

    // 模拟上线
    vi.stubGlobal("navigator", { onLine: true });
    act(() => {
      window.dispatchEvent(new Event("online"));
    });

    expect(screen.getByText("已恢复连接")).toBeInTheDocument();
  });

  it("恢复提示 3 秒后自动消失", () => {
    vi.stubGlobal("navigator", { onLine: false });
    const { container } = render(<OfflineIndicator />);

    // 模拟上线 → 进入 recovered 状态
    vi.stubGlobal("navigator", { onLine: true });
    act(() => {
      window.dispatchEvent(new Event("online"));
    });
    expect(screen.getByText("已恢复连接")).toBeInTheDocument();

    // 快进 3 秒
    act(() => {
      vi.advanceTimersByTime(3000);
    });

    // 提示消失
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
});
