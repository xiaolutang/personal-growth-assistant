import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import PageSuggestions from "./PageSuggestions";

describe("PageSuggestions", () => {
  it("home 页渲染正确建议", () => {
    render(
      <PageSuggestions
        pageContext={{ page_type: "home" }}
        onSuggestionClick={vi.fn()}
        hasMessages={false}
      />
    );
    expect(screen.getByText("今日有哪些任务?")).toBeDefined();
    expect(screen.getByText("帮我记个想法")).toBeDefined();
    expect(screen.getByText("整理待办")).toBeDefined();
  });

  it("explore 页渲染正确建议", () => {
    render(
      <PageSuggestions
        pageContext={{ page_type: "explore" }}
        onSuggestionClick={vi.fn()}
        hasMessages={false}
      />
    );
    expect(screen.getByText("最近学了什么?")).toBeDefined();
    expect(screen.getByText("搜索相关笔记")).toBeDefined();
  });

  it("entry 页渲染正确建议", () => {
    render(
      <PageSuggestions
        pageContext={{ page_type: "entry", entry_id: "inbox-abc" }}
        onSuggestionClick={vi.fn()}
        hasMessages={false}
      />
    );
    expect(screen.getByText("帮我补充内容")).toBeDefined();
    expect(screen.getByText("关联到其他条目")).toBeDefined();
  });

  it("review 页渲染正确建议", () => {
    render(
      <PageSuggestions
        pageContext={{ page_type: "review" }}
        onSuggestionClick={vi.fn()}
        hasMessages={false}
      />
    );
    expect(screen.getByText("本周完成率?")).toBeDefined();
    expect(screen.getByText("生成本月总结")).toBeDefined();
  });

  it("graph 页渲染正确建议", () => {
    render(
      <PageSuggestions
        pageContext={{ page_type: "graph" }}
        onSuggestionClick={vi.fn()}
        hasMessages={false}
      />
    );
    expect(screen.getByText("我的知识图谱有哪些概念?")).toBeDefined();
  });

  it("有消息时不渲染 chips", () => {
    const { container } = render(
      <PageSuggestions
        pageContext={{ page_type: "home" }}
        onSuggestionClick={vi.fn()}
        hasMessages={true}
      />
    );
    expect(container.innerHTML).toBe("");
  });

  it("无 pageContext 时不渲染 chips", () => {
    const { container } = render(
      <PageSuggestions
        pageContext={null}
        onSuggestionClick={vi.fn()}
        hasMessages={false}
      />
    );
    expect(container.innerHTML).toBe("");
  });

  it("点击 chip 触发 onSuggestionClick 回调", () => {
    const onClick = vi.fn();
    render(
      <PageSuggestions
        pageContext={{ page_type: "home" }}
        onSuggestionClick={onClick}
        hasMessages={false}
      />
    );
    fireEvent.click(screen.getByText("帮我记个想法"));
    expect(onClick).toHaveBeenCalledWith("帮我记个想法");
  });

  it("未知的 page_type 不渲染", () => {
    const { container } = render(
      <PageSuggestions
        pageContext={{ page_type: "unknown" } as any}
        onSuggestionClick={vi.fn()}
        hasMessages={false}
      />
    );
    expect(container.innerHTML).toBe("");
  });
});
