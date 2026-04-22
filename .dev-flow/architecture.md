# 架构文档

> 项目：personal-growth-assistant
> 版本：v0.24.0
> 更新：2026-04-22

## 系统总览

```
personal-growth-assistant          log-service (独立仓库)
┌─────────────────────┐           ┌──────────────────────────┐
│  FastAPI 后端        │           │  FastAPI 服务端           │
│  ├── routers/       │  SDK      │  ├── routers/             │
│  ├── services/      │──────────>│  │   POST /api/logs/ingest│
│  ├── infrastructure/│  HTTP     │  │   GET  /api/logs        │
│  └── graphs/        │  POST     │  │   GET  /api/logs/stats  │
│                     │           │  │   DELETE /api/logs/cleanup│
│  React 前端         │           │  ├── storage/ (SQLite)     │
│  ├── pages/         │           │  └── middleware/            │
│  └── stores/        │           │                             │
│                     │           │  logs-ui (React SPA)       │
│  Flutter 移动端     │           │  └── service_name 筛选      │
│  ├── lib/pages/     │           └──────────────────────────┘
│  └── lib/services/  │
└─────────────────────┘
```

## 三层存储架构（personal-growth-assistant）

| 层 | 技术 | 职责 |
|----|------|------|
| Source of Truth | Markdown (.md) | 数据主源，data/users/{user_id}/ 目录 |
| 知识图谱 | Neo4j | 概念关系，节点带 user_id 属性 |
| 向量检索 | Qdrant | 语义搜索，payload 带 user_id 字段 |

SyncService 负责三层存储的同步，所有操作按 user_id 隔离。

## 用户认证架构（R002）

### 认证流程

```
用户 → Login/Register 页面 → auth API → JWT Token
                                              ↓
前端 localStorage 存储 token → fetch 拦截器注入 Authorization header
                                              ↓
后端 get_current_user 依赖 → 验证 token → 注入 User 上下文
                                              ↓
所有路由通过 Depends(get_current_user) 守卫 → 服务层传递 user_id
```

### 不变量

- 所有数据操作必须携带 user_id，不允许无用户上下文的数据访问（系统路由如 /health 除外）
- JWT secret 必须通过环境变量配置，不硬编码
- 密码使用 bcrypt 哈希，永不存储明文

### 禁止模式

- 不在前端存储敏感信息（密码、hashed_password）
- 不在日志中记录 token 或密码
- 不使用客户端生成的 user_id
- 不做 refresh_token（R002 仅 access_token，7天过期）

## Flutter 移动端架构（R024）

### 架构模式：MVVM

```
┌──────────┐     ┌──────────────┐     ┌──────────┐
│   View   │────▶│  ViewModel   │────▶│  Model   │
│ Pages/   │     │ Providers/   │     │ Services/│
│ Widgets/ │◀────│ (Riverpod)   │◀────│ + 后端API│
└──────────┘     └──────────────┘     └──────────┘
```

### 目录结构

```
mobile/
├── lib/
│   ├── main.dart
│   ├── app.dart
│   ├── config/       # 主题、路由、常量、API 配置
│   ├── models/       # Entry, ChatMessage, User, SseEvent
│   ├── services/     # ApiClient, AuthService, SSEService
│   ├── providers/    # Riverpod providers（auth, entry, chat）
│   ├── pages/        # LoginPage, TodayPage, ChatPage, TasksPage, EntryDetailPage
│   └── widgets/      # BottomNav, ChatBubble, TaskCard, EntryCard, ProgressRing
├── test/
├── pubspec.yaml
└── analysis_options.yaml
```

### 核心技术选型

| 维度 | 方案 |
|------|------|
| 框架 | Flutter (iOS + Android) |
| 状态管理 | Riverpod (flutter_riverpod) |
| 网络层 | Dio + 自定义 SSE 客户端 |
| 路由 | go_router |
| 本地存储 | flutter_secure_storage (JWT + session_id) |
| Markdown | flutter_markdown |
| 认证 | JWT Bearer，与 Web 端共享 |

### MVVM 分层职责（不变量）

**View（Pages + Widgets）**
- 只做渲染和用户交互回调
- 通过 `ref.watch(provider)` 读取状态
- 通过 `ref.read(provider.notifier).action()` 触发操作
- 禁止在 Widget 中直接调用 ApiClient 或写业务逻辑
- 禁止在 Widget 中持有业务状态（loading/error/data）

**ViewModel（Riverpod Providers）**
- 每个页面一个 Provider（如 TodayTasksProvider, ChatMessagesProvider）
- 用 AsyncNotifier 管理异步状态：loading → data / error
- 调用 Service 层获取数据，暴露 immutable state 给 View
- Provider 命名：`{Feature}Provider`（如 AuthProvider, EntryProvider, ChatProvider）
- 文件对应：`providers/{feature}_provider.dart`

**Model（Services + 后端 API）**
- Services 是对后端 API 的薄封装，不持有状态
- ApiClient 单例，通过 Riverpod 注入到 Providers
- Service 方法返回 `Future<T>` 或 `Stream<T>`，不处理 UI 逻辑
- Service 命名：`{Domain}Service`（如 AuthService, SSEService）
- 文件对应：`services/{domain}_service.dart`

