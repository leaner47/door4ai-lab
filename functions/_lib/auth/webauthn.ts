// Passkey（WebAuthn）挑战值的存取。挑战存在 D1，浏览器只拿一个 5 分钟的 Cookie 指向它。
import { clearCookie, cookieName, getCookie, now, setCookie, ulid } from './util';

const CHALLENGE_TTL_SEC = 300;

export const rp = (request: Request) => {
  const url = new URL(request.url);
  return { rpID: url.hostname, origin: url.origin, rpName: 'Door4AI Lab' };
};

export async function saveChallenge(db: D1Database, request: Request, kind: 'register' | 'login', challenge: string, userId: string | null): Promise<string> {
  const id = ulid();
  const t = now();
  await db.batch([
    db.prepare('DELETE FROM webauthn_challenges WHERE expires_at < ?1').bind(t),
    db.prepare('INSERT INTO webauthn_challenges (id, user_id, kind, challenge, expires_at) VALUES (?1, ?2, ?3, ?4, ?5)').bind(id, userId, kind, challenge, t + CHALLENGE_TTL_SEC * 1000),
  ]);
  return setCookie(request, 'wac', id, CHALLENGE_TTL_SEC);
}

// 取出并删除（一次性）
export async function takeChallenge(db: D1Database, request: Request, kind: 'register' | 'login'): Promise<{ challenge: string; userId: string | null } | null> {
  const id = getCookie(request, cookieName(request, 'wac'));
  if (!id) return null;
  const row = await db
    .prepare('DELETE FROM webauthn_challenges WHERE id = ?1 AND kind = ?2 RETURNING challenge, user_id, expires_at')
    .bind(id, kind)
    .first<{ challenge: string; user_id: string | null; expires_at: number }>();
  if (!row || row.expires_at < now()) return null;
  return { challenge: row.challenge, userId: row.user_id };
}

export const clearChallengeCookie = (request: Request) => clearCookie(request, 'wac');

// 从 User-Agent 粗略猜一个设备名，方便用户在「我的账号」里认出是哪台设备
export function guessDeviceName(ua: string | null): string {
  if (!ua) return '未知设备';
  if (/iPhone/.test(ua)) return 'iPhone';
  if (/iPad/.test(ua)) return 'iPad';
  if (/Macintosh/.test(ua)) return 'Mac';
  if (/Android/.test(ua)) return 'Android';
  if (/Windows/.test(ua)) return 'Windows';
  if (/Linux/.test(ua)) return 'Linux';
  return '其他设备';
}
