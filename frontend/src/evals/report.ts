/**
 * 评估报告生成器
 * 用于格式化和展示评估结果
 */

// 测试结果接口
export interface TestResult {
  id: string;
  category: string;
  input: string;
  passed: boolean;
  score: number;
  reason?: string;
  duration: number;
}

// 类别统计接口
export interface CategoryStats {
  passCount: number;
  totalCount: number;
  passRate: number;
  failedTests: TestResult[];
}

// 评估报告接口
export interface EvaluationReport {
  timestamp: string;
  totalDuration: number;
  summary: {
    passCount: number;
    totalCount: number;
    passRate: number;
  };
  categoryStats: Record<string, CategoryStats>;
  results: TestResult[];
}

// 格式化报告为 Markdown
export function formatReportAsMarkdown(report: EvaluationReport): string {
  const lines: string[] = [
    "# 智能体评估报告",
    "",
    `**评估时间**: ${report.timestamp}`,
    `**总耗时**: ${report.totalDuration}ms`,
    "",
    "## 总体结果",
    "",
    `| 指标 | 数值 |`,
    `|------|------|`,
    `| 通过数 | ${report.summary.passCount} |`,
    `| 总数 | ${report.summary.totalCount} |`,
    `| 通过率 | ${(report.summary.passRate * 100).toFixed(1)}% |`,
    "",
    "## 分类统计",
    "",
    `| 类别 | 通过/总数 | 通过率 |`,
    `|------|----------|--------|`,
  ];

  // 添加各类别统计
  Object.entries(report.categoryStats).forEach(([category, stats]) => {
    const rate = (stats.passRate * 100).toFixed(1);
    lines.push(`| ${getCategoryLabel(category)} | ${stats.passCount}/${stats.totalCount} | ${rate}% |`);
  });

  // 添加失败案例
  const failedTests = report.results.filter((r) => !r.passed);
  if (failedTests.length > 0) {
    lines.push("", "## 失败案例", "");
    failedTests.forEach((test) => {
      lines.push(`### ${test.id}`, "");
      lines.push(`- **输入**: "${test.input}"`);
      lines.push(`- **类别**: ${getCategoryLabel(test.category)}`);
      if (test.reason) {
        lines.push(`- **失败原因**: ${test.reason}`);
      }
      lines.push("");
    });
  }

  return lines.join("\n");
}

// 格式化报告为控制台输出
export function formatReportAsConsole(report: EvaluationReport): string {
  const lines: string[] = [
    "",
    "═══════════════════════════════════════",
    "         智能体评估报告",
    "═══════════════════════════════════════",
    "",
    `评估时间: ${report.timestamp}`,
    `总耗时: ${report.totalDuration}ms`,
    "",
    "──────────── 总体结果 ────────────",
    "",
    `  通过: ${report.summary.passCount}/${report.summary.totalCount}`,
    `  通过率: ${(report.summary.passRate * 100).toFixed(1)}%`,
    "",
    "──────────── 分类统计 ────────────",
    "",
  ];

  Object.entries(report.categoryStats).forEach(([category, stats]) => {
    const icon = stats.passRate === 1 ? "✅" : stats.passRate >= 0.8 ? "⚠️" : "❌";
    lines.push(`  ${icon} ${getCategoryLabel(category)}: ${stats.passCount}/${stats.totalCount} (${(stats.passRate * 100).toFixed(0)}%)`);
  });

  const failedTests = report.results.filter((r) => !r.passed);
  if (failedTests.length > 0) {
    lines.push("", "──────────── 失败案例 ────────────", "");
    failedTests.forEach((test) => {
      lines.push(`  ❌ [${test.id}] "${test.input}"`);
      if (test.reason) {
        lines.push(`     原因: ${test.reason}`);
      }
    });
  }

  lines.push("", "═══════════════════════════════════════", "");

  return lines.join("\n");
}

// 获取分类标签
function getCategoryLabel(category: string): string {
  const labels: Record<string, string> = {
    intent: "意图检测",
    operation: "操作流程",
    multi_turn: "多轮对话",
    edge_case: "边界情况",
    api: "API 验证",
  };
  return labels[category] || category;
}

// 生成简短摘要
export function generateSummary(report: EvaluationReport): string {
  const rate = (report.summary.passRate * 100).toFixed(1);
  const status = report.summary.passRate >= 0.9
    ? "✅ 优秀"
    : report.summary.passRate >= 0.8
    ? "⚠️ 良好"
    : "❌ 需改进";

  return `评估完成: ${report.summary.passCount}/${report.summary.totalCount} 通过 (${rate}%) - ${status}`;
}

// 评估等级判断
export function getEvaluationGrade(passRate: number): {
  grade: string;
  description: string;
} {
  if (passRate >= 0.95) {
    return { grade: "A+", description: "优秀 - 生产就绪" };
  } else if (passRate >= 0.9) {
    return { grade: "A", description: "优秀" };
  } else if (passRate >= 0.85) {
    return { grade: "B+", description: "良好" };
  } else if (passRate >= 0.8) {
    return { grade: "B", description: "合格" };
  } else if (passRate >= 0.7) {
    return { grade: "C", description: "需改进" };
  } else {
    return { grade: "D", description: "不合格" };
  }
}

export default {
  formatReportAsMarkdown,
  formatReportAsConsole,
  generateSummary,
  getEvaluationGrade,
};
