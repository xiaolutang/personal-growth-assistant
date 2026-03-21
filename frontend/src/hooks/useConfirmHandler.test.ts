/**
 * useConfirmHandler.ts 单元测试
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook } from "@testing-library/react";
import { useConfirmHandler } from "./useConfirmHandler";
import type { ConfirmData } from "./useStreamParse";

describe("useConfirmHandler", () => {
  const mockParse = vi.fn();
  const mockAddMessage = vi.fn();
  const mockCreateSession = vi.fn().mockReturnValue("test-session-id");

  const defaultOptions = {
    currentSessionId: "test-session-id",
    createSession: mockCreateSession,
    addMessage: mockAddMessage,
    parse: mockParse,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("handleConfirm", () => {
    it("没有 confirmData 时应该返回 false", async () => {
      const { result } = renderHook(() =>
        useConfirmHandler(null, defaultOptions)
      );

      const handled = await result.current.handleConfirm("任意输入");
      expect(handled).toBe(false);
    });

    describe("批量操作", () => {
      const confirmData: ConfirmData = {
        action: "delete",
        items: [
          { id: "1", title: "任务1" },
          { id: "2", title: "任务2" },
        ],
      };

      it("应该识别'全部'关键词并执行批量删除", async () => {
        mockParse.mockResolvedValue({});

        const { result } = renderHook(() =>
          useConfirmHandler(confirmData, defaultOptions)
        );

        const handled = await result.current.handleConfirm("全部删除");

        expect(handled).toBe(true);
        expect(mockParse).toHaveBeenCalledTimes(2);
        expect(mockAddMessage).toHaveBeenCalledWith(
          "test-session-id",
          expect.objectContaining({
            role: "assistant",
            content: expect.stringContaining("已删除"),
          })
        );
      });

      it("应该识别'都'关键词并执行批量操作", async () => {
        mockParse.mockResolvedValue({});

        const { result } = renderHook(() =>
          useConfirmHandler(confirmData, defaultOptions)
        );

        const handled = await result.current.handleConfirm("都删除");

        expect(handled).toBe(true);
        expect(mockParse).toHaveBeenCalledTimes(2);
      });

      it("应该识别'所有'关键词", async () => {
        mockParse.mockResolvedValue({});

        const { result } = renderHook(() =>
          useConfirmHandler(confirmData, defaultOptions)
        );

        const handled = await result.current.handleConfirm("所有都删");

        expect(handled).toBe(true);
      });
    });

    describe("数字选择", () => {
      const confirmData: ConfirmData = {
        action: "update",
        items: [
          { id: "1", title: "任务1" },
          { id: "2", title: "任务2" },
          { id: "3", title: "任务3" },
        ],
      };

      it("应该根据数字选择对应项", async () => {
        mockParse.mockResolvedValue({});

        const { result } = renderHook(() =>
          useConfirmHandler(confirmData, defaultOptions)
        );

        const handled = await result.current.handleConfirm("2");

        expect(handled).toBe(true);
        expect(mockParse).toHaveBeenCalledWith(
          expect.stringContaining("任务2"),
          "test-session-id",
          { action: "update", item_id: "2" }
        );
      });

      it("数字超出范围时不应该处理", async () => {
        const { result } = renderHook(() =>
          useConfirmHandler(confirmData, defaultOptions)
        );

        const handled = await result.current.handleConfirm("5");

        expect(handled).toBe(false);
        expect(mockParse).not.toHaveBeenCalled();
      });

      it("数字为 0 时不应该处理", async () => {
        const { result } = renderHook(() =>
          useConfirmHandler(confirmData, defaultOptions)
        );

        const handled = await result.current.handleConfirm("0");

        expect(handled).toBe(false);
      });
    });

    describe("取消操作", () => {
      const confirmData: ConfirmData = {
        action: "delete",
        items: [{ id: "1", title: "任务1" }],
      };

      it("应该识别'取消'并取消操作", async () => {
        const { result } = renderHook(() =>
          useConfirmHandler(confirmData, defaultOptions)
        );

        const handled = await result.current.handleConfirm("取消");

        expect(handled).toBe(true);
        expect(mockAddMessage).toHaveBeenCalledWith(
          "test-session-id",
          expect.objectContaining({
            role: "assistant",
            content: "操作已取消",
          })
        );
        expect(mockParse).not.toHaveBeenCalled();
      });

      it("应该识别'算了'并取消操作", async () => {
        const { result } = renderHook(() =>
          useConfirmHandler(confirmData, defaultOptions)
        );

        const handled = await result.current.handleConfirm("算了");

        expect(handled).toBe(true);
        expect(mockAddMessage).toHaveBeenCalledWith(
          "test-session-id",
          expect.objectContaining({
            content: "操作已取消",
          })
        );
      });

      it("应该识别'不要了'并取消操作", async () => {
        const { result } = renderHook(() =>
          useConfirmHandler(confirmData, defaultOptions)
        );

        const handled = await result.current.handleConfirm("不要了");

        expect(handled).toBe(true);
      });

      it("应该识别'不删'并取消删除", async () => {
        const { result } = renderHook(() =>
          useConfirmHandler(confirmData, defaultOptions)
        );

        const handled = await result.current.handleConfirm("不删了");

        expect(handled).toBe(true);
      });
    });

    describe("无法识别的输入", () => {
      const confirmData: ConfirmData = {
        action: "delete",
        items: [{ id: "1", title: "任务1" }],
      };

      it("应该返回 false 表示未处理", async () => {
        const { result } = renderHook(() =>
          useConfirmHandler(confirmData, defaultOptions)
        );

        const handled = await result.current.handleConfirm("随便说点什么");

        expect(handled).toBe(false);
        expect(mockParse).not.toHaveBeenCalled();
        expect(mockAddMessage).not.toHaveBeenCalled();
      });
    });
  });
});
