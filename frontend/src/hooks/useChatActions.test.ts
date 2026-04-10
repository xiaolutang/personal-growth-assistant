/**
 * useChatActions.ts 单元测试
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useChatActions } from "./useChatActions";
import type { IntentResult, ConfirmData } from "./useStreamParse";

describe("useChatActions", () => {
  const mockFetchEntries = vi.fn();
  const mockSetSearchResults = vi.fn();
  const mockClearSearchResults = vi.fn();
  const mockSetCurrentAction = vi.fn();
  const mockSetLastOperation = vi.fn();
  const mockSetConfirmData = vi.fn();
  const mockSetCurrentIntent = vi.fn();
  const mockAddMessage = vi.fn();
  const mockUpdateSessionTitle = vi.fn();

  const defaultOptions = {
    currentSessionId: "test-session-id",
    currentSession: { title: "新对话" },
    addMessage: mockAddMessage,
    updateSessionTitle: mockUpdateSessionTitle,
    fetchEntries: mockFetchEntries,
    setSearchResults: mockSetSearchResults,
    clearSearchResults: mockClearSearchResults,
    setCurrentAction: mockSetCurrentAction,
    setLastOperation: mockSetLastOperation,
    setConfirmData: mockSetConfirmData,
    setCurrentIntent: mockSetCurrentIntent,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("onCreated", () => {
    it("应该调用 fetchEntries 刷新数据", () => {
      const { result } = renderHook(() => useChatActions(defaultOptions));

      act(() => {
        result.current.onCreated(["id1", "id2"], 2);
      });

      expect(mockFetchEntries).toHaveBeenCalledTimes(1);
    });

    it("当标题为默认值时应该更新会话标题", () => {
      const { result } = renderHook(() => useChatActions(defaultOptions));

      act(() => {
        result.current.onCreated(["id1"], 1);
      });

      expect(mockUpdateSessionTitle).toHaveBeenCalledWith(
        "test-session-id",
        "创建 1 个条目"
      );
    });

    it("当标题不是默认值时不应该更新会话标题", () => {
      const options = {
        ...defaultOptions,
        currentSession: { title: "已有标题" },
      };
      const { result } = renderHook(() => useChatActions(options));

      act(() => {
        result.current.onCreated(["id1"], 1);
      });

      expect(mockUpdateSessionTitle).not.toHaveBeenCalled();
    });

    it("应该设置 currentAction 状态为 success", () => {
      const { result } = renderHook(() => useChatActions(defaultOptions));

      act(() => {
        result.current.onCreated(["id1"], 1);
      });

      expect(mockSetCurrentAction).toHaveBeenCalledWith(expect.any(Function));
      // 验证函数式更新的行为
      const updater = mockSetCurrentAction.mock.calls[0][0];
      expect(updater({ type: "create", status: "running" })).toEqual({
        type: "create",
        status: "success",
      });
    });

    it("应该设置 lastOperation 记录", () => {
      const { result } = renderHook(() => useChatActions(defaultOptions));

      act(() => {
        result.current.onCreated(["id1", "id2"], 2);
      });

      expect(mockSetLastOperation).toHaveBeenCalledWith({
        type: "create",
        status: "success",
        message: "已创建 2 个条目",
        timestamp: expect.any(Number),
      });
    });
  });

  describe("onUpdated", () => {
    it("应该调用 fetchEntries 刷新数据", () => {
      const { result } = renderHook(() => useChatActions(defaultOptions));

      act(() => {
        result.current.onUpdated();
      });

      expect(mockFetchEntries).toHaveBeenCalledTimes(1);
    });

    it("应该设置 currentAction 状态为 success", () => {
      const { result } = renderHook(() => useChatActions(defaultOptions));

      act(() => {
        result.current.onUpdated();
      });

      expect(mockSetCurrentAction).toHaveBeenCalledWith(expect.any(Function));
      const updater = mockSetCurrentAction.mock.calls[0][0];
      expect(updater({ type: "update", status: "running" })).toEqual({
        type: "update",
        status: "success",
      });
    });

    it("当 prev 为 null 时 updater 应返回 null", () => {
      const { result } = renderHook(() => useChatActions(defaultOptions));

      act(() => {
        result.current.onUpdated();
      });

      const updater = mockSetCurrentAction.mock.calls[0][0];
      expect(updater(null)).toBeNull();
    });
  });

  describe("onDeleted", () => {
    it("应该调用 fetchEntries 刷新数据", () => {
      const { result } = renderHook(() => useChatActions(defaultOptions));

      act(() => {
        result.current.onDeleted();
      });

      expect(mockFetchEntries).toHaveBeenCalledTimes(1);
    });

    it("应该设置 currentAction 状态为 success", () => {
      const { result } = renderHook(() => useChatActions(defaultOptions));

      act(() => {
        result.current.onDeleted();
      });

      expect(mockSetCurrentAction).toHaveBeenCalledWith(expect.any(Function));
      const updater = mockSetCurrentAction.mock.calls[0][0];
      expect(updater({ type: "delete", status: "running" })).toEqual({
        type: "delete",
        status: "success",
      });
    });
  });

  describe("onIntentDetected", () => {
    it("应该设置 currentAction 为 running 状态", () => {
      const { result } = renderHook(() => useChatActions(defaultOptions));

      const intentResult: IntentResult = {
        intent: "create",
        confidence: 0.95,
        query: "创建任务",
        entities: {},
      };

      act(() => {
        result.current.onIntentDetected(intentResult);
      });

      expect(mockSetCurrentAction).toHaveBeenCalledWith({
        type: "create",
        name: "create",
        status: "running",
      });
    });

    it("应该正确传递不同意图类型", () => {
      const { result } = renderHook(() => useChatActions(defaultOptions));

      const intentResult: IntentResult = {
        intent: "delete",
        confidence: 0.9,
        query: "删除任务",
        entities: {},
      };

      act(() => {
        result.current.onIntentDetected(intentResult);
      });

      expect(mockSetCurrentAction).toHaveBeenCalledWith({
        type: "delete",
        name: "delete",
        status: "running",
      });
    });
  });

  describe("onConfirm", () => {
    const confirmData: ConfirmData = {
      action: "delete",
      items: [
        { id: "1", title: "任务A" },
        { id: "2", title: "任务B" },
      ],
    };

    it("应该设置 confirmData", () => {
      const { result } = renderHook(() => useChatActions(defaultOptions));

      act(() => {
        result.current.onConfirm(confirmData);
      });

      expect(mockSetConfirmData).toHaveBeenCalledWith(confirmData);
    });

    it("应该添加包含条目列表的助手消息", () => {
      const { result } = renderHook(() => useChatActions(defaultOptions));

      act(() => {
        result.current.onConfirm(confirmData);
      });

      expect(mockAddMessage).toHaveBeenCalledWith(
        "test-session-id",
        expect.objectContaining({
          role: "assistant",
          content: expect.stringContaining("2 个匹配项"),
        })
      );
      expect(mockAddMessage).toHaveBeenCalledWith(
        "test-session-id",
        expect.objectContaining({
          content: expect.stringContaining("任务A"),
        })
      );
    });

    it("delete 操作消息应包含'全部删除'", () => {
      const { result } = renderHook(() => useChatActions(defaultOptions));

      act(() => {
        result.current.onConfirm(confirmData);
      });

      expect(mockAddMessage).toHaveBeenCalledWith(
        "test-session-id",
        expect.objectContaining({
          content: expect.stringContaining("全部删除"),
        })
      );
    });

    it("update 操作消息应包含'全部更新'", () => {
      const updateConfirm: ConfirmData = {
        action: "update",
        items: [{ id: "1", title: "任务A" }],
      };

      const { result } = renderHook(() => useChatActions(defaultOptions));

      act(() => {
        result.current.onConfirm(updateConfirm);
      });

      expect(mockAddMessage).toHaveBeenCalledWith(
        "test-session-id",
        expect.objectContaining({
          content: expect.stringContaining("全部更新"),
        })
      );
    });

    it("没有 sessionId 时不应该添加消息", () => {
      const options = {
        ...defaultOptions,
        currentSessionId: null,
      };
      const { result } = renderHook(() => useChatActions(options));

      act(() => {
        result.current.onConfirm(confirmData);
      });

      expect(mockAddMessage).not.toHaveBeenCalled();
      expect(mockSetConfirmData).toHaveBeenCalledWith(confirmData);
    });

    it("应该重置 currentAction 为 null", () => {
      const { result } = renderHook(() => useChatActions(defaultOptions));

      act(() => {
        result.current.onConfirm(confirmData);
      });

      expect(mockSetCurrentAction).toHaveBeenCalledWith(null);
    });
  });

  describe("onResults", () => {
    it("应该清除旧搜索结果并设置新结果", () => {
      const { result } = renderHook(() => useChatActions(defaultOptions));

      const items = [
        { id: "1", title: "结果1" },
        { id: "2", title: "结果2" },
      ];

      act(() => {
        result.current.onResults(items);
      });

      expect(mockClearSearchResults).toHaveBeenCalledTimes(1);
      expect(mockSetSearchResults).toHaveBeenCalledWith(items);
    });

    it("应该设置 currentIntent 为 read", () => {
      const { result } = renderHook(() => useChatActions(defaultOptions));

      act(() => {
        result.current.onResults([]);
      });

      expect(mockSetCurrentIntent).toHaveBeenCalledWith("read");
    });

    it("应该设置 currentAction 状态为 success", () => {
      const { result } = renderHook(() => useChatActions(defaultOptions));

      act(() => {
        result.current.onResults([]);
      });

      expect(mockSetCurrentAction).toHaveBeenCalledWith(expect.any(Function));
    });
  });

  describe("updateTitleIfNeeded", () => {
    it("当标题为默认值且有 sessionId 时应更新标题", () => {
      const { result } = renderHook(() => useChatActions(defaultOptions));

      act(() => {
        result.current.updateTitleIfNeeded("新标题");
      });

      expect(mockUpdateSessionTitle).toHaveBeenCalledWith(
        "test-session-id",
        "新标题"
      );
    });

    it("当标题不是默认值时不应更新", () => {
      const options = {
        ...defaultOptions,
        currentSession: { title: "已有标题" },
      };
      const { result } = renderHook(() => useChatActions(options));

      act(() => {
        result.current.updateTitleIfNeeded("新标题");
      });

      expect(mockUpdateSessionTitle).not.toHaveBeenCalled();
    });

    it("当没有 sessionId 时不应更新", () => {
      const options = {
        ...defaultOptions,
        currentSessionId: null,
      };
      const { result } = renderHook(() => useChatActions(options));

      act(() => {
        result.current.updateTitleIfNeeded("新标题");
      });

      expect(mockUpdateSessionTitle).not.toHaveBeenCalled();
    });

    it("标题应截断到最大长度", () => {
      const { result } = renderHook(() => useChatActions(defaultOptions));

      const longTitle = "这是一个非常非常非常非常长的标题内容";
      act(() => {
        result.current.updateTitleIfNeeded(longTitle);
      });

      expect(mockUpdateSessionTitle).toHaveBeenCalledWith(
        "test-session-id",
        longTitle.slice(0, 20)
      );
    });
  });
});
