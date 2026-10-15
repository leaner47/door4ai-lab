#!/usr/bin/env bash
# 本地跑账号系统端到端测试：构建 → 临时 wrangler.toml + 本地 D1 → wrangler pages dev → Playwright。
# 用法：bash scripts/test-auth.sh   （截图和日志写到 .wrangler/test-auth/）
# 注意：wrangler.toml 只在测试期间存在，退出时删除——线上绑定以 Cloudflare 控制台为准，仓库里不能有 wrangler.toml。
set -euo pipefail
cd "$(dirname "$0")/.."
OUT=.wrangler/test-auth; mkdir -p "$OUT/shots"
cleanup() { [ -n "${DEV_PID:-}" ] && kill -- "-$DEV_PID" 2>/dev/null; [ -n "${MOCK_PID:-}" ] && kill "$MOCK_PID" 2>/dev/null; rm -f wrangler.toml; }
trap cleanup EXIT
# 测试用 RSA 密钥：应用私钥用 PKCS#1（验证 PKCS#1→PKCS#8 转换），支付宝公钥用 SPKI
node -e '
const { generateKeyPairSync } = require("crypto");
const app = generateKeyPairSync("rsa", { modulusLength: 2048 });
const ali = generateKeyPairSync("rsa", { modulusLength: 2048 });
const body = (pem) => pem.replace(/-----[^-]+-----/g, "").replace(/\s+/g, "");
const out = {
  appPrivateB64: body(app.privateKey.export({ type: "pkcs1", format: "pem" })),
  appPublicPem: app.publicKey.export({ type: "spki", format: "pem" }),
  aliPrivatePem: ali.privateKey.export({ type: "pkcs8", format: "pem" }),
  aliPublicB64: body(ali.publicKey.export({ type: "spki", format: "pem" })),
};
require("fs").writeFileSync(process.argv[1], JSON.stringify(out));
' "$OUT/keys.json"
APP_PRIV=$(node -e 'console.log(require(process.argv[1]).appPrivateB64)' "$PWD/$OUT/keys.json")
ALI_PUB=$(node -e 'console.log(require(process.argv[1]).aliPublicB64)' "$PWD/$OUT/keys.json")
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
ALIPAY_APP_ID = "test-app"
ALIPAY_GATEWAY = "http://127.0.0.1:8790/gateway.do"
TOML
printf 'ALIPAY_PRIVATE_KEY = "%s"\nALIPAY_PUBLIC_KEY = "%s"\n' "$APP_PRIV" "$ALI_PUB" >> wrangler.toml
npm run build >/dev/null
rm -rf .wrangler/state/v3/d1
for f in migrations/*.sql; do npx wrangler d1 execute door4ai-lab --local --file "$f" >/dev/null; done
node scripts/mock-alipay.mjs "$OUT/keys.json" 8790 > "$OUT/mock.log" 2>&1 &
MOCK_PID=$!
if curl -s -o /dev/null http://127.0.0.1:8788/; then echo "8788 端口已被占用，先关掉旧的 wrangler pages dev"; exit 1; fi
setsid npx wrangler pages dev --port 8788 --ip 127.0.0.1 > "$OUT/dev.log" 2>&1 &
DEV_PID=$!
for i in $(seq 1 60); do curl -s -o /dev/null http://127.0.0.1:8788/ && break; sleep 1; done
[ -n "${SKIP_AUTH:-}" ] || node scripts/test-auth-e2e.mjs "$OUT/dev.log" "$OUT/shots"
node_modules/.bin/esbuild functions/_lib/auth/admin.ts --bundle --format=esm --platform=neutral --outfile="$OUT/admin.bundle.mjs" --log-level=warning
node scripts/test-admin-jwt.mjs "$PWD/$OUT/admin.bundle.mjs"
node scripts/test-pay-e2e.mjs "$OUT/dev.log" "$OUT/shots" "$OUT/keys.json"
