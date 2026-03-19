/**
 * 智能体评估体系入口
 *
 * 使用方法：
 * ```typescript
 * import { runAndPrintEvaluation } from '@/evals';
 *
 * // 在浏览器控制台运行
 * runAndPrintEvaluation();
 * ```
 */

export * from "./testCases";
export * from "./graders";
export * from "./runner";
export * from "./report";

import { runEvaluation } from "./runner";
import { formatReportAsConsole, type EvaluationReport } from "./report";

/**
 * 运行评估并打印结果到控制台
 */
export async function runAndPrintEvaluation(): Promise<EvaluationReport> {
  console.log("正在运行智能体评估...");

  try {
    const report = await runEvaluation();
    console.log(formatReportAsConsole(report));
    return report;
  } catch (error) {
    console.error("评估失败:", error);
    throw error;
  }
}

// 在浏览器控制台中可用的全局方法
if (typeof window !== "undefined") {
  (window as unknown as Record<string, unknown>).runAgentEval = runAndPrintEvaluation;
}

export default {
  runEvaluation,
  runAndPrintEvaluation,
};
