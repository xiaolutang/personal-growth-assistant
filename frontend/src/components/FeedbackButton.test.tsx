import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { FeedbackButton } from "./FeedbackButton";
import { useChatStore } from "@/stores/chatStore";
import { ApiError } from "@/services/api";

const { submitFeedbackMock } = vi.hoisted(() => ({
  submitFeedbackMock: vi.fn(),
}));

vi.mock("@/services/api", async () => {
  const actual = await vi.importActual<typeof import("@/services/api")>("@/services/api");
  return {
    ...actual,
    submitFeedback: submitFeedbackMock,
  };
});

describe("FeedbackButton", () => {
  afterEach(() => {
    submitFeedbackMock.mockReset();
    useChatStore.setState({ panelHeight: 300 });
    vi.useRealTimers();
  });

  it("标题为空时提交按钮禁用，并可展开关闭表单", async () => {
    const user = userEvent.setup();
    render(<FeedbackButton />);

    await user.click(screen.getByRole("button", { name: "打开反馈表单" }));
    expect(screen.getByText("提交反馈")).toBeInTheDocument();

    const submitButton = screen.getByRole("button", { name: "提交" });
    expect(submitButton).toBeDisabled();

    await user.click(screen.getByRole("button", { name: "关闭" }));
    expect(screen.queryByText("提交反馈")).not.toBeInTheDocument();
  });

  it("提交成功后显示成功提示并自动关闭", async () => {
    const user = userEvent.setup();
    submitFeedbackMock.mockResolvedValue({
      success: true,
      issue: { id: 1, title: "搜索慢", status: "open", created_at: "2026-04-12T10:00:00Z" },
    });

    render(<FeedbackButton />);

    await user.click(screen.getByRole("button", { name: "打开反馈表单" }));
    await user.type(screen.getByPlaceholderText("例如：搜索结果加载缓慢"), "搜索结果很慢");
    await user.click(screen.getByRole("button", { name: "提交" }));

    expect(await screen.findByText("反馈已提交，我们会尽快处理。")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.queryByText("提交反馈")).not.toBeInTheDocument();
    }, { timeout: 2500 });
  });

  it("提交失败时显示错误信息", async () => {
    const user = userEvent.setup();
    submitFeedbackMock.mockRejectedValue(new ApiError(503, "反馈服务暂时不可用，请稍后重试"));

    render(<FeedbackButton />);

    await user.click(screen.getByRole("button", { name: "打开反馈表单" }));
    await user.type(screen.getByPlaceholderText("例如：搜索结果加载缓慢"), "接口失败");
    await user.click(screen.getByRole("button", { name: "提交" }));

    expect(await screen.findByText("反馈服务暂时不可用，请稍后重试")).toBeInTheDocument();
  });

  it("根据 FloatingChat 高度应用避让偏移", async () => {
    useChatStore.setState({ panelHeight: 360 });

    render(<FeedbackButton />);

    expect(screen.getByTestId("feedback-container")).toHaveStyle({ bottom: "376px" });
  });
});
