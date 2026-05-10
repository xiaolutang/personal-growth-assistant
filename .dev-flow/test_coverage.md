# 测试覆盖清单

## R056: 品牌重命名（个人助手 → 日知）

| Module | Task IDs | Test Type | Required Scenarios | Status | Gaps |
|--------|----------|-----------|--------------------|--------|------|
| Flutter 包名重构 | S01 | config+L1 | flutter analyze 0 error/Android 构建启动/iOS 构建启动/Web PWA 名称 | pending | — |
| Mobile 展示名称 | F01 | F2 | Android app_name=日知/iOS CFBundleDisplayName=日知/Settings 页展示日知 | pending | — |
| 后端+前端+部署+文档 | S02 | L1 | 后端 main.py/agent prompts 使用日知/前端 build 通过/部署脚本使用日知 | pending | — |
| 质量收口 | S03 | integration | flutter analyze+test/pytest/npm build+lint+test/全仓 grep 清零 | pending | — |

### S01 配置风险测试（config risk）

| 场景 | 验证方式 | 优先级 |
|------|---------|--------|
| import 路径全量替换后 analyze 通过 | `flutter analyze` | P0 |
| Android applicationId 变更后 APK 可安装启动 | 手动/CI | P1 |
| iOS bundle id 变更后编译运行 | 手动/CI | P1 |
| Web manifest 变更后 PWA 名称展示 | `flutter build web` + 检查 | P1 |
| 首次安装后启动不崩溃 | 手动 | P1 |
