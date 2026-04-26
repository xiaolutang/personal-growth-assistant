import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// Mock config before importing analytics
vi.mock("@/config/api", () => ({
  API_BASE: "/api",
}));

// We'll set up the authFetch mock below
const mockAuthFetch = vi.fn();
vi.mock("@/lib/authFetch", () => ({
  authFetch: (...args: unknown[]) => mockAuthFetch(...args),
}));

// Import after mocks
import { trackEvent } from "@/lib/analytics";

describe("analytics", () => {
  beforeEach(() => {
    mockAuthFetch.mockReset();
    mockAuthFetch.mockResolvedValue(new Response(null, { status: 200 }));
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("trackEvent calls API with correct payload", async () => {
    await trackEvent("entry_created", { category: "task" });

    expect(mockAuthFetch).toHaveBeenCalledTimes(1);
    expect(mockAuthFetch).toHaveBeenCalledWith(
      "/api/analytics/event",
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
      }),
    );

    const call = mockAuthFetch.mock.calls[0];
    const body = JSON.parse((call[1] as RequestInit).body as string);
    expect(body).toEqual({
      event_type: "entry_created",
      metadata: { category: "task" },
    });
  });

  it("trackEvent sends metadata as null when not provided", async () => {
    await trackEvent("page_viewed");

    const call = mockAuthFetch.mock.calls[0];
    const body = JSON.parse((call[1] as RequestInit).body as string);
    expect(body).toEqual({
      event_type: "page_viewed",
      metadata: null,
    });
  });

  it("trackEvent is silent when API fails", async () => {
    mockAuthFetch.mockRejectedValue(new Error("Network error"));

    // Should NOT throw
    await expect(trackEvent("entry_viewed")).resolves.toBeUndefined();
  });

  it("trackEvent is silent when API returns error status", async () => {
    mockAuthFetch.mockResolvedValue(new Response(null, { status: 500 }));

    // Should NOT throw
    await expect(trackEvent("search_performed")).resolves.toBeUndefined();
  });

  it("trackEvent skips request when offline", async () => {
    const originalOnLine = navigator.onLine;
    Object.defineProperty(navigator, "onLine", {
      value: false,
      writable: true,
      configurable: true,
    });

    try {
      await trackEvent("chat_message_sent");
      expect(mockAuthFetch).not.toHaveBeenCalled();
    } finally {
      Object.defineProperty(navigator, "onLine", {
        value: originalOnLine,
        writable: true,
        configurable: true,
      });
    }
  });

  it("trackEvent sends request when online", async () => {
    const originalOnLine = navigator.onLine;
    Object.defineProperty(navigator, "onLine", {
      value: true,
      writable: true,
      configurable: true,
    });

    try {
      await trackEvent("onboarding_completed");
      expect(mockAuthFetch).toHaveBeenCalledTimes(1);
    } finally {
      Object.defineProperty(navigator, "onLine", {
        value: originalOnLine,
        writable: true,
        configurable: true,
      });
    }
  });

  it("trackEvent handles all event types", async () => {
    const eventTypes = [
      "entry_created",
      "entry_viewed",
      "chat_message_sent",
      "search_performed",
      "page_viewed",
      "onboarding_completed",
    ] as const;

    for (const eventType of eventTypes) {
      mockAuthFetch.mockClear();
      await trackEvent(eventType);
      expect(mockAuthFetch).toHaveBeenCalledTimes(1);
      const call = mockAuthFetch.mock.calls[0];
      const body = JSON.parse((call[1] as RequestInit).body as string);
      expect(body.event_type).toBe(eventType);
    }
  });
});
