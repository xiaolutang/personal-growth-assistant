/**
 * fetch 拦截器测试
 *
 * 测试 Authorization header 自动注入、X-UID 注入、401 自动登出
 */
import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    }),
  };
})();
Object.defineProperty(globalThis, "localStorage", { value: localStorageMock });

// Mock window.location
const originalLocation = window.location;
let locationHref = "";
Object.defineProperty(window, "location", {
  value: {
    ...originalLocation,
    get pathname() {
      return "/tasks";
    },
    set href(val: string) {
      locationHref = val;
    },
  },
  writable: true,
});

// Mock crypto.randomUUID
Object.defineProperty(globalThis, "crypto", {
  value: {
    randomUUID: () => "test-uuid-1234",
  },
});

// Mock import.meta.env
vi.stubGlobal("import.meta", {
  env: { BASE_URL: "/" },
});

// 保存原始 fetch
const originalFetch = globalThis.fetch;

describe("initFetchInterceptor", () => {
  let mockFetch: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    localStorageMock.clear();
    vi.clearAllMocks();
    // 恢复原始 fetch 以便重新初始化拦截器
    globalThis.fetch = originalFetch;
    mockFetch = vi.fn().mockResolvedValue(new Response(null, { status: 200 }));
    globalThis.fetch = mockFetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("有 token 时自动注入 Authorization header", async () => {
    localStorageMock.getItem.mockImplementation(
      (key: string) => (key === "pga_token" ? "my-jwt-token" : key === "pga_uid" ? null : null)
    );

    const { initFetchInterceptor } = await import("./uid");
    initFetchInterceptor();

    await fetch("/api/test");

    expect(mockFetch).toHaveBeenCalled();
    const callArgs = mockFetch.mock.calls[0];
    const init = callArgs[1];
    const headers = new Headers(init.headers);
    expect(headers.get("Authorization")).toBe("Bearer my-jwt-token");
  });

  it("无 token 时不注入 Authorization header", async () => {
    localStorageMock.getItem.mockReturnValue(null);

    const { initFetchInterceptor } = await import("./uid");
    initFetchInterceptor();

    await fetch("/api/test");

    const callArgs = mockFetch.mock.calls[0];
    const init = callArgs[1];
    const headers = new Headers(init.headers);
    expect(headers.get("Authorization")).toBeNull();
  });

  it("401 响应时清除 token 和 user", async () => {
    localStorageMock.getItem.mockImplementation(
      (key: string) => (key === "pga_token" ? "expired-token" : null)
    );
    mockFetch.mockResolvedValue(new Response(null, { status: 401 }));

    const { initFetchInterceptor } = await import("./uid");
    initFetchInterceptor();

    await fetch("/api/protected");

    expect(localStorageMock.removeItem).toHaveBeenCalledWith("pga_token");
    expect(localStorageMock.removeItem).toHaveBeenCalledWith("pga_user");
  });

  it("401 时在非登录页跳转到登录页", async () => {
    localStorageMock.getItem.mockImplementation(
      (key: string) => (key === "pga_token" ? "expired-token" : null)
    );
    mockFetch.mockResolvedValue(new Response(null, { status: 401 }));

    const { initFetchInterceptor } = await import("./uid");
    initFetchInterceptor();

    await fetch("/api/protected");

    expect(locationHref).toBe("/login");
  });

  it("200 响应时不清除 token", async () => {
    localStorageMock.getItem.mockImplementation(
      (key: string) => (key === "pga_token" ? "valid-token" : null)
    );
    mockFetch.mockResolvedValue(new Response(null, { status: 200 }));

    const { initFetchInterceptor } = await import("./uid");
    initFetchInterceptor();

    await fetch("/api/test");

    expect(localStorageMock.removeItem).not.toHaveBeenCalledWith("pga_token");
  });

  it("已有 Authorization header 时不覆盖", async () => {
    localStorageMock.getItem.mockImplementation(
      (key: string) => (key === "pga_token" ? "store-token" : null)
    );

    const { initFetchInterceptor } = await import("./uid");
    initFetchInterceptor();

    await fetch("/api/test", {
      headers: { Authorization: "Custom custom-token" },
    });

    const callArgs = mockFetch.mock.calls[0];
    const init = callArgs[1];
    const headers = new Headers(init.headers);
    expect(headers.get("Authorization")).toBe("Custom custom-token");
  });
});
