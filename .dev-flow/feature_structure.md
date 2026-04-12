# 功能结构图

> 项目：log-service
> 版本：v0.1.0
> 最后更新：2026-04-12

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        log-service                              │
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌───────────────┐  │
│  │   FastAPI 服务   │  │   SQLite 存储    │  │   logs-ui     │  │
│  │                 │  │                 │  │   (React)     │  │
│  │ POST /ingest    │  │  logs 表        │  │               │  │
│  │ GET  /logs      │◄─┤  (service_name) │◄─┤  筛选/查看    │  │
│  │ GET  /stats     │  │                 │  │               │  │
│  │ DEL  /cleanup   │  │                 │  │               │  │
│  └────────▲────────┘  └────────▲────────┘  └───────────────┘  │
│           │                    │                                │
│  ┌────────┴────────┐          │                                │
│  │   中间件         │          │                                │
│  │  RequestID      │          │                                │
│  │  ReqLogging     │──────────┘                                │
│  │  ErrorHandler   │                                           │
│  └─────────────────┘                                           │
└─────────────────────────────────────────────────────────────────┘
           ▲
           │ HTTP POST /api/logs/ingest
           │
    ┌──────┴──────┐  ┌─────────────┐  ┌─────────────┐
    │ Python 项目  │  │ Java 项目    │  │ Go 项目      │
    │             │  │             │  │             │
    │ SDK         │  │ logback     │  │ log hook    │
    │ (pip)       │  │ Appender    │  │             │
    └─────────────┘  └─────────────┘  └─────────────┘
```

## 模块详情

### M1: 日志服务核心

**职责**: 接收、存储、查询、管理日志

**核心流程**:
```
外部项目 → POST /ingest → 校验 → 批量写入 SQLite
内部 Handler → 内存队列 → 后台线程 → 批量写入 SQLite
logs-ui → GET /logs → 查询 SQLite → 返回分页结果
定时/手动 → DELETE /cleanup → 删除过期记录 → VACUUM
```

**页面/入口**:
- API 端点: /api/logs/ingest, /api/logs, /api/logs/stats, /api/logs/cleanup
- 健康检查: /health

### M2: Python SDK

**职责**: 为 Python 项目提供一行代码接入能力

**核心流程**:
```
业务代码 → logger.info() → RemoteLogHandler.emit()
→ queue.Queue → 后台线程攒批(50条/2秒)
→ HTTP POST /api/logs/ingest → 失败重试(3次)
```

**接口**:
- `RemoteLogHandler(endpoint, service_name, level, batch_size, flush_interval)`
- `setup_remote_logging(endpoint, service_name, level)` → 快捷初始化

### M3: 日志前端 (logs-ui)

**职责**: 提供可视化日志查看、筛选、统计界面

**核心流程**:
```
用户访问 → 加载统计概览 → 输入筛选条件
→ GET /api/logs?service_name=xxx&level=ERROR → 渲染日志列表
→ 点击日志 → 弹窗显示详情
```

**页面**:
- 日志列表页（含 FilterBar + StatsCard + LogList + 分页）
- 日志详情弹窗（LogDetail）

### M4: 项目改造

**职责**: personal-growth-assistant 从本地日志改为 SDK 接入

**改造流程**:
```
移除本地日志模块 → 安装 log-service-sdk
→ main.py 中 setup_remote_logging() → 验证日志上报
```

### M5: 部署集成

**职责**: Docker 化部署与端到端验证

**组件**:
- log-service 容器（FastAPI 服务端）
- logs-ui 容器（Nginx 静态文件服务）
- 数据卷（SQLite 数据持久化）

### M10: 反馈功能

**职责**: 在 personal-growth-assistant 中提供用户可见的反馈提交通道，并代理到 log-service Issue API

**核心流程**:
```
用户点击右下角反馈按钮
→ 展开 FeedbackButton 表单
→ submitFeedback()
→ POST /feedback
→ log_service_sdk.report_issue()
→ log-service /api/issues
→ 返回 success / 422 / 503
```

**界面约束**:
- 反馈按钮固定在右下角，但需位于 FloatingChat 上方
- 与 FloatingChat 保持至少 16px 垂直间距
- 窄屏下优先保证聊天入口和反馈提交按钮均可触达

## 数据流图

```
Python SDK ──┐
Java SDK ────┤ HTTP POST
Go SDK ──────┘
             │
             ▼
     ┌───────────────┐
     │  FastAPI       │──── 内部 Handler ────┐
     │  /api/logs/*   │                      │
     └───────┬───────┘                      │
             │                              │
             ▼                              ▼
     ┌───────────────┐              ┌───────────────┐
     │  LogStorage    │◄─────────────│ SQLiteHandler  │
     │  (SQLite)      │              │ (内部日志)      │
     └───────┬───────┘              └───────────────┘
             │
     ┌───────┴───────┐
     │               │
     ▼               ▼
GET /logs      GET /stats
     │               │
     ▼               ▼
┌─────────┐   ┌──────────┐
│ logs-ui │   │ logs-ui  │
│ 日志列表 │   │ 统计卡片  │
└─────────┘   └──────────┘
```

## 模块依赖关系

```
M1(服务核心) ← M2(Python SDK)
M1(服务核心) ← M3(logs-ui)
M2(Python SDK) ← M4(项目改造)
M1 + M3 ← M5(部署集成)
M4 + M5 → 端到端验证
M1(服务核心) ← M10(反馈功能)
M10(反馈功能) 依赖反馈 SDK 契约确认和前端 API 层
```
