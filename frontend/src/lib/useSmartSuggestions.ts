/**
 * useSmartSuggestions - 输入智能提示 Hook
 * 提供日期解析和类型建议功能
 *
 * - 日期解析：从输入文本中提取中文日期关键词并解析
 * - 类型建议：从输入文本中匹配关键词，建议创建类型（仅 CreateDialog）
 * - suppress：手动清除日期后，当前实例内不再自动填充
 * - stale-date 清理：标题移除日期关键词后，自动清除之前填充的日期
 */

import { useState, useCallback, useRef } from "react";
import { parseDateKeyword } from "./dateParser";
import type { ParseResult } from "./dateParser";

/** 创建日期变更处理器，统一处理清除和手动修改逻辑 */
export function createDateChangeHandler(
  currentValue: string,
  onCleared: () => void,
  onManuallyChanged: (value: string) => void
): (newValue: string) => void {
  return (newValue: string) => {
    if (newValue === "") {
      onCleared();
    } else if (newValue !== currentValue) {
      onManuallyChanged(newValue);
    }
  };
}

/** 类型建议结果 */
export interface TypeSuggestion {
  type: string;
  label: string;
}

/** Hook 配置 */
export interface UseSmartSuggestionsOptions {
  /** 是否启用类型建议（CreateDialog=true, QuickCaptureBar=false） */
  enableTypeSuggestion: boolean;
}

/** 决策类型关键词 */
const DECISION_KEYWORDS = ["要不要", "是否", "该不该"];

/** 任务类型关键词 */
const TASK_KEYWORDS = ["完成", "做", "学"];

/** 匹配类型建议 */
function matchTypeSuggestion(text: string): TypeSuggestion | null {
  if (DECISION_KEYWORDS.some((kw) => text.includes(kw))) {
    return { type: "decision", label: "建议创建为决策" };
  }
  if (TASK_KEYWORDS.some((kw) => text.includes(kw))) {
    return { type: "task", label: "建议创建为任务" };
  }
  return null;
}

/**
 * 日期自动填充事件，供消费者在 effect 中响应
 */
export interface DateAutoFillEvent {
  /** 自动填充的日期值，null 表示应清除之前自动填充的日期 */
  date: string | null;
  /** 关键词友好名称（如"明天"、"下周一"） */
  keywordName: string | null;
  /** 事件序号，用于区分不同事件 */
  seq: number;
}

export function useSmartSuggestions(options: UseSmartSuggestionsOptions) {
  const { enableTypeSuggestion } = options;

  const [suggestedDate, setSuggestedDate] = useState<string | null>(null);
  const [dateHint, setDateHint] = useState<string | null>(null);
  const [typeSuggestion, setTypeSuggestion] = useState<TypeSuggestion | null>(null);
  const [dateSuppress, setDateSuppress] = useState(false);

  // 自动填充事件 state（消费者通过 effect 监听）
  const [autoFillEvent, setAutoFillEvent] = useState<DateAutoFillEvent | null>(null);

  // 事件序号计数器，确保相同内容的事件也能触发 effect
  const seqRef = useRef(0);

  // 用 ref 记住当前的建议日期值，用于判断用户手动修改后是否仍是建议值
  const suggestedDateRef = useRef<string | null>(null);

  // 追踪是否曾经自动填充过（用于 stale-date 清理）
  const hadAutoFillRef = useRef(false);

  /** 标题变化时触发解析 */
  const onTitleChange = useCallback(
    (text: string) => {
      // 日期解析
      if (dateSuppress) {
        // suppress 状态下不自动填充日期
        setSuggestedDate(null);
        setDateHint(null);
        suggestedDateRef.current = null;
      } else {
        const parseResult: ParseResult | null = parseDateKeyword(text);
        if (parseResult) {
          setSuggestedDate(parseResult.date);
          suggestedDateRef.current = parseResult.date;
          hadAutoFillRef.current = true;
          const keywordName = parseResult.keyword;
          setDateHint(keywordName ? `已自动设为${keywordName}` : "已自动设为日期");
          // 触发自动填充事件
          seqRef.current += 1;
          setAutoFillEvent({ date: parseResult.date, keywordName, seq: seqRef.current });
        } else {
          setSuggestedDate(null);
          suggestedDateRef.current = null;
          setDateHint(null);
          // 之前有自动填充，现在关键词消失了 → 触发清除事件
          if (hadAutoFillRef.current) {
            hadAutoFillRef.current = false;
            seqRef.current += 1;
            setAutoFillEvent({ date: null, keywordName: null, seq: seqRef.current });
          }
        }
      }

      // 类型建议
      if (enableTypeSuggestion) {
        const suggestion = matchTypeSuggestion(text);
        setTypeSuggestion(suggestion);
      }
    },
    [dateSuppress, enableTypeSuggestion],
  );

  /** 用户手动清除了日期字段 */
  const onDateCleared = useCallback(() => {
    setSuggestedDate(null);
    setDateHint(null);
    suggestedDateRef.current = null;
    hadAutoFillRef.current = false;
    setDateSuppress(true);
    // 清除自动填充事件，防止消费者在状态切换时重放旧事件
    setAutoFillEvent(null);
  }, []);

  /** 用户手动修改了日期字段（非清除） */
  const onDateManuallyChanged = useCallback((newValue: string) => {
    // 如果用户改成了非建议值，清除提示并触发 suppress（后续标题编辑不再覆盖）
    if (newValue && newValue !== suggestedDateRef.current) {
      setDateHint(null);
      setSuggestedDate(null);
      suggestedDateRef.current = null;
      hadAutoFillRef.current = false;
      setDateSuppress(true);
      // 清除自动填充事件，防止消费者在状态切换时重放旧事件
      setAutoFillEvent(null);
    }
  }, []);

  /** 清除类型建议（用户点击了建议后调用） */
  const clearTypeSuggestion = useCallback(() => {
    setTypeSuggestion(null);
  }, []);

  /** 重置所有状态（关闭/重新打开时调用） */
  const reset = useCallback(() => {
    setSuggestedDate(null);
    setDateHint(null);
    setTypeSuggestion(null);
    setDateSuppress(false);
    suggestedDateRef.current = null;
    hadAutoFillRef.current = false;
    setAutoFillEvent(null);
  }, []);

  return {
    suggestedDate,
    dateHint,
    typeSuggestion,
    /** 日期自动填充/清除事件，消费者在 useEffect 中监听 */
    autoFillEvent,
    onTitleChange,
    onDateCleared,
    onDateManuallyChanged,
    clearTypeSuggestion,
    reset,
  };
}
