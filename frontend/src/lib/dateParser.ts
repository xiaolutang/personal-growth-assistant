/**
 * 日期关键词解析工具
 * 从文本中提取中文日期关键词并解析为 YYYY-MM-DD 格式
 */

import { toLocalDateString } from "./utils";

/** 中文星期数字映射 */
const WEEKDAY_MAP: Record<string, number> = {
  一: 1,
  二: 2,
  三: 3,
  四: 4,
  五: 5,
  六: 6,
  日: 0,
  天: 0,
};

/**
 * 获取指定周的某一天的日期
 * @param baseDate 基准日期（用于确定"当前周"）
 * @param dayOfWeek 目标星期几（0=周日, 1=周一, ..., 6=周六）
 * @param weekOffset 周偏移（0=本周, 1=下周）
 */
function getDateOfWeek(baseDate: Date, dayOfWeek: number, weekOffset: number): Date {
  const result = new Date(baseDate);
  // JS getDay: 0=周日, 1=周一, ..., 6=周六
  // 我们需要"本周的周X"。中国习惯周一是第一天，周日是最后一天。
  // 将 dayOfWeek(0=周日) 转换为 "周一偏移"：周一=0, 周二=1, ..., 周六=5, 周日=6
  const adjustedDay = dayOfWeek === 0 ? 6 : dayOfWeek - 1;
  // 获取本周一的日期
  const currentDay = result.getDay();
  const mondayOffset = currentDay === 0 ? -6 : 1 - currentDay;
  result.setDate(result.getDate() + mondayOffset + weekOffset * 7 + adjustedDay);
  return result;
}

/**
 * 获取下个月同一天（处理月末溢出）
 * 例如：1月31日 → 2月28日（非闰年）
 */
function getNextMonthSameDay(baseDate: Date): Date {
  const result = new Date(baseDate);
  const targetMonth = result.getMonth() + 1;
  const targetYear = result.getFullYear() + (targetMonth > 11 ? 1 : 0);
  const adjustedMonth = targetMonth > 11 ? targetMonth - 12 : targetMonth;
  const day = result.getDate();

  // 获取目标月份的最大天数
  const maxDay = new Date(targetYear, adjustedMonth + 1, 0).getDate();
  result.setFullYear(targetYear, adjustedMonth, Math.min(day, maxDay));
  return result;
}

export interface ParseResult {
  /** 解析出的日期字符串 YYYY-MM-DD */
  date: string;
  /** 匹配到的关键词原文 */
  keyword: string;
}

/**
 * 从文本中解析中文日期关键词
 *
 * 支持的关键词：
 * - 今天 → 当天
 * - 明天 → +1天
 * - 后天 → +2天
 * - 大后天 → +3天
 * - 本周一~本周日 → 如果该日期已过则解析为下周同日
 * - 下周一~下周日 → 下周对应日
 * - 下个月 → 下月同日（处理月末溢出）
 *
 * @param text 输入文本
 * @returns 匹配到的解析结果（含日期和关键词），未匹配返回 null
 */
export function parseDateKeyword(text: string): ParseResult | null {
  if (!text) return null;

  const now = new Date();

  // 大后天（必须在"后天"之前匹配）
  if (text.includes("大后天")) {
    const d = new Date(now);
    d.setDate(d.getDate() + 3);
    return { date: toLocalDateString(d), keyword: "大后天" };
  }

  // 后天
  if (text.includes("后天")) {
    const d = new Date(now);
    d.setDate(d.getDate() + 2);
    return { date: toLocalDateString(d), keyword: "后天" };
  }

  // 明天
  if (text.includes("明天")) {
    const d = new Date(now);
    d.setDate(d.getDate() + 1);
    return { date: toLocalDateString(d), keyword: "明天" };
  }

  // 今天
  if (text.includes("今天")) {
    return { date: toLocalDateString(now), keyword: "今天" };
  }

  // 下周X
  const nextWeekMatch = text.match(/下周([一二三四五六日天])/);
  if (nextWeekMatch) {
    const dayOfWeek = WEEKDAY_MAP[nextWeekMatch[1]];
    if (dayOfWeek !== undefined) {
      const keyword = `下周${nextWeekMatch[1]}`;
      return { date: toLocalDateString(getDateOfWeek(now, dayOfWeek, 1)), keyword };
    }
  }

  // 本周X
  const thisWeekMatch = text.match(/本周([一二三四五六日天])/);
  if (thisWeekMatch) {
    const dayOfWeek = WEEKDAY_MAP[thisWeekMatch[1]];
    if (dayOfWeek !== undefined) {
      const keyword = `本周${thisWeekMatch[1]}`;
      const targetDate = getDateOfWeek(now, dayOfWeek, 0);
      const targetDateStr = toLocalDateString(targetDate);
      const todayStr = toLocalDateString(now);
      // 如果该日期已过（< 今天），解析为下周同日
      if (targetDateStr < todayStr) {
        return { date: toLocalDateString(getDateOfWeek(now, dayOfWeek, 1)), keyword };
      }
      return { date: targetDateStr, keyword };
    }
  }

  // 下个月
  if (text.includes("下个月")) {
    return { date: toLocalDateString(getNextMonthSameDay(now)), keyword: "下个月" };
  }

  return null;
}
