# 灵感收集

> 偶现的想法、灵感、待整理的事项

**使用说明**：
- 随时记录想法，不要让灵感溜走
- 定期（每周）回顾整理
- 有价值的想法转化为项目或任务

---

## 2025-03-04

- **AI 编程质量评估与效率平衡**
  - 问题1：如何评判/评估 AI 编写的代码质量？
    - 代码正确性：能否通过编译、测试
    - 代码规范：是否符合项目风格、最佳实践
    - 可维护性：是否过度工程、是否易于理解
    - 安全性：是否有潜在漏洞
    - 上下文理解：是否理解项目架构、是否有幻觉
  - 问题2：如何在 AI 编程过程中平衡效率与质量？
    - 效率：快速生成代码、减少重复劳动
    - 质量：代码健壮性、可维护性、可测试性
    - 平衡点：什么时候该信任 AI、什么时候需要人工审核
  - 延伸思考：
    - 是否需要建立一套 AI 代码评审 checklist
    - 是否可以通过 skill 机制自动检查 AI 代码质量
    - 团队协作中如何规范 AI 代码的使用

  - **评估维度**：
    | 维度 | 检查方式 | 自动化程度 |
    |------|----------|-----------|
    | 正确性 | 编译、单元测试 | ✅ 高 |
    | 规范性 | Lint、格式化 | ✅ 高 |
    | 安全性 | 静态分析、依赖扫描 | ✅ 中 |
    | 可维护性 | 代码复杂度、重复度 | ⚠️ 中 |
    | 架构一致性 | 需要理解项目上下文 | ❌ 低（需人工） |

  - **效率 vs 质量的平衡策略**：
    ```
    快速迭代 ──────────────────────────── 精雕细琢
       │                                    │
       │  AI 快速生成 → 自动检查 → 人工审核   │
       │         ↑              ↑           │
       │      效率           质量把控        │
    ```

  - **实用建议**：
    1. **分层信任**：简单代码信任 AI，复杂逻辑人工审核
    2. **自动化门禁**：编译 + 测试 + Lint 必须通过
    3. **抽样审查**：随机抽 20% AI 代码深度审查
    4. **建立 checklist**：类似项目的 CLEANUP_PROTOCOL.md

  - **TODO**：后续考虑设计一个 AI 代码质量检查 skill

---

## 2025-03-02

- **JoJoRead Flutter 与 Android 原生项目关联关系**
  - Flutter 项目：`/Users/tangxiaolu/project/flutter/jojoread-flutter`
  - Android 原生项目：`/Users/tangxiaolu/project/android/jojoread-mod-app`
  - 关联方式：通过 Bridge 机制通信
  - 关键桥接文件：
    - Flutter 端：`jojoNativeBridge` (调用方)
    - Android 端：`CommonBridgeImpl.kt` (实现方，路径：`core/common_flutter/src/main/kotlin/cn/tinman/jojoread/android/common_flutter/bridge/CommonBridgeImpl.kt`)
  - 典型桥接方法：`flutterPageReady` - Flutter 通知 Native 页面已准备就绪，用于处理待处理的路由跳转

---

## 2025-03-01

- 个人成长管理系统 - 把 aiLearn 转型为个人成长管理中心
- **提示词转换专家** - 本地搭建一个工具，将用户随意的聊天转换为标准的提示词格式，再发送给模型
  - 解决问题：大多数用户直接用自然语言聊天，不会按照标准的提示词格式来提问
  - 核心价值：自动优化用户输入，提升模型输出质量
  - 技术方向：Prompt 优化 + 本地/轻量级服务

---

## 2026-03-11

- **个人成长助手 - 产品定位与技术规划**

  **产品定位**：知识管理 + 任务管理
  ```
  个人成长助手
      │
      ├── 知识管理（输入）
      │    ├── 学习内容
      │    ├── 笔记（notes.md）
      │    └── 想法收集（inbox.md）
      │
      └── 任务管理（输出）
           ├── 待办（todo.md）
           └── 项目进度（projects.md）

  核心闭环：学习 → 想法 → 任务 → 执行 → 新的学习
  ```

  **技术方案**：
  | 模块 | 推荐方案 | 理由 |
  |------|----------|------|
  | RAG 框架 | LangChain | 快速原型开发，生态完善 |
  | 向量存储 | ChromaDB | 轻量级，本地部署，适合个人场景 |
  | 知识图谱 | 先观望 | 复杂度高，ROI 不确定 |

  **RAG 价值**：让助手能"回忆"你学过什么、想过什么
  **知识图谱价值**：把"学到的知识"和"要做的任务"关联起来

  **实施路径**：
  - Phase 1: 纯 RAG（先跑起来）→ LangChain + ChromaDB，检索 inbox.md / notes.md / projects.md / todo.md
  - Phase 2: 评估知识图谱必要性 → RAG 够用就不加，不足再考虑 Neo4j / NebulaGraph
  - Phase 3: 深度优化（可选）→ Hybrid Retrieval、Reranking、RAGAS 评估

  **结论**：个人场景下，先用 RAG 跑通，知识图谱作为后续增强点，不急于引入。

  **学习资源**：
  - [RAG_Techniques GitHub](https://github.com/NirDiamant/RAG_Techniques) - 各种高级 RAG 技术实现
  - [Production RAG Strategies](https://towardsai.net/p/machine-learning/production-rag-the-chunking-retrieval-and-evaluation-strategies-that-actually-work) - 生产级策略

---

## 2026-03-12

- **待调研：客户端如何实现 SSE 功能？**
  - 背景：Day 3 学习流式响应，服务端用 SSE 实现，但客户端如何消费？
  - 需要了解：
    - 浏览器端：EventSource API / fetch + ReadableStream
    - React：如何封装 SSE Hook
    - 移动端：iOS/Android 如何处理 SSE
  - 关联项目：个人成长助手前端需要展示流式输出

---

## 2026-03-14

- **个人成长助手 - 接入飞书**
  - 后期有精力的情况下，把个人成长助手连接通飞书
  - 可能的接入点：飞书文档、飞书多维表格、飞书机器人

---

## 待整理

> 较旧的未分类想法

- 深入学习 Embedding 模型对比
- 尝试 Pinecone 向量数据库
- 阅读 LangChain 源码
