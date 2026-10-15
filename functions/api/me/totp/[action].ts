// 两步验证（TOTP）管理：POST /api/me/totp/<action>
//   setup    → 生成新密钥（未启用状态），返回 { secret, uri }，前端显示二维码 / otpauth 链接
//   enable   { code } → 用当前动态码确认后启用，返回 10 个恢复码（只显示这一次）
//   disable  { code } → 用动态码或恢复码确认后关闭
//   recovery { code } → 用动态码或恢复码确认后重新生成恢复码
import { authEnabled, disabled, err, json, now, rateLimit, readJson, sameOrigin, type AuthEnv } from '../../../_lib/auth/util';
import { getSession } from '../../../_lib/auth/session';
import { checkSecondFactor, decryptSecret, encryptSecret, getFactor, newSecret, otpauthUri, regenerateRecoveryCodes, totpAvailable, verifyTotp } from '../../../_lib/auth/totp';

export const onRequestPost: PagesFunction<AuthEnv> = async ({ request, env, params }) => {
  if (!authEnabled(env)) return disabled();
  if (!totpAvailable(env)) return err(503, 'totp_disabled', '两步验证暂未开放');
  if (!sameOrigin(request)) return err(403, 'bad_origin', '请求来源不正确');
  const { session } = await getSession(env.DB, request);
  if (!session) return err(401, 'login_required', '请先登录');
  const db = env.DB;
  const uid = session.user.id;
  if (!(await rateLimit(db, `totp:${uid}`, 10, 600))) return err(429, 'too_many', '操作太频繁，请 10 分钟后再试');

  const body = (await readJson<{ code?: string }>(request)) || {};
  const code = String(body.code || '').trim();
  const factor = await getFactor(db, uid);

  switch (params.action) {
    case 'setup': {
      if (factor?.enabled_at) return err(400, 'already', '两步验证已经开启');
      const secret = newSecret();
      await db
        .prepare(
          `INSERT INTO totp_factors (user_id, secret_enc, enabled_at, last_step) VALUES (?1, ?2, NULL, NULL)
           ON CONFLICT(user_id) DO UPDATE SET secret_enc = ?2, last_step = NULL WHERE enabled_at IS NULL`,
        )
        .bind(uid, await encryptSecret(env, secret))
        .run();
      return json({ ok: true, secret, uri: otpauthUri(secret, session.user.email) });
    }
    case 'enable': {
      if (!factor) return err(400, 'no_setup', '请先生成密钥');
      if (factor.enabled_at) return err(400, 'already', '两步验证已经开启');
      const step = await verifyTotp(await decryptSecret(env, factor.secret_enc), code.replace(/\s/g, ''), null);
      if (step === null) return err(400, 'wrong_code', '动态码不对。请确认手机时间准确，再输入当前显示的 6 位码');
      await db.prepare('UPDATE totp_factors SET enabled_at = ?1, last_step = ?2 WHERE user_id = ?3').bind(now(), step, uid).run();
      return json({ ok: true, recoveryCodes: await regenerateRecoveryCodes(db, uid) });
    }
    case 'disable': {
      if (!factor?.enabled_at) return err(400, 'not_enabled', '两步验证没有开启');
      if (!(await checkSecondFactor(db, env, uid, code))) return err(400, 'wrong_code', '动态码或恢复码不对');
      await db.batch([db.prepare('DELETE FROM totp_factors WHERE user_id = ?1').bind(uid), db.prepare('DELETE FROM recovery_codes WHERE user_id = ?1').bind(uid)]);
      return json({ ok: true });
    }
    case 'recovery': {
      if (!factor?.enabled_at) return err(400, 'not_enabled', '两步验证没有开启');
      if (!(await checkSecondFactor(db, env, uid, code))) return err(400, 'wrong_code', '动态码或恢复码不对');
      return json({ ok: true, recoveryCodes: await regenerateRecoveryCodes(db, uid) });
    }
    default:
      return err(404, 'not_found', '未知操作');
  }
};
