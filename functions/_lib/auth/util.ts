// 账号系统的公共工具：环境变量、ID、哈希、Cookie、JSON 响应、限流。

export type AuthEnv = {
  DB?: D1Database;
  AUTH_ENABLED?: string;        // '1' 才启用自建账号与门禁；否则全站沿用 Cloudflare Access
  RESEND_API_KEY?: string;      // 发验证码邮件
  MAIL_FROM?: string;           // 例：Door4AI Lab <login@door4ai.com>
  TURNSTILE_SITE_KEY?: string;
  TURNSTILE_SECRET?: string;
  ADMIN_EMAILS?: string;        // 逗号分隔；这些邮箱视为拥有全部权益
  DEV_MAIL_LOG?: string;        // '1' 时验证码打印到日志而不发邮件（仅本地开发）
  TOTP_ENC_KEY?: string;        // base64 的 32 字节；用来加密存储 TOTP 密钥。未设置则不提供两步验证
  ACCESS_TEAM_DOMAIN?: string;  // 例：xxx.cloudflareaccess.com（/admin 校验 Access JWT 用）
  ACCESS_AUD?: string;          // /admin 所在 Access 应用的 Application Audience (AUD) Tag
  DEV_ADMIN_EMAIL?: string;     // 仅 localhost 生效：本地开发时跳过 Access，直接当作这个管理员
};

export const authEnabled = (env: AuthEnv): env is AuthEnv & { DB: D1Database } =>
  env.AUTH_ENABLED === '1' && !!env.DB;

export const now = () => Date.now();

// ---------- ID ----------
const B32 = '0123456789ABCDEFGHJKMNPQRSTVWXYZ';
export function ulid(t = Date.now()): string {
  let ts = '';
  for (let i = 0; i < 10; i++) { ts = B32[t % 32] + ts; t = Math.floor(t / 32); }
  const r = crypto.getRandomValues(new Uint8Array(16));
  let rand = '';
  for (let i = 0; i < 16; i++) rand += B32[r[i] % 32];
  return ts + rand;
}

export function randomCode(len: number, alphabet = '0123456789'): string {
  // 拒绝采样，避免取模偏差
  const out: string[] = [];
  const max = 256 - (256 % alphabet.length);
  while (out.length < len) {
    for (const b of crypto.getRandomValues(new Uint8Array(len * 2))) {
      if (b < max && out.length < len) out.push(alphabet[b % alphabet.length]);
    }
  }
  return out.join('');
}

export function randomToken(bytes = 32): string {
  return b64url(crypto.getRandomValues(new Uint8Array(bytes)));
}

export function b64url(buf: ArrayBuffer | Uint8Array): string {
  const u = buf instanceof Uint8Array ? buf : new Uint8Array(buf);
  let s = '';
  for (const b of u) s += String.fromCharCode(b);
  return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

export function fromB64url(s: string): Uint8Array<ArrayBuffer> {
  const pad = s.replace(/-/g, '+').replace(/_/g, '/') + '==='.slice((s.length + 3) % 4);
  const bin = atob(pad);
  const u = new Uint8Array(new ArrayBuffer(bin.length));
  for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
  return u;
}

export async function sha256(s: string): Promise<string> {
  const d = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s));
  return [...new Uint8Array(d)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

export function safeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let r = 0;
  for (let i = 0; i < a.length; i++) r |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return r === 0;
}

// ---------- 请求 / 响应 ----------
export function json(data: unknown, status = 200, headers: HeadersInit = {}): Response {
  const h = new Headers(headers);
  h.set('content-type', 'application/json; charset=utf-8');
  h.set('cache-control', 'no-store');
  return new Response(JSON.stringify(data), { status, headers: h });
}

export const err = (status: number, code: string, message: string, extra: Record<string, unknown> = {}) =>
  json({ ok: false, code, message, ...extra }, status);

export const disabled = () => err(503, 'auth_disabled', '账号系统尚未启用');

// 写操作只接受本站发起的请求（防 CSRF，配合 SameSite=Lax）
export function sameOrigin(request: Request): boolean {
  const origin = request.headers.get('origin');
  if (!origin) return false;
  return origin === new URL(request.url).origin;
}

export async function readJson<T = any>(request: Request): Promise<T | null> {
  try { return (await request.json()) as T; } catch { return null; }
}

export function normEmail(raw: unknown): string | null {
  if (typeof raw !== 'string') return null;
  const e = raw.trim().toLowerCase();
  if (e.length > 254 || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e)) return null;
  return e;
}

// 只允许站内路径作为登录后的跳转目标
export function safeNext(raw: string | null | undefined): string {
  if (!raw || !raw.startsWith('/') || raw.startsWith('//') || raw.includes('\\')) return '/ai/';
  return raw;
}

export function clientIp(request: Request): string {
  return request.headers.get('cf-connecting-ip') || '0.0.0.0';
}

export function cityOf(request: Request): string | null {
  const cf = (request as any).cf;
  return cf?.city ? String(cf.city) : null;
}

// ---------- Cookie ----------
export function getCookie(request: Request, name: string): string | null {
  const raw = request.headers.get('cookie');
  if (!raw) return null;
  for (const part of raw.split(';')) {
    const i = part.indexOf('=');
    if (i < 0) continue;
    if (part.slice(0, i).trim() === name) return decodeURIComponent(part.slice(i + 1).trim());
  }
  return null;
}

// __Host- 前缀要求 Secure + Path=/ + 无 Domain；本地 http 开发时浏览器会拒收，
// 所以在 http 下退回不带前缀的名字。
export function cookieName(request: Request, base: string): string {
  return new URL(request.url).protocol === 'https:' ? `__Host-${base}` : base;
}

export function setCookie(request: Request, base: string, value: string, maxAgeSec: number, httpOnly = true): string {
  const https = new URL(request.url).protocol === 'https:';
  const parts = [`${cookieName(request, base)}=${encodeURIComponent(value)}`, 'Path=/', 'SameSite=Lax', `Max-Age=${maxAgeSec}`];
  if (https) parts.push('Secure');
  if (httpOnly) parts.push('HttpOnly');
  return parts.join('; ');
}

export const clearCookie = (request: Request, base: string) => setCookie(request, base, '', 0);

// ---------- 限流（固定窗口，计数存 D1） ----------
export async function rateLimit(db: D1Database, key: string, limit: number, windowSec: number): Promise<boolean> {
  const t = now();
  const windowStart = t - (t % (windowSec * 1000));
  const k = `${key}:${windowSec}`;
  const row = await db
    .prepare(
      `INSERT INTO rate_limits (key, window_start, count) VALUES (?1, ?2, 1)
       ON CONFLICT(key) DO UPDATE SET
         count = CASE WHEN window_start = ?2 THEN count + 1 ELSE 1 END,
         window_start = ?2
       RETURNING count`,
    )
    .bind(k, windowStart)
    .first<{ count: number }>();
  return (row?.count ?? 1) <= limit;
}
