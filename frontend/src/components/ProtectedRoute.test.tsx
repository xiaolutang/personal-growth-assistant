/**
 * ProtectedRoute 组件测试
 *
 * 测试路由守卫：认证状态、加载状态、重定向逻辑
 */
import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { useUserStore } from "@/stores/userStore";
import { ProtectedRoute } from "./ProtectedRoute";

function renderWithRouter(ui: React.ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

describe("ProtectedRoute", () => {
  beforeEach(() => {
    useUserStore.setState({
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: false,
    });
  });

  it("已认证时渲染子组件", () => {
    useUserStore.setState({ isAuthenticated: true });

    renderWithRouter(
      <ProtectedRoute>
        <div>受保护内容</div>
      </ProtectedRoute>
    );

    expect(screen.getByText("受保护内容")).toBeInTheDocument();
  });

  it("未认证时重定向到 /login", () => {
    useUserStore.setState({ isAuthenticated: false });

    const { container } = renderWithRouter(
      <ProtectedRoute>
        <div>受保护内容</div>
      </ProtectedRoute>
    );

    // Navigate 组件不会渲染子内容
    expect(screen.queryByText("受保护内容")).not.toBeInTheDocument();
    // Navigate 会产生一个空渲染
    expect(container.innerHTML).not.toContain("受保护内容");
  });

  it("加载中时显示加载提示", () => {
    useUserStore.setState({ isLoading: true, isAuthenticated: false });

    renderWithRouter(
      <ProtectedRoute>
        <div>受保护内容</div>
      </ProtectedRoute>
    );

    expect(screen.getByText("加载中...")).toBeInTheDocument();
    expect(screen.queryByText("受保护内容")).not.toBeInTheDocument();
  });

  it("加载完成但未认证时重定向", () => {
    useUserStore.setState({ isLoading: false, isAuthenticated: false });

    const { container } = renderWithRouter(
      <ProtectedRoute>
        <div>受保护内容</div>
      </ProtectedRoute>
    );

    expect(screen.queryByText("加载中...")).not.toBeInTheDocument();
    expect(screen.queryByText("受保护内容")).not.toBeInTheDocument();
  });
});
