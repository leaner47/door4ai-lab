// POST /api/pay/alipay/notify —— 支付宝异步通知（服务器到服务器）。
// 验签 → 核对 app_id → 只处理 TRADE_SUCCESS / TRADE_FINISHED → 核对金额 → 幂等开通 → 回复 success。
// 返回非 success 时支付宝会按 4m/10m/10m/1h/2h/6h/15h 重试。
import { authEnabled, now, ulid, type AuthEnv } from '../../../_lib/auth/util';
import { fulfillOrder, yuanToCents } from '../../../_lib/pay/orders';
import { alipayConfigured, verifyNotify, type AlipayEnv } from '../../../_lib/pay/alipay';

const text = (s: string) => new Response(s, { headers: { 'content-type': 'text/plain' } });

export const onRequestPost: PagesFunction<AuthEnv & AlipayEnv> = async ({ request, env }) => {
  if (!authEnabled(env) || !alipayConfigured(env)) return text('failure');
  const raw = await request.text();
  const form: Record<string, string> = {};
  for (const [k, v] of new URLSearchParams(raw)) form[k] = v;

  const ok = await verifyNotify(env, form);
  let result = 'bad_signature';
  if (ok) {
    if (form.app_id !== env.ALIPAY_APP_ID) result = 'wrong_app';
    else if (form.trade_status !== 'TRADE_SUCCESS' && form.trade_status !== 'TRADE_FINISHED') result = `ignored:${form.trade_status}`;
    else result = await fulfillOrder(env.DB, form.out_trade_no, form.trade_no, yuanToCents(form.total_amount), raw);
  }
  await env.DB
    .prepare('INSERT INTO webhook_events (id, provider, signature_ok, body, result, created_at) VALUES (?1, ?2, ?3, ?4, ?5, ?6)')
    .bind(ulid(), 'alipay', ok ? 1 : 0, raw.slice(0, 4000), result, now())
    .run();
  // 验签失败 / 金额不符 / 未知订单：回 failure，留给后台人工处理；其余（含已处理、忽略的状态）回 success
  return text(ok && !['amount_mismatch', 'unknown_order', 'wrong_app'].includes(result) ? 'success' : 'failure');
};
