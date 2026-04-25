import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { BatchActionBar } from "../BatchActionBar";

describe("BatchActionBar", () => {
  const defaultProps = {
    selectedCount: 3,
    batchLoading: false,
    onBatchCategory: vi.fn(),
    onBatchDelete: vi.fn(),
  };

  it("渲染已选数量", () => {
    render(<BatchActionBar {...defaultProps} />);
    expect(screen.getByText("已选 3 项")).toBeTruthy();
  });

  it("渲染转笔记、转灵感、删除按钮", () => {
    render(<BatchActionBar {...defaultProps} />);
    expect(screen.getByText("转笔记")).toBeTruthy();
    expect(screen.getByText("转灵感")).toBeTruthy();
    expect(screen.getByText("删除")).toBeTruthy();
  });

  it("点击转笔记按钮触发 onBatchCategory('note')", () => {
    const onBatchCategory = vi.fn();
    render(<BatchActionBar {...defaultProps} onBatchCategory={onBatchCategory} />);
    fireEvent.click(screen.getByText("转笔记"));
    expect(onBatchCategory).toHaveBeenCalledWith("note");
  });

  it("点击转灵感按钮触发 onBatchCategory('inbox')", () => {
    const onBatchCategory = vi.fn();
    render(<BatchActionBar {...defaultProps} onBatchCategory={onBatchCategory} />);
    fireEvent.click(screen.getByText("转灵感"));
    expect(onBatchCategory).toHaveBeenCalledWith("inbox");
  });

  it("点击删除按钮触发 onBatchDelete", () => {
    const onBatchDelete = vi.fn();
    render(<BatchActionBar {...defaultProps} onBatchDelete={onBatchDelete} />);
    fireEvent.click(screen.getByText("删除"));
    expect(onBatchDelete).toHaveBeenCalled();
  });

  it("batchLoading=true 时按钮禁用", () => {
    render(<BatchActionBar {...defaultProps} batchLoading={true} />);
    const buttons = screen.getAllByRole("button");
    for (const btn of buttons) {
      expect(btn).toBeDisabled();
    }
  });

  it("batchLoading=false 时按钮可用", () => {
    render(<BatchActionBar {...defaultProps} batchLoading={false} />);
    const buttons = screen.getAllByRole("button");
    for (const btn of buttons) {
      expect(btn).not.toBeDisabled();
    }
  });
});
