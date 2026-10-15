-- Door4AI Lab 账号与支付：初始表结构（D1 / SQLite）
-- 应用：npx wrangler d1 execute door4ai-lab --remote --file migrations/0001_init.sql
-- 约定：金额为整数「分」；时间为 UTC 毫秒时间戳；id 为 ULID 文本。

CREATE TABLE IF NOT EXISTS users (
  id          TEXT PRIMARY KEY,
  email       TEXT NOT NULL UNIQUE,
  status      TEXT NOT NULL DEFAULT 'active',      -- active | banned
  ref_code    TEXT NOT NULL UNIQUE,                -- 本人的推荐码
  referred_by TEXT,                                -- 推荐人 user id
  created_at  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS passkeys (
  id           TEXT PRIMARY KEY,                   -- credential id (base64url)
  user_id      TEXT NOT NULL REFERENCES users(id),
  public_key   TEXT NOT NULL,                      -- base64url
  sign_count   INTEGER NOT NULL DEFAULT 0,
  transports   TEXT,                               -- JSON array
  device_name  TEXT,
  backed_up    INTEGER NOT NULL DEFAULT 0,
  created_at   INTEGER NOT NULL,
  last_used_at INTEGER
);
CREATE INDEX IF NOT EXISTS passkeys_user ON passkeys(user_id);

CREATE TABLE IF NOT EXISTS totp_factors (
  user_id    TEXT PRIMARY KEY REFERENCES users(id),
  secret_enc TEXT NOT NULL,                        -- AES-GCM 加密后的密钥
  enabled_at INTEGER,
  last_step  INTEGER
);

CREATE TABLE IF NOT EXISTS recovery_codes (
  user_id   TEXT NOT NULL REFERENCES users(id),
  code_hash TEXT NOT NULL,
  used_at   INTEGER
);
CREATE INDEX IF NOT EXISTS recovery_user ON recovery_codes(user_id);

-- 每个账号同一时间只有一条有效会话；被新登录顶掉的会话标 revoked_reason = 'replaced'
CREATE TABLE IF NOT EXISTS sessions (
  id             TEXT PRIMARY KEY,
  user_id        TEXT NOT NULL REFERENCES users(id),
  token_hash     TEXT NOT NULL UNIQUE,
  auth_method    TEXT NOT NULL,                    -- email | passkey
  ua             TEXT,
  city           TEXT,
  created_at     INTEGER NOT NULL,
  expires_at     INTEGER NOT NULL,
  last_seen_at   INTEGER NOT NULL,
  revoked_at     INTEGER,
  revoked_reason TEXT                              -- logout | replaced | admin
);
CREATE INDEX IF NOT EXISTS sessions_user ON sessions(user_id, revoked_at);

CREATE TABLE IF NOT EXISTS otp_codes (
  email      TEXT PRIMARY KEY,                     -- 每个邮箱只保留最新一条
  code_hash  TEXT NOT NULL,
  attempts   INTEGER NOT NULL DEFAULT 0,
  expires_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS webauthn_challenges (
  id         TEXT PRIMARY KEY,
  user_id    TEXT,                                 -- 注册时有；登录时为空
  kind       TEXT NOT NULL,                        -- register | login
  challenge  TEXT NOT NULL,
  expires_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS rate_limits (
  key          TEXT PRIMARY KEY,                   -- 例：otp:email:x@y.com:60
  window_start INTEGER NOT NULL,
  count        INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS signup_attribution (
  user_id       TEXT NOT NULL REFERENCES users(id),
  touch         TEXT NOT NULL,                     -- first | last
  utm_source    TEXT,
  utm_medium    TEXT,
  utm_campaign  TEXT,
  ref           TEXT,
  referer_host  TEXT,
  landing_path  TEXT,
  survey_answer TEXT,
  at            INTEGER NOT NULL,
  PRIMARY KEY (user_id, touch)
);
CREATE INDEX IF NOT EXISTS attribution_source ON signup_attribution(utm_source);

CREATE TABLE IF NOT EXISTS channels (
  code       TEXT PRIMARY KEY,                     -- 例：xhs-01
  name       TEXT NOT NULL,
  note       TEXT,
  created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
  id     TEXT PRIMARY KEY,
  name   TEXT NOT NULL,
  scope  TEXT NOT NULL,                            -- all | series:<name> | post:<slug>
  active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS prices (
  id         TEXT PRIMARY KEY,
  product_id TEXT NOT NULL REFERENCES products(id),
  amount     INTEGER NOT NULL,
  currency   TEXT NOT NULL DEFAULT 'CNY',
  active     INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS orders (
  id         TEXT PRIMARY KEY,
  order_no   TEXT NOT NULL UNIQUE,
  user_id    TEXT NOT NULL REFERENCES users(id),
  price_id   TEXT NOT NULL REFERENCES prices(id),
  amount     INTEGER NOT NULL,
  currency   TEXT NOT NULL,
  status     TEXT NOT NULL DEFAULT 'pending',      -- pending | paid | expired | refunded
  source     TEXT,                                 -- 下单时的来源快照（JSON）
  created_at INTEGER NOT NULL,
  paid_at    INTEGER
);
CREATE INDEX IF NOT EXISTS orders_user ON orders(user_id);
CREATE INDEX IF NOT EXISTS orders_status ON orders(status, created_at);

CREATE TABLE IF NOT EXISTS payments (
  id                TEXT PRIMARY KEY,
  order_id          TEXT NOT NULL REFERENCES orders(id),
  provider          TEXT NOT NULL,
  provider_trade_no TEXT NOT NULL,
  amount            INTEGER NOT NULL,
  raw               TEXT,
  created_at        INTEGER NOT NULL,
  UNIQUE (provider, provider_trade_no)
);

CREATE TABLE IF NOT EXISTS entitlements (
  id         TEXT PRIMARY KEY,
  user_id    TEXT NOT NULL REFERENCES users(id),
  scope      TEXT NOT NULL,                        -- all | series:<name> | post:<slug>
  source     TEXT NOT NULL,                        -- order | grant
  order_id   TEXT,
  starts_at  INTEGER NOT NULL,
  expires_at INTEGER,                              -- 买断为空；赠送可设到期
  revoked_at INTEGER
);
CREATE INDEX IF NOT EXISTS entitlements_user ON entitlements(user_id, scope);

CREATE TABLE IF NOT EXISTS webhook_events (
  id           TEXT PRIMARY KEY,
  provider     TEXT NOT NULL,
  signature_ok INTEGER NOT NULL,
  body         TEXT,
  result       TEXT,
  created_at   INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
  id         TEXT PRIMARY KEY,
  actor      TEXT NOT NULL,
  action     TEXT NOT NULL,
  target     TEXT,
  detail     TEXT,
  created_at INTEGER NOT NULL
);
