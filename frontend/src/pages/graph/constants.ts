// === 掌握度颜色映射 ===
export const masteryColors: Record<string, string> = {
  advanced: "#22c55e",
  intermediate: "#3b82f6",
  beginner: "#f97316",
  new: "#9ca3af",
};

export const masteryLabels: Record<string, string> = {
  advanced: "精通",
  intermediate: "熟练",
  beginner: "入门",
  new: "新概念",
};

export const masterySuggestions: Record<string, string> = {
  advanced: "你已经精通这个概念，可以尝试教授他人或挑战更高难度的应用。",
  intermediate: "你正在稳步进步，继续保持实践和深入探索。",
  beginner: "刚刚开始接触，建议多阅读相关资料并动手实践。",
  new: "这是一个新的知识领域，建议从基础概念开始了解。",
};

// === 视角 Tab 配置 ===
export const viewTabs = [
  { key: "domain", label: "领域" },
  { key: "mastery", label: "掌握度" },
  { key: "project", label: "项目" },
  { key: "capability", label: "能力地图" },
] as const;

export type ViewKey = (typeof viewTabs)[number]["key"];

// === 掌握度等级列表 ===
export const MASTERY_LEVELS = ["advanced", "intermediate", "beginner", "new"] as const;

// === 性能优化常量 ===
export const NODE_THRESHOLD = 50;
export const EDGE_LABEL_THRESHOLD = 100;
