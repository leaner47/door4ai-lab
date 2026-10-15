// GET /api/pay/order?o=<订单号> → 订单状态。待支付超过 10 秒时主动向支付宝查单（防止异步通知丢失）。
import { authEnabled, disabled, err, json, now, type AuthEnv } from '../../_lib/auth/util';
import { getSession } from '../../_lib/auth/session';
import { fulfillOrder, yuanToCents } from '../../_lib/pay/orders';
import { alipayConfigured, queryTrade, type AlipayEnv } from '../../_lib/pay/alipay';

export const onRequestGet: PagesFunction<AuthEnv & AlipayEnv> = async ({ request, env }) => {
  if (!authEnabled(env)) return disabled();
  const { session } = await getSession(env.DB, request);
  if (!session) return err(401, 'login_required', '请先登录');
  const orderNo = new URL(request.url).searchParams.get('o') || '';
  const o = await env.DB.prepare('SELECT order_no, user_id, amount, status, created_at FROM orders WHERE order_no = ?1').bind(orderNo).first<any>();
  if (!o || o.user_id !== session.user.id) return err(404, 'not_found', '没有这个订单');

  let status = o.status as string;
  if (status === 'pending' && alipayConfigured(env) && now() - o.created_at > 10_000) {
    try {
      const q = await queryTrade(env, orderNo);
      if (q.code === '10000' && (q.trade_status === 'TRADE_SUCCESS' || q.trade_status === 'TRADE_FINISHED')) {
        const r = await fulfillOrder(env.DB, orderNo, q.trade_no || '', yuanToCents(q.total_amount), JSON.stringify(q));
        if (r === 'ok' || r === 'already') status = 'paid';
      } else if (q.code === '10000' && q.trade_status === 'TRADE_CLOSED') {
        await env.DB.prepare(`UPDATE orders SET status = 'expired' WHERE order_no = ?1 AND status = 'pending'`).bind(orderNo).run();
        status = 'expired';
      }
    } catch (e) {
      console.error('alipay query', e);
    }
  }
  return json({ ok: true, orderNo, status, amount: o.amount });
};
