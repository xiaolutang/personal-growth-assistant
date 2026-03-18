/**
 * API 配置
 *
 * 统一管理前端连接后端的地址
 * 修改此文件即可全局生效
 */

// 开发环境：通过 Vite 代理访问后端
// 生产环境：直接访问部署地址
export const API_CONFIG = {
  // API 基础路径（开发环境通过 Vite 代理，生产环境直接访问）
  base: "/api",

  // 后端服务地址（仅用于参考，实际请求通过 base 发送）
  // 开发环境: http://localhost (Vite 代理转发)
  // 生产环境: 根据实际部署地址修改
  backendUrl: "http://localhost",
} as const;

// 导出便捷常量
export const API_BASE = API_CONFIG.base;
