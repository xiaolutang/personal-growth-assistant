# 项目说明

> 项目：personal-growth-assistant
> 版本：v0.8.0

## 目标

- R010 工程化提升 — E2E 测试覆盖 + API 可观测性 + CI/CD Pipeline + 性能基线

## 前置依赖（R001-R009 已完成）

- 用户认证 + 数据隔离 + 路由守卫
- Chat 用户 ID 透传（R009）
- 所有核心功能模块已就绪

## 范围

### 包含
- B34: Health check + trace_id + 统一错误响应
- B35: E2E 基础设施（webServer 配置 + 认证 fixture + 工具函数）
- B36: 认证流程 E2E 测试
- B37: 条目 CRUD E2E 测试
- B38: Chat 对话 E2E 测试
- B39: 回顾页 E2E 测试
- B40: GitHub Actions CI Pipeline
- B41: 性能基线建立

### 不包含
- 负载测试 / 压力测试
- CD（持续部署）— 仅 CI
- 前端组件测试补充（已有 231 个）

## 用户路径（E2E 覆盖）

1. 注册 → 登录 → 访问首页 → 登出 → 重定向到登录页
2. 登录 → 创建任务 → 任务列表可见 → 更新状态 → 删除 → 列表不可见
3. 登录 → Chat 对话创建条目 → 搜索条目 → 更新条目 → 删除条目
4. 登录 → 查看回顾页 → 统计数据展示 → 趋势图可见

## 技术约束

- E2E 测试使用 Playwright（已安装），webServer 自动启停后端
- CI 使用 GitHub Actions
- 性能基线不引入新依赖，使用现有工具（vitest、pytest-bench）
