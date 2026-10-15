// POST /api/pay/checkout → 创建订单，返回支付宝收银台地址
import { authEnabled, disabled, err, json, rateLimit, sameOrigin, type AuthEnv } from '../../_lib/auth/util';
import { getSession, hasEntitlement } from '../../_lib/auth/session';
import { readAttribution } from '../../_lib/auth/attribution';
import { PRODUCT_ID, createOrder, resolvePrice } from '../../_lib/pay/orders';
import { alipayConfigured, createPayUrl, type AlipayEnv } from '../../_lib/pay/alipay';

export const onRequestPost: PagesFunction<AuthEnv & AlipayEnv> = async ({ request, env }) => {
  if (!authEnabled(env)) return disabled();
  if (!alipayConfigured(env)) return err(503, 'pay_disabled', '在线支付暂未开放');
  if (!sameOrigin(request)) return err(403, 'bad_origin', '请求来源不正确');
  const { session } = await getSession(env.DB, request);
  if (!session) return err(401, 'login_required', '请先登录');
  if (!(await rateLimit(env.DB, `checkout:${session.user.id}`, 10, 3600))) return err(429, 'too_many', '下单太频繁，请稍后再试');

  const price = await resolvePrice(env.DB, session.user.id, PRODUCT_ID);
  if (!price) return err(404, 'no_product', '商品未上架');
  if (await hasEntitlement(env.DB, session.user.id, [price.scope])) return err(400, 'owned', '你已经拥有这门课程了');

  const ua = request.headers.get('user-agent') || '';
  const mode = /Mobile|Android|iPhone|iPad/i.test(ua) ? 'wap' : 'page';
  const attr = readAttribution(request);
  const order = await createOrder(env.DB, session.user.id, price, PRODUCT_ID, mode, attr ? JSON.stringify(attr) : null);
  const origin = new URL(request.url).origin;
  const payUrl = await createPayUrl(env, {
    outTradeNo: order.orderNo,
    amount: order.amount,
    subject: `Door4AI Lab · ${price.productName}`,
    notifyUrl: `${origin}/api/pay/alipay/notify`,
    returnUrl: `${origin}/pay/return/?o=${order.orderNo}`,
    mode,
  });
  return json({ ok: true, orderNo: order.orderNo, payUrl });
};
