/**
 * useSmartSuggestions hook 单元测试
 * 覆盖日期解析集成、类型建议、suppress 逻辑、stale-date 清理
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useSmartSuggestions } from "./useSmartSuggestions";

// 固定时间避免午夜/date-rollover 测试失败
const FIXED_DATE = new Date(2025, 3, 30); // 2025-04-30 周三

describe("useSmartSuggestions", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(FIXED_DATE);
  });

  afterEach(() => {
    vi.useRealTimers();
  });
  describe("日期解析", () => {
    it("输入含'明天'时返回解析后的日期", () => {
      const { result } = renderHook(() => useSmartSuggestions({ enableTypeSuggestion: true }));
      act(() => {
        result.current.onTitleChange("明天交报告");
      });
      expect(result.current.suggestedDate).toBeTruthy();
      // 固定时间 2025-04-30，明天 = 2025-05-01
      expect(result.current.suggestedDate).toBe("2025-05-01");
    });

    it("输入普通文本时无日期建议", () => {
      const { result } = renderHook(() => useSmartSuggestions({ enableTypeSuggestion: true }));
      act(() => {
        result.current.onTitleChange("买牛奶");
      });
      expect(result.current.suggestedDate).toBeNull();
    });

    it("返回日期提示文本", () => {
      const { result } = renderHook(() => useSmartSuggestions({ enableTypeSuggestion: true }));
      act(() => {
        result.current.onTitleChange("明天交报告");
      });
      expect(result.current.dateHint).toBeTruthy();
      expect(result.current.dateHint).toContain("已自动设为");
    });
  });

  describe("suppress 逻辑", () => {
    it("手动清除日期后不再自动填充", () => {
      const { result } = renderHook(() => useSmartSuggestions({ enableTypeSuggestion: true }));

      // 先触发日期解析
      act(() => {
        result.current.onTitleChange("明天交报告");
      });
      expect(result.current.suggestedDate).toBeTruthy();

      // 手动清除
      act(() => {
        result.current.onDateCleared();
      });
      expect(result.current.suggestedDate).toBeNull();

      // 再次输入含日期关键词的文本
      act(() => {
        result.current.onTitleChange("后天开会");
      });
      // suppress 后不再自动填充
      expect(result.current.suggestedDate).toBeNull();
    });

    it("重置 suppress 后日期可重新自动填充", () => {
      const { result } = renderHook(() => useSmartSuggestions({ enableTypeSuggestion: true }));

      act(() => {
        result.current.onTitleChange("明天交报告");
      });
      expect(result.current.suggestedDate).toBeTruthy();

      act(() => {
        result.current.onDateCleared();
      });

      // 重置
      act(() => {
        result.current.reset();
      });

      // 重置后可以重新填充
      act(() => {
        result.current.onTitleChange("后天开会");
      });
      expect(result.current.suggestedDate).toBeTruthy();
    });
  });

  describe("类型建议（仅 enableTypeSuggestion: true）", () => {
    it("输入含'要不要'时建议创建为 decision", () => {
      const { result } = renderHook(() => useSmartSuggestions({ enableTypeSuggestion: true }));
      act(() => {
        result.current.onTitleChange("要不要学 Rust");
      });
      expect(result.current.typeSuggestion).toEqual({ type: "decision", label: "建议创建为决策" });
    });

    it("输入含'是否'时建议创建为 decision", () => {
      const { result } = renderHook(() => useSmartSuggestions({ enableTypeSuggestion: true }));
      act(() => {
        result.current.onTitleChange("是否需要重构");
      });
      expect(result.current.typeSuggestion).toEqual({ type: "decision", label: "建议创建为决策" });
    });

    it("输入含'该不该'时建议创建为 decision", () => {
      const { result } = renderHook(() => useSmartSuggestions({ enableTypeSuggestion: true }));
      act(() => {
        result.current.onTitleChange("该不该换工作");
      });
      expect(result.current.typeSuggestion).toEqual({ type: "decision", label: "建议创建为决策" });
    });

    it("输入含'完成'时建议创建为 task", () => {
      const { result } = renderHook(() => useSmartSuggestions({ enableTypeSuggestion: true }));
      act(() => {
        result.current.onTitleChange("完成项目文档");
      });
      expect(result.current.typeSuggestion).toEqual({ type: "task", label: "建议创建为任务" });
    });

    it("输入含'做'时建议创建为 task", () => {
      const { result } = renderHook(() => useSmartSuggestions({ enableTypeSuggestion: true }));
      act(() => {
        result.current.onTitleChange("做一个新功能");
      });
      expect(result.current.typeSuggestion).toEqual({ type: "task", label: "建议创建为任务" });
    });

    it("输入含'学'时建议创建为 task", () => {
      const { result } = renderHook(() => useSmartSuggestions({ enableTypeSuggestion: true }));
      act(() => {
        result.current.onTitleChange("学 TypeScript");
      });
      expect(result.current.typeSuggestion).toEqual({ type: "task", label: "建议创建为任务" });
    });

    it("普通文本无类型建议", () => {
      const { result } = renderHook(() => useSmartSuggestions({ enableTypeSuggestion: true }));
      act(() => {
        result.current.onTitleChange("买牛奶");
      });
      expect(result.current.typeSuggestion).toBeNull();
    });

    it("enableTypeSuggestion: false 时不返回类型建议", () => {
      const { result } = renderHook(() => useSmartSuggestions({ enableTypeSuggestion: false }));
      act(() => {
        result.current.onTitleChange("要不要学 Rust");
      });
      expect(result.current.typeSuggestion).toBeNull();
    });
  });

  describe("clearTypeSuggestion", () => {
    it("清除后类型建议为 null", () => {
      const { result } = renderHook(() => useSmartSuggestions({ enableTypeSuggestion: true }));
      act(() => {
        result.current.onTitleChange("要不要学 Rust");
      });
      expect(result.current.typeSuggestion).toBeTruthy();

      act(() => {
        result.current.clearTypeSuggestion();
      });
      expect(result.current.typeSuggestion).toBeNull();
    });
  });

  describe("日期关键词到提示文本的映射", () => {
    it("'今天' 显示 '今天'", () => {
      const { result } = renderHook(() => useSmartSuggestions({ enableTypeSuggestion: true }));
      act(() => {
        result.current.onTitleChange("今天交报告");
      });
      expect(result.current.dateHint).toContain("今天");
    });

    it("'明天' 显示 '明天'", () => {
      const { result } = renderHook(() => useSmartSuggestions({ enableTypeSuggestion: true }));
      act(() => {
        result.current.onTitleChange("明天交报告");
      });
      expect(result.current.dateHint).toContain("明天");
    });

    it("'后天' 显示 '后天'", () => {
      const { result } = renderHook(() => useSmartSuggestions({ enableTypeSuggestion: true }));
      act(() => {
        result.current.onTitleChange("后天开会");
      });
      expect(result.current.dateHint).toContain("后天");
    });

    it("'下周一' 显示 '下周一'", () => {
      const { result } = renderHook(() => useSmartSuggestions({ enableTypeSuggestion: true }));
      act(() => {
        result.current.onTitleChange("下周一开会");
      });
      expect(result.current.dateHint).toContain("下周一");
    });
  });

  describe("onDateManuallyChanged", () => {
    it("手动修改为非建议值时清除日期提示", () => {
      const { result } = renderHook(() => useSmartSuggestions({ enableTypeSuggestion: true }));
      act(() => {
        result.current.onTitleChange("明天交报告");
      });
      expect(result.current.suggestedDate).toBeTruthy();
      expect(result.current.dateHint).toBeTruthy();

      // 手动修改为另一个日期
      act(() => {
        result.current.onDateManuallyChanged("2099-12-31");
      });
      expect(result.current.dateHint).toBeNull();
      expect(result.current.suggestedDate).toBeNull();
    });

    it("手动修改为建议值本身时不清除提示", () => {
      const { result } = renderHook(() => useSmartSuggestions({ enableTypeSuggestion: true }));
      act(() => {
        result.current.onTitleChange("明天交报告");
      });
      const suggested = result.current.suggestedDate;
      expect(suggested).toBeTruthy();

      // 手动修改为相同值（建议值本身）
      act(() => {
        result.current.onDateManuallyChanged(suggested!);
      });
      expect(result.current.dateHint).toBeTruthy();
    });

    it("手动修改为非建议值后 suppress 生效，后续标题编辑不覆盖", () => {
      const { result } = renderHook(() => useSmartSuggestions({ enableTypeSuggestion: true }));
      act(() => {
        result.current.onTitleChange("明天交报告");
      });
      expect(result.current.suggestedDate).toBeTruthy();

      // 手动修改为另一个日期
      act(() => {
        result.current.onDateManuallyChanged("2099-12-31");
      });

      // 再次输入含日期关键词的文本，不应再自动填充
      act(() => {
        result.current.onTitleChange("后天开会");
      });
      expect(result.current.suggestedDate).toBeNull();
    });
  });

  describe("autoFillEvent 事件", () => {
    it("自动填充时触发事件，含日期和关键词名", () => {
      const { result } = renderHook(() => useSmartSuggestions({ enableTypeSuggestion: true }));

      act(() => {
        result.current.onTitleChange("明天交报告");
      });

      expect(result.current.autoFillEvent).toBeTruthy();
      expect(result.current.autoFillEvent!.date).toBeTruthy();
      expect(result.current.autoFillEvent!.keywordName).toBe("明天");
      expect(result.current.autoFillEvent!.seq).toBeGreaterThan(0);
    });

    it("移除日期关键词后触发事件，date 为 null", () => {
      const { result } = renderHook(() => useSmartSuggestions({ enableTypeSuggestion: true }));

      act(() => {
        result.current.onTitleChange("明天交报告");
      });
      const firstSeq = result.current.autoFillEvent!.seq;

      act(() => {
        result.current.onTitleChange("买牛奶");
      });
      // 事件 date 为 null（stale-date 清理）
      expect(result.current.autoFillEvent!.date).toBeNull();
      expect(result.current.autoFillEvent!.keywordName).toBeNull();
      expect(result.current.autoFillEvent!.seq).toBeGreaterThan(firstSeq);
    });

    it("从未有自动填充时修改标题不触发事件", () => {
      const { result } = renderHook(() => useSmartSuggestions({ enableTypeSuggestion: true }));

      act(() => {
        result.current.onTitleChange("买牛奶");
      });
      // 无日期关键词，不触发事件
      expect(result.current.autoFillEvent).toBeNull();

      act(() => {
        result.current.onTitleChange("看书");
      });
      // 仍然无日期关键词，且从未有自动填充，不触发事件
      expect(result.current.autoFillEvent).toBeNull();
    });

    it("onDateCleared 后 autoFillEvent 被清除", () => {
      const { result } = renderHook(() => useSmartSuggestions({ enableTypeSuggestion: true }));

      act(() => {
        result.current.onTitleChange("明天交报告");
      });
      expect(result.current.autoFillEvent).not.toBeNull();

      act(() => {
        result.current.onDateCleared();
      });
      // onDateCleared 应清除 autoFillEvent
      expect(result.current.autoFillEvent).toBeNull();

      act(() => {
        result.current.onTitleChange("买牛奶");
      });
      // suppress 后不会触发新事件（因为 onDateCleared 已清理 hadAutoFill）
      expect(result.current.autoFillEvent).toBeNull();
    });

    it("reset() 清除 autoFillEvent", () => {
      const { result } = renderHook(() => useSmartSuggestions({ enableTypeSuggestion: true }));

      act(() => {
        result.current.onTitleChange("明天交报告");
      });
      expect(result.current.autoFillEvent).not.toBeNull();

      act(() => {
        result.current.reset();
      });
      expect(result.current.autoFillEvent).toBeNull();
    });

    it("切换日期关键词不触发清除事件（先有后变）", () => {
      const { result } = renderHook(() => useSmartSuggestions({ enableTypeSuggestion: true }));

      act(() => {
        result.current.onTitleChange("明天交报告");
      });
      const firstSeq = result.current.autoFillEvent!.seq;

      act(() => {
        result.current.onTitleChange("后天开会");
      });
      // 直接从"明天"切到"后天"，不会触发清除（因为始终有日期关键词）
      expect(result.current.autoFillEvent!.date).toBeTruthy();
      expect(result.current.autoFillEvent!.keywordName).toBe("后天");
      expect(result.current.autoFillEvent!.seq).toBeGreaterThan(firstSeq);
    });
  });

  describe("混合关键词优先级", () => {
    it("含'明天'和'下周一'时，hint 和 date 都基于'明天'（先匹配优先）", () => {
      const { result } = renderHook(() => useSmartSuggestions({ enableTypeSuggestion: true }));
      act(() => {
        result.current.onTitleChange("明天或者下周一");
      });
      expect(result.current.dateHint).toContain("明天");
      // 固定时间 2025-04-30，明天 = 2025-05-01
      expect(result.current.suggestedDate).toBe("2025-05-01");
    });
  });
});