### 错误处理约定（不变量）

- Service 层抛异常（DioException、超时、服务端错误）
- Provider 层 catch 异常，映射为用户友好消息
- View 层通过 `state.when(loading:, data:, error:)` 统一渲染
- 网络错误统一显示 SnackBar：无法连接服务器，请检查网络
- 401 错误由 ApiClient 拦截器统一处理：清除 token → 跳转登录页

### 页面间数据传递

- 简单 ID 传递：路由参数 `GoRouter.of(context).go('/entries/$id')`
- 页面状态：各自 Provider 独立管理，不跨页面共享
- 禁止在页面间传递对象（只用 ID + 各自拉取）

### SSE 消费模式

- SSEService 返回 `Stream<SseEvent>`
- ChatProvider 订阅 stream，收到事件后更新 messages 列表
- 页面 dispose 时自动取消订阅（Riverpod 的 ref.onDispose）
- 连接失败 → Provider 状态变 error → View 显示重试按钮

### 设计约束

- Flutter 端是纯 API 消费层，不修改后端
- 3 Tab 底栏导航：今天 / 日知 / 任务
- AI 对话是核心交互（一等公民），不是附件
- 录入优先：零摩擦输入，打开 → 说 → 关
- 不做 Web 端全功能移植，只做移动端高频场景最小可用集
- MVP 无本地缓存，所有数据实时从后端获取

### 禁止模式

- Widget 中直接调用 ApiClient（必须通过 Provider）
- Provider 中包含 UI 导航逻辑（导航由 View 层触发）
- 页面间传递业务对象（只传 ID，各自拉取）
- Provider 持有可变 List/Map（必须 immutable，变更时创建新实例）
- 多个 Provider 监听同一个 SSE 连接（一个 ChatProvider 独占）

## 后端结构

```
backend/app/
├── main.py              # FastAPI 入口 + 生命周期
├── routers/             # API 路由（entries, search, knowledge, intent, parse, review, chat）
├── services/            # 业务服务（sync_service, entry_service, ai_chat_service）
├── infrastructure/      # 基础设施（storage/, llm/）
├── graphs/              # LangGraph 图（task_parser_graph）
├── models/              # 数据模型（Task, Category, Status）
└── mcp/                 # MCP Server（9 个 Tools）
```

## 关键设计模式

| 模式 | 说明 |
|------|------|
| 依赖注入 | deps.py 全局变量 + getter 函数 + get_current_user |
| 认证守卫 | Depends(get_current_user) 注入用户上下文 |
| 存储工厂 | StorageFactory 按 user_id 创建隔离存储实例 |
| LangGraph 任务解析 | AsyncSqliteSaver + thread_id 会话隔离 + SSE 流式 |
| OpenAPI 类型同步 | 后端 schema → openapi-typescript → 前端类型 |
| Flutter API 消费 | Dio + JWT 拦截器 + SSE 客户端 → 复用同一套后端 API |

## 技术栈

| 组件 | 技术 |
|------|------|
| 后端 | Python 3.11+ / FastAPI / Pydantic |
| 存储 | SQLite（默认）/ Neo4j / Qdrant |
| Web 前端 | React 18 / Tailwind CSS / Vite / Zustand |
| 移动端 | Flutter / Riverpod / Dio / go_router |
| LLM | LangGraph / LangSmith |
| 日志服务 | FastAPI / SQLite / httpx SDK |
| 部署 | Docker Compose |

## 环境变量

| 变量 | 用途 |
|------|------|
| LLM_API_KEY / LLM_BASE_URL / LLM_MODEL | LLM 调用 |
| JWT_SECRET | JWT 签名密钥 |
| JWT_ALGORITHM | JWT 算法（默认 HS256） |
| ACCESS_TOKEN_EXPIRE_DAYS | Access Token 过期天数（默认 7） |
| NEO4J_URI / USERNAME / PASSWORD | 知识图谱 |
| QDRANT_URL / API_KEY | 向量检索 |
| DATA_DIR | Markdown 数据目录 |
| FRONTEND_BASE_PATH | 前端基础路径 |
| LOG_LEVEL | 日志级别 |

## 跨语言接入约束

- 协议：HTTP REST（JSON），不使用 gRPC
- 不依赖外部消息队列
- Flutter 端通过标准 HTTP/SSE 对接后端，无特殊协议

## 反馈功能架构

- 后端双写：本地 SQLite + log-service 异步上报
- 前端：FeedbackButton 组件（双 Tab：提交 + 我的反馈）
- 移动端 MVP 不含反馈功能

## 部署架构

### 单容器模式（Web）

```
Traefik (:80)
    ├── /growth/api/* (priority=100) → FastAPI routes
    └── /growth/*    (priority=50)  → StaticFiles
```

### 移动端

- App 独立安装（App Store / Google Play，V2 考虑）
- 后端 API 通过 BaseURL 配置连接（默认 localhost:8001）
- 不做独立后端部署，复用同一套 FastAPI 服务
