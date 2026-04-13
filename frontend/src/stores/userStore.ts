import { create } from "zustand";
import { API_BASE } from "@/config/api";

const TOKEN_KEY = "pga_token";
const USER_KEY = "pga_user";

export interface UserInfo {
  id: string;
  username: string;
  email: string;
  is_active: boolean;
}

interface UserState {
  user: UserInfo | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;

  login: (username: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<void>;
  logout: () => void;
  loadFromStorage: () => void;
  fetchMe: () => Promise<void>;
}

export const useUserStore = create<UserState>((set, get) => ({
  user: null,
  token: null,
  isAuthenticated: false,
  isLoading: false,

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

  logout: () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    set({ user: null, token: null, isAuthenticated: false });
  },

  loadFromStorage: () => {
    const token = localStorage.getItem(TOKEN_KEY);
    const userStr = localStorage.getItem(USER_KEY);
    if (token) {
      let user = null;
      if (userStr) {
        try {
          user = JSON.parse(userStr);
        } catch {
          // ignore
        }
      }
      set({ token, user, isAuthenticated: true, isLoading: true });
      // 验证 token 是否仍然有效
      get().fetchMe().finally(() => {
        set({ isLoading: false });
      });
    }
  },

  fetchMe: async () => {
    const { token } = get();
    if (!token) return;
    try {
      const res = await fetch(`${API_BASE}/auth/me`);
      if (!res.ok) {
        get().logout();
        return;
      }
      const user = await res.json();
      localStorage.setItem(USER_KEY, JSON.stringify(user));
      set({ user });
    } catch {
      get().logout();
    }
  },
}));
