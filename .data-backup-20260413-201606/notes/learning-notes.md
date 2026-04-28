# 学习笔记与想法

> 记录学习过程中的想法、心得、疑问和灵感

---

## 2026-03-08 Week 2 Day 1：FastAPI 基础概念复盘 #FastAPI

### 1. FastAPI 是什么？为什么选它？

**定位**：现代 Python Web 框架，专门用来写 API。

**与其他框架对比**：

| 框架 | 定位 | 性能 | 异步 | 适合场景 |
|------|------|------|------|----------|
| Django | 全栈框架 | 中 | ❌ | 快速出完整网站 |
| Flask | 微框架 | 中 | ❌ | 小项目、原型 |
| **FastAPI** | API 专用 | 高 | ✅ | API 服务、AI 后端 |

**AI 开发选 FastAPI 的原因**：
1. **异步支持** - 调用大模型不阻塞，并发能力强
2. **自动文档** - Swagger UI 自动生成，省沟通成本
3. **Pydantic 集成** - 数据验证自动搞定
4. **性能好** - 接近 Go/Node.js

---

### 2. Pydantic 与 FastAPI 的关系

**Pydantic**：用 Python 类型注解自动做数据验证和转换。

**关系**：Pydantic 是 FastAPI 的**核心数据验证引擎**，不只是依赖库。

```
请求进来 → FastAPI 用 Pydantic 解析 → 验证 + 转换 → 传给你的函数
                ↓
         同时用 Pydantic 模型生成 Swagger 文档
```

**核心价值**：
- 类型验证自动完成
- JSON ↔ Python 对象自动转换
- 文档自动生成

---

### 3. 路由参数 vs 查询参数

| 类型 | 作用 | 判断标准 |
|------|------|----------|
| **路由参数** | 标识**资源**（哪个） | 定位唯一的东西 |
| **查询参数** | **过滤/配置**（怎么返回） | 可选的附加条件 |

**例子**：
```
/users/123           ← 路由参数，标识"哪个用户"
/users?limit=10      ← 查询参数，配置"返回多少个"
/articles/456        ← 路由参数，标识"哪篇文章"
/articles?category=tech  ← 查询参数，过滤类别
```

**判断口诀**：找"谁"用路由参数，"怎么找"用查询参数。

---

### 4. async/await

**核心概念**：
- `async def` → 声明"我可能会 await"
- `await` → 真正的"让出控制权，去处理别的"

**什么时候用**：
| 场景 | 用什么 | 原因 |
|------|--------|------|
| 调用大模型 API | `async def` + `await` | 网络请求，耗时 |
| 数据库操作 | `async def` + 异步驱动 | IO 等待 |
| 纯计算 | `def` 或 `async def` 都行 | 没有等待 |

---

### 5. response_model

**完整作用**：

| 作用 | 说明 |
|------|------|
| **过滤输出** | 只返回模型定义的字段，其他字段丢弃 |
| **文档生成** | Swagger 显示正确的响应结构 |
| **验证输出** | 确保返回数据符合模型定义 |
| **格式转换** | datetime 等类型自动转成 JSON 兼容格式 |

**例子**：
```python
class UserResponse(BaseModel):
    id: int
    name: str
    # 没有 password 字段

@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int):
    user = {"id": 1, "name": "张三", "password": "secret123"}
    return user  # password 会被过滤掉
```

---

### 总结：FastAPI 数据流

```
请求 → Pydantic 验证输入 → 业务逻辑 → response_model 过滤输出 → 响应
```

**两边都兜住，API 才安全。**

---

## 2026-03-04 Git Worktree 问题 #疑问

**问题**: worktree 如何工作?

---

## 2026-03-04 Claude Code Skill 问题 #疑问

**问题**:
1. Skill 的作用是什么?
2. 什么时候应该用 Skill?
3. Skill 应该怎么写?
4. Skill 和 Agent 有什么区别? 什么时候应该使用 Agent，什么时候应该使用 Skill?
5. Skill 和 Agent 可以交替工作吗? 如何协作?

---

## 2026-03-04 OpenAI 官方 Prompt Engineering 指南

> 来源：https://platform.openai.com/docs/guides/prompt-engineering

### 一、消息角色（Message Roles）

| 角色 | 说明 | 优先级 |
|------|------|--------|
| `developer` | 应用开发者提供的指令 | 最高 |
| `user` | 用户提供的内容 | 中等 |
| `assistant` | 模型生成的回复 | - |

**类比理解**：
- `developer` 消息 = 函数定义（系统规则）
- `user` 消息 = 函数参数（具体输入）

