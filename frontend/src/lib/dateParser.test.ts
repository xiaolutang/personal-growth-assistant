/**
 * dateParser.ts 单元测试
 * 覆盖 parseDateKeyword 所有日期关键词解析规则
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { parseDateKeyword } from "./dateParser";
import { toLocalDateString } from "./utils";

describe("parseDateKeyword", () => {
  it("输入不含日期关键词时返回 null", () => {
    expect(parseDateKeyword("买牛奶")).toBeNull();
    expect(parseDateKeyword("完成项目文档")).toBeNull();
    expect(parseDateKeyword("")).toBeNull();
  });

  describe("基本日期关键词", () => {
    it("今天 → 当天日期", () => {
      const result = parseDateKeyword("今天交报告");
      expect(result).not.toBeNull();
      expect(result!.date).toBe(toLocalDateString(new Date()));
      expect(result!.keyword).toBe("今天");
    });

    it("明天 → +1天", () => {
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      const result = parseDateKeyword("明天交报告");
      expect(result!.date).toBe(toLocalDateString(tomorrow));
      expect(result!.keyword).toBe("明天");
    });

    it("后天 → +2天", () => {
      const dayAfter = new Date();
      dayAfter.setDate(dayAfter.getDate() + 2);
      const result = parseDateKeyword("后天开会");
      expect(result!.date).toBe(toLocalDateString(dayAfter));
      expect(result!.keyword).toBe("后天");
    });

    it("大后天 → +3天", () => {
      const day3 = new Date();
      day3.setDate(day3.getDate() + 3);
      const result = parseDateKeyword("大后天去旅游");
      expect(result!.date).toBe(toLocalDateString(day3));
      expect(result!.keyword).toBe("大后天");
    });
  });

  describe("本周X 规则", () => {
    // 使用固定日期 mock 来保证确定性
    // 2025-01-15 是周三
    const fixedDate = new Date(2025, 0, 15); // 2025-01-15 周三

    beforeEach(() => {
      vi.useFakeTimers();
      vi.setSystemTime(fixedDate);
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it("本周三（当天）→ 本周三", () => {
      const result = parseDateKeyword("本周三开会");
      expect(result!.date).toBe("2025-01-15");
      expect(result!.keyword).toBe("本周三");
    });

    it("本周四（未过）→ 本周四", () => {
      const result = parseDateKeyword("本周四交报告");
      expect(result!.date).toBe("2025-01-16");
      expect(result!.keyword).toBe("本周四");
    });

    it("本周五（未过）→ 本周五", () => {
      const result = parseDateKeyword("本周五聚餐");
      expect(result!.date).toBe("2025-01-17");
      expect(result!.keyword).toBe("本周五");
    });

    it("本周六（未过）→ 本周六", () => {
      const result = parseDateKeyword("本周六休息");
      expect(result!.date).toBe("2025-01-18");
      expect(result!.keyword).toBe("本周六");
    });

    it("本周日（未过）→ 本周日", () => {
      const result = parseDateKeyword("本周日放松");
      expect(result!.date).toBe("2025-01-19");
      expect(result!.keyword).toBe("本周日");
    });

    it("本周一（已过）→ 下周一", () => {
      const result = parseDateKeyword("本周一开会");
      // 2025-01-13 是本周一，已过，所以是下周一 = 2025-01-20
      expect(result!.date).toBe("2025-01-20");
      expect(result!.keyword).toBe("本周一");
    });

    it("本周二（已过）→ 下周二", () => {
      const result = parseDateKeyword("本周二学习");
      // 2025-01-14 是本周二，已过，所以是下周二 = 2025-01-21
      expect(result!.date).toBe("2025-01-21");
      expect(result!.keyword).toBe("本周二");
    });
  });

  describe("下周X 规则", () => {
    const fixedDate = new Date(2025, 0, 15); // 2025-01-15 周三

    beforeEach(() => {
      vi.useFakeTimers();
      vi.setSystemTime(fixedDate);
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it("下周一 → 下周一", () => {
      const result = parseDateKeyword("下周一开会");
      expect(result!.date).toBe("2025-01-20");
      expect(result!.keyword).toBe("下周一");
    });

    it("下周二 → 下周二", () => {
      const result = parseDateKeyword("下周二学习");
      expect(result!.date).toBe("2025-01-21");
      expect(result!.keyword).toBe("下周二");
    });

    it("下周三 → 下周三", () => {
      const result = parseDateKeyword("下周三汇报");
      expect(result!.date).toBe("2025-01-22");
      expect(result!.keyword).toBe("下周三");
    });

    it("下周日 → 下周日", () => {
      const result = parseDateKeyword("下周日休息");
      expect(result!.date).toBe("2025-01-26");
      expect(result!.keyword).toBe("下周日");
    });
  });

  describe("下个月 规则", () => {
    it("下个月 → 下月同日", () => {
      vi.useFakeTimers();
      vi.setSystemTime(new Date(2025, 2, 15)); // 2025-03-15
      const result = parseDateKeyword("下个月出差");
      expect(result!.date).toBe("2025-04-15");
      expect(result!.keyword).toBe("下个月");
      vi.useRealTimers();
    });

    it("月末边界：1月31日输入'下个月' → 2月28日", () => {
      vi.useFakeTimers();
      vi.setSystemTime(new Date(2025, 0, 31)); // 2025-01-31
      const result = parseDateKeyword("下个月出差");
      // 2月没有31日，取最后一天 = 2025-02-28
      expect(result!.date).toBe("2025-02-28");
      expect(result!.keyword).toBe("下个月");
      vi.useRealTimers();
    });

    it("闰年2月29日输入'下个月' → 3月29日", () => {
      vi.useFakeTimers();
      vi.setSystemTime(new Date(2024, 1, 29)); // 2024-02-29（闰年）
      const result = parseDateKeyword("下个月出差");
      expect(result!.date).toBe("2024-03-29");
      vi.useRealTimers();
    });

    it("非闰年2月28日输入'下个月' → 3月28日", () => {
      vi.useFakeTimers();
      vi.setSystemTime(new Date(2025, 1, 28)); // 2025-02-28
      const result = parseDateKeyword("下个月出差");
      expect(result!.date).toBe("2025-03-28");
      vi.useRealTimers();
    });

    it("12月输入'下个月' → 次年1月同日", () => {
      vi.useFakeTimers();
      vi.setSystemTime(new Date(2025, 11, 15)); // 2025-12-15
      const result = parseDateKeyword("下个月出差");
      expect(result!.date).toBe("2026-01-15");
      vi.useRealTimers();
    });
  });

  describe("月末边界（自然日期）", () => {
    it("4月30日输入'明天' → 5月1日", () => {
      vi.useFakeTimers();
      vi.setSystemTime(new Date(2025, 3, 30)); // 2025-04-30
      const result = parseDateKeyword("明天交报告");
      expect(result!.date).toBe("2025-05-01");
      vi.useRealTimers();
    });

    it("12月31日输入'明天' → 次年1月1日", () => {
      vi.useFakeTimers();
      vi.setSystemTime(new Date(2025, 11, 31)); // 2025-12-31
      const result = parseDateKeyword("明天交报告");
      expect(result!.date).toBe("2026-01-01");
      vi.useRealTimers();
    });
  });

  describe("关键词在句子中的位置", () => {
    it("关键词在句首", () => {
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      expect(parseDateKeyword("明天交报告")!.date).toBe(toLocalDateString(tomorrow));
    });

    it("关键词在句中", () => {
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      expect(parseDateKeyword("请在明天之前完成")!.date).toBe(toLocalDateString(tomorrow));
    });

    it("关键词在句尾", () => {
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      expect(parseDateKeyword("截止日期是明天")!.date).toBe(toLocalDateString(tomorrow));
    });
  });

  describe("返回值格式", () => {
    it("返回 ParseResult 对象，含 date 和 keyword", () => {
      const result = parseDateKeyword("今天");
      expect(result).not.toBeNull();
      expect(result!.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      expect(result!.keyword).toBe("今天");
    });
  });
});
