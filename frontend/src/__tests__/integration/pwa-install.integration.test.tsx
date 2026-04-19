import { describe, it, expect, vi, beforeEach, type Mock } from "vitest";
import { render, screen, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import { Header } from "@/components/layout/Header";
import { SidebarProvider } from "@/components/layout/SidebarContext";
import { ThemeProvider } from "@/lib/theme";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

// Mock useOnlineStatus
vi.mock("@/hooks/useOnlineStatus", () => ({
  useOnlineStatus: () => ({ isOnline: true }),
}));

// Mock NotificationCenter (uses navigate / API calls we don't need here)
vi.mock("@/components/NotificationCenter", () => ({
  NotificationCenter: () => null,
}));

// Mock sonner
vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
  Toaster: () => null,
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const storage: Record<string, string> = {};

function setupLocalStorage() {
  vi.stubGlobal("localStorage", {
    getItem: vi.fn((key: string) => storage[key] ?? null),
    setItem: vi.fn((key: string, value: string) => {
      storage[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete storage[key];
    }),
    clear: vi.fn(() => {
      Object.keys(storage).forEach((k) => delete storage[k]);
    }),
    get length() {
      return Object.keys(storage).length;
    },
    key: vi.fn((_index: number) => null),
  });
}

/** Create a fake BeforeInstallPromptEvent and fire it on window */
function fireBeforeInstallPrompt(promptFn?: Mock) {
  const event = new Event("beforeinstallprompt");
  const prompt = promptFn ?? vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(event, "preventDefault", { value: vi.fn() });
  Object.defineProperty(event, "prompt", { value: prompt });
  Object.defineProperty(event, "userChoice", {
    value: Promise.resolve({ outcome: "dismissed" as const }),
  });
  act(() => {
    window.dispatchEvent(event);
  });
  return { event, prompt };
}

function fireAppInstalled() {
  act(() => {
    window.dispatchEvent(new Event("appinstalled"));
  });
}

/** Render Header with required providers */
function renderHeader(title = "Test Page") {
  return render(
    <MemoryRouter>
      <ThemeProvider>
        <SidebarProvider>
          <Header title={title} />
        </SidebarProvider>
      </ThemeProvider>
    </MemoryRouter>
  );
}

/** Query the PWA banner (returns null when not rendered) */
function queryBanner() {
  return screen.queryByText(/添加到桌面/);
}

/** Get the dismiss (X) button inside the banner */
function getDismissButton() {
  return screen.getByLabelText("关闭安装提示");
}

/** Get the install button inside the banner */
function getInstallButton() {
  return screen.getByRole("button", { name: /安装到桌面/ });
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("PWA install banner lifecycle (Header + usePWAInstall)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Object.keys(storage).forEach((k) => delete storage[k]);
    setupLocalStorage();
  });

  // ----- 1. Banner lifecycle: show -> dismiss -> immediate hide ----------------

  it("shows banner when conditions met, hides immediately on dismiss", () => {
    storage["pwa-usage-count"] = "3";

    renderHeader();

    // Banner should not be visible yet (no beforeinstallprompt fired)
    expect(queryBanner()).toBeNull();

    // Fire the browser install prompt event
    fireBeforeInstallPrompt();

    // Now the banner should appear
    expect(queryBanner()).toBeInTheDocument();

    // Click the dismiss (X) button
    act(() => {
      getDismissButton().click();
    });

    // Banner disappears immediately (synchronous state update)
    expect(queryBanner()).toBeNull();
  });

  // ----- 2. Banner does not show when usageCount < 3 --------------------------

  it("does not show banner when usageCount < 3", () => {
    storage["pwa-usage-count"] = "2";

    renderHeader();
    fireBeforeInstallPrompt();

    expect(queryBanner()).toBeNull();
  });

  // ----- 3. Banner shows after dismiss expires (7 days) -----------------------

  it("shows banner after 7-day dismiss period expires", () => {
    const eightDaysAgo = Date.now() - 8 * 24 * 60 * 60 * 1000;
    storage["pwa-usage-count"] = "3";
    storage["pwa-banner-dismissed"] = String(eightDaysAgo);

    renderHeader();
    fireBeforeInstallPrompt();

    expect(queryBanner()).toBeInTheDocument();
  });

  // ----- 4. appinstalled event hides banner -----------------------------------

  it("hides banner when appinstalled event fires", () => {
    storage["pwa-usage-count"] = "3";

    renderHeader();
    fireBeforeInstallPrompt();

    // Confirm banner is showing
    expect(queryBanner()).toBeInTheDocument();

    // Simulate the OS-level "app installed" event
    fireAppInstalled();

    // Banner should disappear
    expect(queryBanner()).toBeNull();
  });

  // ----- 5. Install button triggers promptInstall -----------------------------

  it("calls event.prompt() when install button is clicked", async () => {
    storage["pwa-usage-count"] = "3";
    const mockPrompt = vi.fn().mockResolvedValue(undefined);

    renderHeader();
    fireBeforeInstallPrompt(mockPrompt);

    // Banner visible with install button
    expect(queryBanner()).toBeInTheDocument();

    // Click install button
    const user = userEvent.setup();
    await user.click(getInstallButton());

    // The deferred prompt's .prompt() should have been called
    expect(mockPrompt).toHaveBeenCalledTimes(1);
  });
});
