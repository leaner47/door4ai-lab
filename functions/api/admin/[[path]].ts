// /api/admin/* —— 后台接口。每个请求都要通过 adminEmail()（Access JWT + ADMIN_EMAILS）。
// 所有写操作记入 audit_log。
import { authEnabled, disabled, err, json, normEmail, now, randomCode, readJson, sameOrigin, ulid, type AuthEnv } from '../../_lib/auth/util';
import { adminEmail } from '../../_lib/auth/admin';
import { POSTS } from '../../_lib/access-map';

const DAY = 86400 * 1000;

const audit = (db: D1Database, actor: string, action: string, target: string, detail: unknown = null) =>
  db.prepare('INSERT INTO audit_log (id, actor, action, target, detail, created_at) VALUES (?1, ?2, ?3, ?4, ?5, ?6)').bind(ulid(), actor, action, target, detail ? JSON.stringify(detail) : null, now());

const validScope = (s: string) =>
  s === 'all' || (s.startsWith('series:') && Object.values(POSTS).some((p) => `series:${p.series}` === s)) || (s.startsWith('post:') && s.slice(5) in POSTS);

// 来源归类：渠道码 > utm_source > 来源网站 > 直接访问
const SOURCE_SQL = `COALESCE(NULLIF(a.ref,''), NULLIF(a.utm_source,''), NULLIF(a.referer_host,''), '直接访问')`;

async function userByEmail(db: D1Database, email: string) {
  return db.prepare('SELECT id, email, status, ref_code, referred_by, created_at FROM users WHERE email = ?1').bind(email).first<any>();
}

async function ensureUser(db: D1Database, email: string) {
  const u = await userByEmail(db, email);
  if (u) return u;
  await db
    .prepare('INSERT INTO users (id, email, status, ref_code, created_at) VALUES (?1, ?2, ?3, ?4, ?5) ON CONFLICT(email) DO NOTHING')
    .bind(ulid(), email, 'active', randomCode(8, 'abcdefghjkmnpqrstuvwxyz23456789'), now())
    .run();
  return userByEmail(db, email);
}

