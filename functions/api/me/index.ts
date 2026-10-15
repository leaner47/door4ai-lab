// GET /api/me → 当前登录状态（导航栏、我的账号页用）
import { authEnabled, json, type AuthEnv } from '../../_lib/auth/util';
import { getSession, isAdmin, listEntitlements } from '../../_lib/auth/session';
import { recoveryLeft, totpAvailable, totpEnabled } from '../../_lib/auth/totp';

export const onRequestGet: PagesFunction<AuthEnv> = async ({ request, env }) => {
  if (!authEnabled(env)) return json({ enabled: false });
  const { session, replaced } = await getSession(env.DB, request);
  if (!session) return json({ enabled: true, user: null, replaced });

  const u = session.user;
  const [entitlements, pk, survey, totpOn, recLeft] = await Promise.all([
    listEntitlements(env.DB, u.id),
    env.DB.prepare('SELECT id, device_name, backed_up, created_at, last_used_at FROM passkeys WHERE user_id = ?1 ORDER BY created_at').bind(u.id).all(),
    env.DB.prepare(`SELECT survey_answer FROM signup_attribution WHERE user_id = ?1 AND touch = 'first'`).bind(u.id).first<{ survey_answer: string | null }>(),
    totpEnabled(env.DB, u.id),
    recoveryLeft(env.DB, u.id),
  ]);
  return json({
    enabled: true,
    user: { email: u.email, refCode: u.ref_code, createdAt: u.created_at },
    admin: isAdmin(env, u.email),
    authMethod: session.auth_method,
    entitlements,
    passkeys: pk.results,
    surveyAnswered: !!survey?.survey_answer,
    totp: { available: totpAvailable(env), enabled: totpOn, recoveryLeft: recLeft },
  });
};
