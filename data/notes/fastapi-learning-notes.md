# FastAPI 学习笔记

> 从入门到进阶的完整指南

---

## 一、为什么选择 FastAPI

| 优势 | 说明 |
|------|------|
| **性能高** | 接近 Go/Node，比 Flask/Django 快 |
| **简单** | 几行代码就能跑起来 |
| **自动文档** | 写完代码自动生成 Swagger UI（`/docs`） |
| **类型校验** | Pydantic 自动校验请求/响应 |
| **异步支持** | 原生 async/await，适合 LLM 调用 |
| **生态** | Python AI 生态首选框架 |

**一句话**：Python 里做 API，FastAPI 是目前最优解。

---

## 二、快速开始

### 安装

```bash
pip install fastapi uvicorn
```

### 最简示例

```python
# main.py
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def index():
    return {"msg": "Hello World"}

@app.get("/users/{id}")
def get_user(id: int):
    return {"id": id}
```

### 运行

```bash
uvicorn main:app --reload
```

### 访问

- API: http://localhost:8000
- Swagger 文档: http://localhost:8000/docs
- ReDoc 文档: http://localhost:8000/redoc

---

## 三、路由（Routing）

### 基本路由

```python
@app.get("/users")           # GET 请求
@app.post("/users")          # POST 请求
@app.put("/users/{id}")      # PUT 请求
@app.delete("/users/{id}")   # DELETE 请求
@app.patch("/users/{id}")    # PATCH 请求
```

### 路径参数

```python
@app.get("/users/{id}")
def get_user(id: int):  # 自动转换为 int
    return {"id": id}

# 访问: /users/123
# 返回: {"id": 123}
```

### 查询参数

```python
@app.get("/users")
def list_users(skip: int = 0, limit: int = 10):
    return {"skip": skip, "limit": limit}

# 访问: /users?skip=0&limit=20
# 返回: {"skip": 0, "limit": 20}
```

### 路径参数 + 查询参数

```python
@app.get("/users/{user_id}/items/{item_id}")
def get_item(user_id: int, item_id: str, q: str | None = None):
    item = {"user_id": user_id, "item_id": item_id}
    if q:
        item["q"] = q
    return item

# 访问: /users/1/items/foo?q=bar
# 返回: {"user_id": 1, "item_id": "foo", "q": "bar"}
```

---

## 四、请求体（Request Body）

### Pydantic 模型

```python
from pydantic import BaseModel
from typing import Optional

class User(BaseModel):
    name: str
    age: int
    email: str | None = None  # 可选字段
    is_active: bool = True    # 默认值
```

### POST 请求

```python
@app.post("/users")
def create_user(user: User):
    return {
        "name": user.name,
        "age": user.age,
        "email": user.email
    }
```

**请求示例**：
```bash
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{"name": "Tom", "age": 25}'
```

**响应**：
```json
{
  "name": "Tom",
  "age": 25,
  "email": null
}
```

### 请求体 + 路径参数 + 查询参数

```python
@app.put("/users/{user_id}")
def update_user(user_id: int, user: User, q: str | None = None):
    result = {"user_id": user_id, **user.model_dump()}
    if q:
        result["q"] = q
    return result
```

---

## 五、响应模型（response_model）

### 基本使用

```python
class UserOut(BaseModel):
    id: int
    name: str
    # 不包含 password

@app.get("/users/{id}", response_model=UserOut)
def get_user(id: int):
    # 假设从数据库获取的用户包含 password
    user = {"id": id, "name": "Tom", "password": "123456"}
    return user  # 自动过滤掉 password
```

**响应**：
```json
{
  "id": 1,
  "name": "Tom"
}
```

### 输入输出模型分离

```python
class UserIn(BaseModel):
    name: str
    password: str

class UserOut(BaseModel):
    id: int
    name: str

@app.post("/users", response_model=UserOut)
def create_user(user: UserIn):
    # 存入数据库（含 password）
    saved_user = save_to_db(user)
    # 返回时过滤掉 password
    return saved_user
```

### 常用参数

```python
@app.get(
    "/users",
    response_model=list[UserOut],
    response_model_exclude_unset=True,  # 只返回设置过的字段
    response_model_exclude={"id"},       # 排除 id 字段
)
def list_users():
    ...
```

---

## 六、依赖注入（Dependency Injection）

### 基本概念

**问题**：多个接口需要共享逻辑（数据库连接、认证等），如何复用？

**解决**：FastAPI 的依赖注入系统

### 基本语法

