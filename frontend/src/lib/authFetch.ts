/**
 * 显式注入认证头，避免依赖全局 fetch 拦截器的初始化时机。
 */

const TOKEN_KEY = "pga_token";
const UID_KEY = "pga_uid";

function getOrCreateUid(): string {
  let uid = localStorage.getItem(UID_KEY);
  if (!uid) {
    uid = crypto.randomUUID();
    localStorage.setItem(UID_KEY, uid);
  }
  return uid;
}

export function buildAuthHeaders(init?: RequestInit): Headers {
  const headers = new Headers(init?.headers);
  const token = localStorage.getItem(TOKEN_KEY);

  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  if (!headers.has("X-UID")) {
    headers.set("X-UID", getOrCreateUid());
  }

  return headers;
}

export async function authFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  return fetch(input, {
    ...init,
    headers: buildAuthHeaders(init),
  });
}
