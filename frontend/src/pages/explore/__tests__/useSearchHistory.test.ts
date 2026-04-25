import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";

// Mock utils localStorage helpers
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => { store[key] = value; }),
    removeItem: vi.fn((key: string) => { delete store[key]; }),
    clear: vi.fn(() => { store = {}; }),
  };
})();
Object.defineProperty(window, "localStorage", { value: localStorageMock });

import { useSearchHistory } from "../useSearchHistory";

describe("useSearchHistory", () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.clearAllMocks();
  });

  it("初始从 localStorage 加载历史", () => {
    localStorageMock.setItem("search_history", JSON.stringify(["q1", "q2"]));
    const { result } = renderHook(() => useSearchHistory());
    expect(result.current.searchHistory).toEqual(["q1", "q2"]);
  });

  it("空 localStorage 返回空数组", () => {
    const { result } = renderHook(() => useSearchHistory());
    expect(result.current.searchHistory).toEqual([]);
  });

  it("removeHistory 移除条目", () => {
    localStorageMock.setItem("search_history", JSON.stringify(["q1", "q2"]));
    const { result } = renderHook(() => useSearchHistory());

    act(() => {
      result.current.removeHistory("q1");
    });

    expect(result.current.searchHistory).toEqual(["q2"]);
  });

  it("refresh 从 localStorage 重新加载", () => {
    const { result } = renderHook(() => useSearchHistory());
    expect(result.current.searchHistory).toEqual([]);

    // 外部修改 localStorage
    localStorageMock.setItem("search_history", JSON.stringify(["new"]));

    act(() => {
      result.current.refresh();
    });

    expect(result.current.searchHistory).toEqual(["new"]);
  });
});
