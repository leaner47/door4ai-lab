-- 第 1 期：支付宝买断 + 按渠道定价
-- 应用：npx wrangler d1 execute door4ai-lab --remote --file migrations/0002_payments.sql
--      （或在 D1 控制台 Console 执行去掉注释后的单行版本）

-- 价格可按渠道码区分：channel_code 为空 = 默认价；否则 = 该渠道（首次触达 ref）的专属价
ALTER TABLE prices ADD COLUMN channel_code TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS prices_product_channel ON prices(product_id, COALESCE(channel_code, ''));

-- 订单补充字段
ALTER TABLE orders ADD COLUMN product_id TEXT;
ALTER TABLE orders ADD COLUMN channel_code TEXT;     -- 定价依据的渠道码（快照）
ALTER TABLE orders ADD COLUMN provider TEXT;         -- alipay
ALTER TABLE orders ADD COLUMN pay_mode TEXT;         -- page（电脑）| wap（手机）
ALTER TABLE orders ADD COLUMN trade_no TEXT;         -- 支付宝交易号
ALTER TABLE orders ADD COLUMN refunded_at INTEGER;
ALTER TABLE orders ADD COLUMN refund_amount INTEGER;

-- 一个订单最多产生一条权益（回调重复、对账补单都不会重复开通）
CREATE UNIQUE INDEX IF NOT EXISTS entitlements_order ON entitlements(order_id) WHERE order_id IS NOT NULL;

-- 商品：AI 从入门到精通（全套，含以后新增的讲）
INSERT OR IGNORE INTO products (id, name, scope, active) VALUES ('ai-mastery', 'AI 从入门到精通（全套）', 'series:ai-mastery', 1);
-- 默认价 399 元（单位：分），后台可改
INSERT OR IGNORE INTO prices (id, product_id, amount, currency, active, channel_code) VALUES ('ai-mastery@default', 'ai-mastery', 39900, 'CNY', 1, NULL);
