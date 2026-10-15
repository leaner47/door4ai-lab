// DELETE /api/me/passkeys/<credential id> → 移除自己的一个 Passkey
import { authEnabled, disabled, err, json, sameOrigin, type AuthEnv } from '../../../_lib/auth/util';
import { getSession } from '../../../_lib/auth/session';

export const onRequestDelete: PagesFunction<AuthEnv> = async ({ request, env, params }) => {
  if (!authEnabled(env)) return disabled();
  if (!sameOrigin(request)) return err(403, 'bad_origin', '请求来源不正确');
  const { session } = await getSession(env.DB, request);
  if (!session) return err(401, 'login_required', '请先登录');
  const r = await env.DB.prepare('DELETE FROM passkeys WHERE id = ?1 AND user_id = ?2').bind(String(params.id), session.user.id).run();
  if (!r.meta.changes) return err(404, 'not_found', '没有找到这个 Passkey');
  return json({ ok: true });
};
