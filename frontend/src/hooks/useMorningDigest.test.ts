/**
 * F117: 晨报展示优化 — hook 测试
 *
 * 验证:
 * 1. cached_at 非 null 时 hook 返回数据包含该字段
 * 2. cached_at 为 null 时不包含更新时间
 * 3. cached_at 缺失（旧后端）时向前兼容
 * 4. pattern_insights 支持最多 5 条
 * 5. 空 pattern_insights 时不崩溃
 * 6. 加载态和错误态正确
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useMorningDigest } from "./useMorningDigest";
import type { MorningDigestResponse } from "@/services/api";

// Mock API
const mockGetMorningDigest = vi.fn();
vi.mock("@/services/api", () => ({
  getMorningDigest: () => mockGetMorningDigest(),
}));

const baseDigest: MorningDigestResponse = {
  date: "2026-04-24",
  ai_suggestion: "今天可以专注完成一个重要任务",
  todos: [],
  overdue: [],
  stale_inbox: [],
  weekly_summary: { new_concepts: [], entries_count: 0 },
  pattern_insights: [],
};

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("useMorningDigest — F117 晨报展示优化", () => {
  it("cached_at 非 null 时数据包含 cached_at 字段", async () => {
    const digest = { ...baseDigest, cached_at: "2026-04-24T09:30:00" };
    mockGetMorningDigest.mockResolvedValue(digest);

    const { result } = renderHook(() => useMorningDigest());

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.error).toBe(false);
    expect(result.current.data?.cached_at).toBe("2026-04-24T09:30:00");
  });

  it("cached_at 为 null 时数据包含 cached_at 但值为 null", async () => {
    const digest = { ...baseDigest, cached_at: null };
    mockGetMorningDigest.mockResolvedValue(digest);

    const { result } = renderHook(() => useMorningDigest());

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.data?.cached_at).toBeNull();
  });

  it("cached_at 缺失（旧后端）时向前兼容，不崩溃", async () => {
    // 旧后端不返回 cached_at
    const digest = { ...baseDigest };
    mockGetMorningDigest.mockResolvedValue(digest);

    const { result } = renderHook(() => useMorningDigest());

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.error).toBe(false);
    // cached_at 未定义，falsy → 不显示更新时间
    expect(result.current.data?.cached_at).toBeFalsy();
  });

  it("pattern_insights 支持最多 5 条展示", async () => {
    const insights = ["洞察1", "洞察2", "洞察3", "洞察4", "洞察5"];
    const digest = { ...baseDigest, pattern_insights: insights };
    mockGetMorningDigest.mockResolvedValue(digest);

    const { result } = renderHook(() => useMorningDigest());

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.data?.pattern_insights).toHaveLength(5);
    expect(result.current.data?.pattern_insights).toEqual(insights);
  });

  it("空 pattern_insights 不崩溃", async () => {
    const digest = { ...baseDigest, pattern_insights: [] };
    mockGetMorningDigest.mockResolvedValue(digest);

    const { result } = renderHook(() => useMorningDigest());

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.data?.pattern_insights).toEqual([]);
  });

  it("加载态正确：初始 loading=true，完成后 loading=false", async () => {
    let resolvePromise: (v: MorningDigestResponse) => void;
    mockGetMorningDigest.mockReturnValue(
      new Promise<MorningDigestResponse>((resolve) => {
        resolvePromise = resolve;
      })
    );

    const { result } = renderHook(() => useMorningDigest());

    expect(result.current.loading).toBe(true);
    expect(result.current.data).toBeNull();

    resolvePromise!(baseDigest);

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.data).toBeTruthy();
  });

  it("API 失败时 error=true", async () => {
    mockGetMorningDigest.mockRejectedValue(new Error("Network error"));

    const { result } = renderHook(() => useMorningDigest());

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.error).toBe(true);
    expect(result.current.data).toBeNull();
  });
});
