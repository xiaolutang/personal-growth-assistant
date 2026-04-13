/**
 * 请求拦截 - 自动注入 Authorization 和 X-UID header
 * X-UID 用于日志追踪（使用真实 user.id 或匿名 ID）
 */

const UID_KEY = 'pga_uid';

function getOrCreateUid(): string {
  let uid = localStorage.getItem(UID_KEY);
  if (!uid) {
    uid = crypto.randomUUID();
    localStorage.setItem(UID_KEY, uid);
  }
  return uid;
}

/**
 * 全局 fetch 拦截 - 自动携带 Authorization 和 X-UID header
 * 401 响应时自动清除 token 并跳转登录页
 */
export function initFetchInterceptor(): void {
  const originalFetch = window.fetch;

  window.fetch = (input: RequestInfo | URL, init?: RequestInit) => {
    const headers = new Headers(init?.headers);

    // 自动注入 Authorization header
    const token = localStorage.getItem('pga_token');
    if (token && !headers.has('Authorization')) {
      headers.set('Authorization', `Bearer ${token}`);
    }

    // X-UID header 用于日志追踪
    if (!headers.has('X-UID')) {
      headers.set('X-UID', getOrCreateUid());
    }

    return originalFetch(input, { ...init, headers }).then((response) => {
      // 401 自动登出并跳转登录页
      if (response.status === 401) {
        localStorage.removeItem('pga_token');
        localStorage.removeItem('pga_user');
        // 只在非登录页面时跳转
        if (!window.location.pathname.includes('/login') && !window.location.pathname.includes('/register')) {
          window.location.href = `${import.meta.env.BASE_URL}login`;
        }
      }
      return response;
    });
  };
}
