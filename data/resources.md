# 学习资源

> 各阶段学习资源汇总

---

## CS146S：The Modern Software Developer

> 斯坦福 2025 年秋季新开课程，AI 原生开发方法论

### 课程信息

| 属性 | 内容 |
|------|------|
| 课程官网 | [themodernsoftware.dev](https://themodernsoftware.dev) |
| 作业仓库 | [GitHub](https://github.com/mihail911/modern-software-dev-assignments) |
| 周期 | 10 周 |
| 费用 | 免费（PPT、阅读材料、作业全公开） |

### 课程大纲

| 周次 | 主题 | 我们的使用方式 |
|------|------|----------------|
| Week 1 | LLM Programming & Prompt Engineering | ✅ 第一阶段核心 |
| Week 2 | Coding Agents（MCP、Tool Calling） | ✅ 第一阶段核心 |
| Week 3-4 | AI IDEs & Patterns（Claude Code） | ✅ 第一阶段核心 |
| Week 5 | Modern Terminal（Warp） | 选学 |
| Week 6-7 | Testing, Security & Maintenance | ✅ 第五阶段使用 |
| Week 8 | Automated UI & App Building | 选学 |
| Week 9 | Post-Deployment Operations | 选学 |
| Week 10 | Future of AI Software Engineering | 选学 |

### 核心学习资源

- **PPT 幻灯片**：课程官网公开
- **阅读材料**：课程官网公开
- **作业代码**：GitHub 仓库
- **Maven 付费版**：[maven.com](https://maven.com/the-modern-software-developer/ai-course)（可选）

---

## 第一阶段：CS146S Week 1-4（第1-4周）

### Week 1：Prompt Engineering

| 资源 | 类型 | 说明 |
|------|------|------|
| [Prompt Engineering Guide](https://www.promptingguide.ai/zh) | 文档 | 中文指南，必看 |
| [Claude Prompt Engineering](https://docs.anthropic.com/claude/docs/prompt-engineering) | 文档 | Claude 官方指南 |
| [OpenAI Prompt Engineering](https://platform.openai.com/docs/guides/prompt-engineering) | 文档 | OpenAI 官方指南 |
| DeepLearning.AI Prompt 课程 | 视频 | 吴恩达出品，免费 |

### Week 2：Coding Agents & MCP

| 资源 | 类型 | 说明 |
|------|------|------|
| [MCP 官方文档](https://modelcontextprotocol.io) | 文档 | Anthropic 出品，必看 |
| [MCP GitHub](https://github.com/modelcontextprotocol) | 代码 | 官方示例和 SDK |
| [Anthropic Tool Use](https://docs.anthropic.com/claude/docs/tool-use) | 文档 | Claude 工具调用 |
| [OpenAI Function Calling](https://platform.openai.com/docs/guides/function-calling) | 文档 | GPT 工具调用 |

### Week 3-4：AI IDEs & Claude Code

| 资源 | 类型 | 说明 |
|------|------|------|
| [Claude Code 文档](https://docs.anthropic.com/claude-code) | 文档 | 官方使用指南 |
| [Cursor 文档](https://docs.cursor.sh) | 文档 | Cursor IDE 指南 |
| Claude Code 实践 | 实操 | 边用边学 |

### 实践任务

- [ ] 完成 CS146S Week 1-2 作业
- [ ] 熟练使用 Claude Code 进行日常开发
- [ ] 实现一个简单的 Coding Agent
- [ ] 完成 MCP 协议入门实践

---

## 第二阶段：RAG 系统开发（第5-6周）

### 必看课程

| 资源 | 类型 | 链接 | 说明 |
|------|------|------|------|
| Building Applications with Vector Databases | 视频（免费） | DeepLearning.AI | 向量数据库基础 |
| LangChain: Chat with Your Data | 视频（免费） | DeepLearning.AI | RAG 实战 |

### 推荐文档

| 资源 | 说明 |
|------|------|
| [LlamaIndex 官方文档](https://docs.llamaindex.ai) | RAG 框架首选（有中文翻译） |
| [LangChain RAG 文档](https://python.langchain.com/docs/tutorials/rag/) | RAG 教程 |
| [ChromaDB 文档](https://docs.trychroma.com) | 向量数据库 |

### 实践任务

- [ ] 实现文档加载 + 分块 + 向量化
- [ ] 实现相似度检索
- [ ] 完成项目一：智能知识库助手

---

## 第三阶段：Agent 开发（第7-8周）

### 必看课程

| 资源 | 类型 | 链接 | 说明 |
|------|------|------|------|
| Functions, Tools and Agents with LangChain | 视频（免费） | DeepLearning.AI | 必看 |
| AI Agents in LangGraph | 视频（免费） | DeepLearning.AI | Agent 开发 |

### 推荐文档

| 资源 | 说明 |
|------|------|
| [LangGraph 文档](https://langchain-ai.github.io/langgraph/) | Agent 框架 |
| [Anthropic Tool Use](https://docs.anthropic.com/claude/docs/tool-use) | Claude 工具调用 |

### 实践任务

- [ ] 实现多工具 Agent
- [ ] 完成项目二：多工具协作 Agent

---

## 第四阶段：框架精通（第9-10周）

### 推荐文档

| 资源 | 说明 |
|------|------|
| [LangChain 官方文档](https://python.langchain.com/docs/) | 系统学习 |
| [LangGraph 官方文档](https://langchain-ai.github.io/langgraph/) | Agent 进阶 |
| [LlamaIndex 官方文档](https://docs.llamaindex.ai) | RAG 进阶 |

### 实践任务

- [ ] 阅读框架核心源码
- [ ] 实现自定义 Chain/Tool/Agent

---

## 第五阶段：测试、安全与部署（第11-12周）

### CS146S Week 6-7：测试与安全

| 资源 | 类型 | 说明 |
|------|------|------|
| CS146S PPT: Testing | 幻灯片 | 课程官网 |
| CS146S PPT: Security | 幻灯片 | 课程官网 |
| [Semgrep 文档](https://semgrep.dev/docs) | 文档 | SAST 工具 |

### 部署相关

| 资源 | 说明 |
|------|------|
| [vLLM 文档](https://docs.vllm.ai) | 高性能推理 |
| [Ollama 文档](https://ollama.ai) | 本地模型运行 |

### 实践任务

- [ ] AI 代码审查实践
- [ ] Prompt Injection 防御
- [ ] 本地部署开源模型（Ollama）
- [ ] 云端部署 API 服务

---

## 第六阶段：综合实战与求职（第13-16周）

### 实践任务

- [ ] 完成项目三：个人 AI 助手
- [ ] 整理作品集
- [ ] 写技术博客
- [ ] 录 Demo 视频

---

## 常用资源汇总

### 免费课程平台

- [DeepLearning.AI](https://www.deeplearning.ai/short-courses/) - 最推荐，短期课程
- [HuggingFace Course](https://huggingface.co/learn) - NLP/LLM 课程

### 官方文档

| 资源 | 链接 |
|------|------|
| OpenAI API | [platform.openai.com/docs](https://platform.openai.com/docs) |
| Claude API | [docs.anthropic.com](https://docs.anthropic.com) |
| MCP 协议 | [modelcontextprotocol.io](https://modelcontextprotocol.io) |

### 工具

| 工具 | 用途 |
|------|------|
| Claude Code | AI 辅助开发 |
| Cursor | AI IDE |
| 翻译插件 | 沉浸式翻译（Chrome） |

---

## API 费用参考

| 服务 | 价格 | 说明 |
|------|------|------|
| OpenAI GPT-4o | $2.5/1M tokens | 主力模型 |
| Claude 3.5 Sonnet | $3/1M tokens | 主力模型 |
| 通义千问 | 0.008元/千tokens | 国内备选 |
| Embedding | $0.02/1M tokens | 向量化 |

**预估**：每月 API 费用 $20-50，学习阶段够用
