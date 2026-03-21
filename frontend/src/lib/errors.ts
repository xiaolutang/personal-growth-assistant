/**
 * API 错误类
 *
 * 提供更详细的错误信息，包括：
 * - HTTP 状态码
 * - 服务器返回的错误消息
 * - 原始错误详情
 */
export class ApiError extends Error {
  status: number;
  details?: unknown;

  constructor(status: number, message: string, details?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.details = details;
  }

  /**
   * 判断是否为客户端错误（4xx）
   */
  get isClientError(): boolean {
    return this.status >= 400 && this.status < 500;
  }

  /**
   * 判断是否为服务器错误（5xx）
   */
  get isServerError(): boolean {
    return this.status >= 500;
  }

  /**
   * 判断是否为未授权错误
   */
  get isUnauthorized(): boolean {
    return this.status === 401;
  }

  /**
   * 判断是否为禁止访问错误
   */
  get isForbidden(): boolean {
    return this.status === 403;
  }

  /**
   * 判断是否为未找到错误
   */
  get isNotFound(): boolean {
    return this.status === 404;
  }

  /**
   * 格式化为用户友好的消息
   */
  toUserMessage(): string {
    if (this.message) {
      return this.message;
    }

    // 根据状态码返回默认消息
    switch (this.status) {
      case 400:
        return '请求参数有误';
      case 401:
        return '请先登录';
      case 403:
        return '没有权限执行此操作';
      case 404:
        return '请求的资源不存在';
      case 429:
        return '请求过于频繁，请稍后重试';
      case 500:
        return '服务器内部错误';
      case 502:
        return '网关错误';
      case 503:
        return '服务暂时不可用';
      default:
        return `请求失败 (${this.status})`;
    }
  }
}

/**
 * 处理 API 响应，统一错误处理
 *
 * @param response - fetch 返回的 Response 对象
 * @returns 解析后的 JSON 数据
 * @throws ApiError 当响应状态码不为 2xx 时
 */
export async function handleApiResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let message = `HTTP ${response.status}`;
    let details = null;

    try {
      const contentType = response.headers.get('content-type');
      if (contentType?.includes('application/json')) {
        const errorData = await response.json();
        message = errorData.detail || errorData.message || errorData.error || message;
        details = errorData;
      } else {
        const text = await response.text();
        if (text) {
          message = text;
        }
      }
    } catch {
      // 无法解析错误响应，使用默认消息
    }

    throw new ApiError(response.status, message, details);
  }

  return response.json();
}

/**
 * 创建带错误处理的 fetch 函数
 *
 * @param baseUrl - API 基础路径
 * @returns 封装后的 fetch 函数
 */
export function createApiFetch(baseUrl: string) {
  return async <T = unknown>(
    path: string,
    options?: RequestInit
  ): Promise<T> => {
    const response = await fetch(`${baseUrl}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    return handleApiResponse<T>(response);
  };
}
