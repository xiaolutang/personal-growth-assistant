# Personal Growth Assistant - Design System

设计规范文档，确保 UI 一致性。

---

## 1. 设计原则

- **简约**：去除不必要的装饰，聚焦内容
- **专业**：职场人士工具，不花哨
- **高效**：减少点击，快速完成任务
- **一致**：相同功能，相同交互

---

## 2. 配色方案

### 主色板

| 名称 | 色值 | CSS 变量 | 用途 |
|------|------|----------|------|
| 主背景 | `#FFFFFF` | `--background` | 页面背景 |
| 次背景 | `#F9FAFB` | `--secondary` | 卡片、分区背景 |
| 主文字 | `#111827` | `--foreground` | 标题、正文 |
| 次文字 | `#6B7280` | `--muted-foreground` | 描述、辅助文字 |
| 主色调 | `#6366F1` | `--primary` | 按钮、链接、强调 |
| 主色调悬停 | `#4F46E5` | `--primary-hover` | 按钮 hover 状态 |
| 边框 | `#E5E7EB` | `--border` | 分割线、边框 |
| 成功 | `#10B981` | `--success` | 完成状态、成功提示 |
| 警告 | `#F59E0B` | `--warning` | 进行中状态、警告 |
| 错误 | `#EF4444` | `--destructive` | 错误、删除 |

### 语义色

| 状态 | 颜色 | 使用场景 |
|------|------|----------|
| 待开始 | `#6B7280` (灰色) | 任务未开始 |
| 进行中 | `#F59E0B` (橙色) | 任务进行中 |
| 已完成 | `#10B981` (绿色) | 任务完成 |

---

## 3. 字体

### 字体族

```css
font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
```

### 字号规范

| 级别 | 大小 | 行高 | 字重 | 用途 |
|------|------|------|------|------|
| H1 | 24px | 32px | 600 | 页面标题 |
| H2 | 20px | 28px | 600 | 区块标题 |
| H3 | 16px | 24px | 600 | 卡片标题 |
| Body | 14px | 20px | 400 | 正文 |
| Small | 12px | 16px | 400 | 辅助文字、标签 |

---

## 4. 间距系统

基于 **4px** 基准，使用 Tailwind 默认间距：

| Token | 值 | 用途 |
|-------|-----|------|
| 1 | 4px | 紧凑元素间距 |
| 2 | 8px | 图标与文字间距 |
| 3 | 12px | 列表项间距 |
| 4 | 16px | 组件内间距（默认） |
| 5 | 20px | 区块间距 |
| 6 | 24px | 卡片内间距 |
| 8 | 32px | 页面区块间距 |
| 10 | 40px | 大区块间距 |
| 12 | 48px | 页面顶部间距 |

---

## 5. 圆角

| 元素 | 圆角 | Tailwind |
|------|------|----------|
| 按钮 | 8px | `rounded-lg` |
| 输入框 | 8px | `rounded-lg` |
| 卡片 | 12px | `rounded-xl` |
| 标签/徽章 | 9999px | `rounded-full` |

---

## 6. 阴影

| 级别 | 值 | 用途 |
|------|-----|------|
| sm | `0 1px 2px rgba(0,0,0,0.05)` | 轻微浮起 |
| DEFAULT | `0 1px 3px rgba(0,0,0,0.1)` | 卡片默认 |
| md | `0 4px 6px rgba(0,0,0,0.1)` | 悬浮卡片 |

---

## 7. 组件规范

### 按钮

| 类型 | 样式 |
|------|------|
| 主按钮 | 背景主色 + 白字 + hover 变深 |
| 次按钮 | 白底 + 边框 + hover 变灰底 |
| 文字按钮 | 无背景 + 主色字 + hover 有底色 |

**尺寸**：
- 默认：h-10 px-4 text-sm
- 小：h-9 px-3 text-xs
- 图标：h-10 w-10

### 输入框

- 高度：h-10 (40px)
- 圆角：rounded-lg (8px)
- 边框：1px solid border
- 聚焦：ring-2 ring-primary/20

### 卡片

- 背景：background (#FFFFFF)
- 圆角：rounded-xl (12px)
- 边框：border (1px)
- 内间距：p-6 (24px)

---

## 8. 图标

使用 **Lucide React** 图标库

常用图标：
- 任务：`CheckCircle` / `Circle`
- 灵感：`Lightbulb`
- 笔记：`FileText`
- 项目：`Folder`
- 添加：`Plus`
- 设置：`Settings`
- 发送：`Send`
- 加载：`Loader2`

---

## 9. 响应式断点

| 断点 | 宽度 | Tailwind |
|------|------|----------|
| sm | 640px | `sm:` |
| md | 768px | `md:` |
| lg | 1024px | `lg:` |
| xl | 1280px | `xl:` |

**布局策略**：侧边栏固定宽度 256px (w-64)

---

## 10. 无障碍

- 颜色对比度 ≥ 4.5:1（正文）
- 可聚焦元素有 visible focus ring
- 图标按钮有 aria-label
