import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { FeedbackButton } from "./FeedbackButton";
import { useAgentStore } from "@/stores/agentStore";
import { ApiError } from "@/services/api";

const { submitFeedbackMock, getFeedbackListMock, syncFeedbackMock } = vi.hoisted(() => ({
  submitFeedbackMock: vi.fn(),
  getFeedbackListMock: vi.fn(),
  syncFeedbackMock: vi.fn(),
}));

vi.mock("@/services/api", async () => {
  const actual = await vi.importActual<typeof import("@/services/api")>("@/services/api");
  return {
    ...actual,
    submitFeedback: submitFeedbackMock,
    getFeedbackList: getFeedbackListMock,
    syncFeedback: syncFeedbackMock,
  };
});

describe("FeedbackButton", () => {
  afterEach(() => {
    submitFeedbackMock.mockReset();
    getFeedbackListMock.mockReset();
    syncFeedbackMock.mockReset();
    useAgentStore.setState({ panelHeight: 300 });
    vi.useRealTimers();
  });

  it("标题为空时提交按钮禁用，并可展开关闭面板", async () => {
    const user = userEvent.setup();
    render(<FeedbackButton />);

    await user.click(screen.getByRole("button", { name: "打开反馈面板" }));
    // "提交反馈" appears as tab text
    expect(screen.getByRole("button", { name: "提交反馈" })).toBeInTheDocument();

    const submitButton = screen.getByRole("button", { name: "提交" });
    expect(submitButton).toBeDisabled();

    await user.click(screen.getByRole("button", { name: "关闭" }));
    expect(screen.queryByRole("button", { name: "提交反馈" })).not.toBeInTheDocument();
  });

  it("提交成功后显示成功提示并自动切换到我的反馈 Tab", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

    submitFeedbackMock.mockResolvedValue({
      success: true,
      feedback: { id: 1, title: "搜索慢", severity: "medium", status: "pending", log_service_issue_id: null, created_at: "2026-04-12T10:00:00Z" },
    });
    syncFeedbackMock.mockRejectedValue(new Error("sync unavailable"));
    getFeedbackListMock.mockResolvedValue({
      items: [
        { id: 1, title: "搜索慢", severity: "medium", status: "pending", log_service_issue_id: null, created_at: "2026-04-12T10:00:00Z" },
      ],
      total: 1,
    });

    render(<FeedbackButton />);

    await user.click(screen.getByRole("button", { name: "打开反馈面板" }));
    await user.type(screen.getByPlaceholderText("例如：搜索结果加载缓慢"), "搜索结果很慢");
    await user.click(screen.getByRole("button", { name: "提交" }));

    expect(await screen.findByText("反馈已提交，我们会尽快处理。")).toBeInTheDocument();

    // after timer fires, should auto-switch to list tab
    vi.advanceTimersByTime(1500);

    await waitFor(() => {
      expect(screen.getByText("搜索慢")).toBeInTheDocument();
    });

    // verify only one list fetch happened (no double-request)
    expect(getFeedbackListMock).toHaveBeenCalledTimes(1);
  });

  it("提交失败时显示错误信息", async () => {
    const user = userEvent.setup();
    submitFeedbackMock.mockRejectedValue(new ApiError(503, "反馈服务暂时不可用，请稍后重试"));

    render(<FeedbackButton />);

    await user.click(screen.getByRole("button", { name: "打开反馈面板" }));
    await user.type(screen.getByPlaceholderText("例如：搜索结果加载缓慢"), "接口失败");
    await user.click(screen.getByRole("button", { name: "提交" }));

    expect(await screen.findByText("反馈服务暂时不可用，请稍后重试")).toBeInTheDocument();
  });

  it("根据 FloatingChat 高度应用避让偏移", async () => {
    useAgentStore.setState({ panelHeight: 360 });

    render(<FeedbackButton />);

    expect(screen.getByTestId("feedback-container")).toHaveStyle({ bottom: "376px" });
  });

  it("点击「我的反馈」Tab 展示反馈列表", async () => {
    const user = userEvent.setup();
    syncFeedbackMock.mockRejectedValue(new Error("sync unavailable"));
    getFeedbackListMock.mockResolvedValue({
      items: [
        { id: 1, title: "Bug A", severity: "high", status: "pending", log_service_issue_id: null, created_at: "2026-04-12T10:00:00Z" },
        { id: 2, title: "Bug B", severity: "low", status: "reported", log_service_issue_id: 42, created_at: "2026-04-11T08:00:00Z" },
      ],
      total: 2,
    });

    render(<FeedbackButton />);

    await user.click(screen.getByRole("button", { name: "打开反馈面板" }));
    await user.click(screen.getByRole("button", { name: "我的反馈" }));

    expect(await screen.findByText("Bug A")).toBeInTheDocument();
    expect(screen.getByText("Bug B")).toBeInTheDocument();
    // status colors
    expect(screen.getByText("待处理")).toHaveClass("text-amber-500");
    expect(screen.getByText("已上报")).toHaveClass("text-blue-600");
  });

  it("反馈列表为空时显示引导文案", async () => {
    const user = userEvent.setup();
    syncFeedbackMock.mockRejectedValue(new Error("sync unavailable"));
    getFeedbackListMock.mockResolvedValue({ items: [], total: 0 });

    render(<FeedbackButton />);

    await user.click(screen.getByRole("button", { name: "打开反馈面板" }));
    await user.click(screen.getByRole("button", { name: "我的反馈" }));

    expect(await screen.findByText("暂无反馈记录")).toBeInTheDocument();
  });

  it("反馈列表加载失败时显示错误提示和重试按钮", async () => {
    const user = userEvent.setup();
    syncFeedbackMock.mockRejectedValue(new Error("sync unavailable"));
    getFeedbackListMock.mockRejectedValue(new Error("Network error"));

    render(<FeedbackButton />);

    await user.click(screen.getByRole("button", { name: "打开反馈面板" }));
    await user.click(screen.getByRole("button", { name: "我的反馈" }));

    expect(await screen.findByText("加载失败，请重试")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "重试" })).toBeInTheDocument();
  });
});
