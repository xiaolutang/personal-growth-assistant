/**
 * 智能体评估体系入口
 *
 * 使用方法：
 * ```typescript
 * import { runAndPrintEvaluation } from '@/evals';
 *
 * // 在浏览器控制台运行
 * runAgentEval();        // 两阶段评估（模拟 + 真实 API）
 * runMockEval();         // 仅模拟验证
 * runRealEval();         // 仅真实 API 验证
 * ```
 */

export * from "./testCases";
export * from "./graders";
export * from "./runner";
export * from "./report";

import { runEvaluation, runTwoPhaseEvaluation, mockEvaluation, realEvaluation, type EvalMode } from "./runner";
import { formatReportAsConsole, type EvaluationReport } from "./report";

/**
 * 运行评估并打印结果到控制台
 * @param mode "mock" | "real" | "both"
 */
export async function runAndPrintEvaluation(
  mode: EvalMode = "both"
): Promise<EvaluationReport> {
  console.log("═══════════════════════════════════════");
  console.log("       智能体两阶段评估");
  console.log("═══════════════════════════════════════\n");

  try {
    const report = await runTwoPhaseEvaluation(mode);
    console.log(formatReportAsConsole(report));
    return report;
  } catch (error) {
    console.error("评估失败:", error);
    throw error;
  }
}

// 在浏览器控制台中可用的全局方法
if (typeof window !== "undefined") {
  (window as unknown as Record<string, unknown>).runAgentEval = () => runAndPrintEvaluation("both");
  (window as unknown as Record<string, unknown>).runMockEval = () => runAndPrintEvaluation("mock");
  (window as unknown as Record<string, unknown>).runRealEval = () => runAndPrintEvaluation("real");
}

export default {
  runEvaluation,
  runTwoPhaseEvaluation,
  runAndPrintEvaluation,
  mockEvaluation,
  realEvaluation,
};