---

### 二、提示词结构（推荐顺序）

```
1. Identity（身份）     - 定义角色、沟通风格、目标
2. Instructions（指令） - 规则、做什么、不做什么
3. Examples（示例）     - 输入输出样例
4. Context（上下文）    - 额外信息、私有数据
```

---

### 三、核心技巧

#### 1. Few-shot Learning（少样本学习）
通过示例让模型学会模式：
```markdown
# Examples

<product_review id="example-1">
I absolutely love this headphones!
</product_review>

<assistant_response id="example-1">
Positive
</assistant_response>
```

#### 2. 使用 Markdown + XML 标签
- Markdown 标题/列表 → 划分逻辑区块
- XML 标签 → 标记内容边界

#### 3. GPT 模型 vs 推理模型

| 模型类型 | 特点 | 提示策略 |
|----------|------|----------|
| GPT 模型 | 快、便宜 | 需要精确、详细的指令 |
| 推理模型 | 慢、强 | 只需高层目标，自己推导细节 |

**类比**：
- GPT 模型 = 初级员工（需要明确指令）
- 推理模型 = 资深同事（给目标即可）

---

### 四、GPT-5 编码任务最佳实践

1. **明确角色和工作流程** - 定义 agent 的职责
2. **要求测试和验证** - 让模型测试自己的代码
3. **提供工具使用示例** - 给出具体的调用示例
4. **设置 Markdown 输出标准** - 规范输出格式

**推荐库**：
- 样式/UI：Tailwind CSS, shadcn/ui, Radix Themes
- 图标：Lucide, Material Symbols, Heroicons
- 动画：Motion

---

### 五、Agent 任务提示词模板

```markdown
Remember, you are an agent - please keep going until the user's
query is completely resolved. Decompose the user's query into
all required sub-requests, and confirm that each is completed.
Do not stop after completing only part of the request.
```

---

### 六、完整示例：代码生成助手

```markdown
# Identity

You are coding assistant that helps enforce the use of snake case
variables in JavaScript code, and writing code that will run in
Internet Explorer version 6.

# Instructions

* When defining variables, use snake case names (e.g. my_variable)
  instead of camel case names (e.g. myVariable).
* To support old browsers, declare variables using the older
  "var" keyword.
* Do not give responses with Markdown formatting, just return
  the code as requested.

# Examples

<user_query>
How do I declare a string variable for a first name?
</user_query>

<assistant_response>
var first_name = "Anna";
</assistant_response>
```

---

### 七、六大核心策略（经典版）

1. **写清楚指令 (Write clear instructions)** - 指令越明确越好
2. **提供参考文本** - 帮助模型理解上下文
3. **拆分复杂任务** - 分解为简单子任务
4. **给模型思考时间** - 让模型逐步推理
5. **有效使用外部工具** - 结合其他资源
6. **系统性测试变更** - 持续优化验证

---

## 2026-03-03 Day 2：工作原则与Prompt优化

### 工作原则 - 让自己不可替代

**核心五问**：
1. **关键结果推进** - 我今天有没有把关键结果往前推？
2. **结果可视化** - 用结果可视化，让产出可见
3. **本周推进** - 卡点是什么，需要什么资源？
4. **优先级谈判** - 让自己去做更正确、更有结果的事情
5. **不可替代性** - 掌握关键流程、关键工具，进入关键链路

**如何让自己不可替代**：
- 掌握关键流程
- 掌握关键工具
- 进入关键链路
- 触达核心业务

> 核心逻辑：价值 = 影响力 × 不可替代性

---

### Prompt优化与Chain-of-Thought

### 快速入门模版

#### 一、最少且必备的知识（覆盖 80% 场景）

**1. 结构化 Prompt 模板（必会）**
```
# 角色
你是 [具体角色]，擅长 [核心能力]

# 任务
请 [具体任务]

# 上下文
背景：[相关背景]
输入：[需要处理的内容]

# 约束
- 格式：[输出格式]
- 长度：[字数/条数]
- 风格：[语气/风格]

# 示例
输入：[示例输入]
输出：[示例输出]
```

**2. Chain-of-Thought 三种形式**
| 形式 | 用法 | 场景 |
|------|------|------|
| Zero-shot CoT | 加"让我们一步步思考" | 通用 |
| Few-shot CoT | 给带推理过程的示例 | 复杂推理 |
| Self-Consistency | 多次推理取共识 | 高准确度 |

**3. 核心公式**
```
好的输出 = 清晰的指令 + 充足的上下文 + 明确的约束
```

---

