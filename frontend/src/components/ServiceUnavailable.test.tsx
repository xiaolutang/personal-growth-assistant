import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ServiceUnavailable } from "./ServiceUnavailable";

describe("ServiceUnavailable", () => {
  it("显示服务不可用提示文案", () => {
    render(<ServiceUnavailable />);

    expect(screen.getByText("服务暂时不可用")).toBeInTheDocument();
    expect(
      screen.getByText("后端服务正在启动中或暂时无法响应，请稍后重试")
    ).toBeInTheDocument();
  });

  it("有重试按钮时渲染并可点击", async () => {
    const onRetry = vi.fn();
    render(<ServiceUnavailable onRetry={onRetry} />);

    const retryButton = screen.getByText("重试");
    expect(retryButton).toBeInTheDocument();

    await userEvent.click(retryButton);
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("无重试按钮时不渲染按钮", () => {
    render(<ServiceUnavailable />);

    expect(screen.queryByText("重试")).not.toBeInTheDocument();
  });
});
