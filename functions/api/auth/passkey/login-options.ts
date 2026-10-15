// POST /api/auth/passkey/login-options → 生成登录挑战（不指定账号，由浏览器列出本站的 Passkey）
import { generateAuthenticationOptions } from '@simplewebauthn/server';
import { authEnabled, clientIp, disabled, err, json, rateLimit, sameOrigin, type AuthEnv } from '../../../_lib/auth/util';
import { rp, saveChallenge } from '../../../_lib/auth/webauthn';

export const onRequestPost: PagesFunction<AuthEnv> = async ({ request, env }) => {
  if (!authEnabled(env)) return disabled();
  if (!sameOrigin(request)) return err(403, 'bad_origin', '请求来源不正确');
  if (!(await rateLimit(env.DB, `pk:ip:${clientIp(request)}`, 60, 3600))) return err(429, 'too_many', '请求过多，请稍后再试');
  const options = await generateAuthenticationOptions({ rpID: rp(request).rpID, userVerification: 'preferred' });
  const cookie = await saveChallenge(env.DB, request, 'login', options.challenge, null);
  return json(options, 200, { 'set-cookie': cookie });
};
