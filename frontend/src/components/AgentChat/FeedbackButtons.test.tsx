import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FeedbackButtons } from "./FeedbackButtons";

describe("FeedbackButtons", () => {
  const defaultProps = {
    messageId: "msg-test-001",
    onSubmit: vi.fn(),
  };

  it("渲染三个反馈按钮（赞、踩、标记）", () => {
    render(<FeedbackButtons {...defaultProps} />);
    expect(screen.getByLabelText("赞")).toBeInTheDocument();
    expect(screen.getByLabelText("踩")).toBeInTheDocument();
    expect(screen.getByLabelText("标记")).toBeInTheDocument();
  });

  it("点击赞直接提交正面反馈", async () => {
    const onSubmit = vi.fn();
    render(<FeedbackButtons {...defaultProps} onSubmit={onSubmit} />);

    fireEvent.click(screen.getByLabelText("赞"));
    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit).toHaveBeenCalledWith({ type: "positive" });
  });

  it("点击赞后按钮变为已提交状态", async () => {
    render(<FeedbackButtons {...defaultProps} />);
    fireEvent.click(screen.getByLabelText("赞"));
    expect(screen.getByText("已反馈")).toBeInTheDocument();
    // 再次点击不应该重复提交
    const onSubmit = defaultProps.onSubmit;
    onSubmit.mockClear();
    fireEvent.click(screen.getByLabelText("赞"));
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("点击踩展开反馈面板", async () => {
    render(<FeedbackButtons {...defaultProps} />);
    fireEvent.click(screen.getByLabelText("踩"));
    expect(screen.getByText("请选择问题类型：")).toBeInTheDocument();
    // 应该有 6 个预设选项
    expect(screen.getByText("理解错了")).toBeInTheDocument();
    expect(screen.getByText("操作不正确")).toBeInTheDocument();
    expect(screen.getByText("回复没帮助")).toBeInTheDocument();
    expect(screen.getByText("应该追问没追问")).toBeInTheDocument();
    expect(screen.getByText("不该追问追问了")).toBeInTheDocument();
    expect(screen.getByText("其他")).toBeInTheDocument();
  });

  it("选择预设选项并提交", async () => {
    const onSubmit = vi.fn();
    render(<FeedbackButtons {...defaultProps} onSubmit={onSubmit} />);

    // 展开负面反馈面板
    fireEvent.click(screen.getByLabelText("踩"));

    // 选择"理解错了"
    const radio = screen.getByDisplayValue("understanding_wrong");
    fireEvent.click(radio);

    // 点击提交
    const submitBtn = screen.getByRole("button", { name: "提交反馈" });
    fireEvent.click(submitBtn);

    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit).toHaveBeenCalledWith({
      type: "negative",
      reason: "understanding_wrong",
      detail: undefined,
    });

    // 提交后变为已提交状态
    expect(screen.getByText("已反馈")).toBeInTheDocument();
  });

  it("输入其他内容并提交", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<FeedbackButtons {...defaultProps} onSubmit={onSubmit} />);

    // 展开负面反馈面板
    await user.click(screen.getByLabelText("踩"));

    // 选择"其他"
    const radio = screen.getByDisplayValue("other");
    await user.click(radio);

    // 输入自定义内容
    const textarea = screen.getByPlaceholderText("请描述具体问题...");
    await user.type(textarea, "自定义反馈内容");

    // 点击提交
    await user.click(screen.getByRole("button", { name: "提交反馈" }));

    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit).toHaveBeenCalledWith({
      type: "negative",
      reason: "other",
      detail: "自定义反馈内容",
    });
  });

  it("未选择选项时提交按钮为禁用状态", () => {
    render(<FeedbackButtons {...defaultProps} />);
    fireEvent.click(screen.getByLabelText("踩"));

    const submitBtn = screen.getByRole("button", { name: "提交反馈" });
    expect(submitBtn).toBeDisabled();
  });

  it("点击标记展开标记面板并可提交", async () => {
    const onSubmit = vi.fn();
    render(<FeedbackButtons {...defaultProps} onSubmit={onSubmit} />);

    fireEvent.click(screen.getByLabelText("标记"));
    expect(screen.getByText("标记此回复不当")).toBeInTheDocument();

    const submitBtn = screen.getByRole("button", { name: "提交标记" });
    fireEvent.click(submitBtn);

    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit).toHaveBeenCalledWith({ type: "flag" });
  });

  it("提交后所有按钮不可点击", async () => {
    render(<FeedbackButtons {...defaultProps} />);
    fireEvent.click(screen.getByLabelText("赞"));

    expect(screen.getByLabelText("赞")).toBeDisabled();
    expect(screen.getByLabelText("踩")).toBeDisabled();
    expect(screen.getByLabelText("标记")).toBeDisabled();
  });
});
