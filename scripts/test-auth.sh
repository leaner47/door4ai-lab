#!/usr/bin/env bash
# 本地跑账号系统端到端测试：构建 → 临时 wrangler.toml + 本地 D1 → wrangler pages dev → Playwright。
# 用法：bash scripts/test-auth.sh   （截图和日志写到 .wrangler/test-auth/）
# 注意：wrangler.toml 只在测试期间存在，退出时删除——线上绑定以 Cloudflare 控制台为准，仓库里不能有 wrangler.toml。
set -euo pipefail
cd "$(dirname "$0")/.."
OUT=.wrangler/test-auth; mkdir -p "$OUT/shots"
cleanup() { [ -n "${DEV_PID:-}" ] && kill -- "-$DEV_PID" 2>/dev/null; rm -f wrangler.toml; }
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
DEV_ADMIN_EMAIL = "admin@example.com"
TOTP_ENC_KEY = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="
TOML
npm run build >/dev/null
rm -rf .wrangler/state/v3/d1
npx wrangler d1 execute door4ai-lab --local --file migrations/0001_init.sql >/dev/null
if curl -s -o /dev/null http://127.0.0.1:8788/; then echo "8788 端口已被占用，先关掉旧的 wrangler pages dev"; exit 1; fi
setsid npx wrangler pages dev --port 8788 --ip 127.0.0.1 > "$OUT/dev.log" 2>&1 &
DEV_PID=$!
for i in $(seq 1 60); do curl -s -o /dev/null http://127.0.0.1:8788/ && break; sleep 1; done
node scripts/test-auth-e2e.mjs "$OUT/dev.log" "$OUT/shots"
node_modules/.bin/esbuild functions/_lib/auth/admin.ts --bundle --format=esm --platform=neutral --outfile="$OUT/admin.bundle.mjs" --log-level=warning
node scripts/test-admin-jwt.mjs "$PWD/$OUT/admin.bundle.mjs"
