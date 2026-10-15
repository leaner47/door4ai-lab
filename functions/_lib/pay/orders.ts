// 订单与定价。价格按用户「首次触达」的渠道码（ref）决定，注册后固定，避免事后换便宜链接。
import { now, randomCode, ulid } from '../auth/util';

export const PRODUCT_ID = 'ai-mastery';

export type ResolvedPrice = { priceId: string; amount: number; currency: string; channelCode: string | null; productName: string; scope: string };

// anonRef：未登录访客用其来源 Cookie 里的首次触达 ref 预估价格（只用于展示，下单时一律以数据库为准）
export async function resolvePrice(db: D1Database, userId: string | null, productId = PRODUCT_ID, anonRef: string | null = null): Promise<ResolvedPrice | null> {
  let ref: string | null = userId ? null : anonRef;
  if (userId) {
    const a = await db.prepare(`SELECT ref FROM signup_attribution WHERE user_id = ?1 AND touch = 'first'`).bind(userId).first<{ ref: string | null }>();
    ref = a?.ref || null;
  }
  const row = await db
    .prepare(
      `SELECT pr.id, pr.amount, pr.currency, pr.channel_code, p.name, p.scope
         FROM prices pr JOIN products p ON p.id = pr.product_id
        WHERE pr.product_id = ?1 AND pr.active = 1 AND p.active = 1
          AND (pr.channel_code = ?2 OR pr.channel_code IS NULL)
        ORDER BY pr.channel_code IS NULL LIMIT 1`,
    )
    .bind(productId, ref)
    .first<any>();
  if (!row) return null;
  return { priceId: row.id, amount: row.amount, currency: row.currency, channelCode: row.channel_code, productName: row.name, scope: row.scope };
}

// 订单号：LAB + 北京时间到秒 + 6 位随机，≤ 64 字符，支付宝 out_trade_no 要求
export function newOrderNo(t = Date.now()): string {
  const d = new Date(t + 8 * 3600 * 1000).toISOString().replace(/\D/g, '').slice(0, 14);
  return `LAB${d}${randomCode(6, '0123456789ABCDEFGHJKLMNPQRSTUVWXYZ')}`;
}

export async function createOrder(db: D1Database, userId: string, price: ResolvedPrice, productId: string, payMode: 'page' | 'wap', sourceSnapshot: string | null) {
  const order = { id: ulid(), orderNo: newOrderNo(), amount: price.amount, currency: price.currency };
  await db
    .prepare(
      `INSERT INTO orders (id, order_no, user_id, price_id, amount, currency, status, source, created_at, product_id, channel_code, provider, pay_mode)
       VALUES (?1, ?2, ?3, ?4, ?5, ?6, 'pending', ?7, ?8, ?9, ?10, 'alipay', ?11)`,
    )
    .bind(order.id, order.orderNo, userId, price.priceId, price.amount, price.currency, sourceSnapshot, now(), productId, price.channelCode, payMode)
    .run();
  return order;
}

export type FulfillResult = 'ok' | 'already' | 'unknown_order' | 'amount_mismatch' | 'refunded';

// 确认到账并开通。幂等：重复回调 / 查单补单都只会开通一次（payments 唯一键 + entitlements(order_id) 唯一索引）。
export async function fulfillOrder(db: D1Database, orderNo: string, tradeNo: string, paidCents: number, raw: string): Promise<FulfillResult> {
  const o = await db.prepare('SELECT id, amount, status FROM orders WHERE order_no = ?1').bind(orderNo).first<{ id: string; amount: number; status: string }>();
  if (!o) return 'unknown_order';
  if (o.amount !== paidCents) return 'amount_mismatch';
  if (o.status === 'refunded') return 'refunded';
  if (o.status === 'paid') return 'already';
  const t = now();
  await db.batch([
    db.prepare(`UPDATE orders SET status = 'paid', paid_at = ?1, trade_no = ?2 WHERE id = ?3 AND status IN ('pending', 'expired')`).bind(t, tradeNo, o.id),
    db.prepare(`INSERT OR IGNORE INTO payments (id, order_id, provider, provider_trade_no, amount, raw, created_at) VALUES (?1, ?2, 'alipay', ?3, ?4, ?5, ?6)`).bind(ulid(), o.id, tradeNo, paidCents, raw.slice(0, 4000), t),
    db
      .prepare(
        `INSERT OR IGNORE INTO entitlements (id, user_id, scope, source, order_id, starts_at)
         SELECT ?1, o.user_id, p.scope, 'order', o.id, ?2
           FROM orders o JOIN products p ON p.id = o.product_id
          WHERE o.id = ?3 AND o.status = 'paid'`,
      )
      .bind(ulid(), t, o.id),
  ]);
  return 'ok';
}

// 支付宝的元字符串 → 分（避免浮点误差）
export function yuanToCents(s: string | undefined): number {
  if (!s || !/^\d+(\.\d{1,2})?$/.test(s)) return -1;
  const [a, b = ''] = s.split('.');
  return Number(a) * 100 + Number((b + '00').slice(0, 2));
}
