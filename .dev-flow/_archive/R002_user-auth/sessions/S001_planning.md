# S001: R002 用户认证与数据隔离 — 规划 Session

> 日期：2026-04-13
> 需求周期：R002
> 状态：规划中

## 用户输入

- 需求：为 personal-growth-assistant 添加用户登录功能
- 认证方式：JWT Token
- 数据隔离：完整隔离（每用户独立数据空间）
- 用户管理：注册 + 登录 + 登出（基础三件套）

## 需求分析

### 当前状态
- 系统无任何认证机制，全局共享数据
- 前端有匿名 X-UID 机制（仅用于日志追踪）
- 四层存储（SQLite/Markdown/Neo4j/Qdrant）均无 user_id 概念
- 会话（LangGraph）无用户隔离

### 核心挑战
1. 数据层全面改造：SQLite 加列、Markdown 分目录、Neo4j/Qdrant 加属性
2. 现有数据迁移：已有数据需归属到首个注册用户
3. 服务层传递用户上下文：EntryService/SyncService 等需感知用户
4. 全路由守卫：8 个路由文件需添加认证依赖

### 架构决策

1. **JWT 方案**：Access Token（30min）+ Refresh Token（7d, httpOnly cookie）
2. **密码存储**：bcrypt via passlib
3. **存储隔离策略**：
   - SQLite: entries 表加 user_id 列，查询加 WHERE 过滤
   - Markdown: 按用户分子目录 `data/users/{user_id}/`
   - Neo4j: Entry/Concept 节点加 user_id 属性
   - Qdrant: payload 加 user_id，搜索加 filter
4. **服务工厂**：MarkdownStorage 改为工厂模式，按 user_id 创建实例
5. **现有数据**：迁移到 `data/users/_default/`，首个注册用户可选择认领

### 拆解模式
- 主模式：模式 1（认证/登录链路）
- 辅助模式：模式 7（依赖登录态的首页）

## 任务概览

| Phase | 任务 | 类型 |
|-------|------|------|
| P1 | S01 契约定义, B01 User模型, B02 认证API, B03 认证测试 | 认证基础 |
| P2 | B04 SQLite隔离, B05 Markdown隔离, B06 Neo4j隔离, B07 Qdrant隔离, B08 服务层改造, B09 会话隔离 | 数据隔离 |
| P3 | B10 认证中间件, B11 全路由守卫 | 路由守卫 |
| P4 | F01 状态管理, F02 登录注册页, F03 路由守卫+拦截器, F04 侧边栏用户信息 | 前端认证 |
| P5 | S02 全链路联调 | 集成验证 |

总计 17 个任务。

## 规划审核

- **审核时间**：2026-04-13
- **审核结论**：conditional_pass
- **修复项**：
  - RC-01: 移除 refresh_token，R002 仅 access_token（7天过期）
  - RC-02: B09 明确 LangGraph 隔离策略为 thread_id 命名空间化
  - RC-03: deps.py 保持全局单例，user_id 通过方法参数传递
  - RC-04: 移除 get_optional_current_user，所有数据路由必须认证
  - RC-05: MCP Server 不在 R002 范围，标记为 R003 候选
- **用户确认**：全部采纳

### 第二轮审核

- **审核时间**：2026-04-13
- **审核结论**：conditional_pass
- **修复项**：
  - RC-06: 删除 architecture.md 重复的"禁止模式"段落
  - RC-07: 统一 JWT 过期时间配置命名为 ACCESS_TOKEN_EXPIRE_DAYS
  - RC-08: B09 补充 parse.py 文件声明和 thread_id 命名空间化验收标准
  - F-04: session_id 合法字符约束（仅字母数字和连字符）
  - F-05: api_contracts.md CONTRACT-A03 明确 logout 语义
