# 测试覆盖清单

## R045: 评估 HTML 报告

| Module | Task IDs | Test Type | Required Scenarios | Status | Gaps |
|--------|----------|-----------|--------------------|--------|------|
| 报告数据模型+生成器 | B193 | unit | generate_html_report 合法数据返回非空 HTML/append_history 追加到空/已有 history.json/build_report_data 按 dataset_mode=single/negative/all 聚合正向+负面/escape_for_html 转义引号标签/escape_for_js 序列化含</script>字符串/input 含 HTML 标签不破坏 DOM/agent_reply 含 </script> 不关闭 script/history.json 不存在时自动创建/corrupted history.json 备份旧文件并重建 | pending | L1 |
| HTML 报告模板 | B194 | unit | 模板渲染合法数据不抛异常/生成 HTML 包含全部 7 板块标题/失败用例展示期望 vs 实际/离线时 HTML 文件浏览器打开文字完整/全部通过时显示"全部通过"/无历史数据时趋势显示"首次运行"/single 模式负面板块显示"未运行负面评估"/negative 模式正向统计显示"未运行正向评估"/模板文件不存在时降级 | pending | L1 |
| run_eval 集成 | B195 | unit+integration | 评估完成后生成 HTML 文件/history.json 含 dataset_mode 和通过率/连续两次运行 history.json 有两条记录/--output JSON 兼容性不受影响/single/negative/all 三种 dataset 模式均可生成报告/正向 HTML 展示 agent_reply/负面 HTML 展示 agent_reply/SSE content payload key='content' 验证/默认 report-dir 解析到项目根 data//corrupted history.json 全链路降级仍生成 HTML/metadata 缺失时降级不阻塞 | pending | L1 |

## R043: 架构收敛

| Module | Task IDs | Test Type | Required Scenarios | Status | Gaps |
|--------|----------|-----------|--------------------|--------|------|
| sqlite 拆分 | B177 | unit+startup | 现有 pytest 全量回归/_conn() 上下文管理器正常+异常回滚/连接迁移失败恢复/print 全消除/__import__ 消除/导入路径兼容（from storage.sqlite import SQLiteStorage）/app 启动 bootstrap 兼容 | pending | L1 |
| MCP deps | B178 | unit+auth | MCP handler 通过 service 层创建条目触发完整流程/batch_create 共享 _build_entry_from_args/neo4j=None 防护/auth 失败无效 user_id/deps service 注入失败降级/MCP 单条创建→HTTP 读取一致/MCP 批量创建→HTTP 列表一致/MCP 更新→HTTP 报告 tag_auto 同步 | pending | L1 |
| entry_service deps | B179 | unit | 无 from routers.deps/GoalService setter 注入/reindex_backlinks 功能不变/无循环导入 | pending | L1 |
| knowledge 模型提取 | B180 | unit | 15 个模型正确导出/mastery 计算结果合理/.dict()→.model_dump() | pending | L1 |
| goal_service N+1 | B181 | unit | list_goals 10+ 目标查询 ≤3 次/tag_auto 进度不变/_get_goal_or_error 错误返回 | pending | L1 |
| review_service 模板 | B182 | unit | 日报/周报/月报 JSON 输出与重构前一致/趋势数据结构不变 | pending | L1 |
| entry_service batch | B183 | unit | 20 条 link 查询 ≤2 次/批量存在性检查结果与逐条一致 | pending | L1 |
| sqlite 重复合并 | B184 | unit | 合并后方法输出与原方法一致/边界条件（空 tags/无日期范围）/SQL 趋势聚合与全量拉取结果一致 | pending | L1 |
| api.ts 统一 | F177 | F1 | npm run build/npm run test:run/里程碑 CRUD openapi-fetch/fetchProgressHistory openapi-fetch/fetchRecommendations openapi-fetch（/knowledge/recommendations）/schema 覆盖验证/gen:types 类型验证 | pending | F1 |
| 质量收口 | S44 | L3+smoke | pytest 全量/vitest 全量/npm build/Docker smoke + MCP→HTTP + HTTP→MCP 双向 parity 验证 | pending | L3 |

## R042: Flutter 条目详情交互升级

| Module | Task IDs | Test Type | Required Scenarios | Status | Gaps |
|--------|----------|-----------|--------------------|--------|------|
| API Client 扩展 | F172 | unit | 7 个新增方法正常/PUT 返回 SuccessResponse/POST links 201+400+409/DELETE links 204/direction 422/summary=null/404/500 | pending | L1 |
| Provider 扩展 | F173 | unit | family provider 隔离/嵌套导航/编辑切换/updateEntry 成功后 GET 刷新+invalidate/generateSummary 成功失败 summary=null/loadBacklinks/loadEntryLinks/createLink 400+409/deleteLink 204/searchEntriesForLink | pending | L1 |
| EntryDetail 编辑 | F174 | widget+smoke | 编辑进入/标题内容状态保存/保存失败/未修改 disabled/标题空白超长/标签添加重复/标签删除/invalidate EntryListProvider/首次编辑 smoke | pending | F2 |
| AI 摘要+知识上下文 | F175 | widget+smoke | 摘要生成 loading→展示/503 失败重试/summary=null 禁用按钮/cached=true 直接展示/知识上下文 mastery 映射(beginner/intermediate/advanced/null)/entry_count/空态/网络异常 smoke | pending | F2 |
| 关联+反向引用 | F176 | widget+smoke | 关联列表/删除 204/反向引用/添加关联搜索→选择→创建 201/网络失败/400 自关联/409 重复关联/搜索空结果/搜索空白不触发/relation_type 选择/嵌套导航返回状态恢复/首次添加 smoke | pending | F2 |
| 质量收口 | S43 | integration+smoke | flutter analyze/flutter test/flutter build/pytest/vitest/npm build/Docker smoke | pending | L3 |

