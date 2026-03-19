/**
 * 评估执行器
 * 用于运行测试用例并收集结果
 */

import { detectIntent, type Intent } from "@/lib/intentDetection";
import { allTestCases, type TestCase } from "./testCases";
import { gradeTestCase } from "./graders";
import type { EvaluationReport, TestResult, CategoryStats } from "./report";

// 模拟的多轮对话上下文
interface MockContext {
  hasPendingItems: boolean;
  pendingType?: "delete" | "update";
}

// 执行单个测试用例
export async function executeTestCase(
  testCase: TestCase,
  mockContext?: MockContext
): Promise<{
  intent?: Intent;
  message?: string;
  success: boolean;
}> {
  const { input, context } = testCase;

  // 检查是否有 pending 状态
  const hasPending = context?.hasPendingItems || mockContext?.hasPendingItems;

  // 如果有待处理项，先检查是否是批量操作
  if (hasPending && input) {
    const batchKeywords = ["都", "全部", "所有", "两个", "三个", "这几个", "以上"];
    const isBatchAction = batchKeywords.some(k => input.includes(k));

    if (isBatchAction) {
      // 模拟批量操作成功
      return {
        message: `已${mockContext?.pendingType === "delete" ? "删除" : "更新"} 2 个条目`,
        success: true,
      };
    }

    // 检查数字选择
    const num = parseInt(input);
    if (!isNaN(num) && num >= 1) {
      return {
        message: `已${mockContext?.pendingType === "delete" ? "删除" : "更新"}「测试条目」`,
        success: true,
      };
    }

    // 检查取消操作
    if (/取消|算了|不要了|不删|不更/.test(input)) {
      return {
        message: "操作已取消",
        success: true,
      };
    }
  }

  // 空输入检查
  if (!input.trim()) {
    return { success: false };
  }

  // 执行意图检测
  const intent = detectIntent(input);

  // 根据意图生成模拟响应
  let message = "";
  switch (intent) {
    case "read":
      message = "找到 2 个相关结果";
      break;
    case "update":
      message = "已更新「测试条目」";
      break;
    case "delete":
      message = "已删除「测试条目」";
      break;
    case "review":
      message = "## 今日回顾\n\n**任务完成情况**\n- 总任务: 5\n- 已完成: 3";
      break;
    case "knowledge":
      message = "已加载 \"MCP\" 的知识图谱";
      break;
    case "help":
      message = "## 🎯 我能帮你做什么？";
      break;
    default:
      message = "已识别 1 个任务";
  }

  return { intent, message, success: true };
}

// 运行所有测试用例
export async function runEvaluation(
  testCases: TestCase[] = allTestCases
): Promise<EvaluationReport> {
  const results: TestResult[] = [];
  const startTime = Date.now();

  for (const testCase of testCases) {
    const testStartTime = Date.now();

    try {
      const actualResult = await executeTestCase(testCase);
      const gradeResult = gradeTestCase(testCase, actualResult);

      results.push({
        id: testCase.id,
        category: testCase.category,
        input: testCase.input,
        passed: gradeResult.passed,
        score: gradeResult.score,
        reason: gradeResult.reason,
        duration: Date.now() - testStartTime,
      });
    } catch (error) {
      results.push({
        id: testCase.id,
        category: testCase.category,
        input: testCase.input,
        passed: false,
        score: 0,
        reason: error instanceof Error ? error.message : "未知错误",
        duration: Date.now() - testStartTime,
      });
    }
  }

  const totalDuration = Date.now() - startTime;

  // 计算统计信息
  const passCount = results.filter((r) => r.passed).length;
  const totalCount = results.length;
  const passRate = totalCount > 0 ? passCount / totalCount : 0;

  // 按类别统计
  const categoryStats: Record<string, CategoryStats> = {};
  results.forEach((result) => {
    if (!categoryStats[result.category]) {
      categoryStats[result.category] = {
        passCount: 0,
        totalCount: 0,
        passRate: 0,
        failedTests: [],
      };
    }
    categoryStats[result.category].totalCount++;
    if (result.passed) {
      categoryStats[result.category].passCount++;
    } else {
      categoryStats[result.category].failedTests.push(result);
    }
  });

  // 计算各类别通过率
  Object.keys(categoryStats).forEach((category) => {
    const stats = categoryStats[category];
    stats.passRate = stats.totalCount > 0 ? stats.passCount / stats.totalCount : 0;
  });

  return {
    timestamp: new Date().toISOString(),
    totalDuration,
    summary: {
      passCount,
      totalCount,
      passRate,
    },
    categoryStats,
    results,
  };
}

// 快速评估（只运行意图检测测试）
export async function quickEvaluation(): Promise<EvaluationReport> {
  const { intentTestCases } = await import("./testCases");
  return runEvaluation(intentTestCases);
}

export default {
  executeTestCase,
  runEvaluation,
  quickEvaluation,
};
