// /admin 的身份校验：Cloudflare Access 在请求头 Cf-Access-Jwt-Assertion 里带签名 JWT，
// 这里用 Access 公钥验签、核对 aud / iss / exp，再要求邮箱在 ADMIN_EMAILS 里。
// 本地开发（localhost / 127.0.0.1）可设 DEV_ADMIN_EMAIL 跳过 Access：此时要求以该邮箱登录本站账号。
import { fromB64url, type AuthEnv } from './util';
import { getSession, isAdmin } from './session';

type Jwk = JsonWebKey & { kid: string };
let certCache: { at: number; team: string; keys: Jwk[] } | null = null;

async function accessKeys(team: string): Promise<Jwk[]> {
  if (certCache && certCache.team === team && Date.now() - certCache.at < 10 * 60 * 1000) return certCache.keys;
  const r = await fetch(`https://${team}/cdn-cgi/access/certs`);
  if (!r.ok) throw new Error(`access certs ${r.status}`);
  const { keys } = (await r.json()) as { keys: Jwk[] };
  certCache = { at: Date.now(), team, keys };
  return keys;
}

async function verifyAccessJwt(env: AuthEnv, token: string): Promise<string | null> {
  const team = env.ACCESS_TEAM_DOMAIN, aud = env.ACCESS_AUD;
  if (!team || !aud) return null;
  const parts = token.split('.');
  if (parts.length !== 3) return null;
  const dec = (s: string) => JSON.parse(new TextDecoder().decode(fromB64url(s)));
  const header = dec(parts[0]);
  const payload = dec(parts[1]);
  if (header.alg !== 'RS256') return null;
  const jwk = (await accessKeys(team)).find((k) => k.kid === header.kid);
  if (!jwk) return null;
  const key = await crypto.subtle.importKey('jwk', jwk, { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' }, false, ['verify']);
  const ok = await crypto.subtle.verify('RSASSA-PKCS1-v1_5', key, fromB64url(parts[2]), new TextEncoder().encode(`${parts[0]}.${parts[1]}`));
  if (!ok) return null;
  const auds = Array.isArray(payload.aud) ? payload.aud : [payload.aud];
  if (!auds.includes(aud)) return null;
  if (payload.iss !== `https://${team}`) return null;
  if (typeof payload.exp !== 'number' || payload.exp * 1000 < Date.now()) return null;
  return typeof payload.email === 'string' ? payload.email.toLowerCase() : null;
}

export async function adminEmail(env: AuthEnv, request: Request): Promise<string | null> {
  const host = new URL(request.url).hostname;
  if ((host === 'localhost' || host === '127.0.0.1') && env.DEV_ADMIN_EMAIL && env.DB) {
    const { session } = await getSession(env.DB, request);
    const dev = env.DEV_ADMIN_EMAIL.toLowerCase();
    return session?.user.email === dev ? dev : null;
  }
  const token = request.headers.get('cf-access-jwt-assertion');
  if (!token) return null;
  let email: string | null = null;
  try { email = await verifyAccessJwt(env, token); } catch (e) { console.error('access jwt', e); }
  return email && isAdmin(env, email) ? email : null;
}
