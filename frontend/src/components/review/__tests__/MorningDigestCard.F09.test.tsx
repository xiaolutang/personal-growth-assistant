import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

// Mock useMorningDigest
const mockUseMorningDigest = vi.fn();
vi.mock("@/hooks/useMorningDigest", () => ({
  useMorningDigest: () => mockUseMorningDigest(),
}));

import { MorningDigestCard } from "@/components/review/MorningDigestCard";
import type { MorningDigestResponse } from "@/services/api";

const mockDigest: MorningDigestResponse = {
  ai_suggestion: "今日建议：专注完成重要任务",
  todos: [
    { id: "1", title: "完成任务A" },
    { id: "2", title: "完成任务B" },
  ],
  overdue: [{ id: "3", title: "过期任务" }],
  stale_inbox: [{ id: "4", title: "待处理灵感" }],
  weekly_summary: {
    new_concepts: ["React", "TypeScript"],
  },
  learning_streak: 5,
  cached_at: "2026-05-08T08:00:00Z",
  daily_focus: {
    title: "今日聚焦：完成项目",
    description: "集中精力完成项目开发",
    target_entry_id: "entry-1",
  },
  pattern_insights: ["你最近在学习 React 方面很积极"],
  knowledge_recommendations: {
    knowledge_gaps: [{ concept: "Redux", missing_prerequisites: ["React 基础"] }],
    review_suggestions: [{ concept: "Hooks", last_seen_days_ago: 7 }],
    related_concepts: [{ concept: "Next.js", score: 0.8 }],
  },
} as unknown as MorningDigestResponse;

describe("MorningDigestCard — 合并后参数化组件", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("variant='review'", () => {
    it("visible=false 时不渲染", () => {
      mockUseMorningDigest.mockReturnValue({ data: mockDigest, loading: false, error: null });
      const { container } = render(<MorningDigestCard variant="review" visible={false} />);
      expect(container.innerHTML).toBe("");
    });

    it("data 为 null 时不渲染", () => {
      mockUseMorningDigest.mockReturnValue({ data: null, loading: false, error: null });
      const { container } = render(<MorningDigestCard variant="review" visible={true} />);
      expect(container.innerHTML).toBe("");
    });

    it("正常渲染 review 变体，显示琥珀色边框和晨报标题", () => {
      mockUseMorningDigest.mockReturnValue({ data: mockDigest, loading: false, error: null });
      render(<MorningDigestCard variant="review" visible={true} />);

      expect(screen.getByText("今日晨报")).toBeInTheDocument();
      expect(screen.getByText("连续 5 天")).toBeInTheDocument();
      expect(screen.getByText("待办 2 项")).toBeInTheDocument();
      expect(screen.getByText("过期 1 项")).toBeInTheDocument();
      expect(screen.getByText("灵感提醒 1 项")).toBeInTheDocument();
    });

    it("使用琥珀色左边框（amber）", () => {
      mockUseMorningDigest.mockReturnValue({ data: mockDigest, loading: false, error: null });
      const { container } = render(<MorningDigestCard variant="review" visible={true} />);

      // 找到 Card 元素（第一个包含 border-l 的元素）
      const card = container.querySelector("[class*='border-l-amber']");
      expect(card).toBeInTheDocument();
    });
  });

  describe("variant='home'", () => {
    it("loading 状态渲染骨架屏", () => {
      render(
        <MorningDigestCard
          variant="home"
          digest={null}
          digestLoading={true}
          digestError={null}
          onDismiss={vi.fn()}
          onNavigateToEntry={vi.fn()}
        />
      );
      // 骨架屏使用 animate-pulse
      const pulses = document.querySelectorAll(".animate-pulse");
      expect(pulses.length).toBeGreaterThan(0);
    });

    it("error 状态显示错误信息", () => {
      render(
        <MorningDigestCard
          variant="home"
          digest={null}
          digestLoading={false}
          digestError="加载失败"
          onDismiss={vi.fn()}
          onNavigateToEntry={vi.fn()}
        />
      );
      expect(screen.getByText("晨报加载失败，请稍后刷新")).toBeInTheDocument();
    });

    it("正常渲染 home 变体，显示靛蓝色边框和日知晨报标题", () => {
      render(
        <MorningDigestCard
          variant="home"
          digest={mockDigest}
          digestLoading={false}
          digestError={null}
          onDismiss={vi.fn()}
          onNavigateToEntry={vi.fn()}
        />
      );

      expect(screen.getByText("日知晨报")).toBeInTheDocument();
      // 检查 indigo 色调
      expect(screen.getByText("日知晨报").closest("[class]")?.className).toMatch(/indigo/);
      expect(screen.getByText("待办")).toBeInTheDocument();
      expect(screen.getByText("逾期")).toBeInTheDocument();
    });

    it("点击收起按钮回调 onDismiss", async () => {
      const onDismiss = vi.fn();
      render(
        <MorningDigestCard
          variant="home"
          digest={mockDigest}
          digestLoading={false}
          digestError={null}
          onDismiss={onDismiss}
          onNavigateToEntry={vi.fn()}
        />
      );

      const dismissBtn = screen.getByText("收起");
      expect(dismissBtn).toBeInTheDocument();
      await userEvent.click(dismissBtn);
      expect(onDismiss).toHaveBeenCalledTimes(1);
    });

    it("显示学习连续天数", () => {
      render(
        <MorningDigestCard
          variant="home"
          digest={mockDigest}
          digestLoading={false}
          digestError={null}
          onDismiss={vi.fn()}
          onNavigateToEntry={vi.fn()}
        />
      );

      expect(screen.getByText("连续学习 5 天")).toBeInTheDocument();
    });

    it("显示今日聚焦区域", () => {
      render(
        <MorningDigestCard
          variant="home"
          digest={mockDigest}
          digestLoading={false}
          digestError={null}
          onDismiss={vi.fn()}
          onNavigateToEntry={vi.fn()}
        />
      );

      expect(screen.getByText("今日聚焦：完成项目")).toBeInTheDocument();
    });

    it("显示知识建议", () => {
      render(
        <MorningDigestCard
          variant="home"
          digest={mockDigest}
          digestLoading={false}
          digestError={null}
          onDismiss={vi.fn()}
          onNavigateToEntry={vi.fn()}
        />
      );

      expect(screen.getByText("知识建议")).toBeInTheDocument();
      expect(screen.getByText("Redux")).toBeInTheDocument();
    });

    it("显示模式洞察", () => {
      render(
        <MorningDigestCard
          variant="home"
          digest={mockDigest}
          digestLoading={false}
          digestError={null}
          onDismiss={vi.fn()}
          onNavigateToEntry={vi.fn()}
        />
      );

      expect(screen.getByText(/你最近在学习 React 方面很积极/)).toBeInTheDocument();
    });
  });
});
