/**
 * F03: Home 页面集成测试 - 空状态入口
 * - '记灵感' 点击聚焦输入栏
 * - '建任务' 打开 CreateDialog(task)
 * - 非空状态下 QuickCaptureBar 正常渲染
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { Home } from "../Home";
import { useTaskStore } from "@/stores/taskStore";
import { resetStore, createMockTask } from "@/testUtils/taskStoreHelpers";

// Mock sonner
vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
  Toaster: () => null,
}));

// Mock API
vi.mock("@/services/api", () => ({
  getEntries: vi.fn().mockResolvedValue({ entries: [] }),
  createEntry: vi.fn().mockResolvedValue({ id: "1", title: "test", category: "inbox" }),
  updateEntry: vi.fn(),
  deleteEntry: vi.fn(),
  searchEntries: vi.fn(),
  getKnowledgeGraph: vi.fn(),
  getGoals: vi.fn().mockResolvedValue({ goals: [] }),
}));

// Mock Header
vi.mock("@/components/layout/Header", () => ({
  Header: ({ title }: { title: string }) => <header>{title}</header>,
}));

// Mock ServiceUnavailable
vi.mock("@/components/ServiceUnavailable", () => ({
  ServiceUnavailable: ({ onRetry }: { onRetry: () => void }) => (
    <div>
      <span>服务暂时不可用</span>
      <button onClick={onRetry}>重试</button>
    </div>
  ),
}));

// Mock useMorningDigest
vi.mock("@/hooks/useMorningDigest", () => ({
  useMorningDigest: () => ({ data: null, loading: false, error: null }),
}));

// Mock useUserStore
vi.mock("@/stores/userStore", () => ({
  useUserStore: (selector: (state: Record<string, unknown>) => unknown) => {
    const state = { user: { onboarding_completed: true }, updateMe: vi.fn() };
    return selector(state);
  },
}));

// Mock analytics
vi.mock("@/lib/analytics", () => ({
  trackEvent: vi.fn(),
}));

function renderWithRouter(ui: React.ReactElement) {
  return render(
    <MemoryRouter initialEntries={["/"]}>
      {ui}
    </MemoryRouter>
  );
}

// HTMLDialogElement polyfill for jsdom
beforeEach(() => {
  HTMLDialogElement.prototype.showModal = vi.fn(function (this: HTMLDialogElement) {
    this.open = true;
  });
  HTMLDialogElement.prototype.close = vi.fn(function (this: HTMLDialogElement) {
    this.open = false;
    this.dispatchEvent(new Event("close"));
  });
});

beforeEach(() => {
  resetStore();
  vi.clearAllMocks();
});

describe("F03: Home 空状态入口", () => {
  it("空状态下显示'记灵感'和'建任务'按钮", () => {
    useTaskStore.setState({
      tasks: [],
      isLoading: false,
      serviceUnavailable: false,
    });

    renderWithRouter(<Home />);

    expect(screen.getByText("记灵感")).toBeTruthy();
    expect(screen.getByText("建任务")).toBeTruthy();
  });

  it("点击'记灵感'聚焦 QuickCaptureBar 输入框", async () => {
    useTaskStore.setState({
      tasks: [],
      isLoading: false,
      serviceUnavailable: false,
    });

    renderWithRouter(<Home />);

    const focusBtn = screen.getByText("记灵感");
    await userEvent.click(focusBtn);

    const input = screen.getByPlaceholderText("记录灵感或任务...");
    expect(input).toBeTruthy();
    // focusTrigger 触发后 input 会被 focus
    await waitFor(() => {
      expect(document.activeElement).toBe(input);
    });
  });

  it("点击'建任务'打开 CreateDialog(task)", async () => {
    useTaskStore.setState({
      tasks: [],
      isLoading: false,
      serviceUnavailable: false,
    });

    renderWithRouter(<Home />);

    const createBtn = screen.getByText("建任务");
    await userEvent.click(createBtn);

    // CreateDialog 应该打开，显示类型选择器
    await waitFor(() => {
      expect(screen.getByText("新建条目")).toBeTruthy();
    });
  });
});

describe("F03: Home 非空状态下 QuickCaptureBar 渲染", () => {
  it("非空状态显示 QuickCaptureBar 而非 6 个按钮", () => {
    useTaskStore.setState({
      tasks: [createMockTask({ id: "1" })],
      isLoading: false,
      serviceUnavailable: false,
    });

    renderWithRouter(<Home />);

    // QuickCaptureBar 存在
    expect(screen.getByPlaceholderText("记录灵感或任务...")).toBeTruthy();

    // 旧的 6 个快捷按钮不应存在
    expect(screen.queryByText("写笔记")).toBeNull();
    expect(screen.queryByText("记决策")).toBeNull();
    expect(screen.queryByText("写复盘")).toBeNull();
    expect(screen.queryByText("记疑问")).toBeNull();
  });

  it("非空状态下其他卡片正常渲染", () => {
    useTaskStore.setState({
      tasks: [createMockTask({ id: "1" })],
      isLoading: false,
      serviceUnavailable: false,
    });

    renderWithRouter(<Home />);

    // 最近灵感卡片
    expect(screen.getByText("最近灵感")).toBeTruthy();
  });
});
