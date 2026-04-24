/**
 * userStore 离线启动恢复 单元测试
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { useUserStore } from "../userStore";

// Mock fetch for logout API call
const mockFetch = vi.fn();
Object.defineProperty(globalThis, "fetch", { value: mockFetch, writable: true });

// Mock authFetch
vi.mock("@/lib/authFetch", () => ({
  authFetch: vi.fn(),
}));

// Mock API_BASE
vi.mock("@/config/api", () => ({
  API_BASE: "/api",
}));

import { authFetch } from "@/lib/authFetch";
const mockedAuthFetch = vi.mocked(authFetch);

describe("userStore 离线启动恢复", () => {
  beforeEach(() => {
    localStorage.clear();
    useUserStore.setState({
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: false,
    });
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("网络失败 (TypeError: Failed to fetch) 时不调用 logout，保留 token 和 user", async () => {
    // 设置已登录状态
    const token = "test-token-123";
    const user = {
      id: "1",
      username: "testuser",
      email: "test@test.com",
      is_active: true,
      onboarding_completed: true,
    };
    localStorage.setItem("pga_token", token);
    localStorage.setItem("pga_user", JSON.stringify(user));
    useUserStore.setState({ token, user, isAuthenticated: true });

    // 模拟网络失败
    mockedAuthFetch.mockRejectedValueOnce(
      new TypeError("Failed to fetch")
    );

    await useUserStore.getState().fetchMe();

    // 验证：token 和 user 保留，不调用 logout
    const state = useUserStore.getState();
    expect(state.token).toBe(token);
    expect(state.user).toEqual(user);
    expect(state.isAuthenticated).toBe(true);
    expect(localStorage.getItem("pga_token")).toBe(token);
  });

  it("/auth/me 返回 401 时调用 logout，清除 token", async () => {
    const token = "test-token-456";
    const user = {
      id: "1",
      username: "testuser",
      email: "test@test.com",
      is_active: true,
      onboarding_completed: true,
    };
    localStorage.setItem("pga_token", token);
    localStorage.setItem("pga_user", JSON.stringify(user));
    useUserStore.setState({ token, user, isAuthenticated: true });

    // 模拟 401 响应
    mockedAuthFetch.mockResolvedValueOnce({
      ok: false,
      status: 401,
      json: async () => ({ detail: "Unauthorized" }),
    } as Response);

    // logout 会调 fetch POST /auth/logout
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ message: "logged out" }),
    });

    await useUserStore.getState().fetchMe();

    // 等待 async logout 完成
    await vi.waitFor(() => {
      expect(useUserStore.getState().token).toBeNull();
    }, { timeout: 2000 });

    // 验证：logout 被调用
    const state = useUserStore.getState();
    expect(state.token).toBeNull();
    expect(state.user).toBeNull();
    expect(state.isAuthenticated).toBe(false);
    expect(localStorage.getItem("pga_token")).toBeNull();
  });

  it("fetchMe 成功时正常更新 user", async () => {
    const token = "test-token-789";
    useUserStore.setState({ token, isAuthenticated: true });

    const updatedUser = {
      id: "1",
      username: "testuser",
      email: "new@test.com",
      is_active: true,
      onboarding_completed: true,
    };

    mockedAuthFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => updatedUser,
    } as Response);

    await useUserStore.getState().fetchMe();

    const state = useUserStore.getState();
    expect(state.user).toEqual(updatedUser);
    expect(state.isAuthenticated).toBe(true);
  });

  it("没有 token 时 fetchMe 直接返回", async () => {
    useUserStore.setState({ token: null });

    await useUserStore.getState().fetchMe();

    expect(mockedAuthFetch).not.toHaveBeenCalled();
  });

  it("/auth/me 返回 500 时不调用 logout，保留 token", async () => {
    const token = "test-token-500";
    const user = {
      id: "1",
      username: "testuser",
      email: "test@test.com",
      is_active: true,
      onboarding_completed: true,
    };
    localStorage.setItem("pga_token", token);
    localStorage.setItem("pga_user", JSON.stringify(user));
    useUserStore.setState({ token, user, isAuthenticated: true });

    // 模拟 500 响应
    mockedAuthFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => ({ detail: "Internal Server Error" }),
    } as Response);

    await useUserStore.getState().fetchMe();

    const state = useUserStore.getState();
    expect(state.token).toBe(token);
    expect(state.user).toEqual(user);
    expect(state.isAuthenticated).toBe(true);
    expect(localStorage.getItem("pga_token")).toBe(token);
  });

  it("/auth/me 返回 503 时不调用 logout，保留 token", async () => {
    const token = "test-token-503";
    const user = {
      id: "1",
      username: "testuser",
      email: "test@test.com",
      is_active: true,
      onboarding_completed: true,
    };
    localStorage.setItem("pga_token", token);
    localStorage.setItem("pga_user", JSON.stringify(user));
    useUserStore.setState({ token, user, isAuthenticated: true });

    // 模拟 503 响应
    mockedAuthFetch.mockResolvedValueOnce({
      ok: false,
      status: 503,
      json: async () => ({ detail: "Service Unavailable" }),
    } as Response);

    await useUserStore.getState().fetchMe();

    const state = useUserStore.getState();
    expect(state.token).toBe(token);
    expect(state.isAuthenticated).toBe(true);
  });
});
