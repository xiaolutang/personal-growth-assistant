# R010 性能基线

测量日期：2026-04-16

## 前端 Bundle 大小

| 资源 | 大小 (gzip) |
|------|------------|
| JS (index.js) | 352.55 KB |
| CSS (index.css) | 10.25 KB |
| **总计** | **362.80 KB** |

构建命令：`npm run build --prefix frontend/`

基线门禁建议：总计 < 500 KB gzip

## 后端 API 响应时间

本地环境（macOS, Python 3.13, SQLite），单次测量。

| 端点 | 平均响应时间 | 基线门禁 |
|------|------------|---------|
| GET /health | < 10ms | < 50ms |
| GET /entries (空列表) | < 50ms | < 200ms |
| POST /entries (创建) | < 100ms | < 300ms |
| POST /search (空结果) | < 100ms | < 300ms |

## SSE 首字节延迟

| 端点 | 首字节延迟 | 备注 |
|------|-----------|------|
| POST /chat (force_intent=read) | < 200ms | 跳过意图检测 |

## E2E 测试性能

| 测试文件 | 测试数 | 耗时 |
|---------|-------|------|
| infrastructure.spec.ts | 4 | ~15s |
| auth.spec.ts | 6 | ~50s |
| entries.spec.ts | 4 | ~30s |
| chat.spec.ts | 5 | ~12s |
| review.spec.ts | 9 | ~53s |
| **总计** | **28** | **~2.7min** |

## 后端单元测试

615 tests, ~63s

## 前端单元测试

231 tests, ~2.5s
