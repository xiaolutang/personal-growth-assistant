/**
 * userStore.ts 单元测试
 *
 * 测试用户状态管理：登录态、token 持久化、logout 清理
 */
import { describe, it, expect, beforeEach, vi } from "vitest";

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

// Mock fetch
const mockFetch = vi.fn();
Object.defineProperty(globalThis, "fetch", { value: mockFetch, writable: true });

// Mock API_BASE
vi.mock("@/config/api", () => ({
  API_BASE: "http://localhost:8000",
}));

// Import after mocks
import { useUserStore } from "./userStore";

describe("useUserStore", () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.clearAllMocks();
    // Reset store state
    useUserStore.setState({
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: false,
    });
  });

  describe("初始状态", () => {
    it("应该有正确的初始状态", () => {
      const state = useUserStore.getState();
      expect(state.user).toBeNull();
      expect(state.token).toBeNull();
      expect(state.isAuthenticated).toBe(false);
      expect(state.isLoading).toBe(false);
    });
  });

  describe("login", () => {
    it("登录成功应设置 token 和 isAuthenticated", async () => {
      const mockToken = "test.jwt.token";
      const mockUser = {
        id: "user-1",
        username: "testuser",
        email: "test@example.com",
        is_active: true,
        onboarding_completed: false,
      };

      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ access_token: mockToken }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockUser),
        });

      await useUserStore.getState().login("testuser", "password");

      const state = useUserStore.getState();
      expect(state.token).toBe(mockToken);
      expect(state.isAuthenticated).toBe(true);
      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        "pga_token",
        mockToken
      );
    });

    it("登录失败应抛出错误", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: () => Promise.resolve({ detail: "用户名或密码错误" }),
      });

      await expect(
        useUserStore.getState().login("wrong", "creds")
      ).rejects.toThrow("用户名或密码错误");

      const state = useUserStore.getState();
      expect(state.isAuthenticated).toBe(false);
    });
  });

  describe("logout", () => {
    it("有 token 时应先调后端 logout 再清除状态", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ message: "logged out" }),
      });

      useUserStore.setState({
        token: "some-token",
        user: {
          id: "1",
          username: "u",
          email: "e@t.com",
          is_active: true,
          onboarding_completed: true,
        },
        isAuthenticated: true,
      });

      await useUserStore.getState().logout();

      // 验证调用了 POST /auth/logout
      expect(mockFetch).toHaveBeenCalledWith(
        "http://localhost:8000/auth/logout",
        expect.objectContaining({
          method: "POST",
          headers: { Authorization: "Bearer some-token" },
        })
      );
      // 验证清除了状态
      const state = useUserStore.getState();
      expect(state.token).toBeNull();
      expect(state.user).toBeNull();
      expect(state.isAuthenticated).toBe(false);
      expect(localStorageMock.removeItem).toHaveBeenCalledWith("pga_token");
      expect(localStorageMock.removeItem).toHaveBeenCalledWith("pga_user");
    });

    it("无 token 时应跳过后端调用直接清理", async () => {
      useUserStore.setState({
        token: null,
        user: null,
        isAuthenticated: false,
      });

      await useUserStore.getState().logout();

      // 不应调用 fetch
      expect(mockFetch).not.toHaveBeenCalled();
    });

    it("后端 logout 返回 500 时仍清理本地状态", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
      });

      useUserStore.setState({
        token: "bad-backend-token",
        user: {
          id: "1",
          username: "u",
          email: "e@t.com",
          is_active: true,
          onboarding_completed: true,
        },
        isAuthenticated: true,
      });

      await useUserStore.getState().logout();

      const state = useUserStore.getState();
      expect(state.token).toBeNull();
      expect(state.user).toBeNull();
      expect(state.isAuthenticated).toBe(false);
      expect(localStorageMock.removeItem).toHaveBeenCalledWith("pga_token");
    });

    it("后端 logout 网络错误时仍清理本地状态", async () => {
      mockFetch.mockRejectedValueOnce(new TypeError("Failed to fetch"));

      useUserStore.setState({
        token: "network-error-token",
        user: {
          id: "1",
          username: "u",
          email: "e@t.com",
          is_active: true,
          onboarding_completed: true,
        },
        isAuthenticated: true,
      });

      await useUserStore.getState().logout();

      const state = useUserStore.getState();
      expect(state.token).toBeNull();
      expect(state.user).toBeNull();
      expect(state.isAuthenticated).toBe(false);
      expect(localStorageMock.removeItem).toHaveBeenCalledWith("pga_token");
    });
  });

  describe("loadFromStorage", () => {
    it("有 token 时应恢复登录态并验证", async () => {
      localStorageMock.getItem.mockImplementation(
        (key: string) =>
          key === "pga_token"
            ? "saved-token"
            : key === "pga_user"
              ? JSON.stringify({
                  id: "1",
                  username: "u",
                  email: "e@t.com",
                  is_active: true,
                  onboarding_completed: true,
                })
              : (null as unknown as string)
      );

      const mockUser = {
        id: "1",
        username: "u",
        email: "e@t.com",
        is_active: true,
        onboarding_completed: true,
      };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockUser),
      });

      await useUserStore.getState().loadFromStorage();

      const state = useUserStore.getState();
      expect(state.isAuthenticated).toBe(true);
      expect(state.token).toBe("saved-token");
    });

    it("无 token 时不应设置登录态", async () => {
      localStorageMock.getItem.mockReturnValue(null as unknown as string);

      useUserStore.getState().loadFromStorage();

      const state = useUserStore.getState();
      expect(state.isAuthenticated).toBe(false);
    });

    it("token 无效时应清除登录态", async () => {
      localStorageMock.getItem.mockImplementation(
        (key: string) => (key === "pga_token" ? "expired-token" : (null as unknown as string))
      );

      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
      });

      await useUserStore.getState().loadFromStorage();

      const state = useUserStore.getState();
      expect(state.isAuthenticated).toBe(false);
      expect(state.token).toBeNull();
    });
  });
});
