/**
 * reviewFormatter.ts 单元测试
 */

import { describe, it, expect } from "vitest";
import {
  formatReviewReport,
  formatShortReview,
  generateReviewReport,
  type ReviewReport,
} from "./reviewFormatter";

// 构造测试用的条目数据
function createMockEntry(overrides: Record<string, unknown> = {}) {
  return {
    id: "test-id",
    title: "测试条目",
    score: 0.9,
    type: "task",
    category: "task",
    status: "complete" as const,
    tags: [] as string[],
    created_at: new Date().toISOString(),
    file_path: "test.md",
    ...overrides,
  };
}

describe("formatReviewReport", () => {
  const baseReport: ReviewReport = {
    type: "daily",
    dateRange: { start: "2026-04-11", end: "2026-04-11" },
    taskStats: {
      total: 10,
      completed: 5,
      inProgress: 3,
      pending: 2,
      completionRate: 50,
    },
    categoryStats: { task: 6, note: 4 },
    tagStats: { TypeScript: 3, React: 2 },
    recentEntries: [],
    highlights: [],
  };

  it("应该格式化日报标题", () => {
    const result = formatReviewReport({ ...baseReport, type: "daily" });
    expect(result).toContain("今日回顾");
  });

  it("应该格式化周报标题", () => {
    const result = formatReviewReport({ ...baseReport, type: "weekly" });
    expect(result).toContain("本周回顾");
  });

  it("应该格式化月报标题", () => {
    const result = formatReviewReport({ ...baseReport, type: "monthly" });
    expect(result).toContain("本月回顾");
  });

  it("应该包含时间范围", () => {
    const result = formatReviewReport(baseReport);
    expect(result).toContain("2026-04-11 ~ 2026-04-11");
  });

  it("应该包含任务统计表格", () => {
    const result = formatReviewReport(baseReport);
    expect(result).toContain("总任务");
    expect(result).toContain("10");
    expect(result).toContain("已完成");
    expect(result).toContain("5");
    expect(result).toContain("进行中");
    expect(result).toContain("3");
    expect(result).toContain("待开始");
    expect(result).toContain("2");
    expect(result).toContain("50%");
  });

  it("应该包含分类统计（按数量降序）", () => {
    const result = formatReviewReport(baseReport);
    const taskIndex = result.indexOf("任务: 6");
    const noteIndex = result.indexOf("笔记: 4");
    expect(taskIndex).toBeGreaterThan(-1);
    expect(noteIndex).toBeGreaterThan(-1);
    expect(taskIndex).toBeLessThan(noteIndex);
  });

  it("应该包含标签云", () => {
    const result = formatReviewReport(baseReport);
    expect(result).toContain("标签云");
    expect(result).toContain("`TypeScript`(3)");
    expect(result).toContain("`React`(2)");
  });

  it("没有标签时不应该显示标签云", () => {
    const report = { ...baseReport, tagStats: {} };
    const result = formatReviewReport(report);
    expect(result).not.toContain("标签云");
  });

  it("应该包含亮点", () => {
    const report = {
      ...baseReport,
      highlights: ["完成了核心功能", "修复了关键bug"],
    };
    const result = formatReviewReport(report);
    expect(result).toContain("今日亮点");
    expect(result).toContain("完成了核心功能");
    expect(result).toContain("修复了关键bug");
  });

  it("没有亮点时不应该显示亮点区域", () => {
    const result = formatReviewReport(baseReport);
    expect(result).not.toContain("今日亮点");
  });

  it("应该包含最近条目", () => {
    const report = {
      ...baseReport,
      recentEntries: [
        createMockEntry({ title: "完成的任务", status: "complete" }),
        createMockEntry({ title: "进行中的任务", status: "doing" }),
        createMockEntry({ title: "待开始的任务", status: "waitStart" }),
      ],
    };
    const result = formatReviewReport(report);
    expect(result).toContain("最近记录");
    expect(result).toContain("完成的任务");
    expect(result).toContain("进行中的任务");
    expect(result).toContain("待开始的任务");
  });

  it("最近条目应该有正确的状态图标", () => {
    const report = {
      ...baseReport,
      recentEntries: [
        createMockEntry({ title: "任务A", status: "complete" }),
        createMockEntry({ title: "任务B", status: "doing" }),
        createMockEntry({ title: "任务C", status: "waitStart" }),
      ],
    };
    const result = formatReviewReport(report);
    expect(result).toContain("✅");
    expect(result).toContain("🔄");
    expect(result).toContain("⏳");
  });

  it("最多显示 5 个最近条目", () => {
    const entries = Array.from({ length: 8 }, (_, i) =>
      createMockEntry({ title: `条目${i + 1}` })
    );
    const report = { ...baseReport, recentEntries: entries };
    const result = formatReviewReport(report);

    // 只包含前 5 个
    expect(result).toContain("条目1");
    expect(result).toContain("条目5");
    expect(result).not.toContain("条目6");
  });
});

