/**
 * 评估测试用例定义
 * 用于测试意图检测和多轮对话功能
 */

import type { Intent } from "@/lib/intentDetection";

// 测试用例接口
export interface TestCase {
  id: string;
  category: "intent" | "operation" | "multi_turn" | "edge_case" | "api";
  input: string;
  context?: {
    hasPendingItems?: boolean;
    pendingType?: "delete" | "update";
  };
  expected: {
    intent?: Intent;
    message?: string | RegExp;
    success?: boolean;
    batchCount?: number;
    // API 验证相关
    shouldHaveResults?: boolean;      // 搜索应该有结果
    minResultCount?: number;          // 最少结果数
    resultShouldContain?: string;     // 结果应包含的关键词
  };
}

// 意图检测测试用例
export const intentTestCases: TestCase[] = [
  // === 意图检测测试 ===
  {
    id: "I001",
    category: "intent",
    input: "帮我找 MCP 的笔记",
    expected: { intent: "read" },
  },
  {
    id: "I002",
    category: "intent",
    input: "删除测试任务",
    expected: { intent: "delete" },
  },
  {
    id: "I003",
    category: "intent",
    input: "把任务改为完成",
    expected: { intent: "update" },
  },
  {
    id: "I004",
    category: "intent",
    input: "明天下午3点开会",
    expected: { intent: "create" },
  },
  {
    id: "I005",
    category: "intent",
    input: "今天做了什么",
    expected: { intent: "review" },
  },
  {
    id: "I006",
    category: "intent",
    input: "MCP 的知识图谱",
    expected: { intent: "knowledge" },
  },
  {
    id: "I007",
    category: "intent",
    input: "能做什么",
    expected: { intent: "help" },
  },
  {
    id: "I008",
    category: "intent",
    input: "搜索关于 RAG 的内容",
    expected: { intent: "read" },
  },
  {
    id: "I009",
    category: "intent",
    input: "给学习添加标签 AI",
    expected: { intent: "update" },
  },
  {
    id: "I010",
    category: "intent",
    input: "移除临时记录",
    expected: { intent: "delete" },
  },
  // 负向测试：不应误识别
  {
    id: "I011",
    category: "intent",
    input: "删除键在哪里",
    expected: { intent: "create" }, // 不是删除意图
  },
  {
    id: "I012",
    category: "intent",
    input: "修改一下想法",
    expected: { intent: "create" }, // 不是更新意图
  },
  {
    id: "I013",
    category: "intent",
    input: "查找问题的答案",
    expected: { intent: "read" },
  },
  {
    id: "I014",
    category: "intent",
    input: "本周进度",
    expected: { intent: "review" },
  },
  {
    id: "I015",
    category: "intent",
    input: "查看 MCP 的学习路径",
    expected: { intent: "knowledge" },
  },
];

// 多轮对话测试用例
export const multiTurnTestCases: TestCase[] = [
  {
    id: "M001",
    category: "multi_turn",
    input: "都删除",
    context: { hasPendingItems: true, pendingType: "delete" },
    expected: { message: /已删除 \d+ 个条目/ },
  },
  {
    id: "M002",
    category: "multi_turn",
    input: "全部",
    context: { hasPendingItems: true, pendingType: "update" },
    expected: { message: /已更新 \d+ 个条目/ },
  },
  {
    id: "M003",
    category: "multi_turn",
    input: "1",
    context: { hasPendingItems: true, pendingType: "delete" },
    expected: { message: /已删除「.+」/ },
  },
  {
    id: "M004",
    category: "multi_turn",
    input: "2",
    context: { hasPendingItems: true, pendingType: "update" },
    expected: { message: /已更新「.+」/ },
  },
  {
    id: "M005",
    category: "multi_turn",
    input: "取消",
    context: { hasPendingItems: true },
    expected: { message: "操作已取消" },
  },
  {
    id: "M006",
    category: "multi_turn",
    input: "算了",
    context: { hasPendingItems: true },
    expected: { message: "操作已取消" },
  },
];

// 边界情况测试用例
export const edgeCaseTestCases: TestCase[] = [
  {
    id: "E001",
    category: "edge_case",
    input: "",
    expected: { success: false },
  },
  {
    id: "E002",
    category: "edge_case",
    input: "   ",
    expected: { success: false },
  },
  {
    id: "E003",
    category: "edge_case",
    input: "都删除",
    context: { hasPendingItems: false },
    expected: { intent: "create" }, // 无 pending 时应该是 create
  },
  {
    id: "E004",
    category: "edge_case",
    input: "删除",
    expected: { intent: "delete" },
  },
  {
    id: "E005",
    category: "edge_case",
    input: "把",
    expected: { intent: "create" }, // 不完整的 update 指令
  },
];

// 操作流程测试用例（完整 CRUD 流程）
export const operationTestCases: TestCase[] = [
  {
    id: "O001",
    category: "operation",
    input: "新建任务 完成评估测试",
    expected: { intent: "create" },
  },
  {
    id: "O002",
    category: "operation",
    input: "帮我找 评估测试",
    expected: { intent: "read" },
  },
  {
    id: "O003",
    category: "operation",
    input: "把评估测试改为完成",
    expected: { intent: "update" },
  },
  {
    id: "O004",
    category: "operation",
    input: "删除评估测试",
    expected: { intent: "delete" },
  },
];

// 所有测试用例
export const allTestCases: TestCase[] = [
  ...intentTestCases,
  ...multiTurnTestCases,
  ...edgeCaseTestCases,
  ...operationTestCases,
];

// API 验证测试用例（需要真实后端）
export const apiTestCases: TestCase[] = [
  {
    id: "API001",
    category: "api",
    input: "帮我找 MCP 的笔记",
    expected: {
      intent: "read",
      shouldHaveResults: true,
      resultShouldContain: "MCP",
    },
  },
  {
    id: "API002",
    category: "api",
    input: "搜索 RAG 相关内容",
    expected: {
      intent: "read",
      shouldHaveResults: true,
      resultShouldContain: "RAG",
    },
  },
  {
    id: "API003",
    category: "api",
    input: "查找 Agent 相关笔记",
    expected: {
      intent: "read",
      shouldHaveResults: true,
      resultShouldContain: "Agent",
    },
  },
  {
    id: "API004",
    category: "api",
    input: "搜索 Claude",
    expected: {
      intent: "read",
      shouldHaveResults: true,
      resultShouldContain: "Claude",
    },
  },
];

export default allTestCases;
