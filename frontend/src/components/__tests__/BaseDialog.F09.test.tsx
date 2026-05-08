import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

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

import { BaseDialog } from "../BaseDialog";

describe("BaseDialog — backdrop click", () => {
  const defaultProps = {
    open: true,
    onOpenChange: vi.fn(),
    title: "测试弹窗",
    children: <div>内容</div>,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("默认情况下点击遮罩（dialog 自身）会关闭弹窗", async () => {
    const onOpenChange = vi.fn();
    render(<BaseDialog {...defaultProps} onOpenChange={onOpenChange} />);

    const dialog = screen.getByRole("dialog");
    expect(dialog).toBeInTheDocument();

    // 点击 dialog 元素本身（模拟遮罩点击）
    await userEvent.click(dialog);
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("点击内容区域不会关闭弹窗", async () => {
    const onOpenChange = vi.fn();
    render(<BaseDialog {...defaultProps} onOpenChange={onOpenChange} />);

    // 点击内容区
    await userEvent.click(screen.getByText("内容"));
    expect(onOpenChange).not.toHaveBeenCalledWith(false);
  });

  it("backdropClickClose=false 时点击遮罩不关闭弹窗", async () => {
    const onOpenChange = vi.fn();
    render(
      <BaseDialog {...defaultProps} onOpenChange={onOpenChange} backdropClickClose={false} />
    );

    const dialog = screen.getByRole("dialog");
    await userEvent.click(dialog);
    expect(onOpenChange).not.toHaveBeenCalledWith(false);
  });

  it("点击关闭按钮会关闭弹窗", async () => {
    const onOpenChange = vi.fn();
    render(<BaseDialog {...defaultProps} onOpenChange={onOpenChange} />);

    const closeBtn = screen.getByLabelText("关闭");
    await userEvent.click(closeBtn);
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("open=false 时不渲染", () => {
    render(<BaseDialog {...defaultProps} open={false} />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("ESC 键触发 dialog close 事件后调用 onOpenChange(false)", async () => {
    const onOpenChange = vi.fn();
    render(<BaseDialog {...defaultProps} onOpenChange={onOpenChange} />);

    const dialog = screen.getByRole("dialog");
    // dialog 元素 ESC 时原生会调用 close()，触发 onClose 事件
    dialog.dispatchEvent(new Event("close"));
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });
});
