// GET /api/pay/price → 当前用户能看到的价格（按首次触达渠道），以及是否已拥有
import { authEnabled, disabled, json, type AuthEnv } from '../../_lib/auth/util';
import { getSession, hasEntitlement, isAdmin } from '../../_lib/auth/session';
import { PRODUCT_ID, resolvePrice } from '../../_lib/pay/orders';
import { alipayConfigured, type AlipayEnv } from '../../_lib/pay/alipay';
import { readAttribution } from '../../_lib/auth/attribution';

export const onRequestGet: PagesFunction<AuthEnv & AlipayEnv> = async ({ request, env }) => {
  if (!authEnabled(env)) return disabled();
  const { session } = await getSession(env.DB, request);
  const price = await resolvePrice(env.DB, session?.user.id ?? null, PRODUCT_ID, readAttribution(request)?.f?.ref ?? null);
  if (!price) return json({ ok: false, message: '商品未上架' }, 404);
  const owned = session ? isAdmin(env, session.user.email) || (await hasEntitlement(env.DB, session.user.id, [price.scope])) : false;
  return json({
    ok: true,
    product: PRODUCT_ID,
    name: price.productName,
    amount: price.amount,
    currency: price.currency,
    loggedIn: !!session,
    owned,
    payReady: alipayConfigured(env),
  });
};