#### 二、新手常见误区（可延迟学习）

| 误区 | 为什么可延迟 | 不学的影响 |
|------|-------------|-----------|
| 复杂的 Prompt 框架 | 先掌握基础模板，框架是优化手段 | 无，基础模板够用 |
| 所有场景都用 CoT | 简单问题不需要，浪费 token | 无，按需使用即可 |
| 追求"完美 Prompt" | Prompt 需要迭代，一次写不完美 | 无，快速迭代更高效 |

---

#### 三、今日实战任务

**任务1：代码注释生成器**
```python
# 测试代码
def quick_sort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quick_sort(left) + middle + quick_sort(right)
```

**要求输出**：
```python
def quick_sort(arr):
    """
    功能：[一句话描述]
    参数：arr - [参数说明]
    返回：[返回值说明]
    时间复杂度：O(n log n)
    """
```

---

**任务2：Bug 分析器（CoT 实战）**
```python
# 测试代码
def calculate_average(numbers):
    total = 0
    for num in numbers:
        total += num
    return total / len(numbers)
```

**要求**：使用 Zero-shot CoT，输出包含：问题识别 → 原因分析 → 修复方案

---

**任务3：Python → Kotlin 转换器**
```python
data = {"name": "Alice", "age": 25, "city": "Beijing"}
for key, value in data.items():
    print(f"{key}: {value}")
```

**要求**：输出 Kotlin 代码，保持风格一致

---

#### 四、检验标准

完成今天的学习后，你应该能：
- [ ] 5 分钟内写出一个结构化 Prompt
- [ ] 判断一个问题是否需要 CoT
- [ ] 让输出格式稳定统一

---

### 今日总结

> 完成后填写

**学到的核心点**：
1.
2.
3.

---

## 2025-03-02

### Prompt Engineering 基础学习

**学习内容**: 提示词工程基础 - 基本概念、要素、技巧、示例

**专题笔记**: [prompt-engineering.md](./prompt-engineering.md)

**收获**:
- 提示词四要素：指令、上下文、输入数据、输出指示
- 核心技巧：从简单开始、具体明确、正向表述
- 应用场景：概括、提取、问答、分类、对话、代码、推理

---

## 2025-03-01

### 借助 AI 快速进入一个行业的标准操作提示词

**背景**: 这是一个通用的方法论，帮助快速进入任何新领域

**模板**：

```
你可以把我当作一个完全的新手，我想要快速转行到【目标领域】，请你根据 28 原则：

1. 告诉我这个领域最少且必备的知识，帮我列举 3-5 条最关键的知识，要求能涵盖这个领域 80% 的使用场景。别告诉我这些概念为什么重要，对于很重要但在实操过程中一定会接触到的知识没有必要列入其中。

2. 告诉我作为新手经常会陷入哪些低效的或完全没有必要现在就学习的误区，帮我列出 3 条看起来很基础但实际上完全可以延迟学习的关键概念，告诉我它为什么可以被延迟，暂时不学习它会造成什么样的影响。

3. 帮我设计一个最小可行的任务，让我在 3 天之内完成，通过这个任务建立信心。
```

**使用场景**：
- 转行到新领域
- 学习新技术栈
- 快速上手新工具

**核心逻辑**：
1. **28 原则抓核心** - 先学 20% 的知识覆盖 80% 场景
2. **避坑指南** - 跳过看起来重要但可以延迟的内容
3. **最小可行任务** - 3 天内做出东西，建立信心

**后续复用**：
- 把【目标领域】替换成任何想进入的领域
- 可根据领域特点调整天数（3-7 天）

---

## 2025-02-28

### 文档记录机制的想法

**背景**: 希望在 Claude Code 对话时能够自动整理内容到文档中

**想法**:
- 分离 todo.md 和 notes.md，职责清晰
- 保留 plan.md 作为主计划，增量更新
- 使用 Markdown 复选框，兼容 GitHub 渲染

**下一步**:
- [x] 创建 todo.md 和 notes.md 文件
- [ ] 更新 plan.md 添加进度概览
- [ ] 更新 CLAUDE.md 添加记录机制定义

---

## 标签索引

- #RAG - RAG 相关笔记
- #Prompt - [Prompt Engineering 专题](./prompt-engineering.md)
- #LangChain - LangChain 框架
- #思考 - 深度思考类笔记
- #疑问 - 待解决的问题

---

## 专题笔记索引

| 主题 | 文件 | 进度 |
|------|------|------|
| Prompt Engineering | [prompt-engineering.md](./prompt-engineering.md) | 进行中 |
