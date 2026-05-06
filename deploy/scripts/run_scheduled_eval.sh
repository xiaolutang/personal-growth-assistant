#!/usr/bin/env bash
# run_scheduled_eval.sh — 定期评估包装脚本
#
# 封装 run_eval.py 的完整执行流程：
#   健康检查 → 登录获取 token → 执行评估 → 输出摘要
#
# 退出码:
#   0 = 评估通过（通过率 >= 阈值）
#   1 = 评估通过率低于阈值
#   2 = 执行失败（健康检查/登录/评估异常）
#
# 环境变量（必须）:
#   EVAL_USERNAME  — 登录用户名
#   EVAL_PASSWORD  — 登录密码
#
# 用法:
#   EVAL_USERNAME=admin EVAL_PASSWORD=secret ./run_scheduled_eval.sh
#   ./run_scheduled_eval.sh --dry-run
#   ./run_scheduled_eval.sh --threshold 90 --notify /path/to/notify.sh

set -euo pipefail

# ── 默认值 ──

BASE_URL="${BASE_URL:-http://localhost:8000}"
THRESHOLD=80
NOTIFY_CMD=""
DRY_RUN=false
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# ── 参数解析 ──

while [[ $# -gt 0 ]]; do
    case "$1" in
        --base-url)
            BASE_URL="$2"
            shift 2
            ;;
        --threshold)
            THRESHOLD="$2"
            shift 2
            ;;
        --notify)
            NOTIFY_CMD="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            sed -n '2,/^$/p' "$0" | sed 's/^# //; s/^#//'
            exit 0
            ;;
        *)
            echo "[ERROR] 未知参数: $1" >&2
            exit 2
            ;;
    esac
done

# ── 工具函数 ──

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

die() {
    log "ERROR: $*"
    exit 2
}

# ── 前置检查 ──

log "=== 定期评估开始 ==="
log "BASE_URL=$BASE_URL  THRESHOLD=$THRESHOLD%  DRY_RUN=$DRY_RUN"

if [[ -z "${EVAL_USERNAME:-}" ]]; then
    die "环境变量 EVAL_USERNAME 未设置"
fi
if [[ -z "${EVAL_PASSWORD:-}" ]]; then
    die "环境变量 EVAL_PASSWORD 未设置"
fi

# ── Step 1: 健康检查 ──

MAX_RETRIES=3
RETRY_INTERVAL=10

log "健康检查: GET ${BASE_URL}/health"

health_ok=false
for i in $(seq 1 "$MAX_RETRIES"); do
    if curl -sf --max-time 5 "${BASE_URL}/health" > /dev/null 2>&1; then
        health_ok=true
        log "健康检查通过 (第 ${i} 次)"
        break
    fi
    log "健康检查失败 (第 ${i}/${MAX_RETRIES} 次)，${RETRY_INTERVAL}s 后重试..."
    if [[ $i -lt "$MAX_RETRIES" ]]; then
        sleep "$RETRY_INTERVAL"
    fi
done

if [[ "$health_ok" != "true" ]]; then
    die "健康检查失败，服务不可用"
fi

# ── Step 2: 登录验证（仅 dry-run 模式） ──

if [[ "$DRY_RUN" == "true" ]]; then
    log "验证登录: ${EVAL_USERNAME}@${BASE_URL}"

    TOKEN_RESPONSE=$(curl -sf --max-time 10 \
        -X POST \
        -H "Content-Type: application/json" \
        -d "{\"username\": \"${EVAL_USERNAME}\", \"password\": \"${EVAL_PASSWORD}\"}" \
        "${BASE_URL}/auth/login" 2>/dev/null) || die "登录请求失败"

    TOKEN=$(echo "$TOKEN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null) || die "解析登录响应失败"

    if [[ -z "$TOKEN" ]]; then
        die "登录失败：未获取到 access_token"
    fi

    log "登录验证成功"
fi

# ── Step 3: dry-run 模式 ──

if [[ "$DRY_RUN" == "true" ]]; then
    log "[dry-run] 健康检查和登录验证通过，跳过评估执行"
    log "=== dry-run 完成 ==="
    exit 0
fi

# ── Step 4: 执行评估 ──

REPORT_DIR="${PROJECT_ROOT}/data/eval_reports"
mkdir -p "$REPORT_DIR"

log "执行评估: run_eval.py --dataset all"

cd "$PROJECT_ROOT/backend"

EVAL_EXIT_CODE=0
EVAL_OUTPUT=$(uv run python -m tests.eval.run_eval \
    --username "$EVAL_USERNAME" \
    --password "$EVAL_PASSWORD" \
    --dataset all \
    --base-url "$BASE_URL" \
    2>&1) || EVAL_EXIT_CODE=$?

if [[ "$EVAL_EXIT_CODE" -ne 0 ]]; then
    log "评估执行失败 (exit code: ${EVAL_EXIT_CODE})"
    echo "$EVAL_OUTPUT" | tail -20
    if [[ -n "$NOTIFY_CMD" ]]; then
        log "调用通知脚本: $NOTIFY_CMD"
        ($NOTIFY_CMD "eval_failed" "$EVAL_EXIT_CODE" || true)
    fi
    exit 2
fi

# ── Step 5: 解析通过率 ──

PASS_RATE=$(echo "$EVAL_OUTPUT" | grep -oE 'Overall pass rate: [0-9]+(\.[0-9]+)?%' | grep -oE '[0-9]+(\.[0-9]+)?' | head -1 || echo "0")

if [[ -z "$PASS_RATE" ]]; then
    PASS_RATE="0"
fi

PASS_RATE_INT=$(echo "$PASS_RATE" | awk '{printf "%.0f", $1}')

log "评估完成: 通过率 ${PASS_RATE}% (阈值 ${THRESHOLD}%)"

# ── Step 5b: 趋势输出 ──

HISTORY_FILE="${REPORT_DIR}/history.json"
if [[ -f "$HISTORY_FILE" ]]; then
    log "评估趋势:"
    TREND_OUTPUT=$(cd "$PROJECT_ROOT/backend" && uv run python -m tests.eval.eval_trend --history "$HISTORY_FILE" --last 5 2>/dev/null || true)
    if [[ -n "$TREND_OUTPUT" ]]; then
        echo "$TREND_OUTPUT"
    fi
fi

# ── Step 6: 阈值判断 ──

if [[ "$PASS_RATE_INT" -lt "$THRESHOLD" ]]; then
    log "WARN: 通过率 ${PASS_RATE}% 低于阈值 ${THRESHOLD}%"
    if [[ -n "$NOTIFY_CMD" ]]; then
        log "调用通知脚本: $NOTIFY_CMD"
        ($NOTIFY_CMD "below_threshold" "$PASS_RATE" "$THRESHOLD" || true)
    fi
    log "=== 评估结束 (FAIL) ==="
    exit 1
fi

log "=== 评估结束 (PASS) ==="
exit 0
