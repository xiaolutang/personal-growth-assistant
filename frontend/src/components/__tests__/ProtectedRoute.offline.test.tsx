/**
 * ProtectedRoute 离线启动恢复 单元测试
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { ProtectedRoute } from "../ProtectedRoute";
import { useUserStore } from "@/stores/userStore";

// Mock react-router-dom Navigate
vi.mock("react-router-dom", () => ({
  Navigate: ({ to }: { to: string }) => (
    <div data-testid="navigate" data-to={to}>
      Navigate to {to}
    </div>
  ),
}));

describe("ProtectedRoute 离线启动恢复", () => {
  beforeEach(() => {
    useUserStore.setState({
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: false,
    });
  });

  it("离线状态 + token 存在 → isAuthenticated=true → 放行不跳转登录页", () => {
    // 模拟离线刷新后 loadFromStorage 恢复了 token（但 fetchMe 因网络失败）
    useUserStore.setState({
      token: "cached-token",
      user: {
        id: "1",
        username: "testuser",
        email: "test@test.com",
        is_active: true,
        onboarding_completed: true,
      },
      isAuthenticated: true,
      isLoading: false,
    });

    render(
      <ProtectedRoute>
        <div data-testid="protected-content">受保护的内容</div>
      </ProtectedRoute>
    );

    expect(screen.getByTestId("protected-content")).toBeInTheDocument();
    expect(screen.queryByTestId("navigate")).not.toBeInTheDocument();
  });

  it("离线状态 + 无 token → isAuthenticated=false → 跳转登录页", () => {
    useUserStore.setState({
      token: null,
      user: null,
      isAuthenticated: false,
      isLoading: false,
    });

    render(
      <ProtectedRoute>
        <div data-testid="protected-content">受保护的内容</div>
      </ProtectedRoute>
    );

    expect(screen.queryByTestId("protected-content")).not.toBeInTheDocument();
    expect(screen.getByTestId("navigate")).toBeInTheDocument();
    expect(screen.getByTestId("navigate").dataset.to).toBe("/login");
  });

  it("isLoading=true 时显示加载中", () => {
    useUserStore.setState({
      isAuthenticated: false,
      isLoading: true,
    });

    render(
      <ProtectedRoute>
        <div data-testid="protected-content">受保护的内容</div>
      </ProtectedRoute>
    );

    expect(screen.queryByTestId("protected-content")).not.toBeInTheDocument();
    expect(screen.getByText("加载中...")).toBeInTheDocument();
  });
});
