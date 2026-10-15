// 会话：每个账号同一时间只允许 1 个有效会话，新登录会顶掉旧的。
import { cityOf, clearCookie, cookieName, getCookie, now, randomCode, randomToken, setCookie, sha256, ulid } from './util';
import { persistAttribution, readAttribution } from './attribution';

const SESSION_DAYS = 30;
const SESSION_MS = SESSION_DAYS * 86400 * 1000;
const TOUCH_EVERY_MS = 10 * 60 * 1000; // last_seen / 续期最多 10 分钟写一次

export type User = { id: string; email: string; status: string; ref_code: string; created_at: number };
export type Session = { id: string; user: User; auth_method: string; created_at: number };
export type SessionLookup = { session: Session | null; replaced: boolean };

export async function getSession(db: D1Database, request: Request): Promise<SessionLookup> {
  const token = getCookie(request, cookieName(request, 'sid'));
  if (!token) return { session: null, replaced: false };
  const row = await db
    .prepare(
      `SELECT s.id, s.auth_method, s.created_at, s.expires_at, s.last_seen_at, s.revoked_at, s.revoked_reason,
              u.id AS uid, u.email, u.status, u.ref_code, u.created_at AS ucreated
         FROM sessions s JOIN users u ON u.id = s.user_id
        WHERE s.token_hash = ?1`,
    )
    .bind(await sha256(token))
    .first<any>();
  if (!row) return { session: null, replaced: false };
  if (row.revoked_at) return { session: null, replaced: row.revoked_reason === 'replaced' };
  const t = now();
  if (row.expires_at < t || row.status !== 'active') return { session: null, replaced: false };
  if (t - row.last_seen_at > TOUCH_EVERY_MS) {
    await db.prepare('UPDATE sessions SET last_seen_at = ?1, expires_at = ?2 WHERE id = ?3').bind(t, t + SESSION_MS, row.id).run();
  }
  return {
    replaced: false,
    session: {
      id: row.id,
      auth_method: row.auth_method,
      created_at: row.created_at,
      user: { id: row.uid, email: row.email, status: row.status, ref_code: row.ref_code, created_at: row.ucreated },
    },
  };
}

// 建立新会话：同一个 batch 里先作废该用户其余会话，再插入新会话。
// 返回要写给浏览器的 Set-Cookie。
export async function createSession(db: D1Database, request: Request, userId: string, method: 'email' | 'passkey'): Promise<string> {
  const token = randomToken();
  const t = now();
  await db.batch([
    db.prepare(`UPDATE sessions SET revoked_at = ?1, revoked_reason = 'replaced' WHERE user_id = ?2 AND revoked_at IS NULL`).bind(t, userId),
    db
      .prepare(
        `INSERT INTO sessions (id, user_id, token_hash, auth_method, ua, city, created_at, expires_at, last_seen_at)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?7)`,
      )
      .bind(ulid(), userId, await sha256(token), method, (request.headers.get('user-agent') || '').slice(0, 300), cityOf(request), t, t + SESSION_MS),
  ]);
  return setCookie(request, 'sid', token, SESSION_DAYS * 86400);
}

export async function revokeCurrent(db: D1Database, request: Request): Promise<string> {
  const token = getCookie(request, cookieName(request, 'sid'));
  if (token) {
    await db.prepare(`UPDATE sessions SET revoked_at = ?1, revoked_reason = 'logout' WHERE token_hash = ?2 AND revoked_at IS NULL`).bind(now(), await sha256(token)).run();
  }
  return clearCookie(request, 'sid');
}

// 按邮箱找用户；不存在则创建，并写入注册来源。返回 [user, isNew]。
export async function findOrCreateUser(db: D1Database, request: Request, email: string): Promise<[User, boolean]> {
  const existing = await db.prepare('SELECT id, email, status, ref_code, created_at FROM users WHERE email = ?1').bind(email).first<User>();
  if (existing) return [existing, false];

  const attr = readAttribution(request);
  let referredBy: string | null = null;
  const ref = attr?.l?.ref || attr?.f?.ref;
  if (ref) {
    const r = await db.prepare('SELECT id FROM users WHERE ref_code = ?1').bind(ref).first<{ id: string }>();
    referredBy = r?.id ?? null;
  }
  const user: User = { id: ulid(), email, status: 'active', ref_code: randomCode(8, 'abcdefghjkmnpqrstuvwxyz23456789'), created_at: now() };
  await db
    .prepare('INSERT INTO users (id, email, status, ref_code, referred_by, created_at) VALUES (?1, ?2, ?3, ?4, ?5, ?6) ON CONFLICT(email) DO NOTHING')
    .bind(user.id, user.email, user.status, user.ref_code, referredBy, user.created_at)
    .run();
  // 并发注册时以先写入的为准
  const saved = await db.prepare('SELECT id, email, status, ref_code, created_at FROM users WHERE email = ?1').bind(email).first<User>();
  if (saved && saved.id === user.id) await persistAttribution(db, user.id, attr);
  return [saved ?? user, saved?.id === user.id];
}

// ---------- 权益 ----------
export function isAdmin(env: { ADMIN_EMAILS?: string }, email: string): boolean {
  return (env.ADMIN_EMAILS || '')
    .split(',')
    .map((s) => s.trim().toLowerCase())
    .filter(Boolean)
    .includes(email.toLowerCase());
}

// 需要的范围 needs 形如 ['series:ai-mastery', 'post:attention-qkv']，任一被覆盖即可；'all' 覆盖一切。
export async function hasEntitlement(db: D1Database, userId: string, needs: string[]): Promise<boolean> {
  const scopes = ['all', ...needs];
  const ph = scopes.map((_, i) => `?${i + 3}`).join(',');
  const row = await db
    .prepare(
      `SELECT 1 FROM entitlements
        WHERE user_id = ?1 AND revoked_at IS NULL AND starts_at <= ?2
          AND (expires_at IS NULL OR expires_at > ?2) AND scope IN (${ph}) LIMIT 1`,
    )
    .bind(userId, now(), ...scopes)
    .first();
  return !!row;
}

export async function listEntitlements(db: D1Database, userId: string) {
  const t = now();
  const { results } = await db
    .prepare(
      `SELECT scope, source, starts_at, expires_at FROM entitlements
        WHERE user_id = ?1 AND revoked_at IS NULL AND (expires_at IS NULL OR expires_at > ?2)
        ORDER BY starts_at`,
    )
    .bind(userId, t)
    .all();
  return results;
}
