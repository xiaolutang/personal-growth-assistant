/**
 * 匿名用户标识 - 生成一次后持久化到 localStorage
 * 用于日志追踪，无需登录即可按"用户"维度排查问题
 */

const UID_KEY = 'pga_uid';

export function getOrCreateUid(): string {
  let uid = localStorage.getItem(UID_KEY);
  if (!uid) {
    uid = crypto.randomUUID();
    localStorage.setItem(UID_KEY, uid);
  }
  return uid;
}

/**
 * 全局 fetch 拦截 - 所有请求自动携带 X-UID header
 */
export function initUidHeader(): void {
  const originalFetch = window.fetch;
  const uid = getOrCreateUid();

  window.fetch = (input: RequestInfo | URL, init?: RequestInit) => {
    const headers = new Headers(init?.headers);
    if (!headers.has('X-UID')) {
      headers.set('X-UID', uid);
    }
    return originalFetch(input, { ...init, headers });
  };
}