export const onRequest: PagesFunction<AuthEnv> = async ({ request, env, params }) => {
  if (!authEnabled(env)) return disabled();
  const actor = await adminEmail(env, request);
  if (!actor) return err(403, 'forbidden', '没有后台权限');
  const db = env.DB;
  const route = `${request.method} ${((params.path as string[]) || []).join('/')}`;
  const url = new URL(request.url);
  if (request.method !== 'GET' && !sameOrigin(request)) return err(403, 'bad_origin', '请求来源不正确');
  const body = request.method === 'POST' ? (await readJson<any>(request)) || {} : {};

  switch (route) {
    // ---------- 概览 ----------
    case 'GET stats': {
      const t = now();
      const [totals, bySource, bySurvey, daily] = await Promise.all([
        db
          .prepare(
            `SELECT (SELECT count(*) FROM users) AS users,
                    (SELECT count(*) FROM users WHERE created_at > ?1) AS users7,
                    (SELECT count(*) FROM users WHERE created_at > ?2) AS users30,
                    (SELECT count(DISTINCT user_id) FROM entitlements WHERE revoked_at IS NULL AND source = 'order') AS paying,
                    (SELECT count(DISTINCT user_id) FROM entitlements WHERE revoked_at IS NULL AND source = 'grant') AS granted,
                    (SELECT count(*) FROM orders WHERE status = 'paid') AS orders,
                    (SELECT COALESCE(sum(amount),0) FROM orders WHERE status = 'paid') AS revenue,
                    (SELECT count(*) FROM passkeys) AS passkeys`,
          )
          .bind(t - 7 * DAY, t - 30 * DAY)
          .first(),
        db
          .prepare(
            `SELECT ${SOURCE_SQL} AS source, count(DISTINCT a.user_id) AS signups,
                    count(DISTINCT CASE WHEN e.source = 'order' THEN e.user_id END) AS paying
               FROM signup_attribution a
               LEFT JOIN entitlements e ON e.user_id = a.user_id AND e.revoked_at IS NULL
              WHERE a.touch = 'first'
              GROUP BY source ORDER BY signups DESC LIMIT 50`,
          )
          .all(),
        db.prepare(`SELECT survey_answer AS answer, count(*) AS n FROM signup_attribution WHERE touch = 'first' AND survey_answer IS NOT NULL GROUP BY survey_answer ORDER BY n DESC`).all(),
        db
          .prepare(`SELECT date(created_at/1000, 'unixepoch') AS day, count(*) AS n FROM users WHERE created_at > ?1 GROUP BY day ORDER BY day`)
          .bind(t - 30 * DAY)
          .all(),
      ]);
      return json({ totals, bySource: bySource.results, bySurvey: bySurvey.results, daily: daily.results, scopes: ['series:ai-mastery', 'all', ...Object.keys(POSTS).map((s) => `post:${s}`)] });
    }

    // ---------- 用户 ----------
    case 'GET users': {
      const q = (url.searchParams.get('q') || '').trim().toLowerCase();
      const { results } = await db
        .prepare(
          `SELECT u.email, u.status, u.created_at,
                  (SELECT ${SOURCE_SQL} FROM signup_attribution a WHERE a.user_id = u.id AND a.touch = 'first') AS source,
                  (SELECT group_concat(scope, ' ') FROM entitlements e WHERE e.user_id = u.id AND e.revoked_at IS NULL) AS scopes
             FROM users u WHERE u.email LIKE ?1 ORDER BY u.created_at DESC LIMIT 50`,
        )
        .bind(`%${q}%`)
        .all();
      return json({ users: results });
    }
    case 'GET user': {
      const email = normEmail(url.searchParams.get('email'));
      const u = email && (await userByEmail(db, email));
      if (!u) return err(404, 'not_found', '没有这个用户');
      const [attr, ents, sessions, pk, totp, orders, referrer] = await Promise.all([
        db.prepare('SELECT * FROM signup_attribution WHERE user_id = ?1 ORDER BY touch').bind(u.id).all(),
        db.prepare('SELECT id, scope, source, order_id, starts_at, expires_at, revoked_at FROM entitlements WHERE user_id = ?1 ORDER BY starts_at DESC').bind(u.id).all(),
        db.prepare('SELECT auth_method, ua, city, created_at, last_seen_at, revoked_at, revoked_reason FROM sessions WHERE user_id = ?1 ORDER BY created_at DESC LIMIT 10').bind(u.id).all(),
        db.prepare('SELECT count(*) AS n FROM passkeys WHERE user_id = ?1').bind(u.id).first<{ n: number }>(),
        db.prepare('SELECT enabled_at FROM totp_factors WHERE user_id = ?1').bind(u.id).first<{ enabled_at: number | null }>(),
        db.prepare('SELECT order_no, amount, currency, status, created_at, paid_at FROM orders WHERE user_id = ?1 ORDER BY created_at DESC').bind(u.id).all(),
        u.referred_by ? db.prepare('SELECT email FROM users WHERE id = ?1').bind(u.referred_by).first<{ email: string }>() : null,
      ]);
      const day = now() - DAY;
      const switches = sessions.results.filter((s: any) => s.created_at > day).length;
      return json({
        user: { email: u.email, status: u.status, refCode: u.ref_code, createdAt: u.created_at, referredBy: referrer?.email ?? null },
        attribution: attr.results,
        entitlements: ents.results,
        sessions: sessions.results,
        loginsLast24h: switches,
        passkeys: pk?.n ?? 0,
        totpEnabled: !!totp?.enabled_at,
        orders: orders.results,
      });
    }
    case 'POST grant': {
      const email = normEmail(body.email);
      const scope = String(body.scope || '');
      const days = body.days ? Number(body.days) : null;
      if (!email) return err(400, 'bad_email', '邮箱格式不正确');
      if (!validScope(scope)) return err(400, 'bad_scope', '权益范围不正确');
      if (days !== null && !(days > 0 && days <= 3650)) return err(400, 'bad_days', '天数应在 1–3650 之间');
      const u = await ensureUser(db, email);
      const t = now();
      await db.batch([
        db.prepare(`INSERT INTO entitlements (id, user_id, scope, source, starts_at, expires_at) VALUES (?1, ?2, ?3, 'grant', ?4, ?5)`).bind(ulid(), u.id, scope, t, days ? t + days * DAY : null),
        audit(db, actor, 'grant', email, { scope, days }),
      ]);
      return json({ ok: true });
    }
    case 'POST revoke': {
      const id = String(body.id || '');
      const e = await db.prepare('SELECT e.id, e.scope, u.email FROM entitlements e JOIN users u ON u.id = e.user_id WHERE e.id = ?1').bind(id).first<any>();
      if (!e) return err(404, 'not_found', '没有这条权益');
      await db.batch([db.prepare('UPDATE entitlements SET revoked_at = ?1 WHERE id = ?2 AND revoked_at IS NULL').bind(now(), id), audit(db, actor, 'revoke', e.email, { id, scope: e.scope })]);
      return json({ ok: true });
    }
    case 'POST ban': {
      const email = normEmail(body.email);
      const u = email && (await userByEmail(db, email));
      if (!u) return err(404, 'not_found', '没有这个用户');
      const banned = !!body.banned;
      const stmts = [db.prepare('UPDATE users SET status = ?1 WHERE id = ?2').bind(banned ? 'banned' : 'active', u.id), audit(db, actor, banned ? 'ban' : 'unban', email!)];
      if (banned) stmts.push(db.prepare(`UPDATE sessions SET revoked_at = ?1, revoked_reason = 'admin' WHERE user_id = ?2 AND revoked_at IS NULL`).bind(now(), u.id));
      await db.batch(stmts);
      return json({ ok: true });
    }
    case 'POST logout': {
      const email = normEmail(body.email);
      const u = email && (await userByEmail(db, email));
      if (!u) return err(404, 'not_found', '没有这个用户');
      await db.batch([db.prepare(`UPDATE sessions SET revoked_at = ?1, revoked_reason = 'admin' WHERE user_id = ?2 AND revoked_at IS NULL`).bind(now(), u.id), audit(db, actor, 'logout', email!)]);
      return json({ ok: true });
    }
    case 'POST totp-reset': {
      const email = normEmail(body.email);
      const u = email && (await userByEmail(db, email));
      if (!u) return err(404, 'not_found', '没有这个用户');
      await db.batch([
        db.prepare('DELETE FROM totp_factors WHERE user_id = ?1').bind(u.id),
        db.prepare('DELETE FROM recovery_codes WHERE user_id = ?1').bind(u.id),
        audit(db, actor, 'totp-reset', email!),
      ]);
      return json({ ok: true });
    }

    // ---------- 渠道码 ----------
    case 'GET channels': {
      const { results } = await db
        .prepare(
          `SELECT c.code, c.name, c.note, c.created_at,
                  (SELECT count(*) FROM signup_attribution a WHERE a.ref = c.code AND a.touch = 'first') AS first_touch,
                  (SELECT count(*) FROM signup_attribution a WHERE a.ref = c.code AND a.touch = 'last') AS last_touch,
                  (SELECT count(DISTINCT e.user_id) FROM signup_attribution a JOIN entitlements e ON e.user_id = a.user_id
                     WHERE a.ref = c.code AND a.touch = 'first' AND e.source = 'order' AND e.revoked_at IS NULL) AS paying
             FROM channels c ORDER BY c.created_at DESC`,
        )
        .all();
      return json({ channels: results });
    }
    case 'POST channel': {
      const code = String(body.code || '').trim().toLowerCase();
      const name = String(body.name || '').trim().slice(0, 60);
      if (!/^[a-z0-9][a-z0-9-]{1,31}$/.test(code)) return err(400, 'bad_code', '渠道码只能用小写字母、数字和 -，2–32 位');
      if (!name) return err(400, 'bad_name', '请填写渠道名称');
      const clash = await db.prepare('SELECT 1 FROM users WHERE ref_code = ?1').bind(code).first();
      if (clash) return err(400, 'clash', '这个码和某个用户的推荐码重复了，换一个');
      const r = await db.prepare('INSERT INTO channels (code, name, note, created_at) VALUES (?1, ?2, ?3, ?4) ON CONFLICT(code) DO NOTHING').bind(code, name, String(body.note || '').slice(0, 200) || null, now()).run();
      if (!r.meta.changes) return err(400, 'exists', '这个渠道码已存在');
      await audit(db, actor, 'channel', code, { name }).run();
      return json({ ok: true });
    }

    // ---------- 日志 ----------
    case 'GET audit': {
      const { results } = await db.prepare('SELECT actor, action, target, detail, created_at FROM audit_log ORDER BY created_at DESC LIMIT 100').all();
      return json({ audit: results });
    }
    case 'GET whoami':
      return json({ email: actor });
  }
  return err(404, 'not_found', '未知接口');
};
