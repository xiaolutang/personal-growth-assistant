import { describe, it, expect, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useServiceUnavailable } from "@/hooks/useServiceUnavailable";
import { ApiError } from "@/lib/errors";

describe("useServiceUnavailable", () => {
  it("初始状态 serviceUnavailable 为 false", () => {
    const { result } = renderHook(() => useServiceUnavailable());
    expect(result.current.serviceUnavailable).toBe(false);
  });

  it("503 错误设置 serviceUnavailable=true", async () => {
    const { result } = renderHook(() => useServiceUnavailable());
    const error503 = new ApiError(503, "Service Unavailable", {});

    await act(async () => {
      await result.current.runWith503(async () => {
        throw error503;
      });
    });

    expect(result.current.serviceUnavailable).toBe(true);
  });

  it("成功执行后重置 serviceUnavailable=false", async () => {
    const { result } = renderHook(() => useServiceUnavailable());
    const error503 = new ApiError(503, "Service Unavailable", {});

    // 先触发 503
    await act(async () => {
      await result.current.runWith503(async () => {
        throw error503;
      });
    });
    expect(result.current.serviceUnavailable).toBe(true);

    // 再成功执行
    await act(async () => {
      await result.current.runWith503(async () => {
        // 成功
      });
    });
    expect(result.current.serviceUnavailable).toBe(false);
  });

  it("非 503 错误原样抛出，不设置 serviceUnavailable", async () => {
    const { result } = renderHook(() => useServiceUnavailable());
    const error500 = new ApiError(500, "Internal Server Error", {});

    await expect(
      act(async () => {
        await result.current.runWith503(async () => {
          throw error500;
        });
      })
    ).rejects.toThrow("Internal Server Error");

    expect(result.current.serviceUnavailable).toBe(false);
  });

  it("普通 Error 原样抛出", async () => {
    const { result } = renderHook(() => useServiceUnavailable());

    await expect(
      act(async () => {
        await result.current.runWith503(async () => {
          throw new Error("网络错误");
        });
      })
    ).rejects.toThrow("网络错误");

    expect(result.current.serviceUnavailable).toBe(false);
  });

  it("retry 清除状态并重新执行", async () => {
    const { result } = renderHook(() => useServiceUnavailable());
    const fn = vi.fn().mockResolvedValue(undefined);

    // 先触发 503
    const error503 = new ApiError(503, "Service Unavailable", {});
    await act(async () => {
      await result.current.runWith503(async () => {
        throw error503;
      });
    });
    expect(result.current.serviceUnavailable).toBe(true);

    // retry
    await act(async () => {
      result.current.retry(fn);
    });

    expect(result.current.serviceUnavailable).toBe(false);
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it("retry 后 fn 内部 503 再次触发时保持 serviceUnavailable=true", async () => {
    const { result } = renderHook(() => useServiceUnavailable());
    const error503 = new ApiError(503, "Service Unavailable", {});

    // 先触发 503
    await act(async () => {
      await result.current.runWith503(async () => {
        throw error503;
      });
    });
    expect(result.current.serviceUnavailable).toBe(true);

    // retry 时 fn 内部又 503（模拟：fn 内部调用 runWith503 并再次遇到 503）
    const fnThat503s = vi.fn().mockImplementation(async () => {
      await result.current.runWith503(async () => {
        throw error503;
      });
    });

    await act(async () => {
      result.current.retry(fnThat503s);
    });

    // 应仍为 true：retry 清了状态，但 fn 内部 runWith503 又设回 true
    expect(result.current.serviceUnavailable).toBe(true);
    expect(fnThat503s).toHaveBeenCalledTimes(1);
  });
});
