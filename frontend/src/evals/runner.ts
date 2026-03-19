/**
 * 评估执行器
 * 用于运行测试用例并收集结果
 *
 * 支持两阶段评估：
 * - Phase 1: 模拟验证（测试意图检测逻辑，不依赖外部 API）
 * - Phase 2: 真实调用验证（调用实际后端 API，验证搜索结果）
 */

import { detectIntent, extractSearchQuery, type Intent } from "@/lib/intentDetection";
import { allTestCases, apiTestCases, operationTestCases, type TestCase } from "./testCases";
import { gradeTestCase, type GradeResult } from "./graders";
import type { EvaluationReport, TestResult, CategoryStats } from "./report";
import { searchEntries } from "@/services/api";

// 评估模式
export type EvalMode = "mock" | "real" | "both";

// 真实 API 测试结果
interface RealTestResult {
  intent?: Intent;
  resultCount?: number;
  resultTitles?: string[];
  error?: string;
}

// 扩展的 TestResult，包含阶段信息
interface ExtendedTestResult extends TestResult {
  phase: "mock" | "real";
}

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

// 运行所有测试用例（兼容旧接口）
export async function runEvaluation(
  testCases: TestCase[] = allTestCases
): Promise<EvaluationReport> {
  return runTwoPhaseEvaluation("mock", testCases);
}

// Phase 1: 模拟验证（现有逻辑）
async function runMockEvaluation(testCases: TestCase[]): Promise<ExtendedTestResult[]> {
  const results: ExtendedTestResult[] = [];

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
        phase: "mock",
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
        phase: "mock",
      });
    }
  }

  return results;
}

// 真实 API 测试执行
async function executeRealTest(testCase: TestCase): Promise<RealTestResult> {
  const result: RealTestResult = {};

  // 执行意图检测
  result.intent = detectIntent(testCase.input);

  // 如果是搜索意图，调用真实 API
  if (result.intent === "read") {
    const query = extractSearchQuery(testCase.input);
    try {
      const searchResponse = await searchEntries(query, 10);

      result.resultCount = searchResponse.results.length;
      result.resultTitles = searchResponse.results.map(r => r.title);
    } catch (error) {
      result.error = error instanceof Error ? error.message : "搜索 API 调用失败";
    }
  }

  return result;
}

// API 测试评分
function gradeApiTest(testCase: TestCase, actual: RealTestResult): GradeResult {
  const { expected } = testCase;
  const hasResults = (actual.resultCount ?? 0) > 0;

  // 检查是否有错误
  if (actual.error) {
    return {
      passed: false,
      score: 0,
      reason: `API 错误: ${actual.error}`,
    };
  }

  // 检查意图
  if (expected.intent && actual.intent !== expected.intent) {
    return {
      passed: false,
      score: 0,
      reason: `意图不匹配: 期望 "${expected.intent}", 实际 "${actual.intent}"`,
    };
  }

  // 检查搜索结果
  if (expected.shouldHaveResults !== undefined) {
    if (expected.shouldHaveResults && !hasResults) {
      return {
        passed: false,
        score: 0.5,  // 意图对了但没结果
        reason: `搜索无结果，期望有结果`,
      };
    }
    if (!expected.shouldHaveResults && hasResults) {
      return {
        passed: false,
        score: 0.5,
        reason: `搜索有结果，期望无结果`,
      };
    }
  }

  // 检查结果内容
  if (expected.resultShouldContain && actual.resultTitles) {
    const found = actual.resultTitles.some(title =>
      title.toLowerCase().includes(expected.resultShouldContain!.toLowerCase())
    );
    if (!found) {
      return {
        passed: false,
        score: 0.7,
        reason: `搜索结果不包含 "${expected.resultShouldContain}"`,
      };
    }
  }

  // 检查最少结果数
  if (expected.minResultCount !== undefined && actual.resultCount !== undefined) {
    if (actual.resultCount < expected.minResultCount) {
      return {
        passed: false,
        score: 0.8,
        reason: `搜索结果数不足: 期望至少 ${expected.minResultCount} 个，实际 ${actual.resultCount} 个`,
      };
    }
  }

  return { passed: true, score: 1 };
}

// Phase 2: 真实 API 验证
async function runRealEvaluation(testCases: TestCase[]): Promise<ExtendedTestResult[]> {
  const results: ExtendedTestResult[] = [];

  for (const testCase of testCases) {
    if (testCase.category !== "api" && testCase.category !== "operation") continue;

    const testStartTime = Date.now();

    try {
      const actualResult = await executeRealTest(testCase);
      const gradeResult = gradeApiTest(testCase, actualResult);

      results.push({
        id: testCase.id,
        category: testCase.category,
        input: testCase.input,
        passed: gradeResult.passed,
        score: gradeResult.score,
        reason: gradeResult.reason,
        duration: Date.now() - testStartTime,
        phase: "real",
      });
    } catch (error) {
      results.push({
        id: testCase.id,
        category: testCase.category,
        input: testCase.input,
        passed: false,
        score: 0,
        reason: `API 错误: ${error instanceof Error ? error.message : "未知错误"}`,
        duration: Date.now() - testStartTime,
        phase: "real",
      });
    }
  }

  return results;
}

// 生成评估报告
function generateEvaluationReport(results: ExtendedTestResult[], totalDuration: number): EvaluationReport {
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

// 两阶段评估主入口
export async function runTwoPhaseEvaluation(
  mode: EvalMode = "both",
  testCases: TestCase[] = allTestCases
): Promise<EvaluationReport> {
  const allResults: ExtendedTestResult[] = [];
  const startTime = Date.now();

  // Phase 1: 模拟验证
  if (mode === "mock" || mode === "both") {
    console.log("📋 Phase 1: 模拟验证...");
    const mockResults = await runMockEvaluation(testCases);
    allResults.push(...mockResults);

    const mockPassRate = mockResults.length > 0
      ? mockResults.filter(r => r.passed).length / mockResults.length
      : 0;
    console.log(`   模拟验证通过率: ${(mockPassRate * 100).toFixed(1)}%`);

    // 如果模拟验证失败率超过 20%，不继续真实验证
    if (mode === "both" && mockPassRate < 0.8) {
      console.warn("⚠️ 模拟验证失败率过高，跳过真实 API 验证");
      return generateEvaluationReport(allResults, Date.now() - startTime);
    }
  }

  // Phase 2: 真实 API 验证
  if (mode === "real" || mode === "both") {
    console.log("🔍 Phase 2: 真实 API 验证...");
    const realTestCases = [...apiTestCases, ...operationTestCases];
    const realResults = await runRealEvaluation(realTestCases);
    allResults.push(...realResults);

    const realPassRate = realResults.length > 0
      ? realResults.filter(r => r.passed).length / realResults.length
      : 0;
    console.log(`   真实验证通过率: ${(realPassRate * 100).toFixed(1)}%`);
  }

  return generateEvaluationReport(allResults, Date.now() - startTime);
}

// 快速评估（只运行意图检测测试）
export async function quickEvaluation(): Promise<EvaluationReport> {
  const { intentTestCases } = await import("./testCases");
  return runEvaluation(intentTestCases);
}

// 仅模拟验证
export async function mockEvaluation(): Promise<EvaluationReport> {
  return runTwoPhaseEvaluation("mock");
}

// 仅真实 API 验证
export async function realEvaluation(): Promise<EvaluationReport> {
  return runTwoPhaseEvaluation("real");
}

export default {
  executeTestCase,
  runEvaluation,
  runTwoPhaseEvaluation,
  quickEvaluation,
  mockEvaluation,
  realEvaluation,
};
