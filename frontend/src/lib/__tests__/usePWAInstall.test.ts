import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";

// Mock localStorage
const storage: Record<string, string> = {};
const localStorageMock = {
  getItem: vi.fn((key: string) => storage[key] ?? null),
  setItem: vi.fn((key: string, value: string) => { storage[key] = value; }),
  removeItem: vi.fn((key: string) => { delete storage[key]; }),
  clear: vi.fn(() => Object.keys(storage).forEach((k) => delete storage[k])),
};
vi.stubGlobal("localStorage", localStorageMock);

// Need to import after mocking
import { usePWAInstall } from "../usePWAInstall";

describe("usePWAInstall", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Object.keys(storage).forEach((k) => delete storage[k]);
  });

  it("returns showBanner=false when usageCount < 3", () => {
    storage["pwa-usage-count"] = "1";
    const { result } = renderHook(() => usePWAInstall());
    // canInstall defaults to false, so showBanner is false
    expect(result.current.usageCount).toBe(1);
    expect(result.current.showBanner).toBe(false);
  });

  it("showBanner=true when canInstall=true, usageCount=3, not dismissed", () => {
    storage["pwa-usage-count"] = "3";
    // Trigger beforeinstallprompt to set canInstall=true
    const { result } = renderHook(() => usePWAInstall());

    act(() => {
      const event = new Event("beforeinstallprompt");
      Object.defineProperty(event, "prompt", { value: vi.fn() });
      Object.defineProperty(event, "userChoice", { value: Promise.resolve({ outcome: "dismissed" }) });
      window.dispatchEvent(event);
    });

    expect(result.current.canInstall).toBe(true);
    expect(result.current.showBanner).toBe(true);
  });

  it("showBanner=false when canInstall=false (already installed)", () => {
    storage["pwa-usage-count"] = "5";
    const { result } = renderHook(() => usePWAInstall());
    expect(result.current.canInstall).toBe(false);
    expect(result.current.showBanner).toBe(false);
  });

  it("dismissBanner writes timestamp and immediately hides banner", () => {
    storage["pwa-usage-count"] = "3";
    const { result } = renderHook(() => usePWAInstall());

    // First make banner visible
    act(() => {
      const event = new Event("beforeinstallprompt");
      Object.defineProperty(event, "prompt", { value: vi.fn() });
      Object.defineProperty(event, "userChoice", { value: Promise.resolve({ outcome: "dismissed" }) });
      window.dispatchEvent(event);
    });
    expect(result.current.showBanner).toBe(true);

    // Dismiss and verify immediate state change
    act(() => {
      result.current.dismissBanner();
    });

    expect(localStorageMock.setItem).toHaveBeenCalledWith(
      "pwa-banner-dismissed",
      expect.any(String)
    );
    expect(result.current.showBanner).toBe(false);
  });

  it("showBanner=false when recently dismissed", () => {
    storage["pwa-usage-count"] = "5";
    storage["pwa-banner-dismissed"] = String(Date.now()); // just now
    const { result } = renderHook(() => usePWAInstall());

    act(() => {
      const event = new Event("beforeinstallprompt");
      Object.defineProperty(event, "prompt", { value: vi.fn() });
      Object.defineProperty(event, "userChoice", { value: Promise.resolve({ outcome: "dismissed" }) });
      window.dispatchEvent(event);
    });

    expect(result.current.canInstall).toBe(true);
    expect(result.current.showBanner).toBe(false);
  });

  it("showBanner=true when dismissed > 7 days ago", () => {
    storage["pwa-usage-count"] = "3";
    const sevenDaysAgo = Date.now() - 8 * 24 * 60 * 60 * 1000;
    storage["pwa-banner-dismissed"] = String(sevenDaysAgo);

    const { result } = renderHook(() => usePWAInstall());

    act(() => {
      const event = new Event("beforeinstallprompt");
      Object.defineProperty(event, "prompt", { value: vi.fn() });
      Object.defineProperty(event, "userChoice", { value: Promise.resolve({ outcome: "dismissed" }) });
      window.dispatchEvent(event);
    });

    expect(result.current.showBanner).toBe(true);
  });

  it("incrementUsageCount increments localStorage and dispatches event", () => {
    storage["pwa-usage-count"] = "2";
    const dispatchSpy = vi.spyOn(window, "dispatchEvent");

    const { result } = renderHook(() => usePWAInstall());

    act(() => {
      result.current.incrementUsageCount();
    });

    expect(localStorageMock.setItem).toHaveBeenCalledWith("pwa-usage-count", "3");
    expect(result.current.usageCount).toBe(3);
    expect(dispatchSpy).toHaveBeenCalledWith(expect.any(CustomEvent));

    dispatchSpy.mockRestore();
  });

  it("appinstalled event sets canInstall=false", () => {
    storage["pwa-usage-count"] = "5";
    const { result } = renderHook(() => usePWAInstall());

    act(() => {
      const event = new Event("beforeinstallprompt");
      Object.defineProperty(event, "prompt", { value: vi.fn() });
      Object.defineProperty(event, "userChoice", { value: Promise.resolve({ outcome: "dismissed" }) });
      window.dispatchEvent(event);
    });
    expect(result.current.canInstall).toBe(true);

    act(() => {
      window.dispatchEvent(new Event("appinstalled"));
    });
    expect(result.current.canInstall).toBe(false);
  });
});
