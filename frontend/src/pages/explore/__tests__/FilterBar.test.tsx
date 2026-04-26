import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { FilterBar } from "../FilterBar";

describe("FilterBar", () => {
  const defaultProps = {
    timeRange: "" as const,
    setTimeRange: vi.fn(),
    selectedTags: [] as string[],
    onTagFilter: vi.fn(),
    onClearFilters: vi.fn(),
    hasActiveFilters: false,
  };

  it("渲染所有时间范围选项按钮", () => {
    render(<FilterBar {...defaultProps} />);
    expect(screen.getByText("全部")).toBeTruthy();
    expect(screen.getByText("今天")).toBeTruthy();
    expect(screen.getByText("本周")).toBeTruthy();
    expect(screen.getByText("本月")).toBeTruthy();
  });

  it("当前选中的时间范围高亮", () => {
    render(<FilterBar {...defaultProps} timeRange="today" />);
    const todayBtn = screen.getByText("今天");
    expect(todayBtn.className).toContain("bg-indigo-500");
  });

  it("点击时间范围按钮调用 setTimeRange", () => {
    const setTimeRange = vi.fn();
    render(<FilterBar {...defaultProps} setTimeRange={setTimeRange} />);
    fireEvent.click(screen.getByText("今天"));
    expect(setTimeRange).toHaveBeenCalledWith("today");
  });

  it("hasActiveFilters=false 时不显示清除按钮", () => {
    render(<FilterBar {...defaultProps} hasActiveFilters={false} />);
    expect(screen.queryByText("全部清除")).toBeNull();
  });

  it("hasActiveFilters=true 时显示清除按钮和过滤条件", () => {
    render(
      <FilterBar
        {...defaultProps}
        hasActiveFilters={true}
        timeRange="today"
        selectedTags={["mytag"]}
      />
    );
    expect(screen.getByText("全部清除")).toBeTruthy();
    // "今天" 出现在按钮组和 filter chip 中，使用 getAllByText
    expect(screen.getAllByText("今天").length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("#mytag")).toBeTruthy(); // tag chip
  });

  it("点击全部清除调用 onClearFilters", () => {
    const onClearFilters = vi.fn();
    render(
      <FilterBar
        {...defaultProps}
        hasActiveFilters={true}
        timeRange="today"
        onClearFilters={onClearFilters}
      />
    );
    fireEvent.click(screen.getByText("全部清除"));
    expect(onClearFilters).toHaveBeenCalled();
  });

  it("点击标签 chip 上的 X 调用 onTagFilter", () => {
    const onTagFilter = vi.fn();
    render(
      <FilterBar
        {...defaultProps}
        hasActiveFilters={true}
        selectedTags={["tag1"]}
        onTagFilter={onTagFilter}
      />
    );
    // Find the X button inside the tag chip
    const tagChip = screen.getByText("#tag1").closest("span")!;
    const xBtn = tagChip.querySelector("button");
    expect(xBtn).toBeTruthy();
    fireEvent.click(xBtn!);
    expect(onTagFilter).toHaveBeenCalledWith("tag1");
  });
});
