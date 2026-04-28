---
id: note-3bbfad9d
type: note
title: Week 2 Day 1：FastAPI 基础概念复盘
status: doing
priority: medium
created_at: '2026-03-08T10:00:00'
updated_at: '2026-03-08T10:00:00'
tags:
- FastAPI
---

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
