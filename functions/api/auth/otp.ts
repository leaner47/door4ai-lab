// POST /api/auth/otp  { email, turnstile }  → 发送 6 位登录验证码
import { authEnabled, clientIp, disabled, err, json, normEmail, now, randomCode, rateLimit, readJson, sameOrigin, sha256, type AuthEnv } from '../../_lib/auth/util';
import { verifyTurnstile } from '../../_lib/auth/turnstile';
import { sendLoginCode } from '../../_lib/auth/mail';

const CODE_TTL_MS = 10 * 60 * 1000;

export const onRequestPost: PagesFunction<AuthEnv> = async ({ request, env }) => {
  if (!authEnabled(env)) return disabled();
  if (!sameOrigin(request)) return err(403, 'bad_origin', '请求来源不正确');
  const body = await readJson<{ email?: string; turnstile?: string }>(request);
  const email = normEmail(body?.email);
  if (!email) return err(400, 'bad_email', '邮箱格式不正确');

  const ip = clientIp(request);
  if (!(await verifyTurnstile(env, body?.turnstile, ip))) return err(400, 'turnstile', '人机校验没有通过，请刷新重试');

  const db = env.DB;
  if (!(await rateLimit(db, `otp:email:${email}`, 1, 60))) return err(429, 'too_fast', '发送太频繁，请 60 秒后再试');
  if (!(await rateLimit(db, `otp:email:${email}`, 5, 3600))) return err(429, 'too_many', '这个邮箱 1 小时内发送次数已达上限');
  if (!(await rateLimit(db, `otp:ip:${ip}`, 20, 3600))) return err(429, 'too_many', '请求过多，请稍后再试');

  const code = randomCode(6);
  await db
    .prepare(
      `INSERT INTO otp_codes (email, code_hash, attempts, expires_at) VALUES (?1, ?2, 0, ?3)
       ON CONFLICT(email) DO UPDATE SET code_hash = ?2, attempts = 0, expires_at = ?3`,
    )
    .bind(email, await sha256(`${email}:${code}`), now() + CODE_TTL_MS)
    .run();

  const sent = await sendLoginCode(env, email, code);
  if (!sent.ok) {
    console.error('send code failed', sent.error);
    return err(502, 'mail_failed', '验证码邮件发送失败，请稍后再试');
  }
  return json({ ok: true });
};
