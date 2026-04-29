import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { BatchActionBar } from "../BatchActionBar";

describe("BatchActionBar", () => {
  const defaultProps = {
    selectedCount: 3,
    batchLoading: false,
    onBatchCategory: vi.fn(),
    onBatchDelete: vi.fn(),
    onBatchConvert: vi.fn(),
    allSelectedInbox: true,
  };

  it("渲染已选数量", () => {
    render(<BatchActionBar {...defaultProps} />);
    expect(screen.getByText("已选 3 项")).toBeTruthy();
  });

  it("渲染转任务、转决策、转笔记、转灵感、删除按钮", () => {
    render(<BatchActionBar {...defaultProps} />);
    expect(screen.getByText("转任务")).toBeTruthy();
    expect(screen.getByText("转决策")).toBeTruthy();
    expect(screen.getByText("转笔记")).toBeTruthy();
    expect(screen.getByText("转灵感")).toBeTruthy();
    expect(screen.getByText("删除")).toBeTruthy();
  });

  it("点击转任务按钮触发 onBatchConvert('task')", () => {
    const onBatchConvert = vi.fn();
    render(<BatchActionBar {...defaultProps} onBatchConvert={onBatchConvert} allSelectedInbox={true} />);
    fireEvent.click(screen.getByText("转任务"));
    expect(onBatchConvert).toHaveBeenCalledWith("task");
  });

  it("点击转决策按钮触发 onBatchConvert('decision')", () => {
    const onBatchConvert = vi.fn();
    render(<BatchActionBar {...defaultProps} onBatchConvert={onBatchConvert} allSelectedInbox={true} />);
    fireEvent.click(screen.getByText("转决策"));
    expect(onBatchConvert).toHaveBeenCalledWith("decision");
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

  it("batchLoading=false 且 allSelectedInbox=true 时转化按钮可用", () => {
    render(<BatchActionBar {...defaultProps} batchLoading={false} allSelectedInbox={true} />);
    const taskBtn = screen.getByText("转任务").closest("button")!;
    const decisionBtn = screen.getByText("转决策").closest("button")!;
    expect(taskBtn).not.toBeDisabled();
    expect(decisionBtn).not.toBeDisabled();
  });

  it("allSelectedInbox=false 时转化按钮禁用", () => {
    render(<BatchActionBar {...defaultProps} allSelectedInbox={false} />);
    const taskBtn = screen.getByText("转任务").closest("button")!;
    const decisionBtn = screen.getByText("转决策").closest("button")!;
    expect(taskBtn).toBeDisabled();
    expect(decisionBtn).toBeDisabled();
  });

  it("无 onBatchConvert 时转化按钮禁用", () => {
    render(<BatchActionBar {...defaultProps} onBatchConvert={undefined} allSelectedInbox={true} />);
    const taskBtn = screen.getByText("转任务").closest("button")!;
    expect(taskBtn).toBeDisabled();
  });
});
