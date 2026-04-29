/**
 * FeedbackPanel.test.tsx — 反馈面板组件测试
 *
 * 覆盖：渲染、tab 切换、提交成功/失败、列表加载、空列表、加载失败
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { FeedbackPanel } from "./FeedbackPanel";

// Mock API
vi.mock("@/services/api", () => ({
  submitFeedback: vi.fn(),
  getFeedbackList: vi.fn(),
  syncFeedback: vi.fn(),
  ApiError: class ApiError extends Error {
    status: number;
    constructor(status: number, message: string) {
      super(message);
      this.status = status;
    }
    toUserMessage() {
      return `请求失败 (${this.status})`;
    }
  },
}));

import { submitFeedback, getFeedbackList, syncFeedback } from "@/services/api";

const mockedSubmitFeedback = vi.mocked(submitFeedback);
const mockedGetFeedbackList = vi.mocked(getFeedbackList);
const mockedSyncFeedback = vi.mocked(syncFeedback);

describe("FeedbackPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedSyncFeedback.mockResolvedValue({ items: [], synced_count: 0, updated_count: 0, total: 0 });
    mockedGetFeedbackList.mockResolvedValue({ items: [], total: 0 });
  });

  it("默认显示提交反馈 tab", () => {
    render(<FeedbackPanel isOpen={true} />);
    expect(screen.getByText("提交反馈")).toBeDefined();
    expect(screen.getByText("我的反馈")).toBeDefined();
    expect(screen.getByPlaceholderText("例如：搜索结果加载缓慢")).toBeDefined();
  });

  it("空标题时提交按钮禁用", () => {
    render(<FeedbackPanel isOpen={true} />);
    expect(screen.getByRole("button", { name: "提交" })).toBeDisabled();
  });

  it("有标题时提交按钮启用", () => {
    render(<FeedbackPanel isOpen={true} />);
    const input = screen.getByPlaceholderText("例如：搜索结果加载缓慢");
    fireEvent.change(input, { target: { value: "测试反馈" } });
    expect(screen.getByRole("button", { name: "提交" })).not.toBeDisabled();
  });

  it("提交成功后显示成功消息", async () => {
    mockedSubmitFeedback.mockResolvedValue({ success: true, feedback: {} });

    render(<FeedbackPanel isOpen={true} />);
    const input = screen.getByPlaceholderText("例如：搜索结果加载缓慢");
    fireEvent.change(input, { target: { value: "测试反馈标题" } });
    fireEvent.submit(input.closest("form")!);

    await waitFor(() => {
      expect(screen.getByText("反馈已提交，我们会尽快处理。")).toBeDefined();
    });
    expect(mockedSubmitFeedback).toHaveBeenCalledWith(
      expect.objectContaining({ title: "测试反馈标题" }),
    );
  });

  it("提交失败时显示错误消息", async () => {
    const { ApiError } = await import("@/services/api");
    mockedSubmitFeedback.mockRejectedValue(new ApiError(500, "服务器错误"));

    render(<FeedbackPanel isOpen={true} />);
    const input = screen.getByPlaceholderText("例如：搜索结果加载缓慢");
    fireEvent.change(input, { target: { value: "测试反馈" } });
    fireEvent.submit(input.closest("form")!);

    await waitFor(() => {
      expect(screen.getByText(/请求失败/)).toBeDefined();
    });
  });

  it("点击切换到列表 tab 并加载数据", async () => {
    mockedGetFeedbackList.mockResolvedValue({
      items: [
        {
          id: 1,
          user_id: "user1",
          title: "搜索很慢",
          description: "",
          severity: "medium",
          status: "pending",
          feedback_type: "general",
          created_at: "2026-04-29T10:00:00Z",
          updated_at: null,
        },
      ],
      total: 1,
    });

    render(<FeedbackPanel isOpen={true} />);
    fireEvent.click(screen.getByText("我的反馈"));

    await waitFor(() => {
      expect(screen.getByText("搜索很慢")).toBeDefined();
      expect(screen.getByText("待处理")).toBeDefined();
    });
  });

  it("列表为空时显示空提示", async () => {
    mockedGetFeedbackList.mockResolvedValue({ items: [], total: 0 });

    render(<FeedbackPanel isOpen={true} />);
    fireEvent.click(screen.getByText("我的反馈"));

    await waitFor(() => {
      expect(screen.getByText("暂无反馈记录")).toBeDefined();
    });
  });

  it("列表加载失败时显示重试", async () => {
    mockedGetFeedbackList.mockRejectedValue(new Error("网络错误"));

    render(<FeedbackPanel isOpen={true} />);
    fireEvent.click(screen.getByText("我的反馈"));

    await waitFor(() => {
      expect(screen.getByText("加载失败，请重试")).toBeDefined();
      expect(screen.getByText("重试")).toBeDefined();
    });
  });
});