## R041: Flutter 页面补齐 + 工程健康

| Module | Task IDs | Test Type | Required Scenarios | Status | Gaps |
|--------|----------|-----------|--------------------|--------|------|
| Priority 后端 | B117 | unit | priority 筛选/排序/默认排序 | completed | — |
| Inbox API 层 | F163 | unit+integration | fetchInbox/createInboxItem/convertCategory/error | completed | — |
| Notes 页面 | F164 | widget+provider | 空态/错误/加载/列表/搜索/预览 | completed | — |
| Inbox 页面 | F167 | widget+provider | 空态/错误/加载/列表/底部输入 | completed | — |
| Review 页面 | F168 | widget+provider | 加载/错误/周期切换/概览卡片/趋势图 | completed | — |
| Goals 页面 | F170 | widget+provider | 空态/错误/加载/列表/进度条/里程碑 | completed | — |
| 路由+导航 | F171 | widget | 5 Tab/更多菜单/5 个菜单项/子路由状态 | completed | — |
| Provider 集成 | F163-F170 | integration | GoalsNotifier CRUD/ReviewNotifier loadAll/NotesNotifier/InboxNotifier + mock HTTP | completed | — |
| 质量收口 | S42 | integration+smoke | pytest 1375/vitest 612/flutter test 310/build/Docker | completed | — |

## R039: Flutter Explore + 工程维护

| Module | Task IDs | Test Type | Required Scenarios | Status | Gaps |
|--------|----------|-----------|--------------------|--------|------|
| 分支清理 | S38 | manual+review | git branch 干净/architecture.md 4-tab/project_spec R039 | pending | L1 |
| Explore API 层 | F151 | unit+smoke | 条目列表 param mapping/搜索 param mapping/删除 404/更新 category/搜索历史去重截断/批量编排/超时/malformed JSON/smoke 完整流程 | pending | L2 |
| Explore 页面框架 | F152 | widget+smoke | 5 Tab 渲染/Tab 过滤(灵感→inbox)/加载态/空态/错误态/条目点击跳转/导航栏 4-tab/smoke 完整路径 | pending | F2 |
| Explore 搜索 | F153 | unit+widget | 搜索触发/历史去重截断/空搜索/空历史/API 失败不记历史/搜索栏UI交互/历史面板显示隐藏/清空搜索恢复Tab | pending | F2 |
| Explore 批量操作 | F154 | unit+widget+smoke | 批量删除成功+确认/批量转分类+分类选择/搜索模式下批量操作/部分失败保留选中+重试/全部失败/0 条禁用/重试成功后退出/多选模式UI进出/smoke 完整批量路径 | pending | F2 |
| 质量收口 | S39 | integration+smoke | pytest/vitest/flutter test/build/Docker | pending | L4 |

## R038: 工程健康收口 + 小功能补齐

| Module | Task IDs | Test Type | Required Scenarios | Status | Gaps |
|--------|----------|-----------|--------------------|--------|------|
| architecture.md 更新 | B108 | review | 版本号正确/R037 内容包含/≤120 行/不变量完整 | pending | L1 |
| .gitignore 修复 | B109 | unit+manual | gitignore 条目正确/git status 干净/pytest+vitest 回归 | pending | L1 |
| plan 文档清理 | S36 | review | api_contracts R037=done+R038=planned/归档快照存在/project_spec R038/feature_map 数据正确 | pending | L1 |
| 笔记模板后端 | B110 | unit | GET 模板列表/category 过滤/POST 带 template_id/POST 不带/无效 template_id/不匹配/category 优先/认证隔离 | pending | L2 |
| 笔记模板前端 | F148 | unit | 模板列表渲染/content 预填/非 note 不显示/默认行为不变/API 失败降级/空列表/category 切换/已有 content 不覆盖 | pending | F2 |
| 成功指标后端 | B111 | unit | POST 存储/user_id 隔离/metadata 可选/401/写入失败不影响/表自动创建/422 无效 event_type/422 非 object metadata | pending | L2 |
| 成功指标前端 | F149 | unit | trackEvent 调用/API 失败静默/6 埋点位置正确/离线丢弃不发请求 | pending | F2 |
| 质量收口 | S37 | integration+smoke | pytest 全量/vitest 全量/build/scripts/test-docker.sh | pending | L4 |