```python
from fastapi import Depends

def common_params(q: str | None = None, skip: int = 0, limit: int = 100):
    return {"q": q, "skip": skip, "limit": limit}

@app.get("/items/")
def read_items(commons: dict = Depends(common_params)):
    return commons

@app.get("/users/")
def read_users(commons: dict = Depends(common_params)):
    return commons
```

### 数据库连接示例

```python
def get_db():
    db = Database()
    try:
        yield db  # yield = 交给调用方
    finally:
        db.close()  # 请求结束后执行清理

@app.get("/users")
def list_users(db = Depends(get_db)):
    return db.query("SELECT * FROM users")
```

**执行流程**：
```
请求进来 → FastAPI 调用 get_db() → yield 返回 db
    → 执行 list_users() → finally 关闭 db
```

### 依赖嵌套

```python
def get_token_header(x_token: str = Header()):
    if x_token != "fake-super-secret-token":
        raise HTTPException(status_code=400, detail="Invalid token")
    return x_token

def get_current_user(token: str = Depends(get_token_header)):
    # 验证 token，返回用户
    return {"id": 1, "name": "Tom"}

@app.get("/users/me")
def read_users_me(user = Depends(get_current_user)):
    return user
```

### 类作为依赖

```python
class CommonQueryParams:
    def __init__(self, q: str | None = None, skip: int = 0, limit: int = 100):
        self.q = q
        self.skip = skip
        self.limit = limit

@app.get("/items/")
def read_items(commons: CommonQueryParams = Depends()):
    return commons
```

### 什么时候用依赖注入？

| 情况 | 建议 |
|------|------|
| 个人项目、Demo | 可以不用 |
| 需要单元测试 | **推荐使用**，方便 mock |
| 团队项目 | **推荐使用**，规范统一 |
| 复杂依赖链 | **推荐使用**，自动管理 |

---

## 七、错误处理（Error Handling）

### HTTPException

```python
from fastapi import HTTPException

@app.get("/users/{id}")
def get_user(id: int):
    if id <= 0:
        raise HTTPException(status_code=400, detail="ID 必须大于 0")

    user = db.get(id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    return user
```

**响应示例**：
```json
{
  "detail": "用户不存在"
}
```

**状态码**：404

### HTTP 状态码规范

| 状态码 | 含义 | 使用场景 |
|--------|------|----------|
| 200 | 成功 | 正常返回 |
| 201 | 已创建 | POST 创建资源成功 |
| 400 | 请求错误 | 参数不对 |
| 401 | 未认证 | 没登录 |
| 403 | 禁止访问 | 没权限 |
| 404 | 不存在 | 资源找不到 |
| 422 | 验证失败 | Pydantic 校验失败（自动） |
| 500 | 服务器错误 | 代码 bug |
| 503 | 服务不可用 | 服务未初始化 |

### 自定义异常处理器

```python
from fastapi import Request
from fastapi.responses import JSONResponse

class BusinessException(Exception):
    def __init__(self, code: str, msg: str):
        self.code = code
        self.msg = msg

@app.exception_handler(BusinessException)
def business_exception_handler(request: Request, exc: BusinessException):
    return JSONResponse(
        status_code=400,
        content={
            "code": exc.code,
            "msg": exc.msg,
            "type": "business_error"
        }
    )

# 使用
@app.get("/items/{id}")
def get_item(id: int):
    if id > 100:
        raise BusinessException("LIMIT_EXCEEDED", "超过限制")
    return {"id": id}
```

---

## 八、表单和文件

### 表单数据

```python
from fastapi import Form

@app.post("/login")
def login(username: str = Form(), password: str = Form()):
    return {"username": username}
```

### 文件上传

```python
from fastapi import UploadFile, File

@app.post("/upload")
async def upload_file(file: UploadFile = File()):
    contents = await file.read()
    return {
        "filename": file.filename,
        "size": len(contents)
    }
```

### 多文件上传

```python
@app.post("/upload-many")
async def upload_files(files: list[UploadFile] = File()):
    return {"count": len(files)}
```

---

## 九、后台任务（Background Tasks）

**作用**：返回响应后执行耗时操作，不阻塞用户

```python
from fastapi import BackgroundTasks

def send_email(email: str, message: str):
    # 模拟发送邮件（耗时操作）
    import time
    time.sleep(5)
    print(f"Email sent to {email}: {message}")

@app.post("/send-notification/{email}")
async def send_notification(email: str, background_tasks: BackgroundTasks):
    # 添加后台任务
    background_tasks.add_task(send_email, email, "Hello!")

    # 立即返回响应
    return {"message": "Notification sent, email will be delivered soon"}
```

