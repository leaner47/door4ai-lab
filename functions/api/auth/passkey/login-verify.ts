// POST /api/auth/passkey/login-verify  { response, next } → 用 Passkey 登录，建立唯一会话
import { verifyAuthenticationResponse } from '@simplewebauthn/server';
import { authEnabled, disabled, err, fromB64url, json, now, readJson, safeNext, sameOrigin, type AuthEnv } from '../../../_lib/auth/util';
import { createSession } from '../../../_lib/auth/session';
import { clearChallengeCookie, rp, takeChallenge } from '../../../_lib/auth/webauthn';

export const onRequestPost: PagesFunction<AuthEnv> = async ({ request, env }) => {
  if (!authEnabled(env)) return disabled();
  if (!sameOrigin(request)) return err(403, 'bad_origin', '请求来源不正确');
  const body = await readJson<{ response?: any; next?: string }>(request);
  const ch = await takeChallenge(env.DB, request, 'login');
  if (!ch || !body?.response?.id) return err(400, 'challenge', '操作超时，请重试');

  const pk = await env.DB
    .prepare(
      `SELECT p.id, p.user_id, p.public_key, p.sign_count, p.transports, u.status
         FROM passkeys p JOIN users u ON u.id = p.user_id WHERE p.id = ?1`,
    )
    .bind(String(body.response.id))
    .first<{ id: string; user_id: string; public_key: string; sign_count: number; transports: string | null; status: string }>();
  if (!pk) return err(400, 'unknown_passkey', '这个 Passkey 没有绑定本站账号，请先用邮箱验证码登录');

  const { rpID, origin } = rp(request);
  let verification;
  try {
    verification = await verifyAuthenticationResponse({
      response: body.response,
      expectedChallenge: ch.challenge,
      expectedOrigin: origin,
      expectedRPID: rpID,
      requireUserVerification: false,
      credential: { id: pk.id, publicKey: fromB64url(pk.public_key), counter: pk.sign_count, transports: pk.transports ? JSON.parse(pk.transports) : undefined },
    });
  } catch (e: any) {
    return err(400, 'verify_failed', `Passkey 校验失败：${e?.message || e}`);
  }
  if (!verification.verified) return err(400, 'verify_failed', 'Passkey 校验失败');
  if (pk.status !== 'active') return err(403, 'banned', '这个账号已被停用');

  await env.DB.prepare('UPDATE passkeys SET sign_count = ?1, last_used_at = ?2 WHERE id = ?3').bind(verification.authenticationInfo.newCounter, now(), pk.id).run();
  const cookie = await createSession(env.DB, request, pk.user_id, 'passkey');
  const h = new Headers();
  h.append('set-cookie', cookie);
  h.append('set-cookie', clearChallengeCookie(request));
  return json({ ok: true, next: safeNext(body.next) }, 200, h);
};
