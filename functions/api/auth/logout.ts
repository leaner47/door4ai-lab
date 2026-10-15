// POST /api/auth/logout
import { authEnabled, disabled, err, json, sameOrigin, type AuthEnv } from '../../_lib/auth/util';
import { revokeCurrent } from '../../_lib/auth/session';

export const onRequestPost: PagesFunction<AuthEnv> = async ({ request, env }) => {
  if (!authEnabled(env)) return disabled();
  if (!sameOrigin(request)) return err(403, 'bad_origin', '请求来源不正确');
  const cookie = await revokeCurrent(env.DB, request);
  return json({ ok: true }, 200, { 'set-cookie': cookie });
};
