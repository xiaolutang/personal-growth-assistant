/**
 * errors.ts 单元测试
 */

import { describe, it, expect, vi } from "vitest";
import { ApiError, handleApiResponse, createApiFetch } from "./errors";

describe("ApiError", () => {
  describe("构造函数", () => {
    it("应该正确设置属性", () => {
      const error = new ApiError(404, "Not Found");

      expect(error.name).toBe("ApiError");
      expect(error.status).toBe(404);
      expect(error.message).toBe("Not Found");
      expect(error.details).toBeUndefined();
    });

    it("应该正确设置 details", () => {
      const details = { field: "email", code: "invalid" };
      const error = new ApiError(422, "Validation Error", details);

      expect(error.details).toEqual(details);
    });

    it("应该是 Error 的实例", () => {
      const error = new ApiError(500, "Server Error");

      expect(error).toBeInstanceOf(Error);
      expect(error).toBeInstanceOf(ApiError);
    });
  });

  describe("isClientError", () => {
    it("4xx 状态码应返回 true", () => {
      expect(new ApiError(400, "").isClientError).toBe(true);
      expect(new ApiError(401, "").isClientError).toBe(true);
      expect(new ApiError(403, "").isClientError).toBe(true);
      expect(new ApiError(404, "").isClientError).toBe(true);
      expect(new ApiError(422, "").isClientError).toBe(true);
      expect(new ApiError(429, "").isClientError).toBe(true);
    });

    it("非 4xx 状态码应返回 false", () => {
      expect(new ApiError(200, "").isClientError).toBe(false);
      expect(new ApiError(301, "").isClientError).toBe(false);
      expect(new ApiError(500, "").isClientError).toBe(false);
      expect(new ApiError(503, "").isClientError).toBe(false);
    });
  });

  describe("isServerError", () => {
    it("5xx 状态码应返回 true", () => {
      expect(new ApiError(500, "").isServerError).toBe(true);
      expect(new ApiError(502, "").isServerError).toBe(true);
      expect(new ApiError(503, "").isServerError).toBe(true);
      expect(new ApiError(599, "").isServerError).toBe(true);
    });

    it("非 5xx 状态码应返回 false", () => {
      expect(new ApiError(200, "").isServerError).toBe(false);
      expect(new ApiError(404, "").isServerError).toBe(false);
      expect(new ApiError(499, "").isServerError).toBe(false);
    });
  });

  describe("其他状态码判断", () => {
    it("isUnauthorized", () => {
      expect(new ApiError(401, "").isUnauthorized).toBe(true);
      expect(new ApiError(403, "").isUnauthorized).toBe(false);
    });

    it("isForbidden", () => {
      expect(new ApiError(403, "").isForbidden).toBe(true);
      expect(new ApiError(401, "").isForbidden).toBe(false);
    });

    it("isNotFound", () => {
      expect(new ApiError(404, "").isNotFound).toBe(true);
      expect(new ApiError(403, "").isNotFound).toBe(false);
    });

    it("isServiceUnavailable", () => {
      expect(new ApiError(503, "").isServiceUnavailable).toBe(true);
      expect(new ApiError(500, "").isServiceUnavailable).toBe(false);
    });
  });

  describe("toUserMessage", () => {
    it("有自定义消息时应返回消息", () => {
      const error = new ApiError(400, "邮箱格式不正确");
      expect(error.toUserMessage()).toBe("邮箱格式不正确");
    });

    it("空消息时应根据状态码返回默认消息", () => {
      const testCases: [number, string][] = [
        [400, "请求参数有误"],
        [401, "请先登录"],
        [403, "没有权限执行此操作"],
        [404, "请求的资源不存在"],
        [429, "请求过于频繁，请稍后重试"],
        [500, "服务器内部错误"],
        [502, "网关错误"],
        [503, "服务暂时不可用"],
      ];

      testCases.forEach(([status, expectedMessage]) => {
        expect(new ApiError(status, "").toUserMessage()).toBe(expectedMessage);
      });
    });

    it("未知状态码应返回通用失败消息", () => {
      expect(new ApiError(418, "").toUserMessage()).toBe("请求失败 (418)");
    });
  });
});

describe("handleApiResponse", () => {
  it("响应成功时应返回 JSON 数据", async () => {
    const data = { id: 1, title: "测试任务" };
    const response = new Response(JSON.stringify(data), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });

    const result = await handleApiResponse(response);
    expect(result).toEqual(data);
  });

  it("响应不成功时 JSON 错误应抛出 ApiError", async () => {
    const errorBody = { detail: "任务不存在" };
    const response = new Response(JSON.stringify(errorBody), {
      status: 404,
      headers: { "Content-Type": "application/json" },
    });

    try {
      await handleApiResponse(response);
      expect.unreachable("应该抛出 ApiError");
    } catch (error) {
      expect(error).toBeInstanceOf(ApiError);
      expect((error as ApiError).status).toBe(404);
      expect((error as ApiError).message).toBe("任务不存在");
    }
  });

  it("JSON 错误应优先使用 detail 字段", async () => {
    const errorBody = { detail: "详细错误", message: "普通消息", error: "错误" };
    const response = new Response(JSON.stringify(errorBody), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });

    try {
      await handleApiResponse(response);
      expect.unreachable("应该抛出 ApiError");
    } catch (error) {
      expect(error).toBeInstanceOf(ApiError);
      expect((error as ApiError).message).toBe("详细错误");
    }
  });

  it("JSON 错误无 detail 时应使用 message 字段", async () => {
    const errorBody = { message: "普通消息" };
    const response = new Response(JSON.stringify(errorBody), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });

    try {
      await handleApiResponse(response);
      expect.unreachable("应该抛出 ApiError");
    } catch (error) {
      expect(error).toBeInstanceOf(ApiError);
      expect((error as ApiError).message).toBe("普通消息");
    }
  });

  it("非 JSON 错误响应应使用文本内容", async () => {
    const response = new Response("Bad Gateway", {
      status: 502,
      headers: { "Content-Type": "text/plain" },
    });

    try {
      await handleApiResponse(response);
      expect.unreachable("应该抛出 ApiError");
    } catch (error) {
      expect(error).toBeInstanceOf(ApiError);
      expect((error as ApiError).message).toBe("Bad Gateway");
    }
  });

  it("错误响应应包含 details", async () => {
    const errorBody = { detail: "错误详情", extra: "额外信息" };
    const response = new Response(JSON.stringify(errorBody), {
      status: 422,
      headers: { "Content-Type": "application/json" },
    });

    try {
      await handleApiResponse(response);
      expect.unreachable("应该抛出 ApiError");
    } catch (error) {
      expect(error).toBeInstanceOf(ApiError);
      expect((error as ApiError).details).toEqual(errorBody);
    }
  });
});

describe("createApiFetch", () => {
  it("应该拼接 baseUrl 和 path", async () => {
    const mockFetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );
    vi.stubGlobal("fetch", mockFetch);

    const apiFetch = createApiFetch("http://localhost:8000");
    await apiFetch("/api/test");

    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/test",
      expect.objectContaining({
        headers: expect.objectContaining({ "Content-Type": "application/json" }),
      })
    );

    vi.restoreAllMocks();
  });

  it("应该传递额外的 options", async () => {
    const mockFetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );
    vi.stubGlobal("fetch", mockFetch);

    const apiFetch = createApiFetch("http://localhost:8000");
    await apiFetch("/api/test", { method: "POST", body: '{"data":1}' });

    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/test",
      expect.objectContaining({
        method: "POST",
        body: '{"data":1}',
      })
    );

    vi.restoreAllMocks();
  });
});
