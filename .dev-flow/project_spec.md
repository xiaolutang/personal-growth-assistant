# 项目说明

> 项目：personal-growth-assistant
> 版本：v0.33.0
> 状态：规划中（R033）
> 活跃分支：feat/R033-security-hardening

## 当前范围

R033 安全增强收口（R017 deferred 项）：

1. **B90 JWT Token 黑名单机制**：内存黑名单 + jti 标识 + 定时清理，/auth/logout 真正失效 token
2. **F121 前端 logout 调用后端**：userStore.logout() 先调后端 API 再清本地
3. **B91 Qdrant 懒重连异常保护**：connect() 加 try-except，统一双重检查模式
4. **B92 Neo4j 降级 + 知识图谱路由完善**：_get_session() 防护，路由层返回空数据而非 500
5. **S30 质量收口**：全量测试 + 构建

## 技术约束

- Token 黑名单使用内存 Set（单实例 Docker 部署足够），不引入 Redis
- jti 使用 UUID4 唯一标识，定时清理过期记录（10 分钟间隔）
- 降级修复为防御性改动，不改变现有降级架构
- workflow: B/codex_plugin/skill_orchestrated

## 用户路径

```
JWT 黑名单：
用户点击"退出登录" → 前端调 POST /auth/logout（带 token）
         → 后端将 token jti 加入黑名单
         → 前端清除 localStorage，跳转登录页
         → 旧 token 在过期前也无法使用（已被黑名单拦截）

降级完善：
管理员不配置 NEO4J_URI → 应用正常启动
         → 知识图谱页面返回空数据（200 + 空图），而非 500 错误
         → 搜索功能降级到 SQLite 全文搜索
```
