import { APIRequestContext, expect } from '@playwright/test';

/**
 * 认证辅助函数
 *
 * 通过 API 注册+登录获取 JWT token，供 E2E 测试使用。
 * 所有 API 调用走前端 vite proxy（/api/* → 后端）。
 */

export interface AuthUser {
  username: string;
  password: string;
  token: string;
  userId: string;
}

/**
 * 注册并登录一个测试用户
 *
 * 用户名添加随机后缀避免冲突，使用 suite 级别的 APIRequestContext
 * 或测试级别的 request。
 */
export async function registerAndLogin(
  request: APIRequestContext,
  prefix = 'e2e_user'
): Promise<AuthUser> {
  const suffix = Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
  const username = `${prefix}_${suffix}`;
  const password = 'testpass123';
  const email = `${username}@e2e.test`;

  // 注册
  const registerResp = await request.post('/api/auth/register', {
    data: { username, email, password },
  });
  expect(registerResp.ok()).toBeTruthy();

  // 登录
  const loginResp = await request.post('/api/auth/login', {
    data: { username, password },
  });
  expect(loginResp.ok()).toBeTruthy();

  const loginData = await loginResp.json();
  return {
    username,
    password,
    token: loginData.access_token,
    userId: loginData.user.id,
  };
}