---

## 十、自动文档

### Swagger UI（/docs）

- 交互式 API 文档
- 可以直接在网页上测试 API
- 自动生成

### ReDoc（/redoc）

- 更美观的文档界面
- 适合展示

### OpenAPI JSON（/openapi.json）

- 原始 OpenAPI 规范
- 可导入 Postman 等工具

### 自定义文档

```python
app = FastAPI(
    title="My API",
    description="API 描述",
    version="1.0.0",
    docs_url="/documentation",  # 自定义 Swagger 路径
    redoc_url="/redoc-docs",    # 自定义 ReDoc 路径
)
```

---

## 十一、静态文件和模板

### 静态文件

```python
from fastapi.staticfiles import StaticFiles

app.mount("/static", StaticFiles(directory="static"), name="static")
# 访问: /static/style.css
```

### HTML 模板（需要 Jinja2）

```python
from fastapi import Request
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")

@app.get("/page")
def page(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "title": "Hello"}
    )
```

---

## 十二、CORS 跨域

```python
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # 允许的域名
    allow_credentials=True,
    allow_methods=["*"],           # 允许的方法
    allow_headers=["*"],           # 允许的头
)
```

---

## 十三、生命周期事件

### 启动和关闭

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行
    print("Application starting...")
    yield
    # 关闭时执行
    print("Application shutting down...")

app = FastAPI(lifespan=lifespan)
```

### 实际应用：初始化连接

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动：初始化数据库连接
    app.state.db = await connect_to_db()
    yield
    # 关闭：断开连接
    await app.state.db.disconnect()
```

---

## 十四、实战：完整的 CRUD 示例

```python
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="User API")

# 模拟数据库
fake_db: dict[int, dict] = {}

# 模型
class UserCreate(BaseModel):
    name: str
    email: str

class UserOut(BaseModel):
    id: int
    name: str
    email: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None

# 依赖
def get_user_or_404(user_id: int):
    if user_id not in fake_db:
        raise HTTPException(status_code=404, detail="用户不存在")
    return fake_db[user_id]

# CRUD
@app.post("/users", response_model=UserOut, status_code=201)
def create_user(user: UserCreate):
    user_id = len(fake_db) + 1
    fake_db[user_id] = {"id": user_id, **user.model_dump()}
    return fake_db[user_id]

@app.get("/users", response_model=list[UserOut])
def list_users(skip: int = 0, limit: int = 10):
    return list(fake_db.values())[skip:skip+limit]

@app.get("/users/{user_id}", response_model=UserOut)
def get_user(user = Depends(get_user_or_404)):
    return user

@app.put("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, user_update: UserUpdate):
    user = get_user_or_404(user_id)
    update_data = user_update.model_dump(exclude_unset=True)
    user.update(update_data)
    return user

@app.delete("/users/{user_id}")
def delete_user(user_id: int):
    get_user_or_404(user_id)
    del fake_db[user_id]
    return {"message": "删除成功"}
```

---

## 十五、特性优先级

| 特性 | 重要程度 | 说明 |
|------|---------|------|
| 路由 | ⭐⭐⭐⭐⭐ | 必须掌握 |
| 请求体（Pydantic） | ⭐⭐⭐⭐⭐ | 必须掌握 |
| 自动文档 | ⭐⭐⭐⭐⭐ | 自动生成，用好就行 |
| 响应模型 | ⭐⭐⭐⭐ | 控制输出，推荐使用 |
| 依赖注入 | ⭐⭐⭐⭐ | 测试和复用，推荐使用 |
| 错误处理 | ⭐⭐⭐⭐ | 统一格式，推荐使用 |
| 后台任务 | ⭐⭐⭐ | 特定场景使用 |
| 文件上传 | ⭐⭐ | 需要时再学 |
| 模板渲染 | ⭐⭐ | 前后端分离不太需要 |

---

## 十六、与客户端开发对比

| 概念 | FastAPI | 客户端类比 |
|------|---------|-----------|
| 路由 | `@app.get("/path")` | Retrofit `@GET("/path")` |
| 数据模型 | Pydantic `BaseModel` | Kotlin `data class` |
| 依赖注入 | `Depends()` | Hilt/Koin |
| 异常处理 | `HTTPException` | 自定义 `ApiException` |
| 异步 | `async/await` | Kotlin 协程 |

---

## 参考资料

- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [FastAPI 中文文档](https://fastapi.tiangolo.com/zh/)
- [Pydantic 文档](https://docs.pydantic.dev/)
