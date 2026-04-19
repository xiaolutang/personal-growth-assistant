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

// Mock API config
vi.mock("@/config/api", () => ({
  API_BASE: "http://localhost:8000",
}));

// Mock authFetch
vi.mock("@/lib/authFetch", () => ({
  authFetch: (...args: unknown[]) => mockFetch(...args),
}));

// Mock taskStore
const mockClearOfflineEntries = vi.fn();
vi.mock("@/stores/taskStore", () => ({
  useTaskStore: {
    getState: () => ({ clearOfflineEntries: mockClearOfflineEntries }),
  },
}));

// Mock offlineQueue
const mockClearForUser = vi.fn().mockResolvedValue(undefined);
vi.mock("@/lib/offlineQueue", () => ({
  clearForUser: (...args: unknown[]) => mockClearForUser(...args),
}));

// Import after mocks
import { useUserStore } from "../userStore";

describe("userStore logout 离线数据清理", () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.clearAllMocks();
    useUserStore.setState({
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: false,
    });
  });

  it("logout 时调用 clearOfflineEntries 和 clearForUser", async () => {
    // Set up authenticated state with a real user
    // login calls fetch (for /auth/login) then fetchMe (which uses authFetch → fetch)
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ access_token: "test-token" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ id: "user-123", username: "testuser" }),
      });

    const store = useUserStore.getState();
    await store.login("testuser", "password123");

    const afterLogin = useUserStore.getState();
    expect(afterLogin.user).toBeTruthy();
    expect(afterLogin.user!.id).toBe("user-123");

    // Logout
    useUserStore.getState().logout();

    // Wait for dynamic imports to resolve
    await vi.waitFor(() => {
      expect(mockClearOfflineEntries).toHaveBeenCalledTimes(1);
    }, { timeout: 3000 });

    expect(mockClearForUser).toHaveBeenCalledWith("user-123");
  });

  it("logout 时清除 token 和 user", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ access_token: "test-token", username: "testuser" }),
    });

    await useUserStore.getState().login("testuser", "password123");
    expect(useUserStore.getState().isAuthenticated).toBe(true);

    useUserStore.getState().logout();

    const after = useUserStore.getState();
    expect(after.token).toBeNull();
    expect(after.user).toBeNull();
    expect(after.isAuthenticated).toBe(false);
  });

  it("logout 时没有 user 不调用 clearForUser", async () => {
    useUserStore.setState({ user: null, token: null, isAuthenticated: false });

    useUserStore.getState().logout();

    // Give dynamic imports time
    await new Promise((r) => setTimeout(r, 100));

    expect(mockClearForUser).not.toHaveBeenCalled();
    expect(mockClearOfflineEntries).not.toHaveBeenCalled();
  });
});
