/**
 * NotificationCenter 组件单元测试
 * - 相对时间戳显示
 * - 后台轮询（面板关闭 300s / 面板打开 60s）
 * - 组件卸载清理定时器
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
// Mock API
const mockGetNotifications = vi.fn();
const mockDismissNotification = vi.fn();
const mockGetNotificationPreferences = vi.fn();
const mockUpdateNotificationPreferences = vi.fn();

vi.mock("@/services/api", () => ({
  getNotifications: (...args: any[]) => mockGetNotifications(...args),
  dismissNotification: (...args: any[]) => mockDismissNotification(...args),
  getNotificationPreferences: (...args: any[]) => mockGetNotificationPreferences(...args),
  updateNotificationPreferences: (...args: any[]) => mockUpdateNotificationPreferences(...args),
}));

// Mock react-router-dom
const mockNavigate = vi.fn();
vi.mock("react-router-dom", () => ({
  useNavigate: () => mockNavigate,
  // 为可能需要的 Link 等组件提供基础 mock
  MemoryRouter: ({ children }: { children: React.ReactNode }) => children,
}));

import { NotificationCenter } from "../NotificationCenter";

const defaultNotification = {
  id: "n1",
  type: "overdue_task",
  title: "任务过期",
  message: "任务已过期，请及时处理",
  ref_id: "entry-1",
  created_at: new Date(Date.now() - 5 * 60_000).toISOString(), // 5 分钟前
  dismissed: false,
};

describe("NotificationCenter", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mockGetNotifications.mockClear();
    mockDismissNotification.mockClear();
    mockGetNotificationPreferences.mockClear();
    mockUpdateNotificationPreferences.mockClear();
    mockNavigate.mockClear();
    mockGetNotifications.mockResolvedValue({
      items: [{ ...defaultNotification }],
      unread_count: 1,
    });
    mockDismissNotification.mockResolvedValue(undefined);
    mockGetNotificationPreferences.mockResolvedValue({
      overdue_task_enabled: true,
      stale_inbox_enabled: true,
      review_prompt_enabled: true,
    });
    mockUpdateNotificationPreferences.mockResolvedValue(undefined);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  // === 验收条件 1: 相对时间戳 ===

  it("每条通知显示相对时间戳", async () => {
    await act(async () => {
      render(<NotificationCenter />);
    });

    // 点击铃铛打开面板
    const bellButton = screen.getByLabelText("通知");
    await act(async () => {
      bellButton.click();
    });

    // 应显示 "5 分钟前"
    expect(screen.getByText("5 分钟前")).toBeInTheDocument();
  });

  it("相对时间戳 — 刚刚", async () => {
    mockGetNotifications.mockResolvedValue({
      items: [{ ...defaultNotification, created_at: new Date().toISOString() }],
      unread_count: 1,
    });

    await act(async () => {
      render(<NotificationCenter />);
    });

    await act(async () => {
      screen.getByLabelText("通知").click();
    });

    expect(screen.getByText("刚刚")).toBeInTheDocument();
  });

  it("相对时间戳 — 小时级", async () => {
    mockGetNotifications.mockResolvedValue({
      items: [{ ...defaultNotification, created_at: new Date(Date.now() - 3 * 3600_000).toISOString() }],
      unread_count: 1,
    });

    await act(async () => {
      render(<NotificationCenter />);
    });

    await act(async () => {
      screen.getByLabelText("通知").click();
    });

    expect(screen.getByText("3 小时前")).toBeInTheDocument();
  });

  it("相对时间戳 — 天级", async () => {
    mockGetNotifications.mockResolvedValue({
      items: [{ ...defaultNotification, created_at: new Date(Date.now() - 2 * 86400_000).toISOString() }],
      unread_count: 1,
    });

    await act(async () => {
      render(<NotificationCenter />);
    });

    await act(async () => {
      screen.getByLabelText("通知").click();
    });

    expect(screen.getByText("2 天前")).toBeInTheDocument();
  });

  // === 验收条件 2: 面板关闭时 300s 后台轮询 ===

  it("面板关闭时 300s 后台轮询更新未读计数", async () => {
    await act(async () => {
      render(<NotificationCenter />);
    });

    // 初始加载调用一次
    expect(mockGetNotifications).toHaveBeenCalledTimes(1);

    // 推进 299 秒 — 不应再次调用
    await act(async () => {
      vi.advanceTimersByTime(299_000);
    });
    expect(mockGetNotifications).toHaveBeenCalledTimes(1);

    // 推进到 300 秒 — 应再次调用（后台轮询）
    await act(async () => {
      vi.advanceTimersByTime(1_000);
    });
    expect(mockGetNotifications).toHaveBeenCalledTimes(2);
  });

  // === 验收条件 3: 面板展开时切换为 60s 高频轮询 ===

  it("面板展开时切换为 60s 高频轮询", async () => {
    await act(async () => {
      render(<NotificationCenter />);
    });

    // 打开面板
    await act(async () => {
      screen.getByLabelText("通知").click();
    });

    const callsAfterOpen = mockGetNotifications.mock.calls.length;

    // 推进 59 秒 — 不应再次调用
    await act(async () => {
      vi.advanceTimersByTime(59_000);
    });
    expect(mockGetNotifications.mock.calls.length).toBe(callsAfterOpen);

    // 推进到 60 秒 — 应再次调用（高频轮询）
    await act(async () => {
      vi.advanceTimersByTime(1_000);
    });
    expect(mockGetNotifications.mock.calls.length).toBe(callsAfterOpen + 1);
  });

  it("面板关闭 → 打开 → 关闭，轮询间隔正确切换", async () => {
    await act(async () => {
      render(<NotificationCenter />);
    });
    expect(mockGetNotifications).toHaveBeenCalledTimes(1);

    // 面板关闭状态：推进 300s 触发后台轮询
    await act(async () => {
      vi.advanceTimersByTime(300_000);
    });
    expect(mockGetNotifications).toHaveBeenCalledTimes(2);

    // 打开面板
    await act(async () => {
      screen.getByLabelText("通知").click();
    });

    // 面板打开：推进 60s 触发高频轮询
    await act(async () => {
      vi.advanceTimersByTime(60_000);
    });
    expect(mockGetNotifications).toHaveBeenCalledTimes(3);

    // 关闭面板（点击外部）
    // 通过再次点击铃铛关闭
    await act(async () => {
      screen.getByLabelText("通知").click();
    });

    // 面板关闭：应该是 300s 间隔
    await act(async () => {
      vi.advanceTimersByTime(60_000);
    });
    // 60s 不应触发（因为面板已关闭，间隔是 300s）
    expect(mockGetNotifications).toHaveBeenCalledTimes(3);

    await act(async () => {
      vi.advanceTimersByTime(240_000);
    });
    expect(mockGetNotifications).toHaveBeenCalledTimes(4);
  });

  // === 验收条件 4: 组件卸载时清理所有定时器 ===

  it("组件卸载时清理定时器，不再轮询", async () => {
    const { unmount } = await act(async () => {
      return render(<NotificationCenter />);
    });
    expect(mockGetNotifications).toHaveBeenCalledTimes(1);

    // 卸载组件
    await act(async () => {
      unmount();
    });

    // 推进时间，不应再调用
    await act(async () => {
      vi.advanceTimersByTime(600_000);
    });
    expect(mockGetNotifications).toHaveBeenCalledTimes(1);
  });

  // === 未读计数 badge ===

  it("显示未读计数 badge", async () => {
    mockGetNotifications.mockResolvedValue({
      items: [{ ...defaultNotification }],
      unread_count: 3,
    });

    await act(async () => {
      render(<NotificationCenter />);
    });

    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("未读计数超过 9 显示 9+", async () => {
    mockGetNotifications.mockResolvedValue({
      items: [{ ...defaultNotification }],
      unread_count: 15,
    });

    await act(async () => {
      render(<NotificationCenter />);
    });

    expect(screen.getByText("9+")).toBeInTheDocument();
  });

  it("后台轮询更新未读计数后 badge 刷新", async () => {
    mockGetNotifications.mockResolvedValue({
      items: [{ ...defaultNotification }],
      unread_count: 1,
    });

    await act(async () => {
      render(<NotificationCenter />);
    });
    expect(screen.getByText("1")).toBeInTheDocument();

    // 第二次调用返回新的未读数
    mockGetNotifications.mockResolvedValue({
      items: [],
      unread_count: 0,
    });

    // 触发后台轮询
    await act(async () => {
      vi.advanceTimersByTime(300_000);
    });

    // badge 应消失（未读数 0）
    expect(screen.queryByText("1")).not.toBeInTheDocument();
  });
});
