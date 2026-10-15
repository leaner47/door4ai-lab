// TOTP（RFC 6238，6 位、30 秒、SHA-1——Apple 密码、Google Authenticator 等都支持）+ 恢复码。
// 密钥要能还原才能算码，所以用 AES-GCM 加密后存库，加密密钥放 Pages Secret：TOTP_ENC_KEY（base64 的 32 字节）。
import { b64url, fromB64url, now, randomCode, safeEqual, sha256 } from './util';

export type TotpEnv = { TOTP_ENC_KEY?: string };
export const totpAvailable = (env: TotpEnv) => !!env.TOTP_ENC_KEY;

const STEP = 30;
const B32 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
const ISSUER = 'Door4AI Lab';

export function base32Encode(bytes: Uint8Array): string {
  let bits = 0, value = 0, out = '';
  for (const b of bytes) {
    value = (value << 8) | b; bits += 8;
    while (bits >= 5) { out += B32[(value >>> (bits - 5)) & 31]; bits -= 5; }
  }
  if (bits > 0) out += B32[(value << (5 - bits)) & 31];
  return out;
}

export function base32Decode(s: string): Uint8Array<ArrayBuffer> {
  const clean = s.toUpperCase().replace(/[^A-Z2-7]/g, '');
  const out: number[] = [];
  let bits = 0, value = 0;
  for (const c of clean) {
    value = (value << 5) | B32.indexOf(c); bits += 5;
    if (bits >= 8) { out.push((value >>> (bits - 8)) & 255); bits -= 8; }
  }
  return new Uint8Array(out);
}

export const newSecret = () => base32Encode(crypto.getRandomValues(new Uint8Array(20)));

export function otpauthUri(secret: string, email: string): string {
  const label = encodeURIComponent(`${ISSUER}:${email}`);
  return `otpauth://totp/${label}?secret=${secret}&issuer=${encodeURIComponent(ISSUER)}&algorithm=SHA1&digits=6&period=${STEP}`;
}

async function hotp(secret: string, counter: number): Promise<string> {
  const key = await crypto.subtle.importKey('raw', base32Decode(secret), { name: 'HMAC', hash: 'SHA-1' }, false, ['sign']);
  const msg = new ArrayBuffer(8);
  const view = new DataView(msg);
  view.setUint32(0, Math.floor(counter / 2 ** 32));
  view.setUint32(4, counter >>> 0);
  const mac = new Uint8Array(await crypto.subtle.sign('HMAC', key, msg));
  const off = mac[mac.length - 1] & 15;
  const bin = ((mac[off] & 0x7f) << 24) | (mac[off + 1] << 16) | (mac[off + 2] << 8) | mac[off + 3];
  return String(bin % 1_000_000).padStart(6, '0');
}

export const currentStep = (t = now()) => Math.floor(t / 1000 / STEP);

// 允许前后各 1 个时间步（±30 秒）的时钟误差；返回匹配的时间步，失败返回 null。
// lastStep：上次成功使用的时间步，不允许 <= 它（防重放）。
export async function verifyTotp(secret: string, code: string, lastStep: number | null): Promise<number | null> {
  if (!/^\d{6}$/.test(code)) return null;
  const s = currentStep();
  for (const step of [s - 1, s, s + 1]) {
    if (lastStep !== null && step <= lastStep) continue;
    if (safeEqual(await hotp(secret, step), code)) return step;
  }
  return null;
}

// 测试用：算出某个时间步的码
export const totpAt = (secret: string, step: number) => hotp(secret, step);

// ---------- 加密存储 ----------
async function encKey(env: TotpEnv): Promise<CryptoKey> {
  const raw = Uint8Array.from(atob(env.TOTP_ENC_KEY!), (c) => c.charCodeAt(0));
  if (raw.length !== 32) throw new Error('TOTP_ENC_KEY must be 32 bytes (base64)');
  return crypto.subtle.importKey('raw', raw, 'AES-GCM', false, ['encrypt', 'decrypt']);
}

export async function encryptSecret(env: TotpEnv, secret: string): Promise<string> {
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const ct = await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, await encKey(env), new TextEncoder().encode(secret));
  return `${b64url(iv)}.${b64url(ct)}`;
}

export async function decryptSecret(env: TotpEnv, enc: string): Promise<string> {
  const [iv, ct] = enc.split('.');
  const pt = await crypto.subtle.decrypt({ name: 'AES-GCM', iv: fromB64url(iv) }, await encKey(env), fromB64url(ct));
  return new TextDecoder().decode(pt);
}

// ---------- 数据库操作 ----------
export type Factor = { secret_enc: string; enabled_at: number | null; last_step: number | null };

export const getFactor = (db: D1Database, userId: string) =>
  db.prepare('SELECT secret_enc, enabled_at, last_step FROM totp_factors WHERE user_id = ?1').bind(userId).first<Factor>();

export async function totpEnabled(db: D1Database, userId: string): Promise<boolean> {
  const f = await getFactor(db, userId);
  return !!f?.enabled_at;
}

// 校验 TOTP 码或恢复码（二选一）。成功时更新 last_step / 标记恢复码已用。
export async function checkSecondFactor(db: D1Database, env: TotpEnv, userId: string, input: string): Promise<'totp' | 'recovery' | null> {
  const f = await getFactor(db, userId);
  if (!f?.enabled_at) return null;
  const code = input.replace(/\s|-/g, '');
  if (/^\d{6}$/.test(code)) {
    const step = await verifyTotp(await decryptSecret(env, f.secret_enc), code, f.last_step);
    if (step === null) return null;
    const r = await db.prepare('UPDATE totp_factors SET last_step = ?1 WHERE user_id = ?2 AND (last_step IS NULL OR last_step < ?1)').bind(step, userId).run();
    return r.meta.changes ? 'totp' : null;
  }
  if (/^[a-z0-9]{10}$/i.test(code)) {
    const hash = await sha256(`${userId}:${code.toLowerCase()}`);
    const r = await db.prepare('UPDATE recovery_codes SET used_at = ?1 WHERE user_id = ?2 AND code_hash = ?3 AND used_at IS NULL').bind(now(), userId, hash).run();
    return r.meta.changes ? 'recovery' : null;
  }
  return null;
}

// 生成 10 个新恢复码（旧的全部作废），返回明文，只展示这一次
export async function regenerateRecoveryCodes(db: D1Database, userId: string): Promise<string[]> {
  const codes = Array.from({ length: 10 }, () => randomCode(10, 'abcdefghjkmnpqrstuvwxyz23456789'));
  const hashes = await Promise.all(codes.map((c) => sha256(`${userId}:${c}`)));
  await db.batch([
    db.prepare('DELETE FROM recovery_codes WHERE user_id = ?1').bind(userId),
    ...hashes.map((h) => db.prepare('INSERT INTO recovery_codes (user_id, code_hash) VALUES (?1, ?2)').bind(userId, h)),
  ]);
  return codes;
}

export async function recoveryLeft(db: D1Database, userId: string): Promise<number> {
  const r = await db.prepare('SELECT count(*) AS n FROM recovery_codes WHERE user_id = ?1 AND used_at IS NULL').bind(userId).first<{ n: number }>();
  return r?.n ?? 0;
}

