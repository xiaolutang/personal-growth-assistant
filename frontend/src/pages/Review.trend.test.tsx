import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import { Review } from "./Review";
import { ThemeProvider } from "@/lib/theme";

// --- Mocks ---

// Mock recharts — 测试环境不需要真正渲染 SVG
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

// Mock authFetch — Review 主报告用到，返回空日报让它不报错
const mockAuthFetch = vi.fn();
vi.mock("@/lib/authFetch", () => ({
  authFetch: (...args: unknown[]) => mockAuthFetch(...args),
  buildAuthHeaders: () => new Headers(),
}));

// Mock getReviewTrend — 趋势 API
const mockGetReviewTrend = vi.fn();
vi.mock("@/services/api", () => ({
  getReviewTrend: (...args: unknown[]) => mockGetReviewTrend(...args),
  getActivityHeatmap: () => Promise.resolve({ year: 2026, items: [] }),
  getKnowledgeHeatmap: () => Promise.resolve({ year: 2026, items: [] }),
  getGrowthCurve: () => Promise.resolve([]),
  getProgressSummary: () =>
    Promise.resolve({ active_count: 0, completed_count: 0, goals: [] }),
}));

// 辅助：创建空日报 Response（主报告默认不报错）
function emptyDailyReportResponse() {
  return Promise.resolve({
    ok: true,
    json: () =>
      Promise.resolve({
        date: "2026-04-14",
        task_stats: { total: 0, completed: 0, doing: 0, wait_start: 0, completion_rate: 0 },
        note_stats: { total: 0, recent_titles: [] },
        completed_tasks: [],
      }),
  } as unknown as Response);
}

// 辅助：测试用趋势数据
function makeTrendPeriods(count: number) {
  return Array.from({ length: count }, (_, i) => ({
    date: `2026-04-${String(14 - i).padStart(2, "0")}`,
    total: 5 + i,
    completed: 3 + i,
    completion_rate: 50 + i * 5,
    notes_count: 1,
    task_count: 3 + i,
    inbox_count: 1,
  }));
}

function renderReview() {
  return render(
    <MemoryRouter>
      <ThemeProvider>
        <Review />
      </ThemeProvider>
    </MemoryRouter>,
  );
}

describe("Review — 趋势折线图", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // 默认：主报告返回空日报
    mockAuthFetch.mockImplementation(emptyDailyReportResponse);
    // 默认：趋势 API 返回空数据
    mockGetReviewTrend.mockResolvedValue({ periods: [] });
  });

  // ---- 1. 正常：趋势卡片渲染 ----
  it("加载时显示 loading，完成后显示折线图", async () => {
    mockGetReviewTrend.mockResolvedValue({
      periods: makeTrendPeriods(3),
    });

    renderReview();

    // loading 状态
    expect(screen.getByText("加载趋势数据...")).toBeInTheDocument();

    // 等待数据加载完成
    await waitFor(() => {
      expect(screen.getByText("完成率趋势")).toBeInTheDocument();
    });

    // 折线图组件应该被渲染（4 条线：完成率 + 任务数 + 笔记数 + 灵感数）
    expect(screen.getByTestId("recharts-linechart")).toBeInTheDocument();
    expect(screen.getAllByTestId("recharts-line").length).toBeGreaterThanOrEqual(1);
  });

  // ---- 2. 日/周切换 ----
  it("点击「周」Badge 后 getReviewTrend 以 period=weekly 被调用", async () => {
    mockGetReviewTrend.mockResolvedValue({
      periods: makeTrendPeriods(4),
    });

    const user = userEvent.setup();
    renderReview();

    // 等待首次加载完成
    await waitFor(() => {
      expect(screen.getByText("完成率趋势")).toBeInTheDocument();
    });

    // 初始调用应为 daily
    expect(mockGetReviewTrend).toHaveBeenCalledWith("daily", 7);

    // 点击「周」
    await user.click(screen.getByText("周"));

    await waitFor(() => {
      expect(mockGetReviewTrend).toHaveBeenCalledWith("weekly", 8);
    });
  });

  // ---- 3. 空数据引导文案 ----
  it("getReviewTrend 返回空 periods 时显示「暂无趋势数据」", async () => {
    mockGetReviewTrend.mockResolvedValue({ periods: [] });

    renderReview();

    await waitFor(() => {
      expect(screen.getByText("暂无趋势数据")).toBeInTheDocument();
    });

    expect(
      screen.getByText("持续记录任务完成情况，趋势图将自动生成"),
    ).toBeInTheDocument();
  });

  // ---- 4. API 错误提示 ----
  it("getReviewTrend 抛错时显示「趋势数据加载失败」", async () => {
    mockGetReviewTrend.mockRejectedValue(new Error("Network error"));

    renderReview();

    await waitFor(() => {
      expect(screen.getByText("趋势数据加载失败，请稍后重试")).toBeInTheDocument();
    });
  });

  // ---- 5. 平均完成率摘要 ----
  it("有数据时图表下方显示平均完成率百分比", async () => {
    const periods = [
      { date: "2026-04-14", total: 5, completed: 3, completion_rate: 60.0, notes_count: 1, task_count: 3, inbox_count: 0 },
      { date: "2026-04-13", total: 4, completed: 2, completion_rate: 40.0, notes_count: 0, task_count: 2, inbox_count: 1 },
    ];
    mockGetReviewTrend.mockResolvedValue({ periods });

    renderReview();

    // 平均 = (60 + 40) / 2 = 50.0%
    await waitFor(() => {
      expect(screen.getByText("近 7 天平均完成率")).toBeInTheDocument();
    });
    expect(screen.getByText("50.0%")).toBeInTheDocument();
  });

  // ---- 6. 错误不影响主报告区域 ----
  it("趋势 API 失败时，日报/周报/月报选择器仍正常显示", async () => {
    mockGetReviewTrend.mockRejectedValue(new Error("fail"));

    renderReview();

    // 等待趋势错误显示
    await waitFor(() => {
      expect(screen.getByText("趋势数据加载失败，请稍后重试")).toBeInTheDocument();
    });

    // 选择器应仍然可交互
    expect(screen.getByText("日报")).toBeInTheDocument();
    expect(screen.getByText("周报")).toBeInTheDocument();
    expect(screen.getByText("月报")).toBeInTheDocument();
  });

  // ---- 7. 只有 1 天数据时折线图不报错 ----
  it("只有 1 天数据时折线图正常渲染且显示摘要", async () => {
    const periods = [
      { date: "2026-04-14", total: 3, completed: 2, completion_rate: 66.7, notes_count: 0, task_count: 2, inbox_count: 0 },
    ];
    mockGetReviewTrend.mockResolvedValue({ periods });

    renderReview();

    // 等待数据加载完成
    await waitFor(() => {
      expect(screen.getByTestId("recharts-linechart")).toBeInTheDocument();
    });

    // 1 天数据的摘要也应该正确显示
    expect(screen.getByText("66.7%")).toBeInTheDocument();
    expect(screen.getByText("近 7 天平均完成率")).toBeInTheDocument();
  });
});
