// POST /api/auth/passkey/register-options → 为已登录用户生成创建 Passkey 的参数
import { generateRegistrationOptions } from '@simplewebauthn/server';
import { authEnabled, disabled, err, json, sameOrigin, type AuthEnv } from '../../../_lib/auth/util';
import { getSession } from '../../../_lib/auth/session';
import { rp, saveChallenge } from '../../../_lib/auth/webauthn';

export const onRequestPost: PagesFunction<AuthEnv> = async ({ request, env }) => {
  if (!authEnabled(env)) return disabled();
  if (!sameOrigin(request)) return err(403, 'bad_origin', '请求来源不正确');
  const { session } = await getSession(env.DB, request);
  if (!session) return err(401, 'login_required', '请先登录');

  const { results } = await env.DB.prepare('SELECT id, transports FROM passkeys WHERE user_id = ?1').bind(session.user.id).all<{ id: string; transports: string | null }>();
  const { rpID, rpName } = rp(request);
  const options = await generateRegistrationOptions({
    rpName,
    rpID,
    userName: session.user.email,
    userDisplayName: session.user.email,
    userID: new Uint8Array(new TextEncoder().encode(session.user.id)),
    attestationType: 'none',
    excludeCredentials: results.map((c) => ({ id: c.id, transports: c.transports ? JSON.parse(c.transports) : undefined })),
    authenticatorSelection: { residentKey: 'required', userVerification: 'preferred' },
  });
  const cookie = await saveChallenge(env.DB, request, 'register', options.challenge, session.user.id);
  return json(options, 200, { 'set-cookie': cookie });
};
