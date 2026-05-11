# 项目说明

> 项目：日知 (RiZhi)
> 版本：v0.56.0
> 状态：进行中（R056）
> 活跃分支：chore/R056-brand-rename-to-rizhi

## 当前范围

R056 品牌重命名：将项目名称统一为「日知」。涵盖 Flutter 包名重构、平台配置、后端/前端/部署/文档展示名称统一。

### 核心目标

| # | 改进项 | 范围 | 优先级 |
|---|--------|------|--------|
| 1 | Flutter 包名重构 | growth_assistant → rizhi，72+ 导入路径替换 | P0 |
| 2 | Mobile 展示名称 | Android/iOS/Web 显示名统一为「日知」 | P1 |
| 3 | 后端+前端+部署+文档 | 所有面向用户/开发者的名称统一 | P1 |
| 4 | 质量收口 | 全量构建和测试验证 | P2 |

### Phase 1: 包名重构（1 task）

1. **S01 Flutter 包名 + 导入路径重构**：pubspec.yaml、Android/iOS 配置、全量 import 替换

### Phase 2: 展示名称统一（2 tasks）

2. **F01 Mobile 展示名称统一**：Android strings.xml、iOS Info.plist、AppBar 标题
3. **S02 后端+前端+部署+文档 名称统一**：agent prompts、index.html、deploy 脚本、文档

### Phase 3: 质量收口（1 task）

4. **S03 R056 质量收口**：flutter analyze + flutter test + pytest + npm build

## 命名规范

| 上下文 | 新名称 | 旧名称 |
|--------|--------|--------|
| 产品名（中文） | 日知 | （旧名已替换） |
| 产品名（英文） | RiZhi | （旧名已替换） |
| Flutter 包名 | rizhi | growth_assistant |
| Android applicationId | com.rizhi.app | com.growth.growth_assistant |
| iOS bundle identifier | com.rizhi.app | com.growth.growthAssistant |
| Web app name | rizhi | growth_assistant |

## 技术约束

- 用户数据文件（data/、.data-backup/）不动
- _archive/ 归档文件是历史快照，不动
- 只改代码、配置、文档中的展示名称和包名
- 仓库名 personal-growth-assistant 不在本次范围内（需 GitHub 操作）

## 统计

| 指标 | 值 |
|------|-----|
| 总任务数 | 4 |
| P0 | 1（S01）|
| P1 | 2（F01/S02）|
| P2 | 1（S03）|

## workflow

- mode: B（Codex Plugin 自动审核）
- runtime: skill_orchestrated
- review_provider: codex_plugin
- audit_provider: codex_plugin
- risk_provider: codex_plugin
