#!/bin/bash
# 设置 Git hooks
# 运行方式: ./scripts/setup-hooks.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🔗 设置 Git hooks..."

# 创建软链接（强制覆盖）
ln -sf ../../scripts/hooks/pre-commit "$PROJECT_ROOT/.git/hooks/pre-commit"
chmod +x "$PROJECT_ROOT/.git/hooks/pre-commit"

echo "✅ Git hooks 设置完成"
echo "   - pre-commit: 提交前运行测试和构建"
