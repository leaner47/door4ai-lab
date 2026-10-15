// POST /api/auth/mfa  { code, next } → 邮箱验证码之后的第二步：TOTP 6 位码或 10 位恢复码
import { authEnabled, disabled, err, json, rateLimit, readJson, safeNext, sameOrigin, type AuthEnv } from '../../_lib/auth/util';
import { createSession } from '../../_lib/auth/session';
import { checkSecondFactor } from '../../_lib/auth/totp';
import { clearMfaCookie, dropMfaTicket, readMfaTicket } from '../../_lib/auth/mfa';

export const onRequestPost: PagesFunction<AuthEnv> = async ({ request, env }) => {
  if (!authEnabled(env)) return disabled();
  if (!sameOrigin(request)) return err(403, 'bad_origin', '请求来源不正确');
  const ticket = await readMfaTicket(env.DB, request);
  if (!ticket) return err(400, 'expired', '验证超时，请重新登录');
  if (!(await rateLimit(env.DB, `mfa:${ticket.id}`, 5, 300))) {
    await dropMfaTicket(env.DB, ticket.id);
    return err(429, 'too_many', '错误次数太多，请重新登录');
  }
  const body = await readJson<{ code?: string; next?: string }>(request);
  const kind = await checkSecondFactor(env.DB, env, ticket.userId, String(body?.code || ''));
  if (!kind) return err(400, 'wrong_code', '动态码或恢复码不对');
  await dropMfaTicket(env.DB, ticket.id);
  const h = new Headers();
  h.append('set-cookie', await createSession(env.DB, request, ticket.userId, 'email'));
  h.append('set-cookie', clearMfaCookie(request));
  return json({ ok: true, usedRecovery: kind === 'recovery', next: safeNext(body?.next) }, 200, h);
};
