#!/usr/bin/env bash
# 本地跑账号系统端到端测试：构建 → 临时 wrangler.toml + 本地 D1 → wrangler pages dev → Playwright。
# 用法：bash scripts/test-auth.sh   （截图和日志写到 .wrangler/test-auth/）
# 注意：wrangler.toml 只在测试期间存在，退出时删除——线上绑定以 Cloudflare 控制台为准，仓库里不能有 wrangler.toml。
set -euo pipefail
cd "$(dirname "$0")/.."
OUT=.wrangler/test-auth; mkdir -p "$OUT/shots"
cleanup() { [ -n "${DEV_PID:-}" ] && kill "$DEV_PID" 2>/dev/null; pkill -P "${DEV_PID:-0}" 2>/dev/null || true; rm -f wrangler.toml; }
trap cleanup EXIT
cat > wrangler.toml <<'TOML'
name = "door4ai-lab"
pages_build_output_dir = "dist"
compatibility_date = "2026-10-01"
[[d1_databases]]
binding = "DB"
database_name = "door4ai-lab"
database_id = "00000000-0000-0000-0000-000000000000"
[vars]
AUTH_ENABLED = "1"
DEV_MAIL_LOG = "1"
ADMIN_EMAILS = "admin@example.com"
TOML
npm run build >/dev/null
rm -rf .wrangler/state/v3/d1
npx wrangler d1 execute door4ai-lab --local --file migrations/0001_init.sql >/dev/null
npx wrangler pages dev --port 8788 --ip 127.0.0.1 > "$OUT/dev.log" 2>&1 &
DEV_PID=$!
for i in $(seq 1 60); do curl -s -o /dev/null http://127.0.0.1:8788/ && break; sleep 1; done
node scripts/test-auth-e2e.mjs "$OUT/dev.log" "$OUT/shots"
