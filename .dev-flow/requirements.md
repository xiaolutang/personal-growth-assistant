# 需求记录

> 项目：log-service（从 personal-growth-assistant 抽取）
> 状态：已确认
> 最后更新：2026-03-28

## 当前生效结论
- 当前范围：将 personal-growth-assistant 的日志模块抽取为独立的 log-service 项目
- 当前约束：
  - 使用 HTTP REST（非 gRPC）作为跨语言接入协议
  - 默认 SQLite 存储，预留可扩展接口
  - 先做 Python SDK，Java SDK 后续补充
  - 当前项目（personal-growth-assistant）作为第一个接入方
- 当前未确认项：无
- 当前基线版本：v0.1.0

---

## Session Index

| Session | 时间 | 类型 | 主题 | 结果 |
|---------|------|------|------|------|
| S001 | 2026-03-28 | init | 日志服务抽取规划 | 已确认 |

---

## Session S001 - 初始化需求

> 时间：2026-03-28
> 类型：init
> 状态：confirmed

### 用户输入
- 开发了很多前后端连通的项目，日志系统各个项目都是分开的
- 想抽离一个公共的日志服务模块
- 其他项目可能是 Java，需要跨语言支持
- 不确定每个项目独立日志还是集中管理

### AI 理解
- 核心需求：多项目共享日志基础设施，减少重复代码
- 跨语言约束：不能只做 Python 包，需要协议级接入（HTTP REST）
- 部署形态：独立服务 + 各语言 SDK

### AI 澄清问题
1. 公共日志模块以什么形式分发？→ 用户未确定
2. Java 项目怎么接入？→ 确认不走 RPC，用 HTTP REST
3. 日志是否集中存储？→ 折中方案：代码层面共享，数据层面各自独立但预留集中上报

### 用户回答
- "没想好怎么进行日志共享，还是说每个项目都需要一个独立的日志模块"
- "别的项目如果是 Java 呢？是新写一个还是接入当前这个？"
- 确认走折中方案：独立 log-service 仓库 + Python/Java SDK
- 确认不用 gRPC，用 HTTP REST

### 本轮结论
- 新建独立的 log-service 仓库
- 服务端：FastAPI，从当前项目迁移日志模块
- 接入方式：HTTP POST /api/logs/ingest
- Python SDK：pip install，提供 RemoteLogHandler（logging.Handler 子类）
- Java SDK：后续补充 logback Appender
- 当前项目（personal-growth-assistant）作为第一个接入方
- logs-ui 迁移到 log-service 仓库，新增 service_name 筛选
- 不含 LangSmith（LangSmith 留在各项目内部）

### 影响范围
- 新增：log-service 独立仓库（server + sdks/python + logs-ui）
- 调整：personal-growth-assistant 移除本地日志模块，改用 SDK 接入
- 不影响：LangSmith 配置、业务逻辑、前端业务页面

---

## 已确认需求
- 日志服务作为独立仓库和独立部署单元
- HTTP REST 作为唯一跨语言接入协议
- Python SDK 作为首个客户端实现
- SQLite 作为默认存储，预留扩展接口
- logs-ui 支持 service_name 筛选
- 当前项目作为首个接入方完成改造

## 约束
- 不使用 gRPC
- 不依赖外部消息队列
- 不包含 LangSmith
- 服务端使用 FastAPI
- 存储层可扩展（默认 SQLite）

## 待确认
- 无
