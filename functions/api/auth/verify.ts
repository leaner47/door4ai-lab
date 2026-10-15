// POST /api/auth/verify  { email, code, next }  → 校验验证码，登录（不存在则注册），建立唯一会话
import { authEnabled, clientIp, disabled, err, json, normEmail, now, rateLimit, readJson, safeEqual, safeNext, sameOrigin, sha256, type AuthEnv } from '../../_lib/auth/util';
import { createSession, findOrCreateUser } from '../../_lib/auth/session';

const MAX_ATTEMPTS = 5;

export const onRequestPost: PagesFunction<AuthEnv> = async ({ request, env }) => {
  if (!authEnabled(env)) return disabled();
  if (!sameOrigin(request)) return err(403, 'bad_origin', '请求来源不正确');
  const body = await readJson<{ email?: string; code?: string; next?: string }>(request);
  const email = normEmail(body?.email);
  const code = typeof body?.code === 'string' ? body.code.replace(/\D/g, '') : '';
  if (!email || code.length !== 6) return err(400, 'bad_input', '请输入邮箱和 6 位验证码');

  const db = env.DB;
  if (!(await rateLimit(db, `verify:ip:${clientIp(request)}`, 30, 3600))) return err(429, 'too_many', '尝试次数过多，请稍后再试');

  const row = await db.prepare('SELECT code_hash, attempts, expires_at FROM otp_codes WHERE email = ?1').bind(email).first<{ code_hash: string; attempts: number; expires_at: number }>();
  if (!row || row.expires_at < now()) return err(400, 'expired', '验证码已过期，请重新获取');
  if (row.attempts >= MAX_ATTEMPTS) return err(400, 'locked', '错误次数太多，请重新获取验证码');

  if (!safeEqual(await sha256(`${email}:${code}`), row.code_hash)) {
    await db.prepare('UPDATE otp_codes SET attempts = attempts + 1 WHERE email = ?1').bind(email).run();
    const left = MAX_ATTEMPTS - row.attempts - 1;
    return err(400, 'wrong_code', left > 0 ? `验证码不对，还可以再试 ${left} 次` : '错误次数太多，请重新获取验证码');
  }
  await db.prepare('DELETE FROM otp_codes WHERE email = ?1').bind(email).run();

  const [user, isNew] = await findOrCreateUser(db, request, email);
  if (user.status !== 'active') return err(403, 'banned', '这个账号已被停用');
  const cookie = await createSession(db, request, user.id, 'email');
  const pk = await db.prepare('SELECT 1 FROM passkeys WHERE user_id = ?1 LIMIT 1').bind(user.id).first();

  return json({ ok: true, isNew, hasPasskey: !!pk, next: safeNext(body?.next) }, 200, { 'set-cookie': cookie });
};
