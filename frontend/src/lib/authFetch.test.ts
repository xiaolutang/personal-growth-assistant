import { afterEach, describe, expect, it, vi } from "vitest";
import { authFetch, buildAuthHeaders } from "./authFetch";

describe("authFetch", () => {
  afterEach(() => {
    localStorage.clear();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("保留 Request 原有 Content-Type，同时附加认证头", async () => {
    localStorage.setItem("pga_token", "test-token");
    localStorage.setItem("pga_uid", "uid-1");

    const fetchSpy = vi.fn().mockResolvedValue(new Response(null, { status: 200 }));
    vi.stubGlobal("fetch", fetchSpy);

    const request = new Request("http://localhost/api/search", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ query: "" }),
    });

    await authFetch(request);

    const [, init] = fetchSpy.mock.calls[0] as [Request, RequestInit];
    const headers = new Headers(init.headers);

    expect(headers.get("Content-Type")).toBe("application/json");
    expect(headers.get("Authorization")).toBe("Bearer test-token");
    expect(headers.get("X-UID")).toBe("uid-1");
  });

  it("init.headers 可以覆盖 Request 上的同名头，但保留 Request 其他头", () => {
    localStorage.setItem("pga_token", "test-token");
    localStorage.setItem("pga_uid", "uid-1");

    const request = new Request("http://localhost/api/search", {
      headers: {
        "Content-Type": "application/json",
        "X-Trace-Id": "request-trace",
      },
    });

    const headers = buildAuthHeaders(request, {
      headers: {
        "Content-Type": "text/plain",
        "X-Extra": "from-init",
      },
    });

    expect(headers.get("Content-Type")).toBe("text/plain");
    expect(headers.get("X-Trace-Id")).toBe("request-trace");
    expect(headers.get("X-Extra")).toBe("from-init");
    expect(headers.get("Authorization")).toBe("Bearer test-token");
    expect(headers.get("X-UID")).toBe("uid-1");
  });
});
