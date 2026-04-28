import { create } from "zustand";
import { API_BASE } from "@/config/api";
import { authFetch } from "@/lib/authFetch";

const TOKEN_KEY = "pga_token";
const USER_KEY = "pga_user";

export interface UserInfo {
  id: string;
  username: string;
  email: string;
  is_active: boolean;
  onboarding_completed: boolean;
}

interface UserState {
  user: UserInfo | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;

  login: (username: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  loadFromStorage: () => void;
  fetchMe: () => Promise<void>;
  updateMe: (data: { onboarding_completed?: boolean }) => Promise<UserInfo>;
}

export const useUserStore = create<UserState>((set, get) => {
  // 同步恢复 localStorage 中的 token，避免 ProtectedRoute 首次渲染时竞态
  const _storedToken = localStorage.getItem(TOKEN_KEY);
  const _storedUser = localStorage.getItem(USER_KEY);
  let _initUser: UserInfo | null = null;
  if (_storedUser) {
    try { _initUser = JSON.parse(_storedUser); } catch { /* ignore */ }
  }

  return {
  user: _initUser,
  token: _storedToken,
  isAuthenticated: !!_storedToken,
  isLoading: !!_storedToken, // 有 token 时标记 loading，等 fetchMe 完成再置 false

  login: async (username: string, password: string) => {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "登录失败" }));
      throw new Error(err.detail || "登录失败");
    }
    const data = await res.json();
    const token = data.access_token;
    localStorage.setItem(TOKEN_KEY, token);
    set({ token, isAuthenticated: true });
    // 登录后获取用户信息
    await get().fetchMe();
  },

  register: async (username: string, email: string, password: string) => {
    const res = await fetch(`${API_BASE}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, email, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "注册失败" }));
      throw new Error(err.detail || "注册失败");
    }
    // 注册成功后自动登录
    await get().login(username, password);
  },

  logout: async () => {
    // 先捕获当前数据，再异步清理（避免清理时已置空）
    const { token } = get();
    const userId = get().user?.id;

    // 立即清理本地认证状态（避免 auth 闪现窗口）
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    set({ user: null, token: null, isAuthenticated: false });

    // 异步调后端 logout 将 token 加入黑名单（best-effort）
    if (token) {
      try {
        await fetch(`${API_BASE}/auth/logout`, {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        });
      } catch {
        // 后端调用失败不阻塞前端清理
      }
    }

    if (userId) {
      import("@/stores/taskStore").then(m => m.useTaskStore.getState().clearOfflineEntries()).catch(() => {});
      import("@/lib/offlineQueue").then(m => m.clearForUser(userId).catch(() => {})).catch(() => {});
    }
  },

  loadFromStorage: () => {
    // create() 已同步恢复 localStorage，此处仅验证 token 有效性
    const { token } = get();
    if (token) {
      return get().fetchMe().finally(() => {
        set({ isLoading: false });
      });
    }
  },

  fetchMe: async () => {
    const { token } = get();
    if (!token) return;
    try {
      const res = await authFetch(`${API_BASE}/auth/me`);
      if (res.status === 401) {
        // 401 明确表示 token 无效，执行 logout 清理本地状态
        // 不 await：401 场景下后端已判定 token 无效，无需再调 logout API
        get().logout();
        return;
      }
      if (!res.ok) {
        // 其他非 ok 响应（500/503 等），服务端临时故障，保留登录态
        return;
      }
      const user = await res.json();
      localStorage.setItem(USER_KEY, JSON.stringify(user));
      set({ user });
    } catch {
      // 网络失败（TypeError: Failed to fetch）或其他异常，保留 token 和 user
      // 以支持离线启动恢复
    }
  },

  updateMe: async (data: { onboarding_completed?: boolean }) => {
    const { token } = get();
    if (!token) throw new Error("未登录");
    const res = await authFetch(`${API_BASE}/auth/me`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "更新失败" }));
      throw new Error(err.detail || "更新失败");
    }
    const user = await res.json();
    localStorage.setItem(USER_KEY, JSON.stringify(user));
    set({ user });
    return user as UserInfo;
  },
}});

