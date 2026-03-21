/**
 * 会话标题相关常量和工具
 */

// 默认会话标题
export const DEFAULT_SESSION_TITLE = "新对话";

// 标题最大长度
export const MAX_TITLE_LENGTH = 20;

/**
 * 检查是否需要更新标题（当标题为默认值时）
 */
export function shouldUpdateTitle(currentTitle: string | undefined | null): boolean {
  return currentTitle === DEFAULT_SESSION_TITLE;
}

/**
 * 截断标题到最大长度
 */
export function truncateTitle(title: string): string {
  return title.slice(0, MAX_TITLE_LENGTH);
}
