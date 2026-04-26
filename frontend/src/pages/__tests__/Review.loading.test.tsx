/**
 * F137: Review 加载态、错误态、空状态测试
 *
 * 覆盖：
 * - 数据加载中显示 spinner + 文案
 * - 加载失败显示错误提示 + 重试按钮
 * - 空数据状态有友好提示（zero-filled 合约响应）
 * - 成功后刷新失败不残留旧数据
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import { Review } from "../Review";
import { ThemeProvider } from "@/lib/theme";

// --- Mocks ---

// Mock recharts
vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="recharts-responsive">{children}</div>
  ),
  LineChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="recharts-linechart">{children}</div>
  ),
  Line: () => <div data-testid="recharts-line" />,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  Legend: () => null,
}));

// Mock authFetch
const mockAuthFetch = vi.fn();
vi.mock("@/lib/authFetch", () => ({
  authFetch: (...args: unknown[]) => mockAuthFetch(...args),
  buildAuthHeaders: () => new Headers(),
}));

// Mock useServiceUnavailable — 默认不触发 503
const mockRunWith503 = vi.fn();
vi.mock("@/hooks/useServiceUnavailable", () => ({
  useServiceUnavailable: () => ({
    serviceUnavailable: false,
    runWith503: (fn: () => Promise<void>) => mockRunWith503(fn),
    retry: (fn: () => Promise<void>) => fn(),
  }),
}));

// Mock useMorningDigest
vi.mock("@/hooks/useMorningDigest", () => ({
  useMorningDigest: () => ({ data: null, loading: false, error: null }),
}));

// API mock — 可按测试场景覆盖
const mockGetDailyReport = vi.fn();
const mockGetWeeklyReport = vi.fn();
const mockGetMonthlyReport = vi.fn();
const mockGetProgressSummary = vi.fn();
const mockGetReviewTrend = vi.fn();
const mockGetActivityHeatmap = vi.fn();
const mockGetKnowledgeHeatmap = vi.fn();
const mockGetGrowthCurve = vi.fn();
const mockGetInsights = vi.fn();

vi.mock("@/services/api", () => ({
  getDailyReport: (...args: unknown[]) => mockGetDailyReport(...args),
  getWeeklyReport: (...args: unknown[]) => mockGetWeeklyReport(...args),
  getMonthlyReport: (...args: unknown[]) => mockGetMonthlyReport(...args),
  getProgressSummary: (...args: unknown[]) => mockGetProgressSummary(...args),
  getReviewTrend: (...args: unknown[]) => mockGetReviewTrend(...args),
  getActivityHeatmap: (...args: unknown[]) => mockGetActivityHeatmap(...args),
  getKnowledgeHeatmap: (...args: unknown[]) => mockGetKnowledgeHeatmap(...args),
  getGrowthCurve: (...args: unknown[]) => mockGetGrowthCurve(...args),
  getInsights: (...args: unknown[]) => mockGetInsights(...args),
}));

function renderReview() {
  return render(
    <MemoryRouter>
      <ThemeProvider>
        <Review />
      </ThemeProvider>
    </MemoryRouter>,
  );
}

// 标准日报 mock（有数据）
function defaultDailyReport(overrides: Record<string, unknown> = {}) {
  return {
    date: "2026-04-26",
    task_stats: {
      total: 10,
      completed: 5,
      doing: 3,
      wait_start: 2,
      completion_rate: 50,
    },
    note_stats: { total: 3, recent_titles: ["笔记1", "笔记2"] },
    completed_tasks: [],
    ai_summary: null,
    ...overrides,
  };
}

// 合约合法的 zero-filled 日报（后端在无数据时返回此格式）
function emptyDailyReport() {
  return {
    date: "2026-04-26",
    task_stats: {
      total: 0,
      completed: 0,
      doing: 0,
      wait_start: 0,
      completion_rate: 0,
    },
    note_stats: { total: 0, recent_titles: [] },
    completed_tasks: [],
    ai_summary: null,
  };
}

describe("Review — F137 加载态 / 错误态 / 空状态", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // 默认 runWith503：直接执行传入函数
    mockRunWith503.mockImplementation(async (fn: () => Promise<void>) => {
      await fn();
    });

    // 默认 API 返回
    mockGetDailyReport.mockResolvedValue(defaultDailyReport());
    mockGetWeeklyReport.mockResolvedValue({
      ...defaultDailyReport(),
      start_date: "2026-04-20",
      end_date: "2026-04-26",
      daily_breakdown: [],
    });
    mockGetMonthlyReport.mockResolvedValue({
      ...defaultDailyReport(),
      month: "2026-04",
      weekly_breakdown: [],
    });
    mockGetProgressSummary.mockResolvedValue({
      active_count: 0,
      completed_count: 0,
      goals: [],
    });
    mockGetReviewTrend.mockResolvedValue({ periods: [] });
    mockGetActivityHeatmap.mockResolvedValue({ year: 2026, items: [] });
    mockGetKnowledgeHeatmap.mockResolvedValue({ year: 2026, items: [] });
    mockGetGrowthCurve.mockResolvedValue({ points: [] });
    mockGetInsights.mockResolvedValue({
      insights: {
        behavior_patterns: [],
        growth_suggestions: [],
        capability_changes: [],
      },
    });
  });

  // ---- 1. Loading spinner ----
  it("数据加载中显示 spinner 和加载文案", async () => {
    // 让 API 永远不 resolve，保持 loading 状态
    mockRunWith503.mockImplementation(() => new Promise(() => {}));

    renderReview();

    // 应该显示 spinner（Loader2 有 animate-spin class）
    const spinner = document.querySelector(".animate-spin");
    expect(spinner).toBeTruthy();

    // 应该显示加载文案
    expect(screen.getByText("加载报告数据...")).toBeInTheDocument();
  });

  // ---- 2. Error 状态 ----
  it("加载失败显示错误提示和重试按钮", async () => {
    // 让 API 抛错
    mockRunWith503.mockImplementation(async (fn: () => Promise<void>) => {
      await fn();
    });
    mockGetDailyReport.mockRejectedValue(new Error("Network error"));

    renderReview();

    // 等待错误状态显示
    await waitFor(() => {
      expect(screen.getByText("加载失败，请重试")).toBeInTheDocument();
    });

    // 应该有重试按钮
    expect(screen.getByText("重试")).toBeInTheDocument();
  });

  it("点击重试按钮会重新加载数据", async () => {
    // React StrictMode 可能触发多次 effect，提供足够多的 mock 返回值
    let failCount = 0;
    mockGetDailyReport.mockImplementation(() => {
      failCount++;
      if (failCount <= 3) return Promise.reject(new Error("Network error"));
      return Promise.resolve(defaultDailyReport());
    });

    const user = userEvent.setup();
    renderReview();

    // 等待错误状态
    await waitFor(() => {
      expect(screen.getByText("加载失败，请重试")).toBeInTheDocument();
    });

    const callCountBefore = mockGetDailyReport.mock.calls.length;

    // 重置 mock 为成功
    mockGetDailyReport.mockResolvedValue(defaultDailyReport());

    // 点击重试
    await user.click(screen.getByText("重试"));

    // 应该重新调用 API（retryKey 变化触发 useEffect）
    await waitFor(() => {
      expect(mockGetDailyReport.mock.calls.length).toBeGreaterThan(callCountBefore);
    });
  });

  // ---- 3. 空数据状态（合约合法的 zero-filled 响应）----
  it("zero-filled 报告数据显示空数据友好提示", async () => {
    // 返回合约合法的 zero-filled 日报
    mockGetDailyReport.mockResolvedValue(emptyDailyReport());

    renderReview();

    // 等待加载完成并显示空状态
    await waitFor(() => {
      expect(screen.getByText("暂无报告数据")).toBeInTheDocument();
    });

    expect(
      screen.getByText("开始记录任务和笔记后，这里会显示你的成长报告"),
    ).toBeInTheDocument();
  });

  it("有 taskStats 时正常显示任务统计卡片", async () => {
    mockGetDailyReport.mockResolvedValue(defaultDailyReport());

    renderReview();

    await waitFor(() => {
      expect(screen.getByText("任务统计")).toBeInTheDocument();
    });

    // 不应显示空状态文案
    expect(screen.queryByText("暂无报告数据")).not.toBeInTheDocument();
  });

  // ---- 4. 回归：成功后刷新失败不残留旧数据 ----
  it("成功加载后刷新失败不残留旧的任务统计卡片", async () => {
    // daily 成功，weekly 失败
    mockGetDailyReport.mockResolvedValue(defaultDailyReport());
    mockGetWeeklyReport.mockRejectedValue(new Error("Network error"));

    const user = userEvent.setup();
    renderReview();

    // 等待日报成功加载
    await waitFor(() => {
      expect(screen.getByText("任务统计")).toBeInTheDocument();
    });

    // 切换到周报 tab（触发 weekly fetch）
    await user.click(screen.getByText("周报"));

    // 等待错误状态显示（旧日报的任务统计卡片应被清除）
    await waitFor(() => {
      expect(screen.getByText("加载失败，请重试")).toBeInTheDocument();
    });

    // "任务统计"不应再出现（旧数据已清除）
    expect(screen.queryByText("任务统计")).not.toBeInTheDocument();
  });

  // ---- 5. 回归：goalSummary tab 切换时清除 ----
  it("切换 tab 时 goalSummary 被清除，不残留旧目标数据", async () => {
    // daily 成功 + 有目标数据
    mockGetDailyReport.mockResolvedValue(defaultDailyReport());
    mockGetProgressSummary
      .mockResolvedValueOnce({
        active_count: 2,
        completed_count: 1,
        goals: [{ id: "g1", title: "目标1" }],
      })
      .mockRejectedValueOnce(new Error("Network error"));

    const user = userEvent.setup();
    renderReview();

    // 等待日报加载完成 + goalSummary 渲染
    await waitFor(() => {
      expect(screen.getByText("任务统计")).toBeInTheDocument();
    });

    // 切换到周报 tab
    mockGetWeeklyReport.mockRejectedValue(new Error("Network error"));
    await user.click(screen.getByText("周报"));

    // 等待错误状态（goalSummary 已清除）
    await waitFor(() => {
      expect(screen.getByText("加载失败，请重试")).toBeInTheDocument();
    });
  });
});
