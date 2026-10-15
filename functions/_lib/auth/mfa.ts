// 邮箱验证码已通过、但账号开了两步验证时，先发一张 5 分钟有效的「待验证」票据，
// 输入 TOTP 或恢复码后才建立会话。票据存在 webauthn_challenges 表（kind = 'mfa'）。
import { clearCookie, cookieName, getCookie, now, setCookie, ulid } from './util';

const TTL_SEC = 300;

export async function issueMfaTicket(db: D1Database, request: Request, userId: string): Promise<string> {
  const id = ulid();
  await db.prepare(`INSERT INTO webauthn_challenges (id, user_id, kind, challenge, expires_at) VALUES (?1, ?2, 'mfa', '', ?3)`).bind(id, userId, now() + TTL_SEC * 1000).run();
  return setCookie(request, 'mfa', id, TTL_SEC);
}

export async function readMfaTicket(db: D1Database, request: Request): Promise<{ id: string; userId: string } | null> {
  const id = getCookie(request, cookieName(request, 'mfa'));
  if (!id) return null;
  const row = await db.prepare(`SELECT user_id, expires_at FROM webauthn_challenges WHERE id = ?1 AND kind = 'mfa'`).bind(id).first<{ user_id: string; expires_at: number }>();
  if (!row || row.expires_at < now()) return null;
  return { id, userId: row.user_id };
}

export const dropMfaTicket = (db: D1Database, id: string) => db.prepare('DELETE FROM webauthn_challenges WHERE id = ?1').bind(id).run();
export const clearMfaCookie = (request: Request) => clearCookie(request, 'mfa');
