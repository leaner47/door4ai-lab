// POST /api/me/survey  { answer } → 记录「你从哪里知道我们的」（只记一次）
import { authEnabled, disabled, err, json, now, readJson, sameOrigin, type AuthEnv } from '../../_lib/auth/util';
import { getSession } from '../../_lib/auth/session';

export const onRequestPost: PagesFunction<AuthEnv> = async ({ request, env }) => {
  if (!authEnabled(env)) return disabled();
  if (!sameOrigin(request)) return err(403, 'bad_origin', '请求来源不正确');
  const { session } = await getSession(env.DB, request);
  if (!session) return err(401, 'login_required', '请先登录');
  const body = await readJson<{ answer?: string }>(request);
  const answer = typeof body?.answer === 'string' ? body.answer.trim().slice(0, 80) : '';
  if (!answer) return err(400, 'empty', '请选择或填写一个来源');
  await env.DB
    .prepare(
      `INSERT INTO signup_attribution (user_id, touch, survey_answer, at) VALUES (?1, 'first', ?2, ?3)
       ON CONFLICT(user_id, touch) DO UPDATE SET survey_answer = COALESCE(survey_answer, ?2)`,
    )
    .bind(session.user.id, answer, now())
    .run();
  return json({ ok: true });
};