describe("formatShortReview", () => {
  const baseReport: ReviewReport = {
    type: "daily",
    dateRange: { start: "2026-04-11", end: "2026-04-11" },
    taskStats: {
      total: 10,
      completed: 7,
      inProgress: 2,
      pending: 1,
      completionRate: 70,
    },
    categoryStats: { task: 6, note: 3, inbox: 1 },
    tagStats: {},
    recentEntries: [],
    highlights: [],
  };

  it("日报应该包含'今日回顾'", () => {
    const result = formatShortReview(baseReport);
    expect(result).toContain("今日回顾");
  });

  it("周报应该包含'本周回顾'", () => {
    const result = formatShortReview({ ...baseReport, type: "weekly" });
    expect(result).toContain("本周回顾");
  });

  it("月报应该包含'本月回顾'", () => {
    const result = formatShortReview({ ...baseReport, type: "monthly" });
    expect(result).toContain("本月回顾");
  });

  it("应该包含任务完成情况", () => {
    const result = formatShortReview(baseReport);
    expect(result).toContain("总任务: 10");
    expect(result).toContain("已完成: 7");
    expect(result).toContain("完成率: 70%");
  });

  it("应该包含分类统计", () => {
    const result = formatShortReview(baseReport);
    expect(result).toContain("任务: 6");
    expect(result).toContain("笔记: 3");
    expect(result).toContain("灵感: 1");
  });
});

describe("generateReviewReport", () => {
  const today = new Date().toISOString().split("T")[0];

  it("日报应该包含今天的条目", () => {
    const entries = [
      createMockEntry({ title: "今天的任务", created_at: new Date().toISOString() }),
      createMockEntry({
        title: "很久以前的任务",
        created_at: "2020-01-01T00:00:00Z",
      }),
    ];

    const report = generateReviewReport(entries, "daily");

    expect(report.type).toBe("daily");
    expect(report.taskStats.total).toBe(1);
    expect(report.taskStats.completed).toBe(1);
  });

  it("周报应该包含最近 7 天的条目", () => {
    const threeDaysAgo = new Date();
    threeDaysAgo.setDate(threeDaysAgo.getDate() - 3);

    const entries = [
      createMockEntry({ title: "今天的", created_at: new Date().toISOString() }),
      createMockEntry({ title: "3天前的", created_at: threeDaysAgo.toISOString() }),
      createMockEntry({
        title: "去年的",
        created_at: "2020-01-01T00:00:00Z",
      }),
    ];

    const report = generateReviewReport(entries, "weekly");

    expect(report.type).toBe("weekly");
    expect(report.taskStats.total).toBe(2);
  });

  it("月报应该包含本月条目", () => {
    const entries = [
      createMockEntry({ title: "今天的", created_at: new Date().toISOString() }),
      createMockEntry({
        title: "去年的",
        created_at: "2020-01-01T00:00:00Z",
      }),
    ];

    const report = generateReviewReport(entries, "monthly");

    expect(report.type).toBe("monthly");
    expect(report.taskStats.total).toBe(1);
    // 月报的 start 应该是当月第一天
    expect(report.dateRange.start).toBe(today.substring(0, 8) + "01");
  });

  it("空条目列表应返回零统计", () => {
    const report = generateReviewReport([], "daily");

    expect(report.taskStats.total).toBe(0);
    expect(report.taskStats.completed).toBe(0);
    expect(report.taskStats.inProgress).toBe(0);
    expect(report.taskStats.pending).toBe(0);
    expect(report.taskStats.completionRate).toBe(0);
  });

  it("应该正确统计完成率", () => {
    const entries = [
      createMockEntry({ status: "complete" }),
      createMockEntry({ status: "complete" }),
      createMockEntry({ status: "doing" }),
      createMockEntry({ status: "waitStart" }),
    ];

    const report = generateReviewReport(entries, "daily");

    expect(report.taskStats.total).toBe(4);
    expect(report.taskStats.completed).toBe(2);
    expect(report.taskStats.completionRate).toBe(50);
  });

  it("应该正确统计分类", () => {
    const entries = [
      createMockEntry({ category: "task" }),
      createMockEntry({ category: "task" }),
      createMockEntry({ category: "note" }),
    ];

    const report = generateReviewReport(entries, "daily");

    expect(report.categoryStats.task).toBe(2);
    expect(report.categoryStats.note).toBe(1);
  });

  it("没有分类的条目应归入 other", () => {
    const entry = createMockEntry({ category: "" as any });

    const report = generateReviewReport([entry], "daily");

    expect(report.categoryStats.other).toBe(1);
  });

  it("应该正确统计标签", () => {
    const entries = [
      createMockEntry({ tags: ["TypeScript", "React"] }),
      createMockEntry({ tags: ["TypeScript"] }),
      createMockEntry({ tags: [] }),
    ];

    const report = generateReviewReport(entries, "daily");

    expect(report.tagStats.TypeScript).toBe(2);
    expect(report.tagStats.React).toBe(1);
  });

  it("应该生成高优先级已完成任务的亮点", () => {
    const entries = [
      createMockEntry({ status: "complete", priority: "high", title: "重要任务" }),
      createMockEntry({ status: "complete", priority: "low", title: "低优先级任务" }),
      createMockEntry({ status: "doing", priority: "high", title: "进行中的高优先级" }),
    ];

    const report = generateReviewReport(entries, "daily");

    expect(report.highlights).toEqual(["重要任务"]);
  });

  it("亮点最多 3 个", () => {
    const entries = Array.from({ length: 5 }, (_, i) =>
      createMockEntry({
        status: "complete",
        priority: "high",
        title: `重要任务${i + 1}`,
      })
    );

    const report = generateReviewReport(entries, "daily");

    expect(report.highlights).toHaveLength(3);
  });

  it("日期范围应该正确", () => {
    const report = generateReviewReport([], "daily");
    expect(report.dateRange.end).toBe(today);

    const weeklyReport = generateReviewReport([], "weekly");
    const weekStart = new Date();
    weekStart.setDate(weekStart.getDate() - 7);
    expect(weeklyReport.dateRange.start).toBe(
      weekStart.toISOString().split("T")[0]
    );
  });
});
