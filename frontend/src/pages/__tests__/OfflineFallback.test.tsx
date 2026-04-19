/**
 * OfflineFallback 组件单元测试
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { OfflineFallback } from "@/pages/OfflineFallback";

// Mock useOnlineStatus
const mockIsOnline = vi.fn();
vi.mock("@/hooks/useOnlineStatus", () => ({
  useOnlineStatus: () => ({ isOnline: mockIsOnline() }),
}));

function renderWithRouter() {
  return render(
    <MemoryRouter>
      <OfflineFallback />
    </MemoryRouter>
  );
}

describe("OfflineFallback", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("离线时显示离线提示文案", () => {
    mockIsOnline.mockReturnValue(false);
    renderWithRouter();
    expect(screen.getByText("你当前处于离线状态")).toBeInTheDocument();
    expect(
      screen.getByText(/无法连接到服务器/)
    ).toBeInTheDocument();
  });

  it("离线时首页链接可点击", () => {
    mockIsOnline.mockReturnValue(false);
    renderWithRouter();
    const homeLink = screen.getByText("返回首页");
    expect(homeLink).toBeInTheDocument();
    expect(homeLink.closest("a")).toHaveAttribute("href", "/");
  });

  it("离线时任务链接可点击", () => {
    mockIsOnline.mockReturnValue(false);
    renderWithRouter();
    const taskLink = screen.getByText("查看任务");
    expect(taskLink).toBeInTheDocument();
    expect(taskLink.closest("a")).toHaveAttribute("href", "/tasks");
  });

  it("在线时不渲染离线页", () => {
    mockIsOnline.mockReturnValue(true);
    const { container } = renderWithRouter();
    expect(container.innerHTML).toBe("");
  });
});
