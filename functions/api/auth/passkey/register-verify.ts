// POST /api/auth/passkey/register-verify  { response } → 校验并保存新 Passkey
import { verifyRegistrationResponse } from '@simplewebauthn/server';
import { authEnabled, b64url, disabled, err, json, now, readJson, sameOrigin, type AuthEnv } from '../../../_lib/auth/util';
import { getSession } from '../../../_lib/auth/session';
import { clearChallengeCookie, guessDeviceName, rp, takeChallenge } from '../../../_lib/auth/webauthn';

export const onRequestPost: PagesFunction<AuthEnv> = async ({ request, env }) => {
  if (!authEnabled(env)) return disabled();
  if (!sameOrigin(request)) return err(403, 'bad_origin', '请求来源不正确');
  const { session } = await getSession(env.DB, request);
  if (!session) return err(401, 'login_required', '请先登录');

  const body = await readJson<{ response?: any }>(request);
  const ch = await takeChallenge(env.DB, request, 'register');
  if (!ch || ch.userId !== session.user.id || !body?.response) return err(400, 'challenge', '操作超时，请重试');

  const { rpID, origin } = rp(request);
  let verification;
  try {
    verification = await verifyRegistrationResponse({ response: body.response, expectedChallenge: ch.challenge, expectedOrigin: origin, expectedRPID: rpID, requireUserVerification: false });
  } catch (e: any) {
    return err(400, 'verify_failed', `Passkey 校验失败：${e?.message || e}`);
  }
  if (!verification.verified || !verification.registrationInfo) return err(400, 'verify_failed', 'Passkey 校验失败');

  const { credential, credentialBackedUp } = verification.registrationInfo;
  await env.DB
    .prepare(
      `INSERT INTO passkeys (id, user_id, public_key, sign_count, transports, device_name, backed_up, created_at)
       VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8) ON CONFLICT(id) DO NOTHING`,
    )
    .bind(
      credential.id,
      session.user.id,
      b64url(credential.publicKey),
      credential.counter,
      credential.transports ? JSON.stringify(credential.transports) : null,
      guessDeviceName(request.headers.get('user-agent')),
      credentialBackedUp ? 1 : 0,
      now(),
    )
    .run();
  return json({ ok: true }, 200, { 'set-cookie': clearChallengeCookie(request) });
};
