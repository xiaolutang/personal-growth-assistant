import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { SearchBar } from "../SearchBar";

describe("SearchBar", () => {
  const defaultProps = {
    searchQuery: "",
    onSearchQueryChange: vi.fn(),
    onKeyDown: vi.fn(),
    onFocus: vi.fn(),
    onBlur: vi.fn(),
    showPanel: false,
    searchHistory: [],
    onDeleteHistory: vi.fn(),
    onSuggestionClick: vi.fn(),
    popularTags: [],
    selectedTags: [],
    onTagFilter: vi.fn(),
  };

  it("渲染输入框和 placeholder", () => {
    render(<SearchBar {...defaultProps} />);
    const input = screen.getByPlaceholderText("试试搜索：最近学习的主题...");
    expect(input).toBeTruthy();
  });

  it("输入内容触发 onSearchQueryChange", () => {
    const onSearchQueryChange = vi.fn();
    render(<SearchBar {...defaultProps} onSearchQueryChange={onSearchQueryChange} />);
    const input = screen.getByPlaceholderText("试试搜索：最近学习的主题...");
    fireEvent.change(input, { target: { value: "hello" } });
    expect(onSearchQueryChange).toHaveBeenCalledWith("hello");
  });

  it("按 Enter 触发 onKeyDown", () => {
    const onKeyDown = vi.fn();
    render(<SearchBar {...defaultProps} onKeyDown={onKeyDown} />);
    const input = screen.getByPlaceholderText("试试搜索：最近学习的主题...");
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onKeyDown).toHaveBeenCalled();
  });

  it("showPanel=true 且有历史时显示建议面板", () => {
    render(
      <SearchBar
        {...defaultProps}
        showPanel={true}
        searchHistory={["query1", "query2"]}
      />
    );
    expect(screen.getByText("最近搜索")).toBeTruthy();
    expect(screen.getByText("query1")).toBeTruthy();
    expect(screen.getByText("query2")).toBeTruthy();
  });

  it("showPanel=false 时不显示建议面板", () => {
    render(
      <SearchBar
        {...defaultProps}
        showPanel={false}
        searchHistory={["query1"]}
      />
    );
    expect(screen.queryByText("最近搜索")).toBeNull();
  });

  it("点击历史项触发 onSuggestionClick", () => {
    const onSuggestionClick = vi.fn();
    render(
      <SearchBar
        {...defaultProps}
        showPanel={true}
        searchHistory={["query1"]}
        onSuggestionClick={onSuggestionClick}
      />
    );
    // Use mousedown on the history item row
    const queryEl = screen.getByText("query1");
    fireEvent.mouseDown(queryEl.closest("div")!);
    expect(onSuggestionClick).toHaveBeenCalledWith("query1");
  });

  it("点击删除历史按钮触发 onDeleteHistory 且不触发 onSuggestionClick", () => {
    const onDeleteHistory = vi.fn();
    const onSuggestionClick = vi.fn();
    render(
      <SearchBar
        {...defaultProps}
        showPanel={true}
        searchHistory={["query1"]}
        onDeleteHistory={onDeleteHistory}
        onSuggestionClick={onSuggestionClick}
      />
    );
    const historyRow = screen.getByText("query1").closest("div")!;
    const deleteBtn = historyRow.querySelector("button") as HTMLElement;
    expect(deleteBtn).toBeTruthy();
    // 模拟真实事件序列：mouseDown + click
    fireEvent.mouseDown(deleteBtn);
    fireEvent.click(deleteBtn);
    expect(onDeleteHistory).toHaveBeenCalledWith("query1");
    // mouseDown 被 stopPropagation 阻止冒泡，不应触发父级 onSuggestionClick
    expect(onSuggestionClick).not.toHaveBeenCalled();
  });

  it("showPanel=true 且有热门标签时显示标签", () => {
    render(
      <SearchBar
        {...defaultProps}
        showPanel={true}
        popularTags={["tag1", "tag2"]}
      />
    );
    expect(screen.getByText("热门标签")).toBeTruthy();
    expect(screen.getByText("#tag1")).toBeTruthy();
    expect(screen.getByText("#tag2")).toBeTruthy();
  });

  it("点击标签触发 onTagFilter", () => {
    const onTagFilter = vi.fn();
    render(
      <SearchBar
        {...defaultProps}
        showPanel={true}
        popularTags={["tag1"]}
        onTagFilter={onTagFilter}
      />
    );
    const tagBtn = screen.getByText("#tag1");
    fireEvent.mouseDown(tagBtn);
    expect(onTagFilter).toHaveBeenCalledWith("tag1");
  });

  it("已选标签高亮显示", () => {
    render(
      <SearchBar
        {...defaultProps}
        showPanel={true}
        popularTags={["tag1"]}
        selectedTags={["tag1"]}
      />
    );
    const tagBtn = screen.getByText("#tag1").closest("button")!;
    expect(tagBtn.className).toContain("bg-indigo-500");
  });
});
