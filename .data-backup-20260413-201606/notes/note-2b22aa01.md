---
id: note-2b22aa01
type: note
title: Day 2：工作原则与Prompt优化
status: doing
priority: medium
created_at: '2026-03-03T10:00:00'
updated_at: '2026-03-03T10:00:00'
tags:
- Prompt工程
---

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
