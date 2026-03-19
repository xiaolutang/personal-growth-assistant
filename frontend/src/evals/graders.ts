/**
 * 评估评分器
 * 用于评估意图检测和多轮对话的质量
 */

import type { Intent } from "@/lib/intentDetection";
import type { TestCase } from "./testCases";

// 评分结果接口
export interface GradeResult {
  passed: boolean;
  score: number; // 0-1
  reason?: string;
}

// 意图检测评分器
export function gradeIntentDetection(
  actual: Intent,
  expected: Intent
): GradeResult {
  const passed = actual === expected;
  return {
    passed,
    score: passed ? 1 : 0,
    reason: passed
      ? undefined
      : `意图不匹配: 期望 "${expected}", 实际 "${actual}"`,
  };
}

// 消息匹配评分器
export function gradeMessage(
  actual: string,
  expected: string | RegExp
): GradeResult {
  if (expected instanceof RegExp) {
    const passed = expected.test(actual);
    return {
      passed,
      score: passed ? 1 : 0,
      reason: passed
        ? undefined
        : `消息不匹配正则: ${expected.source}`,
    };
  }

  const passed = actual.includes(expected);
  return {
    passed,
    score: passed ? 1 : 0,
    reason: passed
      ? undefined
      : `消息不包含期望文本: "${expected}"`,
  };
}

// 操作完成评分器
export function gradeOperation(
  expected: boolean,
  actual: boolean
): GradeResult {
  const passed = expected === actual;
  return {
    passed,
    score: passed ? 1 : 0,
    reason: passed
      ? undefined
      : `操作结果不匹配: 期望 ${expected}, 实际 ${actual}`,
  };
}

// 综合评分器
export function gradeTestCase(
  testCase: TestCase,
  actualResult: {
    intent?: Intent;
    message?: string;
    success?: boolean;
  }
): GradeResult {
  const { expected } = testCase;

  // 意图检测评分
  if (expected.intent !== undefined) {
    return gradeIntentDetection(
      actualResult.intent || "create",
      expected.intent
    );
  }

  // 消息匹配评分
  if (expected.message !== undefined) {
    return gradeMessage(
      actualResult.message || "",
      expected.message
    );
  }

  // 操作完成评分
  if (expected.success !== undefined) {
    return gradeOperation(expected.success, actualResult.success ?? true);
  }

  // 默认通过
  return { passed: true, score: 1 };
}

// 计算通过率
export function calculatePassRate(results: GradeResult[]): {
  passCount: number;
  totalCount: number;
  passRate: number;
} {
  const passCount = results.filter((r) => r.passed).length;
  const totalCount = results.length;
  const passRate = totalCount > 0 ? passCount / totalCount : 0;

  return { passCount, totalCount, passRate };
}

// 按类别计算通过率
export function calculatePassRateByCategory(
  testCases: TestCase[],
  results: GradeResult[]
): Record<string, { passCount: number; totalCount: number; passRate: number }> {
  const categories: Record<
    string,
    { passCount: number; totalCount: number; passRate: number }
  > = {};

  testCases.forEach((testCase, index) => {
    const category = testCase.category;
    if (!categories[category]) {
      categories[category] = { passCount: 0, totalCount: 0, passRate: 0 };
    }
    categories[category].totalCount++;
    if (results[index]?.passed) {
      categories[category].passCount++;
    }
  });

  // 计算通过率
  Object.keys(categories).forEach((category) => {
    const cat = categories[category];
    cat.passRate = cat.totalCount > 0 ? cat.passCount / cat.totalCount : 0;
  });

  return categories;
}

export default {
  gradeIntentDetection,
  gradeMessage,
  gradeOperation,
  gradeTestCase,
  calculatePassRate,
  calculatePassRateByCategory,
};
